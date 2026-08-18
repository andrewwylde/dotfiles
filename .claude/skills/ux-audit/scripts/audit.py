#!/usr/bin/env python3
"""
UX Audit data collector.

Visits a URL with Playwright, captures screenshots at multiple viewports,
measures performance, runs axe-core accessibility scans, and tests keyboard
navigation. Outputs a JSON report + screenshots for Claude to analyze.

Usage: python audit.py <url> <output_dir>
"""

import json
import sys
import time
from pathlib import Path


def capture_performance(page):
    """Get performance metrics from the Performance API."""
    return page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        const paint = performance.getEntriesByType('paint');
        const fcp = paint.find(p => p.name === 'first-contentful-paint');
        const resources = performance.getEntriesByType('resource');

        return {
            ttfb_ms: nav ? Math.round(nav.responseStart) : null,
            fcp_ms: fcp ? Math.round(fcp.startTime) : null,
            dom_content_loaded_ms: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
            load_time_ms: nav ? Math.round(nav.loadEventEnd) : null,
            dom_interactive_ms: nav ? Math.round(nav.domInteractive) : null,
            resource_count: resources.length,
            total_transfer_bytes: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0)
        };
    }""")


def capture_page_info(page):
    """Get basic page structure information."""
    return page.evaluate("""() => {
        const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
            .map(h => ({ level: h.tagName, text: h.textContent.trim().substring(0, 80) }));
        const imgs = document.querySelectorAll('img');
        const noAlt = document.querySelectorAll('img:not([alt])');

        return {
            title: document.title,
            lang: document.documentElement.lang || null,
            meta_viewport: document.querySelector('meta[name="viewport"]')?.content || null,
            headings: headings,
            link_count: document.querySelectorAll('a').length,
            button_count: document.querySelectorAll('button, [role="button"], input[type="submit"]').length,
            form_count: document.querySelectorAll('form').length,
            image_count: imgs.length,
            images_without_alt: noAlt.length
        };
    }""")


def run_axe_core(page):
    """Inject axe-core and run an accessibility scan."""
    try:
        return page.evaluate("""async () => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js';
            document.head.appendChild(script);
            await new Promise((resolve, reject) => {
                script.onload = resolve;
                script.onerror = reject;
                setTimeout(reject, 10000);
            });

            const results = await axe.run();
            return {
                violations: results.violations.map(v => ({
                    id: v.id,
                    impact: v.impact,
                    description: v.description,
                    help: v.help,
                    help_url: v.helpUrl,
                    nodes_count: v.nodes.length,
                    nodes: v.nodes.slice(0, 5).map(n => ({
                        html: n.html.substring(0, 200),
                        target: n.target,
                        failure_summary: n.failureSummary
                    }))
                })),
                passes_count: results.passes.length,
                violations_count: results.violations.length,
                incomplete_count: results.incomplete.length
            };
        }""")
    except Exception as e:
        return {"error": str(e)}


def test_keyboard_nav(page, screenshots_dir):
    """Tab through focusable elements and check focus visibility."""
    focus_screenshots = {}

    # Click body to reset focus
    page.evaluate("document.body.focus()")

    focusable_elements = []
    visible_count = 0
    not_visible_count = 0
    seen = set()
    repeats = 0
    tab_trap = False

    for i in range(20):
        page.keyboard.press("Tab")
        page.wait_for_timeout(100)

        focused = page.evaluate("""() => {
            const el = document.activeElement;
            if (!el || el === document.body) return null;

            const rect = el.getBoundingClientRect();
            const styles = window.getComputedStyle(el);
            const hasOutline = styles.outlineStyle !== 'none' && styles.outlineWidth !== '0px';
            const hasBoxShadow = styles.boxShadow && styles.boxShadow !== 'none';

            return {
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role'),
                text: (el.textContent || el.getAttribute('aria-label') || '').trim().substring(0, 60),
                type: el.getAttribute('type'),
                in_viewport: rect.top >= 0 && rect.top < window.innerHeight,
                has_visible_focus: hasOutline || hasBoxShadow,
                outline: styles.outlineStyle + ' ' + styles.outlineWidth + ' ' + styles.outlineColor,
                selector: el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '')
            };
        }""")

        if not focused:
            continue

        key = focused["selector"] + "|" + focused["text"]
        if key in seen:
            repeats += 1
            if repeats >= 3:
                tab_trap = True
                break
        else:
            repeats = 0
            seen.add(key)

        focusable_elements.append(focused)
        if focused["has_visible_focus"]:
            visible_count += 1
        else:
            not_visible_count += 1

        # Screenshot first 3 focused elements
        if i < 3:
            path = screenshots_dir / f"focus_{i}.png"
            page.screenshot(path=str(path), full_page=False)
            focus_screenshots[f"focus_{i}"] = f"screenshots/focus_{i}.png"

    return {
        "focusable_elements": focusable_elements,
        "focus_visible_count": visible_count,
        "focus_not_visible_count": not_visible_count,
        "tab_trap_detected": tab_trap,
    }, focus_screenshots


def check_mobile(page):
    """Mobile-specific checks: tap target sizes, horizontal scroll."""
    return page.evaluate("""() => {
        const interactive = document.querySelectorAll(
            'a, button, input, select, textarea, [role="button"]'
        );
        const undersized = [];
        let too_small = 0;

        interactive.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && (rect.width < 44 || rect.height < 44)) {
                too_small++;
                if (undersized.length < 10) {
                    undersized.push({
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 40),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    });
                }
            }
        });

        return {
            undersized_tap_targets: too_small,
            examples: undersized,
            has_horizontal_scroll: document.documentElement.scrollWidth > window.innerWidth
        };
    }""")


def run_audit(url, output_dir):
    from playwright.sync_api import sync_playwright

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    screenshots_dir = output_path / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    results = {
        "url": url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "performance": {},
        "accessibility": {},
        "keyboard_nav": {},
        "console_errors": [],
        "console_warnings": [],
        "page_info": {},
        "mobile": {},
        "screenshots": {},
    }

    console_messages = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- Desktop (primary audit) ---
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type, "text": msg.text
        }))

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            results["load_error"] = str(e)

        results["performance"] = capture_performance(page)
        results["page_info"] = capture_page_info(page)

        # Full-page + viewport-only screenshots
        page.screenshot(path=str(screenshots_dir / "desktop_full.png"), full_page=True)
        page.screenshot(path=str(screenshots_dir / "desktop_viewport.png"), full_page=False)
        results["screenshots"]["desktop_full"] = "screenshots/desktop_full.png"
        results["screenshots"]["desktop_viewport"] = "screenshots/desktop_viewport.png"

        # Accessibility scan
        results["accessibility"] = run_axe_core(page)

        # Keyboard navigation
        kb_results, focus_shots = test_keyboard_nav(page, screenshots_dir)
        results["keyboard_nav"] = kb_results
        results["screenshots"].update(focus_shots)

        ctx.close()

        # --- Tablet ---
        ctx = browser.new_context(viewport={"width": 768, "height": 1024})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(screenshots_dir / "tablet.png"), full_page=True)
            results["screenshots"]["tablet"] = "screenshots/tablet.png"
        except Exception as e:
            results["tablet_error"] = str(e)
        ctx.close()

        # --- Mobile ---
        ctx = browser.new_context(
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            has_touch=True,
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=str(screenshots_dir / "mobile.png"), full_page=True)
            results["screenshots"]["mobile"] = "screenshots/mobile.png"
            results["mobile"] = check_mobile(page)
        except Exception as e:
            results["mobile_error"] = str(e)
        ctx.close()

        browser.close()

    # Separate errors from warnings
    results["console_errors"] = [m for m in console_messages if m["type"] == "error"]
    results["console_warnings"] = [m for m in console_messages if m["type"] == "warning"]

    # Write report
    report_path = output_path / "audit_results.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    a11y = results.get("accessibility", {})
    kb = results.get("keyboard_nav", {})
    print(f"Audit complete: {url}")
    print(f"  Screenshots: {len(results['screenshots'])}")
    print(f"  A11y violations: {a11y.get('violations_count', 'N/A')}")
    print(f"  Keyboard focus visible: {kb.get('focus_visible_count', '?')}/{kb.get('focus_visible_count', 0) + kb.get('focus_not_visible_count', 0)}")
    print(f"  Console errors: {len(results['console_errors'])}")
    print(f"  Results: {report_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python audit.py <url> <output_dir>")
        print("Example: python audit.py https://example.com /tmp/ux-audit-output")
        sys.exit(1)

    run_audit(sys.argv[1], sys.argv[2])
