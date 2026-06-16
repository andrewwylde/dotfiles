---
name: changeset-decomposition
description: Use when a branch, PR, or working tree contains too many unrelated changes — large diffs with mixed concerns, changes spanning multiple domains, features bundled with refactors, or any time "this is too big to review" is the instinctive reaction. Runs a structured 5-pattern analysis pipeline to identify natural PR boundaries, map change dependencies, assess risk, and produce a merge-sequenced split plan. Do NOT use for service-level or module-level architectural decomposition of a codebase (use modular-decomposition). For actual git branch creation and commits after a plan exists, use split-to-prs.
---

# Changeset Decomposition

This skill runs the **Patterns 1-5** analysis pipeline before PR splitting. Each pattern is a plain markdown file under `references/`; load the file for that step and execute it against the changeset.

## How to Use

### Quick start (what users can say)

- **Full pipeline:** "Decompose this branch into reviewable PRs," "This diff is too big — analyze it and split it," "Run changeset decomposition on my branch."
- **Single step:** "Inventory what's in this changeset," "Map the dependencies between my changes," "Define PR boundaries for this diff."
- **With context:** "Split this into PRs by domain," "Find which changes are blocking others," "Sequence these changes for stacked PRs."

This skill produces the **split plan**. To execute the plan (create branches, stage hunks, push, open PRs), hand off to **split-to-prs**.

### How the agent should run it

1. **Scope:** Confirm the diff source (uncommitted working tree, branch vs main, specific commit range). Derive it with `git diff main...HEAD --stat` or equivalent if unspecified.
2. **Order:** Run patterns **1 -> 2 -> 3 -> 4 -> 5** in that order. Do not skip a step unless the user explicitly narrows scope.
3. **Load references:** For each pattern, open the matching `references/pattern-NN-*.md` file and follow its instructions exactly.
4. **Carry context forward:** Output from earlier patterns feeds later ones. The inventory from Pattern 1 drives dependency mapping in Pattern 2; both drive boundary definition in Pattern 4.
5. **Deliver:** Produce a concrete split plan — named PRs, file lists per PR, merge order, and stacking dependencies — tied to actual paths in the diff, not generic advice.

### Usage examples

**Example 1 — Full pipeline**

```
User: "This branch has 3 weeks of work on it. Help me split it into reviewable PRs."

Agent: Run git diff main...HEAD --stat, then execute patterns 1->5 in order,
loading each references/pattern-NN-*.md. Deliver a named PR plan with sequencing.
```

**Example 2 — Boundary definition only**

```
User: "I know what's in the diff — I just need help deciding where to draw the PR lines."

Agent: Still run Pattern 1 briefly to confirm the inventory matches the user's
mental model, then focus depth on Patterns 3 and 4 for risk and boundaries.
```

**Example 3 — Stacked PR planning**

```
User: "Some of these changes depend on each other. Figure out the stacking order."

Agent: Pattern 2 (dependency mapping) is the critical step. After it,
use Pattern 5 to produce a stacked PR chain diagram and merge sequence.
```

## Prerequisites

- Access to the git diff or file list representing the changeset.
- Complete **Pattern N** before Pattern N+1 unless the user limits scope. Later patterns depend on earlier outputs.
- If CODEOWNERS or team ownership files exist, load them before Pattern 4 — ownership is a strong PR boundary signal.

## Ordered workflow (Patterns 1-5)

| Step | Pattern | Primary reference |
| ---- | ------- | ----------------- |
| 1 | Changeset inventory | `references/pattern-01-inventory.md` |
| 2 | Dependency mapping | `references/pattern-02-dependency-mapping.md` |
| 3 | Risk and complexity assessment | `references/pattern-03-risk-assessment.md` |
| 4 | PR boundary definition | `references/pattern-04-pr-boundaries.md` |
| 5 | Sequencing and stack plan | `references/pattern-05-sequencing.md` |

## Pattern 6 — execution

**Pattern 6** (branch creation, staging, committing, pushing, opening PRs) is not duplicated here. After Pattern 5 produces the split plan, switch to **split-to-prs** to execute it. That skill handles the git operations, backup snapshot, and per-slice commit workflow.

## PR independence criteria

A well-formed PR from this pipeline must satisfy all of these:

- **Independently deployable:** Merging it alone does not break the main branch.
- **Has its own tests:** Behavior changes ship with the tests that verify them.
- **Coherent scope:** A reviewer can understand its purpose from the title alone.
- **Bounded diff:** Changes one logical thing — a feature, a fix, a refactor, a schema change.

Use these as the acceptance gate when evaluating candidate boundaries in Pattern 4.
