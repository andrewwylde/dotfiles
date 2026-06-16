# Grading rubric (0–100)

Use for every saved assistant response. Record scores in a small table: criterion → points earned → notes.

## Critical violations (automatic 0 for the case if any apply)

Score **0** for the whole case (or cap at 40 if your policy allows partial credit only for non-safety cases) when the response does any of the following:

- **V1 — Schema with consumer in one PR:** Proposes merging `.graphql` / migration changes in the same PR as application code that depends on generated types or new columns, **without** either (a) generated outputs in that same PR plus a coherent single merge, or (b) a clear sequence where schema+generated+migration merge before consumer PRs. (Pattern 4: schema + generated can ship together; hand-written Go/TS consumers must not merge to main before their generated inputs exist.)
- **V2 — Tests without implementation:** Puts all tests in a follow-up PR with no tests in the behavior PR.
- **V3 — Irreversible migration with no rollback note:** Only when the scenario marks a migration as destructive: response has no rollback or forward-fix note in the plan for that PR.

## Structure (max 60 points)

Award only if the section exists **and** uses the concrete file paths from the scenario (not only generic advice):

| Criterion | Max |
| --------- | --- |
| P1 — File-level inventory table (path, domain or layer, change type, size or +/-) | 15 |
| P2 — Explicit dependency edges (hard vs soft) between proposed PRs or change groups | 15 |
| P3 — Risk tier or score per proposed PR (HIGH/MEDIUM/LOW or numeric) | 10 |
| P4 — Named PRs with **file lists** (every scenario file assigned exactly once) | 12 |
| P5 — Merge order **or** waves + optional stack bases + `split-to-prs` hand-off block | 8 |

## Quality (max 40 points)

| Criterion | Max |
| --------- | --- |
| Q1 — At least one independent PR called out when the scenario has obvious independent work | 8 |
| Q2 — Does not bundle unrelated domains into one PR when scenario has clear separation | 10 |
| Q3 — HIGH-risk change isolated (own PR) when scenario includes schema or destructive migration | 10 |
| Q4 — Mentions reviewer / ownership boundary when `CODEOWNERS` snippet is in scenario | 6 |
| Q5 — Identifies circular or impossible split and says so instead of forcing a bad cut | 6 |

## Baseline vs treatment expectation

On cases `01`–`03`, a strong baseline model might reach **35–55** with frequent V1/V2 failures. With the skill, expect **70+** and no critical violations, assuming the agent actually loaded pattern files.

## Quick grade template

```text
Case: ___
Run: baseline | treatment
Critical violations: V1 V2 V3 (list or none)
Structure: __/60
Quality: __/40
Total: __/100
```
