# Widget narration — Frontend Team Overview

Load this when mapping dashboard widgets to speech (Steps 3–4). Canonical dashboard id: `wmq-a8t-wd6` (`https://us5.datadoghq.com/dashboard/wmq-a8t-wd6`).

Template variables (defaults): `env=production`; `rum_service` includes `parable-web-app` (and `parable-website` when relevant); `service` includes `web-api` and `web-admin-api` — **narrate web-api / web-app first**.

## Overview group (open here)

| Widget | What to say | Elevate when |
|---|---|---|
| RUM Sessions | Traffic volume context ("session count steady/up/down") | Sudden drops that suggest tracking or outage |
| p95 API Latency (web-api) | "API felt slower/faster for typical slow requests" | Material rise vs prior window |
| Avg Errors per Session | "Users hit more/fewer client errors per visit" | Crossing yellow/red conditional formats (>0.5 / >2 on the widget) |
| Monitor Summary (`team:frontend`) | Alert posture in one breath | Any alerting/warn counts that need the room |

## Real User Monitoring

Translate Core Web Vitals for mixed audiences:

| Widget | Plain gloss | Good / watch / poor cues on dashboard |
|---|---|---|
| LCP | How long until the main content feels on-screen | Good ~2.5s; poor ~4s markers |
| FCP | How long until something first paints | Good ~1.8s; poor ~3s |
| CLS | Whether the page jumps around while loading | Good ≤0.1; poor >0.25 |
| INP | How quickly the UI reacts after click/tap/key | Good ≤200ms; poor >500ms |
| RUM Errors / Top RUM Errors by Message | What broke in the browser | New top messages or spikes vs prior window |
| Session Frustrations | Rage clicks / dead clicks / similar pain | Sustained spike |
| Page Views by Route | Where traffic concentrated | Only if needed to contextualize an error hotspot |

Pick **2–4** RUM widgets that actually moved. Do not read every CWV chart.

## API Performance

| Widget | Priority | Notes |
|---|---|---|
| Request Rate by Service | Context | Sets baseline for error % |
| Latency Percentiles by Service | High for web-api | Call p95; mention p99 only if scary |
| Error Rate by Service | High for web-api / web-app | Lead narrative |
| Top Routes / Error Rate by Route / p95 by Route | Supporting | Name 1 hotspot max unless multiple burn |
| Top API Errors by Resource | Supporting | One theme for the room |
| web-admin-api 5xx alert graphs | Footnote | One line unless elevated |
| Parable API 5xx alert graph | Mention if firing | Ties to web-api posture |

## Infrastructure Health

Default: **skip in speech** if quiet.

Mention only for restarts storms, desired≠ready, or CPU/memory clearly correlated with API/RUM pain. Production Health is not a K8s deep-dive unless infra is the story.

## Comparison discipline

For each claimed movement:

1. State current-window value or shape.
2. Contrast prior equal window.
3. Tie to user/product impact in one clause.

If data is missing, say so — never fabricate a trend.
