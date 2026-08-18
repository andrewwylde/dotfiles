---
name: prod-health-frontend-weekly
description: Produces a ~5-minute spoken "last week in review" for the Production Health Overview meeting from the Datadog Frontend Team Overview dashboard, prioritizing web-app and web-api with a light web-admin-api footnote. Use when the user asks for "last week in review", "frontend weekly", "Production Health frontend update", "Frontend Overview weekly", "Frontend Team Overview", or last-n-days frontend health for the meeting. Includes plain-language talking points plus Datadog deep links for follow-up share. Do NOT use for general Datadog debugging, incident commander runbooks, backend-only health, or frontend design/perf audits unrelated to Production Health.
license: CC-BY-4.0
metadata:
  author: andrewwylde
  version: 1.0.0
---

# Prod Health Frontend Weekly

Produce a ~5-minute spoken update for the Production Health Overview meeting by narrating the Datadog **Frontend Team Overview** dashboard (often called "Frontend Overview"). Audience is eng/product with non-frontend experts — plain language, light jargon, explain user/product impact.

## Critical rules

1. **Dashboard-first.** Open and talk over Frontend Team Overview widgets. Do not invent a parallel investigation path unless a widget elevates something that needs one clarifying pull.
2. **Priority:** `web-app` + `web-api` lead. `web-admin-api` is one line unless monitors/errors/latency are clearly elevated.
3. **Window:** last `n` days from meeting day (default `n=7`). Ask only if `n` or meeting day is unclear.
4. **Tone:** facts + deltas vs the prior window; one clear verdict; 0–2 asks for the room.
5. **Links:** always include the dashboard deep link with the resolved time range for the follow-up share.

Canonical dashboard: **Frontend Team Overview** — id `wmq-a8t-wd6`, url `https://us5.datadoghq.com/dashboard/wmq-a8t-wd6`. If search returns a different primary match, prefer this id/title and note the mismatch.

## Instructions

### Step 1: Resolve the window

- Default: meeting day = today (or the stated meeting date); lookback = last `n` days ending at meeting day; `n=7` unless specified.
- Compute `from` / `to` (Unix ms or Datadog-relative like `7d`) and a prior comparison window of equal length immediately before `from`.
- State the window in the output header (e.g. `Jul 28 – Aug 4 (7d) vs prior 7d`).

### Step 2: Load Datadog guidance, then the dashboard

Before querying Datadog deeply:

1. Call `list_datadog_skills` with a query like `dashboard rum metrics` and `load_datadog_skill` for clearly matching guides (at minimum dashboards-and-notebooks; add rum/metrics/change-tracking/visualizations when needed).
2. `search_datadog_dashboards` with query `Frontend Overview` or `title:Frontend` to confirm id `wmq-a8t-wd6`.
3. `get_datadog_dashboard` with that id to refresh widget titles and template variables.

Template defaults to assume unless the user overrides: `env:production`; RUM services `parable-web-app` (+ `parable-website` only if relevant); API services emphasize `web-api` / `web-app`; keep `web-admin-api` in scope but de-emphasize.

Read `references/widget-narration.md` when mapping widgets to speech.

### Step 3: Pull signal from the dashboard spine

Gather enough to fill the 5-minute spine (not a full RCA):

| Section | Primary widgets / signals | Depth |
|---|---|---|
| Verdict | Overview KPIs + Monitor Summary (`team:frontend`) | Always |
| Availability / errors | Error Rate by Service; Top API Errors; RUM Errors; Avg Errors per Session | Always — lead with web-api / web-app |
| Latency | p95 API Latency (web-api); Latency Percentiles by Service; p95 by route | Only if materially worse vs prior window |
| RUM / UX | LCP, FCP, CLS, INP; Session Frustrations; Top RUM Errors | Always — translate CWV into user language |
| web-admin-api | Service filter / alert graphs for web-admin-api 5xx | One line unless elevated |
| Infra | Restarts, Desired vs Ready — only if noisy | Skip if quiet |
| Incidents / deploys | Monitors, incidents, change-tracking if something moved | Name only if worth meeting time |

Compare to the prior equal window. Prefer deltas ("errors/session up vs last week") over raw dumps.

If a top-priority service looks bad, one optional clarifying pull is allowed (metric/RUM/spans/incident). Do not turn the skill into an incident commander workflow.

### Step 4: Draft talking points

Read `references/talking-points-template.md` and fill it.

Target ~5 minutes spoken (roughly 650–800 words max; prefer tighter bullets the presenter can expand). Structure:

1. Verdict (1 sentence)
2. Availability / errors — web-app, web-api
3. Latency — only if material
4. RUM / Frontend Overview widgets (2–4 that moved)
5. web-admin-api — brief
6. Incidents / deploys worth naming
7. Asks for the room (0–2)

Language rules for non-frontend experts:

- Prefer "pages felt slow to become usable" over unexplained "LCP".
- If you use a CWV acronym, give a half-sentence gloss once.
- Say what it means for users/product, not just the chart.

### Step 5: Attach follow-up links

Include:

- Dashboard URL with time range query params when possible (from/to matching the window).
- Optional: direct links to any monitor, incident, or notebook you cited.

Offer a tightened Slack/email variant only if asked ("shareable version") — same facts, slightly denser, links preserved.

### Step 6: Stop

Deliver the talking points. Do not open a free-form debugging session unless the user asks to dig in.

## Examples

### Example 1: Standard weekly prep

User says: "last week in review for Production Health"

Actions:

1. Window = last 7 days from today; prior = previous 7 days.
2. Load Datadog skills; fetch Frontend Team Overview `wmq-a8t-wd6`.
3. Pull Overview KPIs, API error/latency for web-api/web-app, RUM CWV + errors, glance web-admin-api.
4. Emit 5-minute talking points + dashboard link.

Result: Spoken script with verdict, web-app/web-api health, 2–3 widget callouts, one-line web-admin-api, 0–2 asks, follow-up link.

### Example 2: Custom window

User says: "frontend health for the meeting — last 14 days"

Actions: same workflow with `n=14` and equal prior comparison window.

Result: Same spine; header shows 14d vs prior 14d.

### Example 3: Follow-up share

User says: "shareable version of that update"

Actions: Reuse the last draft; compress to Slack-friendly bullets; keep links.

Result: Short post suitable to paste after the meeting.

## Troubleshooting

### Error: Dashboard not found / wrong title

Cause: Search query too narrow or dashboard renamed.
Solution: Search `Frontend` / `team:frontend`; prefer id `wmq-a8t-wd6`. If missing, ask the user for the current dashboard link and update mental map for this run.

### Error: Empty or sparse metrics

Cause: Wrong `env` / service template vars, or no data in window.
Solution: Confirm `env:production` and RUM services `parable-web-app` / `parable-website`. State data gaps explicitly in talking points rather than inventing trends.

### Error: web-admin-api dominates the charts

Cause: Service template defaults include both API services.
Solution: Narrate web-api/web-app first; mention web-admin-api only if elevated. Optionally note you filtered emphasis for the meeting.

### Error: User wants deep RCA mid-meeting prep

Cause: A widget looks alarming.
Solution: Flag it in "Asks for the room" or a single clarifying pull. If they want full incident investigation, stop using this skill's scope and switch to incident/debug workflows.
