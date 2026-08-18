# Changeset decomposition — eval harness

Compare **baseline** (no skill) vs **treatment** (agent loads `changeset-decomposition` and its `references/pattern-*.md` before answering).

## What you are measuring

| Metric | Definition |
| ------ | ---------- |
| **Structure score** | Weighted checklist in `RUBRIC.md` (0–100). |
| **Critical violations** | Hard fails from rubric (e.g. bundles schema with consumer). Any violation caps max score or fails the run — see rubric. |
| **Latency / cost** (optional) | Wall time and token usage per run from your harness. |

Baseline runs should score lower on structure and hit more critical violations on adversarial cases. Treatment runs should complete all five pattern artifacts and respect anti-patterns from Pattern 4.

## Protocol (A/B)

1. Pick a case from `cases/`. Copy `scenario.md` user message verbatim.
2. **Baseline run:** System prompt must **not** include the skill. Do not attach `SKILL.md` or `references/`.
3. **Treatment run:** Inject `SKILL.md` (full file) at session start, or instruct: "Follow the changeset-decomposition skill at `~/.claude/skills/changeset-decomposition/SKILL.md`; load each `references/pattern-NN-*.md` in order."
4. Same model, same temperature, same max tokens where applicable.
5. Save raw assistant output to `results/<case-id>/<baseline|treatment>-<run-id>.md`.
6. Grade both with `RUBRIC.md` + case-specific `grading-notes.md` if present.

## Minimum case set

| ID | Case | What baseline usually misses |
| -- | ---- | ----------------------------- |
| `01-mixed-three-concerns` | Billing feature + auth refactor + infra | Ignores ownership / splits by file type |
| `02-schema-and-consumers` | GraphQL + migration + Go + TS | Bundles schema with consumers or wrong merge order |
| `03-refactor-plus-feature` | Same files, refactor + new behavior | One PR or tests deferred |
| `04-independent-chores` | Unrelated small edits | Over-stacks or merges unrelated work |

## Optional automation

- `scripts/score-markdown.sh <response.md>` — grep-based smoke check for pipeline artifacts (P1–P5 keywords). Exit 0 if all match. Does **not** detect semantic violations (use human + `RUBRIC.md`).

```bash
./evals/scripts/score-markdown.sh results/01/treatment-run1.md
```

## Files

- `RUBRIC.md` — shared scoring.
- `protocol.md` — copy-paste blocks for graders.
- `cases/*/scenario.md` — frozen synthetic changesets.
- `cases/*/grading-notes.md` — case-specific must / must-not.
