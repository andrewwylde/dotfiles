---
name: autoimprove
description: Use to autonomously improve skills in the harness via measurable iteration loops. Designed for /loop -- each iteration picks the top improvement opportunity from effectiveness-map, makes one atomic change to one skill, benchmarks it with skill-creator, and keeps or reverts. Triggers on "autoimprove", "improve my harness", "self-improve skills".
---

# Autoimprove

Autonomous skill improvement loop that applies autoresearch-style iteration to the harness itself. Each iteration makes exactly one atomic change to one skill, measures the result, and records whether it helped.

## When to Use

- Run with `/loop` for autonomous multi-iteration improvement
- Run standalone to improve one skill per invocation
- After `effectiveness-map` has identified improvement priorities

## Prerequisites

- `~/.agent/effectiveness-map.json` must exist (run `effectiveness-map` first)
- `skill-creator:skill-creator` plugin must be installed (for benchmarking)
- Git available (for atomic commits and reverts)

## Per-Iteration Protocol

### Step 1: Select Target

1. Read `~/.agent/effectiveness-map.json`
2. Read `~/.agent/improvement-log.jsonl` (if it exists) to skip recently-attempted skills
3. Pick the top-ranked unaddressed improvement opportunity
4. If no opportunities remain, report "Harness is up to date" and stop the loop

### Step 2: Gather Evidence

1. Read the target skill's SKILL.md
2. Read relevant postmortem entries from `~/.agent/postmortems/` that mention this skill
3. Use `read-memories` to search session logs for concrete usage examples
4. Summarize: what specifically is the problem, what would improvement look like

### Step 3: Formulate Hypothesis

Draft a specific improvement hypothesis:

> "Changing [X] in [skill] should improve [Y] because [Z]."

Examples:
- "Narrowing the trigger conditions in arch-review should reduce misfires because it currently triggers on simple handler changes that don't need architectural review."
- "Adding a 'skip for small changes' clause to plan-adversary-review should improve token efficiency because most 1-2 file changes don't need a three-lens review."

### Step 4: Make One Atomic Change

1. Edit the skill's SKILL.md with a minimal, targeted change addressing the hypothesis
2. Commit the change: `git add <skill-path> && git commit -m "autoimprove: [hypothesis summary]"`
3. Do NOT make multiple changes -- one change per iteration

### Step 5: Benchmark

Invoke `skill-creator:skill-creator` to benchmark the change:
1. If existing evals exist for this skill, run them
2. If no evals exist, create 2-3 basic eval scenarios based on the postmortem evidence
3. Compare with-skill vs. baseline behavior

### Step 6: Decide

- **If benchmark shows improvement** (or is neutral with cleaner code): keep the commit
- **If benchmark shows regression**: `git revert HEAD --no-edit`

### Step 7: Log Result

Append to `~/.agent/improvement-log.jsonl`:

```json
{
  "date": "2026-04-14",
  "iteration": 1,
  "skill": "arch-review",
  "hypothesis": "Narrow trigger conditions to exclude simple handler changes",
  "change_description": "Added file-count threshold to trigger conditions",
  "benchmark_result": "improved",
  "kept": true,
  "evidence_source": "postmortem:2026-04-12-connector-work"
}
```

### Step 8: Report and Continue

Output a one-line summary:

> `[autoimprove] arch-review: narrowed triggers -- KEPT (benchmark improved)`

or

> `[autoimprove] swarm-review: added timeout handling -- REVERTED (regression in eval-2)`

If running via `/loop`, return to Step 1 for the next iteration.

## Constraints

- **One change per iteration.** Never modify multiple skills in a single pass.
- **Evidence required.** Never make speculative improvements -- every change must trace to a postmortem finding or usage log pattern.
- **Revert on regression.** No exceptions. If the benchmark doesn't show improvement, revert.
- **Skip recently attempted.** If a skill was attempted in the last 7 days (per improvement-log), skip it and move to the next opportunity.
- **Respect the skill's intent.** Don't change what a skill does -- only how well it does it. Trigger conditions, output quality, token efficiency, and edge case handling are fair game.
