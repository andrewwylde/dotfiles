---
name: career-growth-competency
description: >
  Maps evidence and feedback to Parable Engineering and Values competency
  matrices, producing gap analysis and competency-tagged examples. Use after
  evidence gathering, before self-review or manager review drafting, for
  "competency mapping", "level readiness", "gap analysis", or promotion prep.
disable-model-invocation: true
---

# Career growth competency

Interpret Parable's Engineering and Values matrices against gathered evidence. Never hardcode matrix text -- fetch or accept a user paste.

## Modes

| Mode | Voice in output |
|------|-----------------|
| Self-review | First person for reflection prompts; mapping is factual |
| Manager review | Third person for observations; assessments flagged for human |

## Inputs

| Input | Required |
|-------|----------|
| `employee.level` | yes |
| `engineering_matrix` | yes (Notion fetch or paste) |
| `values_matrix` | yes (Notion fetch or paste) |
| `evidence_ledger` | recommended |
| `feedback` snippets | optional (self, peers, manager) |
| `target_level` | optional (promotion / readiness lens) |

## Outputs

`competency_mapping` YAML:

```yaml
employee_level: IC4
target_level: IC5          # optional

engineering:
  - competency: "Technical execution"
  behaviors_observed: []   # evidence ids + summary
  gaps: []                 # missing vs level expectation
  readiness_note: ""       # "insufficient evidence" | human to confirm

values:
  - value: "..."
    behaviors_observed: []
    gaps: []

themes:
  convergent: []           # multiple sources agree
  divergent: []            # conflicting signals; see edge-cases

human_review_flags: []     # items AI must not rate
```

## Human judgment

Do not assign final level ratings or promotion decisions. Phrase assessments as "evidence suggests" and list `human_review_flags` for calibration.

Principles: [core-principles.md](../references/core-principles.md). Edge cases: [edge-cases.md](../references/edge-cases.md).

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `career-growth-evidence`, `career-growth-org-process` |
| Downstream | `career-growth-self-review`, `career-growth-manager-review`, `career-growth-development-plan`, `career-growth-promotion-packet` |

## Workflow

### Phase 1: Load matrices

1. Fetch Engineering + Values pages from Notion (URLs in [README](../README.md)) or use user paste.
2. Extract expectations for `employee.level` and optionally `target_level`.

### Phase 2: Map evidence

For each ledger entry and feedback snippet:

1. Tag relevant competencies (engineering and values).
2. Quote behavior + outcome; link `evidence_id` when available.
3. Mark `confidence: low` when inference is weak.

### Phase 3: Gap analysis

Compare observed behaviors to level expectations:

- **Strengths**: sustained patterns with multiple evidence points
- **Gaps**: expected behaviors with no evidence (state "no evidence in period", not "failed")
- **Divergent**: route to [edge-cases.md](../references/edge-cases.md)

### Phase 4: Readiness (optional)

If `target_level` is set, list behaviors at next level that are demonstrated vs not yet demonstrated. Do not recommend promote/do not promote.

## Failure modes

| Condition | Action |
|-----------|--------|
| Matrices unavailable | Stop; ask for paste |
| No evidence ledger | Warn; map from feedback only; note thin evidence |
| Level not in matrix | Ask user to confirm level string |
