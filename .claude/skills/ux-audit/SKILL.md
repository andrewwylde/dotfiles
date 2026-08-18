---
name: ux-audit
description: Run a live UX audit on any web page using Playwright browser automation. Visits the actual URL, captures screenshots across viewports, measures performance, tests keyboard navigation, runs accessibility scans, and produces a graded markdown report with actionable fixes. Use this skill whenever the user wants to audit UX, review user experience, test usability of a page, check how a site feels to use, or mentions "UX audit", "usability review", "UX review", "how does my site feel", or "test the UX". Also use when they share a URL and want feedback on the experience — not just the code. Do NOT use for pure code review (use web-quality-audit), pure accessibility compliance (use web-accessibility), or SEO.
---

# UX Audit

Evaluate the real user experience of a live web page by actually visiting it in a browser — not just reading the source code. This produces a graded report covering interaction patterns, performance perception, and accessibility.

## Why browser automation matters

Reading source code tells you what *should* happen. Visiting the page tells you what *actually* happens — layout shifts you can see, focus rings that are invisible, tap targets that are too small on mobile, loading states that feel sluggish. This skill bridges that gap.

## What this audits

| Category | What we check |
|----------|--------------|
| **Interaction patterns** | Button/link discoverability, navigation clarity, form usability, feedback on actions, error states, hover/active states, touch targets |
| **Performance perception** | How fast the page *feels* — first paint timing, layout stability, loading indicators, resource weight |
| **Accessibility** | Keyboard navigation, focus visibility, axe-core violations, color contrast, semantic structure, screen reader compatibility |

## Workflow

### Step 1: Confirm the target and scope

Get the URL from the user. If they're working on a local project, check if a dev server is already running (look for common ports: 3000, 5173, 8080, 4321). If not, help them start one.

Ask if there are specific pages or flows they care about most. A homepage audit is the default, but a good audit should cover **at least 2-3 key pages** when possible:

- **Homepage/landing** — first impression, navigation, above-fold content
- **A key user flow** — login, signup, checkout, search results, or whatever the app's core action is
- **A content-heavy page** — settings, dashboard, listing page — wherever users spend time

The reason to go beyond the homepage: critical issues often hide in authenticated pages or secondary flows. A site can have a polished marketing page but a broken login form. If the user only gives you one URL, audit it — but proactively suggest checking related pages if time allows.

### Step 2: Run the data collection script

Ensure Playwright is available:

```bash
pip show playwright > /dev/null 2>&1 || pip install playwright
python -m playwright install chromium 2>/dev/null
```

Then run the audit collector. The script path is relative to this skill:

```bash
python <skill-dir>/scripts/audit.py <url> /tmp/ux-audit-output
```

This captures:
- **Screenshots** at desktop (1440px), tablet (768px), and mobile (375px) viewports
- **Performance metrics** via the Performance API (FCP, TTFB, load time, resource count)
- **Accessibility violations** via axe-core injection
- **Keyboard navigation data** — tabs through the first 20 focusable elements, checks for visible focus indicators and tab traps
- **Console errors and warnings**
- **Mobile-specific data** — undersized tap targets, horizontal scroll detection
- **Focus state screenshots** — first 3 focused elements

All results go to `/tmp/ux-audit-output/audit_results.json` with screenshots in `/tmp/ux-audit-output/screenshots/`.

### Step 3: Analyze the results

Read `audit_results.json` and all screenshots. This is where your visual analysis matters most — the automated data gives you numbers, but the screenshots reveal the actual experience.

Read `references/heuristics.md` for the detailed evaluation criteria. For each category, work through the checklist:

**Interaction patterns** — Look at the screenshots. Are buttons obviously clickable? Is navigation clear? Are there loading indicators? Do interactive elements have hover/active states? On mobile, are touch targets large enough?

**Performance perception** — Check the metrics. FCP under 1.8s is good, under 1s is excellent. Look at the above-fold screenshot — does it load meaningful content quickly? Is there layout shift (CLS)? How many resources are loaded and how heavy are they?

**Accessibility** — Review the axe-core violations by impact level (critical > serious > moderate > minor). Check the keyboard nav data — what percentage of focusable elements have visible focus? Are there tab traps? Look at the focus screenshots — can you actually see where focus is?

### Step 4: Score and grade

Use this scoring system:

**Start at 100 points, subtract for issues found:**

| Severity | Point deduction | Definition |
|----------|----------------|------------|
| Critical | -15 | Prevents task completion or excludes entire user groups |
| Major | -8 | Significant friction, confusion, or degraded experience |
| Minor | -3 | Polish issues, inconsistencies, small annoyances |

**Convert to letter grade:**

| Score | Grade |
|-------|-------|
| 90-100 | A |
| 80-89 | B |
| 70-79 | C |
| 60-69 | D |
| <60 | F |

Score each category independently, then compute the weighted overall (Interaction 40%, Accessibility 35%, Performance 25%).

**Grade ceiling rule:** A site with poor UX shouldn't get a passing grade just because it loads fast. If **Interaction Patterns** or **Accessibility** scores below 65, the overall grade cannot exceed one letter grade above the lowest of those two. Performance is excluded from this rule because it's less central to the UX experience. For example: if Interaction scores 62 (D) and Accessibility scores 70 (C), the lowest is D — so the overall is capped at C, regardless of how well Performance scores. This prevents fast-but-unusable sites from getting inflated grades.

Apply the ceiling after computing the weighted average — it overrides the math when needed.

### Step 5: Write the report

Use this structure:

```markdown
# UX Audit: [Page Title or URL]

**URL:** [url]
**Date:** [date]
**Overall Grade: [letter]** ([score]/100)

## Summary

[2-3 sentences: what's working, what's not, most impactful issue]

## Grades

| Category | Grade | Score | Top Issue |
|----------|-------|-------|-----------|
| Interaction Patterns | [grade] | [score]/100 | [one-liner] |
| Performance Perception | [grade] | [score]/100 | [one-liner] |
| Accessibility | [grade] | [score]/100 | [one-liner] |

## Interaction Patterns

### Issues Found

[For each issue:]
#### [Severity]: [Issue title]
**What:** [What's wrong]
**Why it matters:** [Impact on users]
**Fix:** [Specific, actionable code change or approach]

### What's Working Well
[Positive observations — this matters for developer morale]

## Performance Perception

### Issues Found
[Same format as above]

### What's Working Well
[Positive observations]

## Accessibility

### Issues Found
[Same format as above, include axe-core violation details]

### What's Working Well
[Positive observations]

## Priority Fixes

[Top 5 issues ranked by impact, with estimated effort: quick/medium/large]

1. **[Issue]** — [one-line fix description] *(quick fix)*
2. ...
```

### Auditing multiple pages

When auditing more than one page, run the audit script separately for each URL into its own output directory:

```bash
python <skill-dir>/scripts/audit.py <url-1> /tmp/ux-audit-output/page-1
python <skill-dir>/scripts/audit.py <url-2> /tmp/ux-audit-output/page-2
```

In the report, score each page's findings together under the same three categories. If a critical issue only appears on one page (like a tab trap on the login page but not the homepage), it still counts toward the overall grade — users don't only visit the homepage.

### Handling edge cases

- **Page requires auth**: Ask the user for credentials or have them log in first, then audit with an authenticated session. Don't try to audit login-gated pages without access.
- **SPA with client-side routing**: The script waits for `networkidle`, which handles most SPAs. If the page is still loading dynamic content, suggest auditing specific routes.
- **Script fails or Bash is unavailable**: This is a browser-automation skill — the whole point is visiting the real page. If you cannot run the script, **do not silently fall back to a knowledge-based report**. Instead, tell the user what's blocking you and ask them to grant Bash access or run the script themselves. A report based on memory rather than measurement defeats the purpose of this skill and may contain outdated or inaccurate information about the site.
- **Local dev server not running**: Help the user start it. Check package.json for `dev`/`start` scripts.
