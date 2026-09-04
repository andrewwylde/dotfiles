# Per-employee input package schema

Artifact (3) from the performance-review workflow. Assembled by `career-growth-self-review` or `career-growth-manager-review` before drafting.

```yaml
employee:
  name:
  title:
  level:              # e.g. IC4, M1
  period_start: YYYY-MM-DD
  period_end: YYYY-MM-DD
  projects: []        # roles held during period

framework:
  engineering_matrix:  # fetched or pasted; do not hardcode
  values_matrix:
  rating_scale:        # if applicable

evidence_ledger:       # from career-growth-evidence (optional but recommended)
competency_mapping:    # from career-growth-competency (optional)

feedback:
  self_assessment:     # text or file path
  manager_observations:  # manager mode required
  peers: []            # [{name, text}]
  direct_reports: []   # optional
  clients: []          # optional
  metrics: []          # quantitative bullets

prior_review:
  cdp_goals: []        # prior development plan items
  prior_ratings:       # optional; human-provided only

optional:
  promotion_under_consideration: false
  special_circumstances: ""
  calibration_notes: ""   # manager mode; human-provided only
```

## Required by mode

| Field | Self-review | Manager review |
|-------|-------------|----------------|
| employee.* | yes | yes |
| framework | yes (fetch or paste) | yes |
| self_assessment | yes | yes |
| manager_observations | no | yes |
| peers | recommended | recommended (2-4) |
| prior_review.cdp_goals | if exists | if exists |
