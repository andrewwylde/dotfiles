---
description: "Implement-Review Iteration Loop. Takes a Linear ticket or free-text task, resolves context, then loops: implement via subagent → swarm-review → fix feedback → re-review, until PASS or max iterations. Usage: /implement-and-review-loop [TICKET-ID or description] [max=N]"
alwaysApply: false
---

# Implement-Review Iteration Loop

Take a task, resolve architectural context, then loop: implement → review → fix →
re-review until the review passes or max iterations is hit. All implementation and
review happens via Claude-native subagents — no external MCP servers required.

## Arguments

Parse from `$ARGUMENTS`:
- **Ticket ID** — a Linear ticket ID (e.g. `SYSTEM-1354`) or free-text description
- **`max=N`** — max iterations (default: 3, hard cap: 5)

## State Variables

Track these across the loop:
- `TICKET_ID`, `TICKET_DESCRIPTION`, `INTENT_SPEC` — from Phase 1
- `MVC_CONTEXT` — from Phase 2
- `ITERATION` = 0
- `MAX_ITERATIONS` — from args or default 3
- `REVIEW_FEEDBACK` = [] — accumulates across iterations
- `ALL_CHANGES_SUMMARY` = [] — what was implemented/fixed each iteration

---

## Phase 0: Repo Detection

Before Phase 1, detect whether we're in the parable-platform monorepo. Many phases below branch on this.

```bash
IS_PARABLE_MONOREPO=$(
  test -d "$(git rev-parse --show-toplevel)/platform-schemas" && echo true || echo false
)
# Presence of platform-schemas/ is the definitive marker.
```

Record the result. If `IS_PARABLE_MONOREPO=false`:
- **Skip Phase 2 entirely** (no Spectacles, no MVC). Set `MVC_CONTEXT=""`.
- Use **generic quality gates** in Phase 3b (lint, type-check, build, test — whatever the repo already has in its Makefile / package.json).
- **Drop Parable-specific constraints** from the subagent prompt; use repo-local conventions instead (read the repo's CLAUDE.md if one exists).
- Do NOT invoke `spectacles`, `psgen`, or `squawk` — the binaries won't exist.

## Phase 1: Task Acquisition

### If given a Linear ticket ID:

1. Fetch the issue via the Linear MCP tool (`mcp__claude_ai_Linear__get_issue`).
2. Extract: title, description, plan steps (if `## Plan` section exists),
   acceptance criteria, and `gitBranchName`.
3. **Sparse ticket escalation:** If the description is empty or under 50 characters
   AND the ticket has a `parentId`:
   - Fetch the parent ticket for acceptance criteria, scope, and constraints
   - List sibling tickets (`mcp__claude_ai_Linear__list_issues` with `parentId`)
     to understand scope boundaries
   - Synthesize an intent spec from parent context + sibling boundaries
   - Flag to user: "Ticket [ID] had no description — used parent [PARENT_ID] for context."
   - Present the synthesized intent spec for user confirmation before proceeding
4. If no `## Plan` section exists, draft one from the description (or synthesized
   intent spec). Present to user for approval before proceeding.

### If given a free-text description:

1. Use the description directly as `TICKET_DESCRIPTION`.
2. Assign `TICKET_ID` = "MANUAL-001" (or user-provided identifier).

## Phase 1.5: Planning Gate (non-trivial tickets)

Skip for trivial/mechanical tasks (single file, simple rename, lint fix).

For tickets that touch 3+ files or cross service boundaries:

1. Invoke `plan-adversary-review` against the plan/intent spec (assumptions,
   pre-mortem, blast radius).
2. If genuine risks surface, incorporate mitigations into the plan.
3. If scope ambiguity surfaces, ask the user to clarify before proceeding.

This gate prevents silent scope drift (the POV-548 failure mode).

## Phase 2: Spectacles Context Resolution

**Skip this phase if `IS_PARABLE_MONOREPO=false`.** Standalone repos do not have Spectacles. Set `MVC_CONTEXT=""` and proceed to Phase 3. The swarm review in Phase 3c still catches issues without it.

Resolve the Minimally Viable Context (MVC) for files the task will touch.

1. **Identify target paths** from the task description and plan. Key domains:

   | Domain | Glob |
   |--------|------|
   | Web API | `services/web-api/**` |
   | Web App | `apps/web-app/**` |
   | Platform Schemas | `platform-schemas/**` |
   | Web DB | `services/web-db/**` |
   | Design System | `apps/packages/design-system/**` |
   | Infrastructure | `infrastructure/**` |

2. **Resolve context:**
   ```bash
   spectacles resolve --paths <comma-separated-paths>
   ```

3. **Read the MVC bundle.** Priority ordering:
   - **Decisions (ADR-*)** — never contradict
   - **Principles (PRI-*)** — error-severity = hard failure
   - **Contracts (CON-*)** — maintain interfaces
   - **Patterns (PAT-*)** — follow recommended practices
   - **Pitfalls (PIT-*)** — avoid documented mistakes

4. Capture as `MVC_CONTEXT`.

## Phase 3: Implement-Review Loop

### Loop Discipline — NON-NEGOTIABLE

- **Every iteration MUST run the full swarm review (Step 3c).** You cannot skip it.
- **You cannot assess your own implementation and declare PASS.** Only a review
  artifact produced by swarm-review subagents counts. Your opinion of the code
  quality is irrelevant to the loop — the review is the measurement.
- **The review artifact file MUST exist** at `~/.agent/reviews/` before you can
  parse a verdict in Step 3d. If the file doesn't exist, the review didn't happen.
- **Iteration 1 always runs the full loop.** Even if the implementation looks
  perfect, the first iteration goes through swarm-review before any PASS is possible.

Red flags — if you're thinking any of these, STOP:
- "The implementation is straightforward, the review would pass" → Run the review.
- "I already addressed the feedback, no need to re-review" → Run the review.
- "This is a small change, a full swarm is overkill" → Run the review (swarm-review
  has a quick mode for small diffs).
- "I can review this myself to save time" → That defeats the loop. Run the swarm.

```
┌──────────────────────────────────────────────────────────┐
│  ITERATION++                                              │
│                                                           │
│  3a. Implementation Subagent                              │
│      ├── Receives: ticket, plan, MVC, prior feedback      │
│      ├── Writes code, runs tests, commits                 │
│      └── Returns: summary of changes                      │
│                                                           │
│  3b. Quality Gates (you run these directly)               │
│      ├── Lint, type-check, test for affected domains      │
│      ├── Spectacles validate-paths                        │
│      └── Fix any mechanical failures before review        │
│                                                           │
│  3c. Swarm Review (via /swarm-review or inline)           │
│      ├── Parallel specialist subagents review the diff    │
│      └── Produces artifact: tactical fixes + systemic     │
│                                                           │
│  3d. Parse Review                                         │
│      ├── PASS (no blockers, no improvements) → exit loop  │
│      ├── NEEDS WORK → collect tactical feedback,          │
│      │   feed back to 3a as REVIEW_FEEDBACK               │
│      └── ITERATION >= MAX → exit loop with remaining      │
│                                                           │
│  Exits when: PASS or ITERATION >= MAX_ITERATIONS          │
└──────────────────────────────────────────────────────────┘
```

### 3a. Dispatch Implementation Subagent

Detect project root dynamically:
```bash
git rev-parse --show-toplevel
```

Launch a `general-purpose` subagent with full tool access. The prompt must include:

```
Agent(
  subagent_type="general-purpose",
  prompt="""
  You are an implementation agent for the parable-platform monorepo.

  ## Task
  Ticket: {TICKET_ID}
  Description: {TICKET_DESCRIPTION}
  Plan: {PLAN from Phase 1}

  ## Architectural Context (Spectacles MVC)
  {MVC_CONTEXT}

  ## Prior Review Feedback to Address
  {REVIEW_FEEDBACK — empty on first iteration}

  ## Constraints
  {{ if IS_PARABLE_MONOREPO }}
  - Never edit generated code in dist/ directories
  - Conventional commits: <type>(<scope>): <description>
  - Go: structured logging only (zap with fields)
  - Svelte 5 runes — never use Svelte stores
  - All DB types must have id: UUID! @unique @key + 6 audit fields
  - Permissions must be declared in permissions.yml before use
  - Squawk must pass on all new migration files
  {{ else }}
  - Follow the conventions already present in this repo. Read CLAUDE.md if one
    exists; otherwise infer from existing code (naming, logger choice,
    Svelte runes vs legacy stores, migration tooling, commit-message style).
  - Do NOT import Parable-platform-only tooling (spectacles, psgen, squawk).
  - Conventional commits encouraged but not enforced unless the repo already
    uses them.
  {{ endif }}

  ## Instructions
  1. Read the relevant existing code before writing anything
  2. Implement the task following the plan and constraints
  3. If this is iteration 2+, focus ONLY on addressing the review feedback — do not
     re-implement what already works
  4. Run tests for the domains you touched (make lint, make test-race for Go;
     npm run lint && npm run check for frontend)
  5. Stage and commit your changes with a conventional commit message
  6. Report in this EXACT format as your final message — do not skip fields:
     ```
     STATUS: done | blocked | partial
     COMMITS: <short-hash list, or "none">
     PLAN_DEVIATIONS: <bulleted list of anything you did differently from the
                      plan (e.g., chose pattern X instead of Y), or "none">
     OPEN_QUESTIONS: <any, or "none">
     QUALITY_GATES: <commands you ran + pass/fail>
     ```
     If STATUS is not "done", the orchestrator treats the work as incomplete
     and will either SendMessage-continue you or take over. Do not exit
     silently after a partial implementation.
  """
)
```

**After the subagent returns, parse its STATUS line.** If it's `partial` or
`blocked`, do NOT move to 3b. Either:
- Send a follow-up message via `SendMessage` with the agent ID, OR
- Take over the remaining work yourself, explicitly noting where the subagent
  stopped so the diff for review still makes sense.

Never assume success when STATUS is missing — treat a missing/malformed status
line as `partial` and continue the subagent, don't silently proceed.

When the subagent returns, read its summary of changes. Add to `ALL_CHANGES_SUMMARY`.

### 3b. Quality Gates

Run these yourself (not in the subagent) to catch mechanical issues before review. Which gates apply depends on Phase 0's `IS_PARABLE_MONOREPO` flag.

#### If `IS_PARABLE_MONOREPO=true` — Parable domain-specific gates

**For Go code (`services/`):**
```bash
cd $(git rev-parse --show-toplevel)/services/web-api && make lint && make test-race
```

**For frontend code (`apps/web-app/`):**
```bash
cd $(git rev-parse --show-toplevel)/apps/web-app && npm run lint && npm run check
```

**For schema changes (`platform-schemas/`):**
```bash
cd $(git rev-parse --show-toplevel)/platform-schemas && psgen validate schemas/<schema>/schema.json
```

**For database migrations (`services/web-db/`):**
```bash
squawk -c services/web-db/.squawk.toml services/web-db/migrations/sql/<migration>.up.sql
```

**Spectacles validation:**
```bash
spectacles validate-paths --paths <changed-files> --strict
```

#### If `IS_PARABLE_MONOREPO=false` — generic gates

Detect the repo's tooling and run whatever it provides. In order of preference:

1. **`Makefile` targets** — if `make help` or the Makefile shows `lint`, `test`, `build`, prefer those:
   ```bash
   make lint test build 2>&1 | tail -30
   ```
2. **Language-specific fallback** when there is no Makefile coverage:
   - Go: `go build ./... && go vet ./... && go test ./...`
   - Node/frontend: `npm run lint 2>/dev/null || true; npm run check 2>/dev/null || npx svelte-check 2>/dev/null || true; npm test 2>/dev/null || true`
   - Python: `ruff check . && pytest` (or whatever the repo uses — check `pyproject.toml` / `tox.ini`)
3. **Pre-commit hook** — if the repo has `.git/hooks/pre-commit`, the hook fires at commit time; you don't need to run it separately, but know that it gates your commits.

Do NOT attempt `spectacles validate-paths`, `psgen validate`, or `squawk` — those binaries won't exist. If a migration is introduced in a standalone repo, read it for obvious safety issues yourself (nullable columns, `IF NOT EXISTS` idempotency, backfill before `SET NOT NULL`).

#### Common to both

If quality gates fail, fix the issues directly (simple lint/type fixes) or feed them
back to the implementation subagent as additional feedback. Do NOT proceed to review
with failing gates.

**Cross-domain cascades:** If `platform-schemas` changed, rebuild downstream
(`psgen build`, then commit generated changes) before review.

### 3c. Swarm Review

Generate the diff of changes since the branch diverged from main:
```bash
git diff $(git merge-base HEAD main)..HEAD
```

Follow the `swarm-review` skill's full workflow (Phase 1-5) using the diff. This
dispatches actual parallel subagents (specialist reviewers) that produce an
independent review artifact.

The review artifact MUST be saved to `~/.agent/reviews/` before proceeding to 3d.

**Verify the artifact exists:**
```bash
ls -la ~/.agent/reviews/  # confirm new file was written this iteration
```

If the artifact was not produced, something went wrong — do NOT proceed. Report
the error and retry the review.

The artifact contains:
- `## Tactical Fixes (this PR)` → `### Blockers` and `### Improvements`
- `## Systemic Follow-ups (separate PRs)`

### 3d. Parse Review and Decide

**Before parsing:** Verify the review artifact file exists and was modified within
the last 5 minutes (to confirm it's from *this* iteration, not a stale prior run):
```bash
find ~/.agent/reviews/ -name "*.md" -mmin -5 | head -1
```
If no recent artifact is found, the review did not run. Go back to Step 3c.

Read the review artifact. Determine the verdict:

- **PASS**: Zero blockers AND zero improvements → exit loop
- **NEEDS WORK**: Any blockers or improvements exist → continue

**If PASS:**
Go to Phase 4 (Reporting).

**If NEEDS WORK and ITERATION < MAX_ITERATIONS:**
1. Extract all tactical fixes (blockers first, then improvements)
2. Append to `REVIEW_FEEDBACK` with iteration number
3. Append systemic items to a separate `DEFERRED_FEEDBACK` list (never act on these)
4. Increment `ITERATION`
5. Go back to Step 3a — the implementation subagent receives the accumulated feedback

**If NEEDS WORK and ITERATION >= MAX_ITERATIONS:**
Go to Phase 4 (Reporting) with incomplete status.

**Same finding across iterations:** If a finding from iteration N reappears in
iteration N+1 after the subagent attempted a fix, move it to "remaining tactical
issues" with a note: "Fix attempted in iteration N but finding persists."

---

## Phase 4: Reporting

### If PASS:

Present to user:
```
✅ Implementation complete

Ticket: {TICKET_ID}
Iterations: {ITERATION}
Branch: {branch-name}

Changes:
{ALL_CHANGES_SUMMARY}

Review: PASS — no blockers or improvements remaining

Next steps:
- [ ] Open PR (/prepare-pr)
- [ ] Manual QA verification
```

### If max iterations reached:

Do NOT commit any uncommitted changes. Leave them staged for inspection.

```
⚠️ Implementation reached max iterations ({MAX_ITERATIONS})

Ticket: {TICKET_ID}
Iterations: {ITERATION}

Remaining tactical issues:
{unresolved findings from REVIEW_FEEDBACK}

Deferred systemic issues:
{DEFERRED_FEEDBACK}

Options:
1. Re-run with higher max (max=5)
2. Address remaining feedback manually, then /review-fix-loop
3. Proceed to PR with known issues
```

### After either outcome:

Suggest running `session-postmortem` to capture what worked and what didn't.

---

## Constraints

### Universal (apply to every repo)

- **Never commit secrets** — use env vars, GCP Secret Manager, or equivalent
- **Never edit generated code** in `dist/` or other build-output directories
- **Conventional commits** encouraged — `<type>(<scope>): <description>`

### Parable monorepo only (skip if `IS_PARABLE_MONOREPO=false`)

The subagent prompt at Phase 3a already branches on the flag, so these do not need
re-injection here — this list is for orchestrator awareness:

- GraphQL is schema DSL only — no runtime GraphQL endpoint
- Branch naming: `<type>/<ticket>-<description>` with enforced prefixes
- Go: structured logging only (zap with fields)
- Svelte 5 runes — never use Svelte stores
- All DB types must have `id: UUID! @unique @key` + 6 audit fields
- Permissions must be declared in `permissions.yml` before use
- Squawk must pass on all new migration files
- Error-severity Spectacles principles are hard failures — never violate

### Standalone repo

No fixed constraint list — the subagent adapts to the repo's conventions by reading
CLAUDE.md and existing code (see Phase 3a). The orchestrator's only job is to avoid
imposing Parable-specific rules that don't fit.

## Recovery Strategies

| Situation | Action |
|-----------|--------|
| Implementation subagent times out | Re-run with a narrower scope or split into sub-tasks |
| Subagent returns no STATUS line, or STATUS != done | Treat as `partial`. SendMessage the agent to continue, OR take over explicitly. Never silently proceed. |
| Subagent reports PLAN_DEVIATIONS | Evaluate: is the deviation reasonable? If yes, update the plan file and continue. If no, send feedback to the subagent to re-do. |
| Spectacles resolve fails (monorepo) | Proceed without MVC context; the review will catch violations |
| Spectacles binary missing (standalone repo) | Expected — skip; Phase 0's flag handled this |
| Review keeps flagging same issue | Read the feedback yourself, fix manually, then re-run review only |
| Cross-domain cascade needed | Run `psgen build` first, commit generated changes, then continue loop |
| Quality gates fail repeatedly | Fix gates directly rather than re-dispatching the subagent |
| Pre-commit hook blocks every commit | Diagnose: does the hook demand tooling the repo doesn't install? If yes, add the missing tooling (prettier, linter, etc.) or ask the user before using `--no-verify`. Never silently bypass. |
