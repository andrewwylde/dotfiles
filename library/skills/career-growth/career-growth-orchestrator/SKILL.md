---
name: career-growth-orchestrator
description: >
  Chains career-growth skills for Parable EOY or mid-year self-review and
  manager review workflows. Use for "run my review workflow", "help me through
  performance review season", "end to end self-review", or when unsure which
  career-growth skill to run first.
disable-model-invocation: true
---

# Career growth orchestrator

Entry point for full review cycles. Runs skills in order, passes artifacts forward, stops on missing required inputs.

## Human judgment

Orchestration does not bypass human decisions on ratings, promotion, or sensitive feedback. At each gate, list what the human must supply or approve.

## Skill map

| Order | Skill | Self-review | Manager review |
|-------|-------|-------------|----------------|
| 1 | `career-growth-org-process` | yes | yes |
| 2 | `career-growth-evidence` | yes | yes |
| 3 | `career-growth-accomplishments` | optional | optional |
| 4 | `career-growth-competency` | yes | yes |
| 5a | `career-growth-self-review` | yes | -- |
| 5b | `career-growth-manager-review` | -- | yes |
| 6 | `career-growth-development-plan` | optional | optional |
| 7 | `career-growth-promotion-packet` | if promotion | if promotion |

Full table: [../README.md#skill-map](../README.md#skill-map).

## Workflow selection

Ask once if unclear:

```
Are you preparing your own self-review, or drafting a review for a direct report?
```

Then follow the matching chain below.

## Self-review chain

```
org-process -> evidence -> accomplishments (optional) -> competency -> self-review -> development-plan (optional) -> promotion-packet (if requested)
```

**Gate 1** (after org-process): Confirm period dates and level.

**Gate 2** (after evidence): User reviews ledger for accuracy.

**Gate 3** (after competency): User confirms mapping before draft.

**Gate 4** (after self-review): User edits draft; AI does not submit.

## Manager review chain

```
org-process -> evidence (for report) -> competency -> manager-review -> development-plan (optional) -> promotion-packet (if requested)
```

**Gate 1**: Confirm direct report identifiers (GitHub, Linear, Slack).

**Gate 2**: Confirm manager observations and peer feedback are loaded.

**Gate 3**: Manager runs [manager-checklist.md](../references/manager-checklist.md) before calibration.

## Artifacts passed between skills

| Artifact | Producer | Consumers |
|----------|----------|-----------|
| `org_process_brief` | org-process | self-review, manager-review |
| `evidence_ledger` | evidence | competency, accomplishments, reviews, promotion |
| `competency_mapping` | competency | reviews, development-plan, promotion |
| `input_package` | self-review / manager-review | development-plan |
| Accomplishments journal | accomplishments | self-review, promotion |

Schemas: [references/](../references/).

## When to skip orchestration

Invoke a single skill directly when the user only needs one task (e.g., "pull my GitHub PRs for Q3").

## External methodology

Structured multi-step synthesis (not one-shot) per [Week 14 article](https://claudecodefornoncoders.substack.com/p/week-14-using-claude-to-draft-performance). Meridian example prompt: [meridian-system-prompt.md](../references/meridian-system-prompt.md).
