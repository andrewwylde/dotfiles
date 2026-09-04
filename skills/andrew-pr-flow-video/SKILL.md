---
name: pr-flow-video
description: Capture Playwright WebM videos of the user-facing flows a PR changed, one short clip per flow, saved under ~/.agent/videos/pr-{number}/. Use when asked to "record videos of the flows we changed", "capture the PR's UX", "show the fix on video", or similar. Handles Parable dev-login, per-flow browser contexts, cold-start warmup, d3/SVG dispatchEvent for drill interactions, and artifact naming. Builds on the playwright-skill executor; writes scripts to /tmp.
---

# pr-flow-video

Records short WebM clips of each user-facing flow a PR touches, one clip per
flow. Each flow gets its own browser context so videos are independent and
playable in isolation. Saves to `~/.agent/videos/pr-{number}/`.

## When to use

- User asks to "record videos of the flows we changed" after shipping a PR.
- Capturing reviewer-facing evidence for a UX-only PR.
- Producing a reusable demo reel alongside a PR review artifact.

Do NOT use for:
- Automated e2e test suites (use Playwright specs in `apps/web-app/e2e/`).
- Pure screenshot captures (use `playwright-skill` directly with
  `page.screenshot`).
- Functional regression checks without video (same — use `playwright-skill`).

## Prerequisites

- `playwright-skill` is installed (`~/.claude/skills/playwright-skill/` with
  `node_modules/playwright` present).
- For Parable work: local stack is green (`ppwt status` shows web-api,
  web-admin-api, web-app, and query-layer all listening).
- TTS / feature-specific seed data is in place if the flow depends on it
  (e.g. run `/seed-tts-data` and enable the tenant's early_access_tenant_flag
  row before recording Time Spend flows).
- Dev login helper exists at
  `~/.agent/scripts/parable/dev-login.js` (per memory
  `reference_local_dev_auth.md`).

## Workflow

1. **Ask the user** (skip if obvious) for:
   - PR number (or "draft" if the PR isn't open yet).
   - URL base + path to navigate to.
   - List of flows to capture (verb + expected outcome, e.g. "Drill into L2
     then double-click an L1 segment and return to L1 view").
   - Dev user name (default `Sarah Administrator` for Parable tenant).

2. **Copy the template** at `$SKILL_DIR/template.js` to
   `/tmp/pr-flow-video-{number}.js`. The template is fully commented and
   provides:
   - Browser + per-flow recording context helpers.
   - Parable dev-login wiring (requires the helper script above).
   - `waitForSegments` with 60s cold-start deadline.
   - `dispatchDblClick` helper for d3-rendered SVG charts (plain `dblclick()`
     fails on d3 elements because the parent SVG intercepts pointer events).
   - Warmup step that loads + discards the first context so the second+ flows
     hit a warm Vite module cache.
   - Artifact renaming: each flow's video lands as
     `~/.agent/videos/pr-{number}/{flow-name}/{flow-name}.webm`.

3. **Fill in the flow functions.** Each flow is an async function taking
   `browser`, opening a recording context, logging in (or reusing a warmup),
   performing the steps, and returning the saved video path. The template
   shows the exact pattern.

4. **Run via `playwright-skill`:**
   ```bash
   cd ~/.claude/skills/playwright-skill \
     && PORT=<webapp-port> PR_NUMBER=<n> node run.js /tmp/pr-flow-video-<n>.js
   ```

5. **Review the artifacts** under `~/.agent/videos/pr-{number}/`. Each
   subdirectory is one flow with a `.webm` and any supporting screenshots.

## Template patterns

The template (`template.js`) encodes lessons learned from manual flow capture:

| Pattern | Why |
|---|---|
| Browser context per flow | Isolated video artifact; clean cookie state per flow |
| `dispatchEvent('dblclick')` | d3 SVG segments have a parent `<svg>` that intercepts pointer events; Playwright's `dblclick()` retries 60× and still fails. Dispatching the event bypasses the actionability hit-test. |
| `waitForSegments` 60s deadline | First browser context after a Vite cold start shows the release-panel fallback stub for ~3-5s while the dynamic import resolves. Hard timeout + poll loop avoids false negatives. |
| Warmup context | Burn one context before the real recordings so Vite modules are pre-resolved. First flow in the batch is otherwise the one that captures a fallback-state video. |
| `slowMo: 80` | Makes pointer/click motions visible in the final video without bloating duration. |
| `viewport 1440x900` | Matches the aspect ratio reviewers see on 13-15" laptops; donut/chart components render at their design size. |
| Stop-picker listener on Download flows | `page.on('filechooser', ...)` detects the OS file picker; a video alone can't prove the absence of the modal. |

## Template

See `$SKILL_DIR/template.js` for the full script. Key extension points:

```js
// Fill in flows here. Each function returns the saved video path.
async function flow1_someBehavior(browser) { ... }
async function flow2_anotherBehavior(browser) { ... }

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 80 });
  try {
    await warmup(browser);                  // <-- pre-warm Vite
    const results = [];
    results.push(await flow1_someBehavior(browser));
    results.push(await flow2_anotherBehavior(browser));
    console.log('Videos:', results);
  } finally {
    await browser.close();
  }
})();
```

## Output

- `~/.agent/videos/pr-{number}/{flow-name}/{flow-name}.webm` — the clip.
- `~/.agent/videos/pr-{number}/{flow-name}/*.png` — any screenshots captured
  inside the flow (e.g. for debug or error states).
- Any downloaded files (e.g. CSV exports) land in the flow's directory too.

## Tips

- **Rerun after each change.** Videos are single-digit MB; quick iteration is
  fine. Delete the flow's directory between runs to avoid confusion.
- **Name flows like user stories.** `01-drill-collapse`,
  `02-back-arrow-vs-title` — the prefix orders them alphabetically so
  `ls ~/.agent/videos/pr-{n}/` shows them in narrative order.
- **Keep flows under 15s.** If a flow takes longer, split it into two.
- **Don't record production.** This skill is for local stacks. Only target
  your own dev server or an isolated preview env.
