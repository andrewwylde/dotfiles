---
name: ship-feature
description: >
  Handle the full feature lifecycle autonomously -- from spec validation
  through reviewed PR. Chains vibe-test, plan, review, implement (TDD),
  commit, push, PR creation, self-review, mandatory Stage 6.5 test benchmark,
  mandatory Stage 6.6 Rust cognitive-complexity gate (auto-runs /code-simplifier
  when clippy flags changed lines), mandatory Stage 6.65 psgen/schema-first gate,
  mandatory Stage 6.7 scalar-lib-it gate
  (conditional /scalar-lib-it audit when plan or PR touches scalars), and a
  GitHub PR comment summarizing the review plus fixes after Stage 6.7 into a
  single flow. After Phase 6 (review, test benchmark, complexity, scalar-lib),
  every actionable finding is fixed automatically via /spec-driven or logged as
  a deferred Linear sub-issue under the parent ticket — never left as orphan
  nits. Use on "ship this", "build and PR", "implement end-to-end", "plan through PR", "build
  this feature", "make this happen", "implement and ship", or when the user
  describes a feature, bug fix, or refactor and expects autonomous delivery
  without manual step-by-step guidance. Also use when the user mentions
  provider-transformations, promote worker, Delta writes, DataFusion engine,
  Rust workspace crates, walking skeleton fixture, duroxide shell, cargo test
  or clippy failures under services/pkg/*-rs -- even if they do not say "ship"
  explicitly. Also use when the plan touches services/ingestion/, connector tap
  JSON under platform-schemas/data/, run_connector_direct, prove-200s, skippable
  HTTP 400 on connector backfills, or ingestion engine-first pytest -- even if
  the user only mentions Zoom, Bronze I empty windows, or connector smoke. Also
  use when the plan touches platform-schemas/services/, utils/psgen/, route-impl,
  .schema.ts, @psgen/* toolchain packages, or schema-first / build-schemas work --
  even if the user says "add an endpoint" or "change the schema" without naming
  psgen. Every /ship-feature run through Stage 5 MUST continue through Stages 6,
  6.5, 6.6, 6.65, and 6.7 automatically -- no user opt-in. Stage 6.6 always
  executes the complexity gate script; Stage 6.65 always executes psgen_gate.py;
  Stage 6.7 always executes scalar_lib_gate.py. When 6.6 triggers, /code-simplifier runs without asking. When 6.7 triggers,
  /scalar-lib-it runs without asking. Always respect global gate enforcement via
  ~/.cursor/skills/_shared/hooks/enforce-gate.sh and run
  ~/.cursor/skills/_shared/skill_gate.py before edits in gated phases.
---

# Ship Feature

Autonomous end-to-end pipeline: **validate → plan → review → implement → commit → PR → self-review → test benchmark → Rust complexity gate → psgen/schema-first gate → scalar-lib conformance gate**.

Each stage corresponds to an existing project command or skill. This skill
orchestrates them in sequence, handling state transitions and error recovery.

## Execution Directives

Take your time and go step by step in your review and analysis. Available
commands: see `~/.cursor/commands/` for reusable workflows.

## Autonomous Self-Healing Contract

`/ship-feature` is expected to recover from routine gate failures without
manual prompting. A failed review, benchmark, lint, test, or implementation
step is not automatically a stop condition. First classify it, log it, revise
the plan when the failure changes scope or test strategy, rerun the failed gate,
and continue when the gate passes.

Use this loop for recoverable failures:

1. **Classify** the failure as environment, missing prerequisite, plan gap,
   test gap, implementation bug, architecture blocker, or user-decision-needed.
2. **Log** the issue in the active Linear ticket when available. If Linear is
   unavailable, write `.context/issues/<task-id>_<slug>.md` and register it in
   the manifest.
3. **Revise** the plan through global `/plan-update` whenever the fix changes
   scope, assumptions, test strategy, phase ordering, or acceptance criteria.
4. **Retry** the failed gate after the plan or implementation is corrected.
5. **Stop only** when recovery would be destructive, credentials are missing
   and no fallback exists, a security/data-safety concern is unresolved, or the
   same gate fails after the documented retry limit.

This contract is the default behavior. Do not ask the user to manually run
Stage 3, update a plan, or decide routine test coverage fixes.

**Phase 6 extension:** Findings from pr-review, code-level test-benchmark,
scalar-lib-it, and complexity gate follow the same contract. Actionable items
are fixed via `/spec-driven` or ticketed under the parent Linear issue — never
left as comment-only recommendations. See
`references/stage-6-action-resolution.md`.

## Hard Pre-Flight Enforcement

Before any file modifications in plan/review/implementation stages, run:

```bash
python3 ~/.cursor/skills/_shared/skill_gate.py state --skill ship-feature
python3 ~/.cursor/skills/_shared/skill_gate.py check --skill ship-feature --action strreplace --file "<target-file>"
```

The global hook at `~/.cursor/skills/_shared/hooks/enforce-gate.sh` is fail-closed and blocks `StrReplace|Write|EditNotebook` when gate preconditions are not satisfied. Do not bypass this.

### Stage 4 Entry Invariant (Resume-Safe, Fail-Closed)

**Run this BEFORE editing any source file under `services/`, `apps/`,
`infrastructure/`, `utils/`, `platform-schemas/`, or any non-test non-doc
directory. Every invocation. Including resumed sessions.**

The `STOP -- IMMEDIATE FIRST ACTION REQUIRED` block below only fires when the
skill is explicitly invoked on a fresh turn. When a session is resumed from a
conversation summary, the main agent may pattern-match on "TDD in progress"
or "implement the flag" and skip straight to Stage 4 code edits without ever
re-reading this skill. This invariant catches that failure at the file-edit
boundary.

Artifact presence check:

```bash
TASK_KEY="$(git branch --show-current | sed 's|.*/||' | sed 's/-[a-f0-9]\{6,\}$//')"

echo "=== Stage 4 entry invariant for $TASK_KEY ==="

# 1. Session activation artifact
ls .context/sessions/*.json 2>/dev/null | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  session activated" \
  || echo "MISSING session -- activate_session.py was never run for this task"

# 2. Plan file for this branch
ls plans/*.plan.md 2>/dev/null | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  plan file exists" \
  || echo "MISSING plan -- Stage 1 (/plan-create) never ran"

# 3. Plan review artifact
ls .context/reviews/plan_*.md 2>/dev/null | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  plan review exists" \
  || echo "MISSING plan review -- Stage 2 (/plan-review) never ran"

# 4. DE adversarial decision
ls .context/adversarial/*.md 2>/dev/null \
  | xargs grep -l "DECISION.*APPROVE" 2>/dev/null \
  | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  DE adversarial approval exists" \
  || echo "MISSING adversarial approval -- Stage 3.5 never ran"

# 5. Plan-level test benchmark
ls .context/test-benchmarks/*_plan-level.md 2>/dev/null | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  plan-level test benchmark exists" \
  || echo "MISSING test benchmark -- Stage 3.75 never ran"

# 6. Deferral register (Stage 3.5b — zero-deferral note counts)
ls .context/deferrals/*_deferrals.md 2>/dev/null | grep -iE "$TASK_KEY" > /dev/null \
  && echo "OK  deferral register exists" \
  || echo "MISSING deferral register -- Stage 3.5b never ran"

# 7. psgen plan gate (Stage 3.7 — skip JSON counts)
test -f .context/psgen-gate-plan.json \
  && grep -q '"triggered"' .context/psgen-gate-plan.json \
  && echo "OK  psgen plan gate (Stage 3.7)" \
  || echo "MISSING psgen plan gate -- Stage 3.7 never ran"

# 8. Scalar-lib plan gate (Stage 3.8 — skip JSON counts)
test -f .context/scalar-lib-gate-plan.json \
  && grep -q '"triggered"' .context/scalar-lib-gate-plan.json \
  && echo "OK  scalar-lib plan gate (Stage 3.8)" \
  || echo "MISSING scalar-lib plan gate -- Stage 3.8 never ran"
```

**If ANY line reports `MISSING`, you are NOT cleared for Stage 4.**

Recovery paths (in order of preference):

1. **Diagnostic-debugger fast-path.** If a handoff doc exists for this task
   (`ls .context/debug/*.md | grep -iE "$TASK_KEY"`), Stages 0-3 are satisfied
   by the investigation. Stage 3.5 (DE adversarial) and Stage 3.75 (plan
   test-benchmark) still must run before any source edit. Route through those
   first.

2. **Fresh activation.** If no task has started yet in this branch, run
   `activate_session.py --from-branch` and execute Stages 0-3.75 in order.
   The `STOP -- IMMEDIATE FIRST ACTION` block below covers this path.

3. **Resumed session, state lost.** If the branch shows in-progress work
   (modified files, prior commits on the branch, checkpoint data) but
   planning artifacts are missing, the prior session was summarized after
   Stage 4 started but before artifacts were persisted -- or Stage 4 was
   entered without ever running Stages 0-3. **STOP.** Report to the user:

   > "Branch `<name>` has feature work in progress (`<N>` modified files,
   > `<M>` commits ahead of main), but the planning artifacts are missing:
   > `<list of MISSING items>`. Proceeding would bypass the gates this skill
   > exists to enforce. Options:
   > (a) reset the branch to origin/main and run the full pipeline from
   >     Stage 0, discarding current work
   > (b) keep current work, retroactively run Stages 0-3.75 against it
   >     (note: a plan written AFTER the code is a rubber stamp, not a plan
   >     -- I will flag this in the plan review)
   > (c) declare this task out of scope for `/ship-feature` and finish it
   >     as a direct commit"
   >
   > Do not proceed without explicit direction.

**Forbidden: backfilling artifacts.** Do not write a plan, review, or
adversarial decision to satisfy this check after code edits have already
begun. The artifacts are gates because they run before the code; a post-hoc
plan cannot gate anything. If you find yourself tempted to "just quickly
write the plan doc so the check passes," stop -- you are rationalizing the
exact anti-pattern this invariant exists to prevent.

## Bundled Resources

| Resource | Purpose | When to Load |
|----------|---------|-------------|
| `references/stage-details.md` | Full procedural details for all 7 stages | When executing a stage — load the relevant section |
| `references/psgen-stage-details.md` | psgen bootstrap, schema-first TDD, CI preflight, post-rebase | **Stage 0** worktree bootstrap; **Stage 4-6** when plan touches `platform-schemas/services/`, `utils/psgen/`, route-impl |
| `references/rust-stage-details.md` | Rust workspace TDD, CI pre-flight, integration tests | **Stage 4-6** when plan touches Rust crates (see language router in stage-details) |
| `references/ingestion-stage-details.md` | Ingestion connector TDD, engine-first tests, optional live smoke | **Stage 4-6** when plan touches `services/ingestion/` or `platform-schemas/data/*.json` |
| `references/pr-review-github-comment.md` | Required PR comment template after self-review | **Stage 6** — post **after Stage 6.7**, not 6.6 |
| `references/stage-6-action-resolution.md` | Fix-or-defer triage for all Phase 6 findings | **After Stages 6, 6.5, 6.65, 6.7** and **before PR comment** |
| `scripts/pipeline_status.py` | Pre-flight checks + pipeline state detection | **Always run first** at skill activation |
| `scripts/psgen_gate.py` | Stage 3.7 / 6.65 trigger detection | **Before** loading psgen-stage-details in 3.7 and 6.65 |
| `scripts/verify_gates.py` | Gate script smoke harness (CI/local) | After changing gate scripts or vendoring skill updates |
| `scripts/scalar_lib_gate.py` | Stage 3.8 / 6.7 trigger detection | **Before** `/scalar-lib-it` in 3.8 and 6.7 |
| `~/.cursor/skills/ship-feature/evals/` (not in repo) | Evaluation scenarios for skill testing | On-demand only; keep in global install (PAR-278) |

## Pipeline Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 0. VALIDATE  │───▶│ 1. PLAN      │───▶│ 2. REVIEW    │───▶│ 3. UPDATE    │
│ (vibe-test)  │    │ (plan-create)│    │ (plan-review)│    │ (plan-update)│
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                                         ┌─────────────────────────┘
                                         ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 3.5 DE       │───▶│ 3.75 TEST    │───▶│ 3.7 PSGEN    │
│ ADVERSARIAL  │    │ BENCHMARK    │    │ GATE         │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │ 3.8 SCALAR   │
                                        │ LIB-IT       │
                                        └──────┬───────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │ 3.5b DEFERRAL│
                                        │ REGISTER     │
                                        └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ 4. IMPLEMENT │
                 │ (spec-driven)│
                 └──────┬───────┘
                        │
                    ┌───┴──────────────────────────┐
                    ▼                              │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 5. SHIP      │───▶│ 6. SELF-     │───▶│ 6.5 TEST     │───▶│ 6.6 RUST     │
│ (commit-push │    │    REVIEW    │    │ BENCHMARK    │    │ COMPLEXITY   │
│  -pr)        │    │ (pr-review)  │    │ (code-level) │    │ GATE         │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │ 6.65 PSGEN   │
                                                              │ GATE         │
                                                              └──────┬───────┘
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │ 6.7 SCALAR   │
                                                              │ LIB-IT       │
                                                              └──────────────┘
```

Pipeline order: `0 → [0 bootstrap] → 1 → 2 → 3 → 3.5 → 3.75 → 3.7 → 3.8 → 3.5b → 4 → 5 → 6 → [6 action resolve] → 6.5 → [6 action resolve] → 6.6 → 6.65 → 6.7 → [6 action resolve + closure gate] → PR comment`

**Phase 6 action resolution** (orchestrator, not delegated): after Stages 6,
6.5, 6.65, and 6.7, triage every actionable finding — fix in-PR via `/spec-driven`
or defer with a Linear sub-issue. Read `references/stage-6-action-resolution.md`.
No orphan "optional follow-ups" without a commit SHA or ticket ID.

### Stage → Command/Skill Mapping

| Stage | Command/Skill | Key Output |
|-------|--------------|------------|
| 0 | `/vibe-test` skill | Gap report or skip note |
| 1 | `/plan-create` command | `plans/{name}_{hash}.plan.md` |
| 2 | `/plan-review` command | READY / READY WITH CHANGES / NOT READY |
| 3 | `/plan-update` command | Updated plan (max 2 cycles) |
| 3.5 | `/de-adversarial-reviewer` skill | APPROVE / APPROVE WITH CONDITIONS / BLOCK + **Deferral Register** |
| 3.75 | `/test-benchmark` (plan-level) | Scorecard + action items -> `/plan-update` if < 7 |
| 3.7 | `psgen_gate.py` + `psgen-stage-details.md` (conditional) | `.context/psgen-gate-plan.json` |
| 3.8 | `/scalar-lib-it` (Design, conditional) | `.context/scalar-lib-gate-plan.json` + optional `{task}_design.md` |
| 3.5b | deferral adjudication (orchestrator) | `.context/deferrals/{task-id}_deferrals.md` |
| 4 | `/spec-driven` command | Committed code + tests (reads 3.7/3.8 audits when present) |
| 5 | `/commit-push-pr` command | PR URL |
| 6 | `/pr-review-local` command (fix cycle: `/pr-review-update`) | `.context/prs/reviews/PR_REVIEW_#NNN.md` (GitHub comment **after 6.7**) |
| 6.5 | `/test-benchmark` skill, code-level (delegated) | Scorecard appended to PR review artifact |
| 6.6 | gate script (orchestrator) + `/code-simplifier` if triggered | Gate JSON + simplifier commit if triggered |
| 6.65 | `psgen_gate.py` (orchestrator) + schema-first checklist if triggered | `.context/psgen-gate-code.json` |
| 6.7 | gate script (orchestrator) + `/scalar-lib-it` Code if triggered | `.context/scalar-lib-gate-code.json` + optional `{task}_code.md` |

**Stages 6.5, 6.6, 6.65, and 6.7 are mandatory harness steps.** They run on every
ship-feature completion after Stage 6 -- not optional, not user-triggered.
Stage 6.6 always runs `rust_cognitive_complexity_gate.py`. Stage 6.65 always
runs `psgen_gate.py`. Stage 6.7 always runs `scalar_lib_gate.py`. When
6.6 `triggered: true`, `/code-simplifier` runs automatically. When 6.65
`triggered: true`, run schema-first checklist from `psgen-stage-details.md`.
When 6.7 `triggered: true`, `/scalar-lib-it` runs automatically.
Do not stop after Stage 6, 6.5, 6.6, or 6.65 and ask the user whether to continue.
The GitHub PR comment posts only after Stage 6.7 completes.

### Stage 3.5 Deferral Framework (mandatory with DE adversarial review)

**Goal:** Reduce silent deferrals. Deferral is a last resort — not a default
way to shrink scope. Anything not done in the current PR must be **tracked,
ticketed, and visible** before Stage 4 starts.

This framework runs **after** Stage 3.8 (scalar-lib plan gate) and
**before** Stage 4. The orchestrator owns deferral decisions; the adversarial
reviewer **proposes** candidates in a `## Proposed deferrals` section (see
`/de-adversarial-reviewer`, `plan-gate` mode). Stage 3.75 HIGH items are
adjudicated here too — not silently deferred in the PR.

#### Default stance: defer less

For every proposed deferral, the orchestrator must attempt **in-PR resolution
first**:

1. **Can it ship in this PR within the active ticket's acceptance criteria?**
   → Do it in Stage 4. Do not defer.
2. **Is it explicitly out of scope for the parent ticket** (different epic,
   different layer, different owner)? → Candidate for deferral **with ticket**.
3. **Is it blocked on another issue or external dependency?** → Defer **with
   ticket** and `blockedBy` link to the blocker.
4. **Is it test/quality hygiene** flagged by adversarial review or plan-level
   benchmark (error paths, negative cases, fixture DRY)? → Prefer adding to
   Stage 4 plan; defer only if estimate exceeds remaining PR scope (XS work
   stays in-PR).

If the orchestrator cannot articulate **why now is wrong** and **why later is
safe**, the item is **not deferrable** — either implement it or escalate to
the user.

#### Hard rules (never defer without tickets)

| Rule | Rationale |
|------|-----------|
| **No deferral of blocking adversarial or plan-review findings** | BLOCK / REQUEST CHANGES must be fixed or plan-updated |
| **No deferral of current-ticket acceptance criteria** | Acceptance gaps are the deliverable, not follow-ups |
| **No deferral of security, data-loss, or prod-mutation risks** | See prod-mutation guardrails |
| **No deferral without a Linear follow-up ticket** | Verbal "we'll do it later" is invalid |
| **No Stage 4 entry while deferrals lack ticket IDs** | Fail-closed gate |

#### Deferral Register (required artifact)

After adjudicating proposed deferrals, write:

`.context/deferrals/{task-id}_deferrals.md`

```markdown
RUN_BY_SKILL: ship-feature

# Deferral Register: {TASK-ID}

**Parent Linear:** {PAR-XXX}
**Adversarial artifact:** .context/reviews/adversarial_{plan-name}.md
**Date:** {ISO date}

| # | Item | Why not in this PR | Risk if ignored | Follow-up ticket | In PR body | In Linear comment |
|---|------|-------------------|-----------------|------------------|------------|-------------------|
| 1 | ... | ... | ... | PAR-YYY | [ ] | [ ] |
```

**For each approved deferral**, before Stage 4:

1. **Create a Linear sub-issue** under the active ticket (`parentId` = parent
   issue). Description must include: origin (adversarial/plan/benchmark),
   scope, acceptance checklist, file paths, and link to parent PR when known.
2. **Add a comment on the parent Linear ticket** listing all follow-up IDs.
3. **Update the plan** via `/plan-update` if deferrals change scope, phases,
   or acceptance criteria — include ticket IDs in a `## Deferred (ticketed)`
   section.
4. Mark register columns `In PR body` / `In Linear comment` as done when
   complete.

**Rejected deferrals** (resolved in-PR instead): list under
`## Deferrals rejected (shipping in this PR)` with one-line rationale.

#### Stage 5 and 6 carry-forward

- **PR body (Stage 5):** include `## Deferred (follow-up tickets)` with
  markdown links to every follow-up issue. Empty section only when the
  register has zero approved deferrals.
- **PR self-review comment (Stage 6):** `Residual / deferred` table must
  include ticket ID + URL for each deferred item (see
  `references/pr-review-github-comment.md`).
- **Session summary:** list deferred ticket IDs under `**Deferred:**`.

#### Phase 6 deferrals (post-review, mandatory triage)

After Stages 6, 6.5, and 6.7, the orchestrator runs **Stage 6 Action
Resolution** (`references/stage-6-action-resolution.md`). Every actionable
finding from pr-review, test-benchmark HIGH items, and scalar-lib critical/P1
recommendations must end as either:

1. **Fixed** — `/spec-driven` TDD batch, commit pushed, logged in
   `.context/implementation/stage-6-fix-log.md`
2. **Deferred** — Linear sub-issue under parent + row in deferral register
   under `## Phase 6 deferrals (post-review)`

**Forbidden:** APPROVE WITH NOTES / "pre-rollout recommendations" / scorecard
HIGH items that appear only in the PR comment with no commit and no ticket.

Append Phase 6 deferrals to the existing `.context/deferrals/{task-id}_deferrals.md`
from Stage 3.5b — do not create a separate register file.

#### Gate check before Stage 4

```bash
TASK_KEY="$(git branch --show-current | sed 's|.*/||' | sed 's/-[a-f0-9]\{6,\}$//')"
REG=".context/deferrals/${TASK_KEY}"*"_deferrals.md"
ls $REG 2>/dev/null | head -1 | xargs grep -q "RUN_BY_SKILL: ship-feature" \
  && echo "OK  deferral register exists" \
  || echo "MISSING deferral register -- run Stage 3.5b deferral adjudication"

# Every approved deferral row must have a PAR-/ENG-/etc ticket id in Follow-up ticket column
# If Proposed deferrals existed and any lack tickets → STOP before Stage 4
```

If the adversarial review lists **zero** proposed deferrals and plan/benchmark
introduce none, still write a minimal register:

`No approved deferrals. All conditions addressed in-PR or rejected.`

#### Subagent prompt addition (Stage 3.5)

When delegating DE adversarial review, append to the subagent prompt:

```
After your review, add a ## Proposed deferrals section. For each condition or
gap you would otherwise leave for "later", propose deferral ONLY if genuinely
out of parent-ticket scope. Each row: item, why-not-now, risk-if-ignored,
suggested follow-up title. Prefer in-PR fixes for XS–S items. Do NOT create
Linear tickets — the orchestrator adjudicates and creates tickets per the
ship-feature Stage 3.5 Deferral Framework.
```

### Provenance Contract

Each stage artifact must identify the command or skill that produced it. This
prevents a generic subagent from manufacturing a file that merely looks like a
valid gate artifact.

Required markers:

| Artifact | Required marker |
|----------|-----------------|
| Plan | `RUN_BY_COMMAND: plan-create` |
| Plan review | `RUN_BY_COMMAND: plan-review` |
| Adversarial review | `RUN_BY_SKILL: de-adversarial-reviewer` |
| Deferral register | `RUN_BY_SKILL: ship-feature` (Stage 3.5b) |
| Plan-level test benchmark | `RUN_BY_SKILL: test-benchmark` |
| Psgen plan gate JSON | `RUN_BY_SCRIPT: psgen_gate.py` |
| Psgen code gate JSON | `RUN_BY_SCRIPT: psgen_gate.py` |
| Scalar-lib plan audit (3.8) | `RUN_BY_SKILL: scalar-lib-it` |
| Scalar-lib code audit (6.7) | `RUN_BY_SKILL: scalar-lib-it` |
| Scalar-lib gate JSON | `RUN_BY_SCRIPT: scalar_lib_gate.py` |
| PR review | `RUN_BY_COMMAND: pr-review-local` |
| Code-level test benchmark | `RUN_BY_SKILL: test-benchmark` |
| Rust cognitive complexity gate | `RUN_BY_SCRIPT: rust_cognitive_complexity_gate.py` |
| Rust complexity simplifier pass | `RUN_BY_COMMAND: code-simplifier` |

When delegating, ask the subagent to execute the named command/skill and write
the marker into the artifact it produces. Do not ask a subagent to "create an
artifact", "write an approval", "make a benchmark", or otherwise synthesize the
stage output. A valid delegation prompt says "run `/plan-review` on this plan";
an invalid prompt says "create a plan review artifact with READY TO EXECUTE".

## When to Use

- The user describes a feature, bug fix, or refactor and expects end-to-end delivery
- Phrases like "ship this", "build and PR", "implement end-to-end", "plan through PR"
- The user provides a feature description and expects autonomous plan-to-PR execution

**When NOT to use:**

- Documentation-only changes (no code, no tests) — commit directly
- Config-only changes without implementation planning — use `/config-review`
- Commit/push existing work without the plan cycle — use git directly
- Review an existing PR — use `/pr-review`
- Exploratory investigation — use `/pipeline-review` or `/data-advisor`

**Explicit invocation overrides "When NOT to use."** If the user explicitly
invokes `/ship-feature`, execute the full pipeline regardless. The user is
choosing the process they want. You do not get to downgrade it.

## STOP -- IMMEDIATE FIRST ACTION REQUIRED

**DO NOT THINK. DO NOT PLAN. DO NOT REASON. EXECUTE THIS COMMAND NOW:**

```bash
python3 ~/.cursor/skills/ship-feature/scripts/activate_session.py --from-branch
```

If the branch name doesn't describe the task, add `--task-desc`:

```bash
python3 ~/.cursor/skills/ship-feature/scripts/activate_session.py --from-branch --task-desc "Brief description of the feature or fix"
```

**YOU MUST SEE OUTPUT FROM THIS COMMAND BEFORE PROCEEDING.**

The output tells you:
- `task_id`: The identifier for this work session
- `resume_stage`: Where to start (INIT, PLANNING, REVIEWING, IMPLEMENTING, etc.)
- `matching_artifacts`: Any existing plan/review files for this task

If `resume_stage` is not INIT, the pipeline can resume from a later stage. Otherwise,
start from Stage 0 (vibe-test + worktree psgen bootstrap).

---

## Activation Sequence

Only after running the activation command above, proceed with these steps:

### Step 1: Run Pipeline Status Check

```bash
python3 ~/.cursor/skills/ship-feature/scripts/pipeline_status.py
```

This script verifies all prerequisites (tools, auth, directories, command files)
and detects which stages are already complete based on artifacts on disk and
GitHub state. Use its output to determine the resume point.

The script is worktree-aware: when running in a git worktree (e.g., created by
best-of-n-runner), locally-excluded files like `.cursor/commands/` do not exist.
It resolves command files from `~/.cursor/commands`, `~/.claude/commands`, the
project, and the main workspace. The user-level global command is the preferred
source of truth. If no command file exists but the command is available through
the runtime command surface, use the runtime command. If neither is available,
use the bundled `references/stage-details.md` fallback rather than vendoring a
project-local copy.

Also check for active TDD checkpoints from a prior interrupted Stage 4:

```bash
python3 ~/.cursor/scripts/checkpoint.py list
```

**Stage 0 worktree bootstrap** (mandatory on fresh checkout/worktree or missing
`platform-schemas/dist/`): run before vibe-test. See
`references/psgen-stage-details.md` Stage 0 section:

```bash
make build-scalar-lib
make build-schemas
# when task touches .schema.ts or utils/psgen/packages/:
make typecheck-psgen-toolchain
```

If an active (in-progress) checkpoint exists for the current task, Stage 4 can
resume mid-implementation via `spec-driven`'s checkpoint resume protocol.

Also run the MCP health pre-flight to detect unreachable servers before
mid-pipeline failures:

```bash
python3 ~/.cursor/scripts/mcp_health.py check --timeout 3
```

If any servers are unhealthy, check whether the current pipeline depends on them:

```bash
python3 ~/.cursor/scripts/mcp_health.py deps --skill ship-feature --timeout 3
```

If a required server is unhealthy, check its fallback:

```bash
python3 ~/.cursor/scripts/mcp_health.py fallback --server <name>
```

**MCP failure protocol:**
- If `linear` is unhealthy or needs auth: Stage 5 (PR creation) can use `gh` CLI
  directly. Note this in the todo list as "Linear MCP unavailable; using gh CLI."
- If `prefect-prod` or `prefect-legacy` is unhealthy: pipeline-health-check and
  prefect-debugger stages use curl fallback (see prefect skill documentation).
- If a server needs auth: call `mcp_auth` for that server before proceeding.
- Never retry a failed MCP call more than twice. After two failures, switch to
  the documented fallback for that server.

Check if a postmortem is overdue:

```bash
if [ -f .context/.last_postmortem ]; then
  echo "Last postmortem: $(cat .context/.last_postmortem)"
else
  echo "No postmortem has been recorded. Consider running /postmortem after this session."
fi
```

If 5+ sessions have occurred since the last postmortem, note in the todo list:
"Postmortem suggested -- 5+ sessions since last analysis."

### Step 1.5: Linear Ticket Gate (mandatory)

Before any stage executes, ensure a Linear ticket exists for this work.
Every ship-feature pipeline run must be traceable in Linear. Follow the
full protocol in `~/.cursor/skills/_shared/LINEAR_TICKET_GATE.md`.

**MCP server priority:** `user-linear` first, then `plugin-linear-linear`
(requires `mcp_auth` call with `{}` first), then ask the user manually.

1. Check branch name for a ticket ID (already extracted in Step 0 activation)
2. Check `--linear` flag or active session's `ticket_id` field
3. Search Linear for a matching in-progress ticket:
   ```
   CallMcpTool(server="user-linear", toolName="list_issues", arguments={
     "query": "<feature description keywords>",
     "team": "Parable",
     "state": "started",
     "assignee": "me",
     "limit": 10
   })
   ```
4. If no match, create one:
   ```
   CallMcpTool(server="user-linear", toolName="save_issue", arguments={
     "title": "<type>(<scope>): <feature description>",
     "description": "Ship-feature pipeline for <description>.\n\n**Triggered by:** /ship-feature\n**Branch:** <branch-name>",
     "team": "Parable",
     "priority": 3,
     "state": "In Progress",
     "assignee": "me",
     "labels": ["agent-created"]
   })
   ```
5. Record the ticket ID in the todo list and environment.

The ticket ID must appear in:
- The plan file header (Stage 1)
- The PR title and body (Stage 5) -- title format: `<type>(<TICKET-ID>): <description>` (e.g. `feat(SYSTEM-47): add auth flow`) to pass `ci/pr-title-format`
- Commit messages where practical
- The session summary (Step 5)

On pipeline completion (Step 4), update the ticket:
- PR created successfully -> set state to "In Review"
- Pipeline failed at a stage -> add comment with failure details, leave In Progress

If both MCP servers are unavailable, ask the user for a ticket ID. Do NOT
skip the gate -- record `LINEAR_TICKET_SKIPPED` with reason and ensure the
PR description notes the missing ticket.

### Step 2: Load Stage Details

Read `references/stage-details.md` for the full procedure of the stage you are
about to execute. Each stage section includes inputs, procedure, state produced,
and failure modes.

### Step 3: Execute Stages in Order

Execute all stages from the resume point through **Stage 6.7**. **No stage may
be skipped, combined, or shortened** -- including 6.5, 6.6, and 6.7. Do not pause
between stages unless a stage fails. If a stage fails, run the Autonomous
Self-Healing Contract before stopping. Report and stop only after recovery is
exhausted or unsafe.

**Stage 6.6 harness rule (automatic):** Immediately after Stage 6.5 completes,
run the cognitive-complexity gate script. Do not ask the user. If
`triggered: true`, run `/code-simplifier` on actionable functions, commit,
push, re-run gate (max 2 simplifier cycles per Error Recovery table). Append
results to the PR review artifact.

**Stage 6.65 harness rule (automatic):** Immediately after Stage 6.6 completes,
run `psgen_gate.py --mode code`. Do not ask the user. If `triggered: true`,
audit diff against `references/psgen-stage-details.md` and fix critical findings
(max 2 `/spec-driven` batches). Append Stage 6.65 section to PR review.

**Stage 6.7 harness rule (automatic):** Immediately after Stage 6.65 completes,
run `scalar_lib_gate.py --mode code`. Do not ask the user. If `triggered: true`,
run `/scalar-lib-it` Code mode on the PR diff, fix critical findings (max 2
cycles), append results to the PR review artifact, then post the GitHub PR
comment. If `triggered: false`, document the skip reason and post the comment.

**Diagnostic-debugger fast-path**: Check for handoff docs by querying the
manifest. When the task description mentions a specific module, tap, or stream,
use `--task` to scope the query:

```bash
# Task-scoped query (preferred -- matches handoff to this specific task)
python3 ~/.cursor/scripts/manifest.py query --skill "diagnostic-debugger" \
  --type "debug-handoff" --status "active" --task "<module-or-tap>"

# Fallback: latest handoff if task scope is ambiguous
python3 ~/.cursor/scripts/manifest.py query --skill "diagnostic-debugger" \
  --type "debug-handoff" --status "active" --latest
```

**Disambiguation when multiple handoffs match:** If the task-scoped query
returns multiple entries, prefer the most recent (`created_at` descending).
If two handoff docs cover overlapping investigations, read both summaries
and select the one whose root cause matches the current task description.

If no manifest entry matches, fall back to scanning `.context/debug/*` by
naming convention.

When a handoff doc exists for this task, Stages 0-3 are already satisfied by
the diagnostic investigation. The handoff doc contains root cause (= plan),
reproduction test (= Red phase input), and blast radius (= review). Resume
directly at Stage 4 with the handoff doc as the spec-driven input. The todo
list should note: "Stages 0-3: Satisfied by diagnostic-debugger handoff
(`<path>`)".

**Stages 1-2 are delegated as a single subagent call** (see Command Delegation
Protocol). Stage 3 is a separate delegation if needed. Do NOT perform plan
creation or review inline — the subagent runs both commands sequentially.

### Step 4: Post-Pipeline Completion

After Stage 6.7 completes, run the goal-aware completion check. This is not
optional -- always check, even if you don't expect an active goal.

```bash
python3 ~/.cursor/scripts/goal.py list
```

If an active goal exists whose description matches this task:
1. Register the PR review in the manifest (Stage 6 already does this).
2. Advance the goal: `goal.py advance --goal <id> --skill ship-feature --artifact <pr-review-entry-id>`
3. Write a handoff: `goal.py handoff --goal <id> --step <N> --from-skill ship-feature --summary "PR #NNN created and self-reviewed. <blocking issues or clean review>."`
4. The `/investigate` orchestrator routes the goal to `pr-review` or marks it complete.

If no active goal exists, present the standard completion summary to the user.

### Step 5: Write Session Summary

After all stages complete (or on pipeline exit for any reason), clear the active
gate session so unrelated workspace edits are not blocked:

```bash
python3 ~/.cursor/skills/ship-feature/scripts/activate_session.py --deactivate
```

Then write a
structured summary. This is the "progress file" pattern from Anthropic's
long-running agents paper -- a compact record that future sessions can read
in ~100 tokens instead of searching transcripts at 100K+ tokens.

```bash
mkdir -p .context/summaries
```

Create `.context/summaries/<task-id>.md` with this structure:

```
## Session Summary: <task-id>
**Date**: <ISO date>
**Linear**: <TICKET-ID> or LINEAR_TICKET_SKIPPED (reason)
**Stages completed**: <list>
**What was built**: <1-2 sentences>
**Key decisions**: <bullet list of non-obvious choices>
**Deferred**: <anything explicitly punted>
**PR**: <URL or "none">
**Blockers**: <any unresolved issues>
```

Register in manifest:

```bash
python3 ~/.cursor/scripts/manifest.py register \
  --skill "ship-feature" \
  --path ".context/summaries/<task-id>.md" \
  --type "session-summary" \
  --task "<task-id>" \
  --tags "summary"
```

Write the summary even if the pipeline failed partway -- the failure context
is valuable for the next session. When resuming, future pipeline_status.py
runs should check for recent summaries:

```bash
python3 ~/.cursor/scripts/manifest.py query --type session-summary --latest
```

## Command Delegation Protocol

Planning commands (`/plan-create`, `/plan-review`, `/plan-update`) are **always
delegated to command-runner subagents**. The subagent's job is to execute the
named command file exactly, not to infer the desired artifact and write it from
scratch. This separation exists because: (a) the subagent follows the command
file procedure end-to-end without the orchestrator's context biasing it toward
shortcuts, (b) the plan and review artifacts are produced as a pair with a
verifiable audit trail, and (c) inline execution invites the "just this one
small fix" rationalization that leads to plan/review drift.

If a stage maps to a skill rather than a command (`de-adversarial-reviewer`,
`test-benchmark`, `pr-review`), delegate the **skill invocation** in the same
command-runner style: the prompt must name the skill path or slash command and
instruct the subagent to follow that skill's instructions. The prompt must not
specify the final verdict, score, or approval marker.

**Stage -> Delegation mapping:**

| Delegation | Commands | Command source | Output artifacts |
|------------|----------|--------------|------------------|
| Stages 1+2 | `/plan-create` then `/plan-review` | Global command first, then project/worktree, runtime, bundled fallback | `plans/{name}_{hash}.plan.md` + `.context/reviews/plan_{name}.md` |
| Stage 3 | `/plan-update` then re-run `/plan-review` | Global command first, then project/worktree, runtime, bundled fallback | Updated plan file + updated review |
| Stage 6 | `/pr-review-local <PR_NUMBER>` (fix: `/pr-review-update`) | `.context/prs/reviews/PR_REVIEW_#NNN.md` |
| Stage 6.5 | `/test-benchmark <PR_NUMBER>` | Code-level scorecard |
| Stage 6.6 | `/code-simplifier` (if gate triggered) | Simplifier commit + gate JSON |
| Stage 6.7 | `/scalar-lib-it code` (if gate triggered) | Scalar audit + gate JSON |

### Pre-Delegation: Write Context Pack

Before invoking the Task tool, write a context pack to disk. The context pack
captures conversational nuance that a flat prompt string loses -- the user's
intent, explicit constraints, prior decisions, domain context, and related files.

```bash
python3 ~/.cursor/scripts/context_pack.py write \
  --task "<feature description>" \
  --intent "<why the user wants this -- motivation, not just what>" \
  --constraints "<explicit constraints from the conversation>" \
  --domain-context "<architecture knowledge, recent changes, conventions>" \
  --prior-decisions "<decisions already made that the subagent must respect>" \
  --related-files "<comma-separated file paths the user referenced>" \
  --conversation-summary "<key conversational points beyond the task description>" \
  --delegating-skill "ship-feature" \
  --target-commands "plan-create,plan-review"
```

Record the returned `relative_path`. The subagent prompt references this file.

**What to capture in each field:**

| Field | What to extract from the conversation |
|-------|--------------------------------------|
| `--intent` | The user's *why* -- not "add retry logic" but "production uploads fail intermittently and they want resilience" |
| `--constraints` | Explicit statements like "do not use X", "must support Y", "max N" |
| `--domain-context` | Architecture knowledge: where the code lives, what frameworks/patterns are used, recent changes that affect the task |
| `--prior-decisions` | Anything already decided: "we agreed to use approach A over B because..." |
| `--related-files` | Files the user mentioned, opened, or that you identified as relevant during conversation |
| `--conversation-summary` | The narrative arc: what was discussed, what alternatives were considered, what was ruled out |

### Plan Deduplication

Before delegating Stages 1+2, check for existing plans that might match:

```bash
ls -la plans/*.plan.md | grep -i "$(git branch --show-current | sed 's|.*/||' | tr '-' '\n' | sort -u | head -3 | tr '\n' '|' | sed 's/|$//')"
```

If plans already exist for this feature (from a prior session or interrupted
run), the orchestrator must decide:
- **Stale plan, no longer relevant**: Delete it before delegating.
- **Valid plan from prior session**: Skip Stage 1, proceed to Stage 2 (review)
  or Stage 3 (update) depending on whether a review also exists.
- **Ambiguous**: Ask the user which plan to keep.

The subagent prompt for Stages 1+2 must also include the branch name so the
subagent can verify no matching plan already exists in `plans/` before creating
a new one. If a matching plan exists, the subagent should report it back rather
than creating a duplicate.

### Delegation for Stages 1+2 (plan-create -> plan-review)

Resolve command instructions before filling in the prompt template:
- Global `~/.cursor/commands`
- Global `~/.claude/commands`
- Project-local `.cursor/commands`
- Main workspace `.cursor/commands` when running in a worktree
- Runtime command surface if no command file exists
- Bundled `references/stage-details.md` fallback if the command is unavailable

Do not copy or create repo-local command files just to satisfy a worktree.

```
Task(
  subagent_type="generalPurpose",
  description="Stages 1+2: plan-create then plan-review",
  prompt="CONTEXT PACK: Read .context/delegations/{context-pack-filename} FIRST.
          This file contains user intent, constraints, prior decisions, and domain
          context that are essential for producing an accurate plan. Constraints
          and prior decisions in the context pack override general heuristics.

          Then execute two commands in sequence:

          PRE-CHECK -- Before creating a plan, list plans/ and check whether a
          plan already exists for this feature. The branch is {branch_name}.
          Match on word stems (e.g. 'transform' matches 'transformation').
          If a matching plan exists, DO NOT create a new one. Instead return:
          'EXISTING_PLAN: {path}' and skip to STEP 2 (review the existing plan).

          STEP 1 -- Execute /plan-create for the following feature. If a command
          file exists in the resolved command path, read it first. If no file
          exists, use the runtime /plan-create command surface. If that is also
          unavailable, follow the Stage 1 plan procedure in ship-feature's
          bundled stage-details fallback:

          {feature description + DEGRADED gaps}

          IMPORTANT: Step 5.7 (Build Assumption Ledger) is mandatory. The plan
          must include an Assumption Ledger section where every assumption is
          numbered, paired with its decision AND the rejected alternative, and
          verified against the codebase.

          Save the plan to plans/. Add this exact marker near the top:
          RUN_BY_COMMAND: plan-create. Record the plan file path.

          STEP 2 -- Execute /plan-review on the plan file from Step 1. If a
          command file exists in the resolved command path, read it first. If no
          file exists, use the runtime /plan-review command surface. If that is
          also unavailable, follow the Stage 2 review procedure in ship-feature's
          bundled stage-details fallback. Save the review to .context/reviews/.
          The review must include the Assumption Audit (Step 3.9).
          Add this exact marker near the top:
          RUN_BY_COMMAND: plan-review.

          Return: (1) plan file path, (2) review file path, (3) review decision
          (READY TO EXECUTE / READY WITH CHANGES / NOT READY),
          (4) assumption audit summary (total/verified/unverified/implicit)."
)
```

**After subagent completes:**
1. Verify BOTH artifacts exist on disk (plan file AND review file)
2. Read the review to extract the decision AND the assumption audit summary
3. If READY TO EXECUTE and no blocking unverified assumptions → proceed to Stage 4
4. If READY WITH CHANGES or NOT READY → delegate Stage 3
5. If assumption audit found blocking unverified assumptions → delegate Stage 3
   even if review decision was READY TO EXECUTE

**Stage 4** is executed directly by the main agent (TDD cycles, git, iterative
fixes) because it benefits from the orchestrator's full context window.

**Stages 6, 6.5, and conditional 6.6/6.7 subagent runs** are **always delegated**
to command-runner subagents. The subagent prompt is **only** the slash command —
no context pack, no feature description, no justification text. Examples:

```
/pr-review-local 4027
/test-benchmark 4027
/code-simplifier
/scalar-lib-it code
```

For Stage 6 fix cycles after blocking findings, delegate `/pr-review-update
<PR_NUMBER>` (same prompt-only rule).

The orchestrator runs gate scripts for 6.6 and 6.7, then delegates the slash
command only when `triggered: true`. The orchestrator posts the GitHub PR
comment after Stage 6.7 — not the Stage 6 subagent.

**Anti-pattern: rubber-stamping Stage 6+ artifacts.** Writing
`.context/prs/reviews/PR_REVIEW_#NNN.md`, test benchmark scorecards, or scalar-lib
audits inline without spawning a subagent that runs the named slash command is
forbidden. If the artifact lacks the provenance marker or no subagent ran the
command, the stage is incomplete — re-delegate with the slash command only.


### Stage 5 draft-first workflow

Stage 5 uses a **two-tier preflight** model. Tier A (fmt, clippy, go build, targeted
tests, squawk) runs locally and blocks the skill step on failure — cheap and
deterministic. Tier B (full docker matrix, postgres-gated integration) is
best-effort: run when env is available; otherwise write an env-skip artifact and
**push a draft PR anyway**. CI is the enforcement boundary for Tier B.

**Procedure:**

1. Rebase onto `origin/main`; re-run hygiene.
2. Run `commit_push_pr_preflight.py --phase push` (Tier A + best-effort Tier B).
3. Push branch: `git push -u origin HEAD` (never blocked locally by default).
4. Create **draft** PR: `/commit-push-pr --draft` or `gh pr create --draft ...`.
5. Stage 6: `/pr-review-local` while CI runs; fix CI failures; push; repeat.
6. Mark ready: `gh pr ready` only when CI green and review resolved.

**Opt-in local hard gate:** `export STAGE5_PUSH_GATE=1` — blocks push when artifacts
are missing, failed, HEAD-stale, or convenience-skip stamped. Env skips
(`postgres_unreachable`, `docker_unavailable`, `budget_exceeded`,
`detect_only_deferred_to_ci`) are allowed. Draft PR create is never blocked.

### Stage 5 Rust gate

Rust Stage 5 preflight runs via `commit_push_pr_preflight.py --phase push` before
push during `/ship-feature`. The script auto-runs `make build-schemas` when needed,
then `cargo fmt`, `clippy`, and `test` on touched crates.

**CI is the enforcement boundary** — push is not blocked locally by default.
Optional hard gate: `export STAGE5_PUSH_GATE=1` (see `hooks/README.md`).

**Local iteration only:** `--skip-tests` stamps `skip_tests_flag`. When
`STAGE5_PUSH_GATE=1` and Rust paths are in the diff, the opt-in hook rejects that
artifact — re-run without the flag before push.

### Stage 5 Docker build gate (PARABLE-451)

When `docker-build-matrix.py --detect-keys` returns non-empty for the branch diff,
run before push:

```bash
python3 ~/.claude/skills/ship-feature/scripts/docker_build_stage5_preflight.py \
  --base origin/main \
  --out .context/docker-build-stage5-preflight.json
```

Path filter uses `.github/docker-build.json` (same SSOT as PR #4371). Push-phase
router uses `--detect-only` (defers builds to CI). Local builds are capped
(`--max-images 3`, `--max-minutes 15`) when run explicitly without `--detect-only`.
CI runs docker-build-validation on the PR. With `STAGE5_PUSH_GATE=1`, the opt-in
hook denies push when the artifact is missing, failed, HEAD-stale, or stamped with
a convenience skip flag while docker inputs are in the diff.

**Local iteration only:** `--skip-build` stamps `skip_build_flag`. Re-run without
`--skip-build` before push when using the opt-in gate.

### Stage 5 ingestion / provider gates

Ingestion and provider-shell prefights follow the same artifact contract. Run
`commit_push_pr_preflight.py --phase push` during ship-feature; CI validates on
the PR. Opt-in local block: `STAGE5_PUSH_GATE=1`.

### Stage 5 PR Description Handoff

**Rust Stage 5 gate (mandatory before `/commit-push-pr` when `*.rs` changed):**

```bash
python3 ~/.claude/skills/ship-feature/scripts/rust_stage5_preflight.py \
  --base origin/main \
  --out .context/rust-stage5-preflight.json
```

The script runs `make build-schemas` when needed, then `cargo fmt --check`,
`cargo clippy -D warnings` (with downstream crates when shared pkg APIs change),
and `cargo test --all-targets`. CI on the PR is authoritative; local push is not
blocked unless `STAGE5_PUSH_GATE=1`.

Before invoking `/commit-push-pr`, prepare a compact PR narrative handoff so the
PR body explains the outcome rather than reciting the diff. Pass this context to
`/commit-push-pr` and preserve it in the PR body:

- **Expected Behavior:** what users or operators can safely do after merge. If
  the user supplied explicit phrasing such as `Expected behavior after all
  merge: ...`, carry that substance forward. Do not compress it into vague
  wording like "improves backfills."
- **Motivation:** why the change matters, who is affected, and why now.
- **Operational Guarantees:** recovery behavior, bounded fanout, durable
  progress, completion or health reporting, overwrite semantics, tuning knobs,
  or similar reliability promises when relevant.
- **Verification Mapping:** tests or manual checks that prove each important
  expected behavior.

For operator-facing work, the PR should include an `Expected Behavior` section
that reads like an acceptance outcome. Example: "After merge, operators can
safely recover large or partial transformation backfills with bounded fanout,
durable progress tracking, accurate completion and health reporting, explicit
full-dataset overwrite when needed, and tunable forced Silver batch sizes."

**Stage 4 checkpoint awareness**: `spec-driven` manages TDD checkpoints
automatically (init at Phase 1, record at each cycle, close at Phase 3).
If a prior session was interrupted mid-Stage-4, check for an active checkpoint:

```bash
python3 ~/.cursor/scripts/checkpoint.py list
```

If an active checkpoint exists for the current task, `spec-driven` Phase 0
detects it and resumes from the last recorded cycle. The plan file path is
stored in the checkpoint, so Stage 4 does not need to re-locate the plan.

## Execution Protocol

**Anti-pattern: Jumping to Stage 4** because changes "seem simple." Every change
benefits from a plan that can be reviewed. A trivial plan is fine — Stage 2
confirms it quickly. Exception: diagnostic-debugger handoffs (see fast-path
above) where the investigation IS the plan.

**Anti-pattern: Applying plan-update fixes inline.** When the review returns
READY WITH CHANGES, the temptation is to "just fix these small things" directly
in the plan file. This is how review feedback gets half-applied, audit trails
disappear, and the plan drifts from what was actually reviewed. The delegation
table explicitly maps Stage 3 to a `/plan-update` subagent. Always delegate it.
Two-line typo fixes and 20-line restructurings get the same treatment -- the
subagent reads the review, applies changes, and re-verifies. If the fixes truly
are trivial, the subagent finishes fast. The cost of delegation is low; the cost
of a plan/review mismatch during Stage 4 is high.

**Anti-pattern: Declaring scope "out of scope."** Stage 2 reviews execution
readiness — whether the plan CAN be implemented. It does not re-evaluate WHETHER
the feature should exist. Scope is the user's decision.

**Anti-pattern: Flagging the deliverable as a "blocking issue."** If the plan
adds identity resolution and Phase 3 adds HAA generalization, that is the
deliverable, not a blocker. Review whether the phase is technically executable.

**Anti-pattern: Requirement substitution.** When the user gives an explicit
technical requirement (e.g., "parse raw_json to extract ephemeral domain_date"),
the agent substitutes an easier proxy (e.g., "just scan Silver" or "compare on
a different column"). This is the inverse of sycophancy — instead of agreeing
with wrong inputs, the agent *disagrees* with correct inputs by silently
downgrading the implementation. **If the user corrects you, implement what they
said. Do not reinterpret, simplify, or propose an alternative unless you can
articulate why it's objectively superior AND the user agrees.**

**Anti-pattern: Pushing without a full service build.** Running `gofmt -w` on
changed files and `go build ./cmd/server` is not enough. When new ORM entities
are added, the generated `TxInterface` expands. Production packages compile
fine because they use the real DB types. But test packages define mock Tx
structs that list every method explicitly -- these break. Only
`go build ./...` (from the service root) compiles test packages too.

**Anti-pattern: Narrow Rust compile.** Running `cargo build -p parable-deltalake-rs`
alone misses downstream integration test breakage in `provider-transformations`
and `query-layer`. Before push, run
`~/.claude/skills/ship-feature/scripts/rust_stage5_preflight.py` (expands touched crates to downstream members) or use `cargo test -p <crate> --all-targets` and
widen manually when shared APIs change (see `references/rust-stage-details.md`).
Similarly,
`squawk` on migration files catches SQL formatting issues that CI's `sqlfluff`
will reject. The CI pre-flight in Stage 5 exists to catch exactly this class
of cross-package breakage before pushing.

**Anti-pattern: Replacing Stage 6 with an informal diff scan or inline synthesis.**
After a long implementation session, the orchestrator may skip delegating
`/pr-review-local` and instead write a short review from memory or a quick diff
scan. This is the most common Stage 6 failure mode — no adversarial subagent run,
no cross-function parameter tracing, no contract-gap analysis. Stage 6 exists
because the author is the worst reviewer of their own code. Delegate
`/pr-review-local <PR_NUMBER>` with no other prompt text.

**Simplicity check (Stage 4 entry gate)**: Before beginning each TDD cycle in
Stage 4, ask: "What is the simplest change that satisfies this cycle's test?"
If the answer involves introducing a new abstraction, helper module, or config
layer that nothing else reuses, do not introduce it. Inline the logic. Two clear
lines beat a named abstraction that will only ever have one caller. This is the
addyosmani "Rule 0" principle -- increment, do not reinvent. Complexity creep
during implementation is the #1 reason PRs balloon from the plan's estimated
scope. Each cycle should produce a minimal diff against the previous cycle, not
a refactoring of the surrounding architecture.

**Blast-radius gate (Stage 4 entry gate)**: Before coding any contract/API fix,
enumerate all call sites/usages. Either migrate all now or explicitly list
deferred paths with issue IDs in the plan/review artifacts. Do not ship a
single-call-site patch when the same failure pattern exists elsewhere.

## Stage 6 Execution Protocol

Stage 6 delegates `/pr-review-local <PR_NUMBER>` to a command-runner subagent.
The review **artifact** is produced by that subagent; the **GitHub comment** is
posted by the orchestrator after Stage 6.7 completes.

This is not optional, not abbreviated, and not replaceable with an inline review.

### Procedure (orchestrator)

1. **Delegate** — spawn a subagent with prompt **exactly**:
   ```
   /pr-review-local <PR_NUMBER>
   ```
   No context pack, no feature description, no extra instructions.

2. **Verify artifact** after subagent completes:
   ```bash
   test -f .context/prs/reviews/PR_REVIEW_#<PR_NUMBER>.md && echo "PASS" || echo "FAIL"
   grep -q "RUN_BY_COMMAND: pr-review-local" .context/prs/reviews/PR_REVIEW_#<PR_NUMBER>.md \
     && echo "PASS: provenance" || echo "FAIL: re-delegate /pr-review-local"
   ```
   If missing or wrong provenance, re-delegate with the same slash command only.

3. **Action resolution** (orchestrator — read `references/stage-6-action-resolution.md`):
   - Extract actionable items from the review artifact into
     `.context/implementation/stage-6-action-queue.md`.
   - **REQUEST CHANGES / Required / blocking:** run `/spec-driven` fix batches
     (max 2), commit, push. Do not implement blocking fixes as one-off edits
     outside spec-driven.
   - **APPROVE WITH CONDITIONS / Optional / HIGH:** XS–S → `/spec-driven`; M+
     or out-of-scope → Linear sub-issue + deferral register row.
   - Re-delegate `/pr-review-update <PR_NUMBER>` after fix batches (prompt only).
   - Log blocker → fix → commit in `.context/implementation/stage-6-fix-log.md`.

4. **Repeat action resolution** after Stage 6.5 (HIGH test items, score `< 5`)
   and after Stage 6.7 (critical scalar findings). Run **closure gate** before
   the GitHub comment — zero open items without commit or ticket.

5. **GitHub comment** — orchestrator posts **after Stage 6.7 action resolution
   + closure gate**, not here. See `references/pr-review-github-comment.md`.

### Stage 6.5 / 6.6 / 6.65 / 6.7 delegation (orchestrator)

Same prompt-only rule:

| Stage | Orchestrator runs | Subagent prompt (when applicable) |
|-------|-------------------|-----------------------------------|
| 6.5 | — | `/test-benchmark <PR_NUMBER>` |
| 6.6 | `rust_cognitive_complexity_gate.py` | `/code-simplifier` if `triggered: true` |
| 6.65 | `psgen_gate.py` | schema-first checklist (orchestrator; no subagent) |
| 6.7 | `scalar_lib_gate.py` | `/scalar-lib-it code` if `triggered: true` |

### What Stage 6 is NOT

- It is NOT the orchestrator writing the review inline
- It is NOT a quick scan of `git diff`
- It is NOT a subagent prompt with context packs or feature justification
- It is NOT complete without `.context/prs/reviews/PR_REVIEW_#<PR_NUMBER>.md`
  from a `/pr-review-local` subagent run

### Git Environment

All git operations that may open an editor MUST use `GIT_EDITOR=true`:

```
GIT_EDITOR=true git rebase --continue
GIT_EDITOR=true git rebase main
```

### Verification Protocol

Follow verification-protocol.mdc throughout all stages:

- Never claim something works without running it
- When two sources disagree, verify both
- Every finding in self-review must include its evidence level
- Prefer running a test over analyzing code

## Error Recovery

| Stage | Failure | Action |
|-------|---------|--------|
| Status | Preflight check fails | Use documented global/runtime/fallback path when possible; stop only if a required tool/auth has no fallback |
| 0 | No spec docs found | Note gap, proceed to Stage 1 |
| 0 | BLOCKING gaps found | Stop, report gaps to user |
| 1 | Ambiguous scope | Ask user one focused clarifying question |
| 1 | Test suite broken before changes | Note pre-existing failures |
| 1 | `uv sync` needed | Run `make install-dev` |
| 2 | NOT READY after 2 cycles | Log remaining blockers, update Linear/context issue, then stop |
| 3.75 | Score < 7 after 2 plan-update cycles | Proceed with warning; note in PR review |
| 3.75 | Scoring rubric file missing | Use inline rubric dimensions from test-benchmark SKILL.md |
| 3.8 | Critical design findings after 2 plan-update cycles | Stop before Stage 4; escalate to user |
| 3.8 | Gate script fails | Fix script/env issue and retry; do not skip Stage 3.8 |
| 4 | `make check` / `cargo test` fails | Classify failure; fix implementation bugs directly; if it exposes missing scope/tests/assumptions, run `/plan-update`, then retry (3 gate attempts max). Rust: see `rust-stage-details.md` |
| 4 | Spec discrepancy found | Propose codebase-consistent approach, continue |
| 4 | Branch already on remote | `git push --force-with-lease` after rebase |
| 5 | Push/PR creation fails | Report error, provide manual fallback |
| 5 | Rebase conflict | Resolve, `GIT_EDITOR=true git rebase --continue`, re-test |
| 5 | Git editor blocks | Ensure `GIT_EDITOR=true`, kill hung editor, retry |
| 6 | `gh` unavailable | Save review artifact; report manual review + PR comment needed |
| 6 | `gh pr comment` fails | Retry once; then note comment URL missing in session summary |
| 6 | Action items remain open at closure gate | Run `/spec-driven` or create Linear ticket; do not post PR comment until resolved or ticketed |
| 6.5 | Score < 5 after fix cycle | `/spec-driven` for HIGH items (max 2 batches); ticket remainder; re-benchmark |
| 6.5 | HIGH items, score 5–6 | Triage each HIGH: `/spec-driven` if XS–S, else Linear sub-issue — do not skip as "non-blocking" |
| 6.5 | No test files in PR diff | Skip with note "no test files changed" |
| 6.5 | `analyze_tests.py` fails | Fall back to inline agent analysis using rubric |
| 6.6 | No Rust files in PR diff | Gate runs automatically; document `no_rust_files_in_diff` in PR review; no simplifier |
| 6.6 | Warnings pre-existing only | Gate runs; document skipped pre-existing; do not refactor untouched functions |
| 6.6 | Still over threshold after 2 passes | Log to Linear; append residual to PR review; stop pipeline (same as Stage 6 fix-cycle limit) |
| 6.6 | Gate script fails | Fix script/env issue and retry; do not skip Stage 6.6 |
| 6.7 | No scalar scope in diff | Gate runs; document skip in PR review; proceed to PR comment |
| 6.7 | Critical findings after 2 spec-driven fix batches | Create blocking Linear sub-issue; post comment with BLOCKED status; stop pipeline |
| 6.7 | Warning-only scalar findings | XS–S → `/spec-driven`; else ticket under parent — no naked "follow-up" in comment |
| 6.7 | Gate script fails | Fix script/env issue and retry; do not skip Stage 6.7 |

## Session Length Guardrails

**Cardinal rule: NEVER stop working because of context window concerns.** Session
management exists to structure recovery points, not to give permission to quit.
The agent completes the plan. If the session ends (crash, timeout, user closes
IDE), the recovery points ensure the next session resumes efficiently. That is the
sole purpose of these checkpoints.

- **Phase boundary checkpoint**: After each plan phase completes and is committed,
  emit a one-line progress summary (completed phases, next phase). This is a
  breadcrumb for crash recovery, not a decision point about whether to continue.
  Continue immediately to the next phase.
- **200-message handoff prep**: When the assistant message count exceeds 200,
  append a structured recovery block to the next commit message (branch name,
  completed phases, next phase, unresolved decisions). Do NOT suggest stopping,
  switching sessions, or ask the user whether to continue. Keep working. The
  recovery block is insurance in case the session dies -- it is never a reason
  to stop.

**Explicitly forbidden behaviors:**
- Suggesting "we should start a new session" or "context is getting long"
- Asking the user whether to continue or split the work
- Slowing down, becoming more cautious, or reducing scope as message count grows
- Using context length, token count, or message count as justification for any
  action other than appending recovery metadata to commits

## State Management

Track pipeline progress using the todo system. Create todos at activation and
update as each stage completes:

```
- [ ] Run pipeline_status.py → determine resume point
- [ ] Linear Ticket Gate → ticket ID recorded (or SKIPPED with reason)
- [ ] Stage 0: Validate specs → gap report (or skip note) + **worktree psgen bootstrap**
- [ ] Stage 1: Plan created → plans/feature_name_hash.plan.md (with Assumption Ledger)
- [ ] Stage 2: Review passed → READY TO EXECUTE (with Assumption Audit)
- [ ] Stage 3: Update (if needed — includes assumption audit resolution)
- [ ] Stage 3.5: DE adversarial review → APPROVE / APPROVE WITH CONDITIONS / BLOCK
- [ ] Stage 3.75: Test benchmark (plan-level) → scorecard >= 7 or plan updated
- [ ] Stage 3.7: psgen gate (plan) → `.context/psgen-gate-plan.json`
- [ ] Stage 3.8: Scalar-lib-it (plan) → gate JSON + optional design audit
- [ ] Stage 3.5b: Deferral adjudication → register + Linear follow-up tickets (or explicit zero-deferral note)
- [ ] Stage 4: Implement (TDD cycles + integration test gate)
- [ ] Stage 5: Ship → PR #NNN
- [ ] Stage 6: Self-review → .context/prs/reviews/PR_REVIEW_#NNN.md
- [ ] Stage 6 action resolve (post-6): blocking/conditions → /spec-driven or ticket
- [ ] Stage 6.5: Test benchmark (code-level) → scorecard appended to PR review (mandatory)
- [ ] Stage 6 action resolve (post-6.5): HIGH items → /spec-driven or ticket
- [ ] Stage 6.6: Rust cognitive complexity gate → always run script; auto simplifier if triggered
- [ ] Stage 6.65: psgen gate (code) → always run script; schema-first checklist if triggered
- [ ] Stage 6.7: Scalar-lib-it (code) → always run gate script; auto audit if triggered
- [ ] Stage 6 action resolve (post-6.7) + closure gate → zero orphan findings
- [ ] GitHub PR comment (after Phase 6 action resolution complete)
- [ ] Step 4: Goal-aware completion → goal.py list + advance/handoff or summary
```

## What This Skill Does NOT Do

- Does not create Linear tickets (use `/linear-to-tasks`)
- Does not merge PRs (human approval required)
- Does not deploy (out of scope)
- Does not run e2e tests requiring GCP auth — but DOES ensure integration tests
  exist and pass locally (GCP-dependent tests documented as follow-up)

## Dependencies

- **Commands**: `plan-create`, `plan-review`, `plan-update`, `spec-driven`,
  `commit-push-pr` (resolved from global `~/.cursor/commands`, global
  `~/.claude/commands`, project commands, main workspace commands, runtime
  command surface, or bundled fallback in that order)
- **Skills**: `vibe-test` (Stage 0), `psgen` skill (Stages 3.7+ when triggered), `test-benchmark` (Stages 3.75, 6.5), `scalar-lib-it` (Stages 3.8, 6.7), `pr-review-local` command (Stage 6), `code-simplifier` (Stage 6.6, automatic when gate triggers)
- **Rules**: `999-agent-execution-protocol.mdc`, `104-plan-execution-hygiene.mdc`,
  `101-testing-hygiene.mdc`, `verification-protocol.mdc`
- **Tools**: `git`, `gh` (GitHub CLI), `make`, `uv`, `python3`
- **MCP Servers**: `linear` (Stages 1-2 subagent may query; Stage 5 PR ops)
- **Directories**: `plans/`, `.context/prs/`

If command files are missing, the stage descriptions in
`references/stage-details.md` are self-contained enough to execute directly.

## Test Quality Gates

Test quality is enforced at three levels in the pipeline. The first two are
non-negotiable stages; the third is inline during implementation.

### Stage 3.75: Plan-Level Test Benchmark

Runs after the adversarial review (Stage 3.5) and before implementation
(Stage 4). Evaluates the *test strategy described in the plan* -- not code,
which does not exist yet. The purpose is to catch structural gaps (missing
integration tests, absent error path coverage, inverted test pyramids) before
a single line of implementation is written. Fixing a plan is cheap; fixing an
implemented codebase whose tests were architecturally wrong from the start is
expensive.

Read `references/stage-details.md` Stage 3.75 for the full procedure. Summary:

1. Read the plan file and the `/test-benchmark` scoring rubric
   (`~/.cursor/skills/test-benchmark/references/scoring-rubric.md`).
2. Score each rubric dimension against the plan's test specifications.
3. Assess the test pyramid ratio implied by the plan (unit / integration / e2e).
4. Produce a plan-level scorecard and prioritized action items.
5. **Gate logic**:
   - Score >= 7 with no HIGH-priority items: proceed to Stage 4.
   - Score < 7 OR any HIGH-priority items: generate structured findings and
     trigger `/plan-update` to embed the required test specifications into the
     plan. Then re-run the benchmark on the updated plan. Max 2 cycles.
   - If still < 7 after 2 update cycles: proceed with a warning note in the
     todo list and the PR review artifact. Do not block indefinitely.

The scorecard is saved to `.context/test-benchmarks/<plan-name>_plan-level.md`
and registered in the manifest.

### Stage 6.5: Code-Level Test Benchmark

Runs after self-review (Stage 6) and before the completion check (Step 4).
Evaluates the *actual test code* that was implemented. This catches quality
issues that only emerge in code -- low assertion density, bare mocks, missing
error paths -- that the plan-level check cannot see.

Read `references/stage-details.md` Stage 6.5 for the full procedure. Summary:

1. Identify all test files changed in the PR: `gh pr diff <PR_NUMBER> --name-only`
   filtered to `*_test.go`, `*_test.py`, `test_*.py`, `*.test.ts`, `*.spec.ts`.
2. For Python tests: run `analyze_tests.py` from the test-benchmark skill.
3. For Go tests: perform inline agent analysis using the scoring rubric --
   count assertions per test function, check for error path tests, verify
   table-driven patterns, assess integration boundary coverage.
4. For Rust tests: inline analysis per `references/rust-stage-details.md` and
   Stage 6.5 in `references/stage-details.md` (`assert!` density, error
   paths, walking-skeleton coverage).
5. Run coverage if available (`pytest --cov` for Python, `go test -cover` for
   Go, `cargo llvm-cov` for Rust when installed).
5. Produce a code-level scorecard.
6. **Gate logic** (after scorecard, run Stage 6 Action Resolution):

   | Score | Action |
   |:-----:|--------|
   | >= 7  | Append "Test Benchmark: PASS ({score}/10)" to the PR review artifact. Triage any remaining HIGH items: `/spec-driven` if XS–S, else ticket. |
   | 5-6   | Append full scorecard. **Triage every HIGH item** — fix via `/spec-driven` or Linear sub-issue. Do not treat as "non-blocking" without resolution. |
   | < 5   | `/spec-driven` fix batches for HIGH items (max 2). Re-score. Ticket unresolved items. If blocking items remain after 2 batches, stop pipeline. |

   Read `references/stage-6-action-resolution.md` for triage procedure.

The scorecard is saved to `.context/test-benchmarks/<service>_code-level.md`
and registered in the manifest.

### Stage 6.6: Rust Cognitive Complexity Gate (mandatory harness step)

**Runs automatically** after Stage 6.5 on every ship-feature completion, before
Step 4 (goal completion). The agent does not ask permission. Non-Rust PRs still
execute the gate script and record the skip reason.

Evidence: PAR-271 spike (sub-issue of PAR-128) on `execute_query.rs` -- helper
extraction brought five functions from 20-52 down to <=15 with full test suite
green.

**Prerequisites** (when absent on a Rust-touching PR, add as part of this stage):

- Root `clippy.toml` with `cognitive-complexity-threshold = 15`
- Touched crates: `[lints.clippy] cognitive_complexity = "warn"`

Read `references/stage-details.md` Stage 6.6 for the full procedure. Summary:

1. **Always detect** (repo root, immediately after 6.5):
   ```bash
   python3 ~/.cursor/skills/ship-feature/scripts/rust_cognitive_complexity_gate.py \
     --base origin/main \
     | tee .context/rust-cognitive-complexity-gate.json
   ```

2. **When `triggered: false`** -- stage still completes; append to PR review:
   `Stage 6.6 PASS/SKIPPED: {reason}`. Continue to Stage 6.65.

3. **When `triggered: true`** -- **automatic simplifier** (no user prompt):
   - Run `/code-simplifier` on each actionable function
   - `cargo test -p <crate> --all-targets` + re-run gate script
   - Commit + push refactor; max 2 cycles (Error Recovery table)
   - Append `Stage 6.6 PASS` with before/after scores to PR review

4. **Harness completion check** before Stage 6.65:
   ```bash
   test -f .context/rust-cognitive-complexity-gate.json \
     && grep -q '"triggered"' .context/rust-cognitive-complexity-gate.json \
     && echo "PASS: Stage 6.6 gate artifact" || echo "FAIL: run Stage 6.6"
   ```

Gate script:
`~/.cursor/skills/ship-feature/scripts/rust_cognitive_complexity_gate.py`

### Stage 6.65: psgen / schema-first gate (mandatory harness step)

**Runs automatically** after Stage 6.6 on every ship-feature completion, before
Stage 6.7.

Read `references/stage-details.md` Stage 6.65 and
`references/psgen-stage-details.md` for the full procedure. Summary:

1. **Always detect** (repo root, immediately after 6.6):
   ```bash
   python3 ~/.cursor/skills/ship-feature/scripts/psgen_gate.py \
     --mode code \
     --base origin/main \
     --out .context/psgen-gate-code.json
   ```

2. **When `triggered: false`** -- append to PR review:
   `Stage 6.65 SKIPPED: {reason}`. Continue to Stage 6.7.

3. **When `triggered: true`** -- audit diff for schema-first violations (mirrors,
   vendored generated copies, raw HTTP clients, wire-form test fixtures). Fix
   critical items via `/spec-driven` (max 2 batches). Append
   `Stage 6.65 PASS|FIXED|BLOCKED` to PR review.

4. **Harness completion check** before Stage 6.7:
   ```bash
   test -f .context/psgen-gate-code.json \
     && grep -q '"triggered"' .context/psgen-gate-code.json \
     && echo "PASS: Stage 6.65 gate artifact" || echo "FAIL: run Stage 6.65"
   ```

Gate script:
`~/.cursor/skills/ship-feature/scripts/psgen_gate.py`
(Mirror: `~/.claude/skills/ship-feature/scripts/psgen_gate.py`)

### Stage 6.7: Scalar-lib-it gate (mandatory harness step)

**Runs automatically** after Stage 6.65 on every ship-feature completion, before
the GitHub PR comment and Step 4 (goal completion).

Read `references/stage-details.md` Stage 6.7 for the full procedure. Summary:

1. **Always detect** (repo root, immediately after 6.65):
   ```bash
   python3 ~/.cursor/skills/ship-feature/scripts/scalar_lib_gate.py \
     --mode code \
     --base origin/main \
     --out .context/scalar-lib-gate-code.json
   ```

2. **When `triggered: false`** -- append to PR review:
   `Stage 6.7 SKIPPED: {reason}`. Post GitHub PR comment.

3. **When `triggered: true`** -- **automatic scalar-lib-it** (no user prompt):
   - Run `/scalar-lib-it` Code mode on PR diff
   - **Critical findings:** `/spec-driven` fix batches (max 2), not inline edits
   - **Warnings / P1 in scope:** triage per `references/stage-6-action-resolution.md`
   - Save audit to `.context/scalar-lib-audits/{task-id}_code.md`
   - Append `Stage 6.7 PASS|FIXED|BLOCKED` to PR review
   - Run Phase 6 closure gate, then post GitHub PR comment

4. **Harness completion check** before PR comment / Step 4:
   ```bash
   test -f .context/scalar-lib-gate-code.json \
     && grep -q '"triggered"' .context/scalar-lib-gate-code.json \
     && echo "PASS: Stage 6.7 gate artifact" || echo "FAIL: run Stage 6.7"
   ```

Gate script:
`~/.cursor/skills/ship-feature/scripts/scalar_lib_gate.py`
(Mirror: `~/.claude/skills/ship-feature/scripts/scalar_lib_gate.py`)

### Inline Checks (Stage 4 TDD Refactor Step)

Quick checks still execute inline during each TDD Refactor step in Stage 4.
These are lightweight and do not produce a formal scorecard:
- Assertion density (2+ per test)
- Error path coverage (at least one error-path test per module)
- Mock fidelity (`spec=RealClass` where importable, `testify/mock` with
  interface matching for Go)
