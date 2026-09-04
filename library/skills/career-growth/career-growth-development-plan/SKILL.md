---
name: career-growth-development-plan
description: >
  Creates a career development plan (CDP) from competency gaps, review feedback,
  and stated career goals with actionable focus areas. Use for "development plan",
  "CDP", "growth plan", "what should I work on next cycle", or after self-review
  or manager review drafting.
disable-model-invocation: true
---

# Career growth development plan

Build a prioritized CDP for the next review period from gaps and goals.

## Modes

| Mode | Framing |
|------|---------|
| Self-review | First person commitments ("I will...") |
| Manager review | Third person agreements ("[Name] will focus on...") |

## Inputs

| Input | Required |
|-------|----------|
| `competency_mapping` or review draft | yes |
| `career_goals` | optional (user-stated) |
| `prior_cdp` | optional |
| `employee.level` | yes |

## Outputs

CDP markdown (2-3 focus areas, not more than 4):

```markdown
# Development plan: [Name]
Period: [next cycle dates]

## Focus 1: [Engineering or Values area] - [Skill/behavior]
- **Why**: [Framework connection]
- **Success looks like**: [Observable behaviors]
- **Actions**: [2-4 concrete steps]
- **Support needed**: [Manager, training, project exposure]

## Focus 2: ...
## Focus 3: ...

## Carried forward from prior CDP
[Items still relevant]

## Human sign-off
[ ] Employee  [ ] Manager (if applicable)
```

## Human judgment

CDP items require employee and manager agreement. AI proposes; humans commit.

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `competency`, `self-review`, `manager-review` |
| Downstream | none (feeds next cycle's review) |

## Workflow

### Step 1: Extract gaps

From `competency_mapping.gaps` and review draft development sections. Prioritize:

1. Gaps vs current level expectations
2. Next-level readiness (if promotion path stated)
3. Patterns across feedback (not one-off noise)

### Step 2: Prioritize

Select 2-3 areas. If more than four gaps exist, rank by impact and manager/employee input.

### Step 3: Frame each area

Per focus area: skill/behavior, why (matrix link), actions, support. Avoid vague goals ("improve communication").

### Step 4: Prior CDP

Note carried-forward items with honest progress reference.

## Failure modes

| Condition | Action |
|-----------|--------|
| No gap data | Ask for review draft or run `career-growth-competency` |
| User wants 10 goals | Push back; recommend 2-3 |
