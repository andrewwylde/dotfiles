---
name: career-growth-self-review
description: >
  Assembles the employee input package and drafts a first-person self-assessment
  aligned to Parable review requirements and competency matrices. Use for
  "write my self-review", "self-assessment", "EOY self-review", "mid-year
  reflection", or employee performance review prep.
disable-model-invocation: true
---

# Career growth self-review

Employee workflow: gather inputs, map to framework, draft a self-assessment the employee edits and submits.

## Mode

**Self-review only** (first person).

## Inputs

See [input-package-schema.md](../references/input-package-schema.md). Minimum:

- Employee info (name, level, period, projects)
- Engineering + Values matrices (fetch via Notion or paste)
- Self-reflection notes or draft bullets
- Optional: evidence ledger, competency mapping, accomplishments journal, prior CDP

Run upstream skills when missing:

1. `career-growth-org-process` -- required sections
2. `career-growth-evidence` -- recommended
3. `career-growth-competency` -- recommended
4. `career-growth-accomplishments` -- optional

## Outputs

1. Completed `input_package` YAML (for reuse)
2. Draft self-review markdown matching `org_process_brief` sections
3. List of `[NEEDS YOUR INPUT]` placeholders where evidence is thin

## Human judgment

The employee submits the final self-review. AI does not assign performance ratings. Do not fabricate peer or manager quotes.

Principles: [core-principles.md](../references/core-principles.md).

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `org-process`, `evidence`, `competency`, `accomplishments` |
| Downstream | `career-growth-development-plan`, `career-growth-promotion-packet` |

## Workflow (multi-step, not one-shot)

### Step 1: Org requirements

Load or confirm `org_process_brief` from `career-growth-org-process`.

### Step 2: Assemble input package

Fill [input-package-schema.md](../references/input-package-schema.md). Stop and ask if level, period, or matrices are missing.

### Step 3: Map framework

If no `competency_mapping` exists, run mapping logic from `career-growth-competency` or ask user to invoke it.

### Step 4: Assess prior CDP

For each prior goal: Significant progress / Some progress / Limited progress / Not addressed -- with evidence or `[NEEDS YOUR INPUT]`.

### Step 5: Draft by section

For each required section from org process:

- Lead with outcomes and behaviors (specificity rule)
- Align claims to Engineering and Values competencies
- Synthesis over bullet dumps of PR titles
- Developmental tone on growth areas

Use Parable section names from Notion, not Meridian role names (see [meridian-system-prompt.md](../references/meridian-system-prompt.md) for contrast only).

### Step 6: Self-review quality pass

- Every claim traceable to evidence id or user-provided note
- No invented 360 feedback
- Flag divergent themes for user to resolve
- End with checklist: what the employee must verify before submit

## Failure modes

| Condition | Action |
|-----------|--------|
| No self-reflection content | Draft from ledger only; mark all narrative sections `[NEEDS YOUR INPUT]` |
| Matrices missing | Stop |
| User asks for rating | Decline; suggest manager/calibration process |
