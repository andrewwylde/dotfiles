---
name: career-growth-manager-review
description: >
  Synthesizes 360 feedback and manager observations into a balanced direct-report
  review draft aligned to Parable matrices and org requirements. Use for
  "draft performance review", "write review for my report", "manager review",
  "360 synthesis", or calibration prep for a direct report.
disable-model-invocation: true
---

# Career growth manager review

Manager workflow: assemble the feedback package, synthesize sources, draft the review document for manager edit and calibration.

## Mode

**Manager review only** (third person; balanced; calibration-aware).

## Inputs

See [input-package-schema.md](../references/input-package-schema.md). Minimum:

- Employee info
- Matrices (fetched or pasted)
- Manager observations (required)
- Employee self-assessment (required)
- Peer feedback (2-4 recommended)
- Optional: DR feedback, client feedback, metrics, evidence ledger, competency mapping, prior CDP, calibration notes

Upstream skills when missing: `org-process`, `evidence`, `competency`.

## Outputs

1. `input_package` YAML
2. Review draft markdown per org-required sections
3. `[MANAGER: ...]` flags for conflicting feedback, thin evidence, ratings
4. Reminder to run [manager-checklist.md](../references/manager-checklist.md)

## Human judgment

You draft. The manager decides. Final ratings, sensitive feedback, and promotion outcomes are human-owned. See [core-principles.md](../references/core-principles.md) and [edge-cases.md](../references/edge-cases.md).

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `org-process`, `evidence`, `competency` |
| Downstream | `career-growth-development-plan` |

## Workflow

### Step 1: Org requirements

Load `org_process_brief` via `career-growth-org-process`.

### Step 2: Assemble input package

Validate manager mode required fields. If peer feedback is missing, warn and proceed with explicit gaps.

### Step 3: Framework mapping

Use `competency_mapping` or produce one. Identify convergent and divergent themes.

### Step 4: CDP progress

Compare prior CDP goals to evidence across all feedback sources. Use progress labels with cited examples.

### Step 5: Section drafting

For each org-required section:

- State competency/level observations as drafts for calibration (`[MANAGER: confirm level narrative]`)
- Strengths: 2-3 specific examples per major area
- Development: 1-2 specific examples; constructive framing
- Synthesize sources; attribute patterns, not anonymous gossip

Structure reference: [review-template-meridian.md](../references/review-template-meridian.md) adapted to Parable sections.

### Step 6: Development plan section

Draft 2-3 focus areas for next period (full CDP may use `career-growth-development-plan`).

### Step 7: Manager checklist

Output the checklist from [manager-checklist.md](../references/manager-checklist.md) with checkboxes unchecked.

## Failure modes

| Condition | Action |
|-----------|--------|
| No manager observations | Stop; cannot draft |
| Conflicting feedback | [edge-cases.md](../references/edge-cases.md) |
| User asks AI to set rating | Refuse; manager sets in calibration |
| Promotion decision requested | Show readiness evidence only; separate process |
