---
name: career-growth-promotion-packet
description: >
  Assembles a promotion packet with leveling worksheet sections and evidence
  mapped to next-level competencies without making a promotion decision. Use
  for "promotion packet", "leveling worksheet", "promotion case", "am I ready
  for IC5", or promotion committee prep.
disable-model-invocation: true
---

# Career growth promotion packet

Compile evidence and competency alignment for a promotion discussion. Does not recommend promote or deny.

## Modes

| Mode | Notes |
|------|-------|
| Self-review | Employee builds their case |
| Manager review | Manager compiles; employee self-assessment included |

## Inputs

| Input | Required |
|-------|----------|
| `employee.level` | yes |
| `target_level` | yes |
| `engineering_matrix`, `values_matrix` | yes |
| `evidence_ledger` | strongly recommended |
| `competency_mapping` with `target_level` | recommended |
| `accomplishments` journal | recommended |
| `promotion_worksheet` | optional (user template or Notion) |
| `self_assessment` | recommended |

## Outputs

Promotion packet markdown:

1. **Summary** -- scope of role today vs target level (factual)
2. **Leveling worksheet sections** -- per org template or default sections below
3. **Evidence appendix** -- entries grouped by competency
4. **Gaps at target level** -- behaviors not yet demonstrated
5. **Open questions for committee** -- human decisions only

Default sections if no worksheet provided:

- Impact at current level (sustained, above bar)
- Behaviors at target level (demonstrated / partial / no evidence)
- Values alignment
- Scope and complexity trajectory
- Feedback themes (synthesized)

## Human judgment

Promotion decisions are made by humans in Parable's promotion process. Show readiness evidence; never state "should be promoted."

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `evidence`, `competency`, `accomplishments`, `org-process` |
| Downstream | none |

## Workflow

### Step 1: Confirm target level

Validate `target_level` is exactly one step or user-specified path. If unclear, ask.

### Step 2: Load next-level bar

From matrices, list expectations at `target_level` only from fetched content.

### Step 3: Map evidence

Reuse `competency_mapping` with `target_level` or regenerate. Every "demonstrated" claim needs evidence ids.

### Step 4: Fill worksheet

Merge user `promotion_worksheet` structure if provided. Otherwise use default sections.

### Step 5: Gaps and questions

List missing evidence honestly. Add committee questions (scope, timing, role availability) without answering them.

## Failure modes

| Condition | Action |
|-----------|--------|
| Thin evidence | State packet is incomplete; list what to gather |
| User asks for promote/deny | Refuse; provide evidence summary only |
