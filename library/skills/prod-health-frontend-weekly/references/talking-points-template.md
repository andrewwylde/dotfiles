# Talking points template

Load this when drafting the spoken update (Step 4). Fill every section; omit Latency / Infra / Incidents bullets only when explicitly quiet.

## Output contract

```markdown
# Frontend — Production Health Overview
Window: {from} – {to} ({n}d) vs prior {n}d
Dashboard: https://us5.datadoghq.com/dashboard/wmq-a8t-wd6?...

## Verdict
{One sentence: healthy / watch / rough week — and why in plain language.}

## Availability / errors (web-app, web-api)
- {Delta or status for web-app — user-facing meaning}
- {Delta or status for web-api — user-facing meaning}
- {Optional: top error theme if it would waste meeting time to skip}

## Latency (only if material)
- {web-api p95 / route hotspot vs prior window — skip section if flat}

## RUM / Frontend Overview
- {Widget 1 that moved — gloss CWV once if used}
- {Widget 2}
- {Optional widgets 3–4}

## web-admin-api
- {One line. Elevate only if 5xx/monitors clearly noisy.}

## Incidents / deploys worth naming
- {Only meeting-worthy items; else "Nothing notable."}

## Asks for the room
- {0–2 prompts. Empty OK.}

## Follow-up links
- Frontend Team Overview ({window}): {url}
- {optional monitor/incident links}
```

## Timing guide (~5:00)

| Segment | Target |
|---|---|
| Verdict | 0:20 |
| Availability / errors | 1:15 |
| Latency | 0:45 (or skip) |
| RUM / widgets | 1:30 |
| web-admin-api | 0:20 |
| Incidents / deploys | 0:30 |
| Asks | 0:20 |

If a segment is quiet, donate time to RUM or errors — do not pad with infra trivia.

## Tone checklist

- Eng/product room; non-frontend experts present.
- One half-sentence gloss the first time you say LCP/FCP/CLS/INP.
- Prefer deltas vs prior window over orphaned absolute numbers.
- No heroics language; no unexplained acronym piles.
- Ends with optional asks — not a homework dump.
