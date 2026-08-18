---
description: "Orchestrated planning chain: brainstorm -> adversary review -> plan. Use when starting significant work that needs structured thinking before execution. Accepts intensity: light (brainstorm+plan), standard (brainstorm+adversary+plan), thorough (brainstorm+2x adversary+plan). Example: /deep-plan thorough add real-time notifications to the connector status page"
alwaysApply: false
---

# Deep Plan

Structured planning chain that ensures ideas are stress-tested before execution. Chains three phases: brainstorming, adversary review, and plan writing.

## Arguments

Parse from `$ARGUMENTS`:
- **Intensity level** (optional, first word if it matches): `light`, `standard`, `thorough` (default: `standard`)
- **Everything else**: the task description / goal

## Phase 1: Brainstorm

Invoke `superpowers:brainstorming` with the task description.

Follow the brainstorming skill's full workflow: explore user intent, clarify requirements, consider approaches, and produce a design direction. The output of this phase is a clear spec or design direction that can be reviewed.

When brainstorming completes, capture the key decisions and design direction as the **spec** for the next phase.

## Phase 2: Adversary Review

**Skip this phase if intensity is `light`.**

### Standard intensity (one pass):

Invoke `plan-adversary-review` against the spec from Phase 1.

Read the adversary review output. For each finding:
- If it reveals a genuine risk: note it for incorporation into the plan
- If it's a false alarm: briefly note why and move on

### Thorough intensity (two passes):

**Pass 1:** Invoke `plan-adversary-review` against the spec from Phase 1. Incorporate valid findings.

**Pass 2:** After incorporating Pass 1 findings into a revised spec, invoke the-fool in "Expose my assumptions" mode against the revised spec. This second pass uses the interactive the-fool to catch assumptions that the automated review missed.

## Phase 3: Write Plan

Invoke `superpowers:writing-plans` with:
- The original task description
- The brainstorming output (design direction)
- The adversary review findings (risks to mitigate, assumptions to validate)

The plan should explicitly address the adversary review's top risks in its approach.

## Output

The final output is a written implementation plan (per the writing-plans skill's format) that has been stress-tested before a single line of code is written.

Present a summary to the user:
```
## Deep Plan Complete

**Task:** [task description]
**Intensity:** [light/standard/thorough]
**Key risks identified:** [from adversary review, or "skipped" if light]
**Plan file:** [path to plan]

Ready to execute with /implement-and-review-loop or superpowers:executing-plans.
```
