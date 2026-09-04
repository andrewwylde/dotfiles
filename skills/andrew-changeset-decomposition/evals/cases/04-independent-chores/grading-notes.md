# Case 04 — grader notes

## Must

- Three independent PRs **or** explicit statement that one PR is acceptable because risk is LOW and team prefers fewer PRs — but then must still give optional split.

## Must not

- Stacked PRs or dependency graph between unrelated files.
- An `executor: gh-stack` group (all work should be `executor: split-to-prs` / independent).
- Missing inventory (trivial but required for full pipeline eval).

## Baseline

Often over-explains or invents fake dependencies. Treatment should stay minimal: small tables, no fake HARD edges.
