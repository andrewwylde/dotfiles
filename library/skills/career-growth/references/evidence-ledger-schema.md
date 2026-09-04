# Evidence ledger schema

Output of `career-growth-evidence`. Downstream skills (`competency`, `accomplishments`, `self-review`, `manager-review`, `promotion-packet`) consume this structure.

```yaml
meta:
  subject:          # display name
  github_login:     # optional
  linear_user_id:   # optional
  slack_user_id:    # optional
  period_start:     # YYYY-MM-DD
  period_end:       # YYYY-MM-DD
  mode:             # self-review | manager-review
  generated_at:     # ISO-8601

themes:             # user-provided or inferred project/themes
  - id: theme-1
    label: "Project Apex"

entries:
  - id: ev-001
    date: YYYY-MM-DD
    source: github | linear | slack | user | other
    theme_ids: [theme-1]           # optional
    competency_hints: []           # optional; filled by competency skill
    summary: "One sentence, perf-review lens"
    impact: "Outcome or behavior observed"   # optional
    url: ""                        # link to PR, issue, message, etc.
    confidence: high | medium | low  # low = needs user confirmation

gaps:
  - source: github
    reason: "No gh auth for target user"
```

## Entry quality bar

- **Include**: merged PRs, shipped issues, incident response, design docs, mentoring threads, cross-team collaboration, measurable outcomes.
- **Exclude**: drive-by comments, bot noise, trivial reactions unless they show sustained pattern.
- **Never fabricate** entries. If a source returned nothing, record it under `gaps`.
