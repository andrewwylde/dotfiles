---
name: writing-branch-stories
description: Use when asked to turn a Git branch, pull request, or commit range into product-facing implementation stories, including requests scoped to a feature or theme. Do not use for release notes, ordinary code review, commit-message generation, or uncommitted-only summaries.
---

# Writing Branch Stories

## Core principle

Understand every branch commit and surviving change, then produce the fewest
coherent business-outcome stories. Branch code is evidence, not automatically
the production specification.

**REQUIRED REFERENCE:** Read `REFERENCE.md` before executing this workflow.

## Workflow

1. **Scope sanity gate (required before inventory):** Compare three candidate scopes and stop if they materially differ until the user confirms one:
   - **Committed branch** — all commits on the branch vs refreshed `origin/main` (default).
   - **Session delta** — uncommitted staged/unstaged/untracked working-tree changes only.
   - **Named-feature / theme** — user- or issue-scoped subset (e.g. "only Ponder fixes").
   Present a short diff of why they diverge (file counts, obvious cleanup like mass deletes, mixed themes). Do **not** convert ambiguous or unrelated surviving changes into stories without confirmation; list them as proposed exclusions instead.
2. Resolve range after scope is confirmed:
   - Default to all committed branch changes against refreshed `origin/main`.
   - An exact user-supplied base wins.
   - If `origin/main` is unavailable, ask for a base and stop.
   - If the working tree is not clean and session delta was not chosen, ask whether to include it.
   - Retrieve linked issue, PR, or design context as supporting evidence.
3. Create a temporary inventory with `scripts/inventory_branch.py`.
4. Dispatch a dynamic swarm with at least two analysis agents and one
   independent auditor. Retry one failed agent, then reassign its partition.
5. Require structured JSON handoffs defined in `REFERENCE.md`. Scope by
   behavior, not path or commit subject. Use file-level coverage unless a mixed
   file requires hunk-level units.
6. Group by user/business problem, acceptance boundary, or rollout decision.
   Never split merely by commit, directory, language, or subsystem.
7. Draft from `assets/story-template.md`. Keep all content in the required
   Problem, Requirements, and Implementation sections unless the user requests
   more sections.
8. Build a temporary coverage manifest and run
   `scripts/validate_coverage.py` with every handoff. Write final files only
   after validation succeeds.
9. Write to
   `~/.agent/stories/<repo>/<branch-slug>/<short-head>/NN-<story-slug>.md`.
   Reuse equivalent output; version differing reruns without overwriting.
10. Delete temporary manifests unless the user requested audit artifacts, then
   report the output path, pinned SHAs, counts, exclusions, dispositions, and
   unresolved items.

## Story rules

- Use bullets in Problem, Requirements, and Implementation.
- Problem is plain language for a CEO or intern.
- Requirements begin with `Confirmed:`, `Inferred:`, or `Needs decision:`.
  Code and tests alone are never Confirmed.
- Implementation distinguishes `Current branch implementation`,
  `Recommended implementation`, and prioritized `Production readiness`.
- Cite commit and change IDs inline with current implementation details.
- Recommend only hardening needed to make the captured outcome safe, correct,
  operable, and supportable.
- Never run tests or builds. Say `Present in branch, not runtime-verified` when
  source evidence exists.
- Map generated output to its source. Missing or unverified regeneration
  becomes a readiness finding.
- For a scoped zero-result, create a context story only when reverted or
  superseded commit evidence exists. An entirely empty branch creates no file.

## Completion gate

Do not write final stories unless:

- Every commit is included, excluded with evidence, reverted, or superseded.
- Every surviving in-scope coverage unit has one primary story.
- The independent auditor rebuilt the inventory and found no gaps.
- Pairwise and alternative regrouping cannot reduce the coherent story count.
- The validator passes every story, coverage mapping, and agent handoff.

If coverage cannot be proven, write nothing and report the blocker.
