# PARABLE-609 campaign stage details (user-scoped)

Procedures for Stages **0.5 / 0.6 / 3.85 / 3.9 / 4.8 / 4.9**. Invoked only when
`campaign_context_gate.py` / `.context/campaign-gate.json` has `triggered: true`.

## Stage 0.5 — Campaign context load

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/campaign_context_gate.py \
  --ticket PARABLE-644 --workspace .
```

Loads:
- `references/campaigns/parable-609/manifest.json` (+ parent.md, scaffold, deps)
- Live ponder-admin SHA + dirty fingerprint
- `origin/main` SHA
- PRD file presence (stories/ is gitignored — missing = readiness gap)
- Visual URL probe

Snapshot: `~/.cursor/ship-feature-state/parable-609/<ticket>/campaign-snapshot.json`

## Stage 0.6 — Reference visual baseline

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode baseline --ticket PARABLE-644
```

Requires `https://local.parable.work:5300/admin/ponder` up. Capture ticket-
relevant screenshots into `.../visual-proof/` (local-only). If URL down, status
`BLOCKED` until restored or explicit user ack on the baseline JSON.

## Stage 3.85 — Reference implementation audit

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/reference_audit_gate.py \
  --ticket PARABLE-644 --write --sha <ponder-sha>
# agent fills preserve|migrate|discard, then:
python3 ~/.cursor/skills/andrew-ship-feature/scripts/reference_audit_gate.py \
  --ticket PARABLE-644 --validate --expect-sha <ponder-sha>
```

Mandatory plan sections when campaign-triggered:

### Reference Fidelity
Table of inspected paths → preserve / migrate / discard + intentional deviations.

**Absolute reference paths required.** The PR worktree is usually `origin/main`
and does **not** contain ponder-admin scaffolds. Every MIGRATE/PRESERVE row must
cite an absolute path under the reference worktree (default:
`/Users/andrewwylde/.cursor/worktrees/parable-platform/3fmc/...`) plus SHA/dirty
fingerprint from the campaign snapshot. Relative paths alone are a reject
(agents cannot open them from the PR checkout).

### Visual Proof Matrix
| state_id | route/harness | viewport | theme | AC ids |

### Linear AC traceability
| Linear AC (paraphrase or quote) | Plan AC id / proof | Disposition |
|---------------------------------|--------------------|-------------|
| … | AC-… / matrix row / test | `in_scope` \| `deferred(<ticket>)` \| `out_of_scope` |

Every bullet on the Linear issue must appear. Thinning a UI slice is allowed
when schema/host contracts are missing, but deferred rows must name an
**existing** blocker ticket or create a **follow-up under PARABLE-609** with
`blockedBy` set (do not invent silent drops; do not open 721-style “migrate
types later” tickets when the type already exists on main).

Reject plans that:
- invent a detached UI with no mapping to Ponder host behavior
- cite reference components without absolute reference-worktree paths
- omit Linear AC bullets without `in_scope` / `deferred(ticket)` / `out_of_scope`

## Stage 3.9 — Implementation approval (HUMAN)

**STOP.** Present:
- Plan path + READY decision
- Reference audit summary
- Baseline thumbs/paths
- Scaffold never-promote list

Wait for: `APPROVE IMPLEMENTATION PARABLE-XXX`

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py \
  --kind implementation --ticket PARABLE-XXX --approve \
  --quote 'APPROVE IMPLEMENTATION PARABLE-XXX' \
  --plan plans/....plan.md \
  --campaign-snapshot ~/.cursor/ship-feature-state/parable-609/parable-xxx/campaign-snapshot.json \
  --ref-fp <fingerprint from snapshot>
```

Any plan/reference change invalidates the approval. Source edits are blocked by
`stage_compliance_check.py --gate stage4` until valid.

## Stage 4.7 — Apply component to PR branch

Copy/apply component + unit tests from the harness worktree onto the child PR
branch. PR base comes from `children_meta.pr_base` in the campaign manifest:

- `schema_tier: 0` → `origin/main`
- `schema_tier: 1` → draft stacked on schema branch (e.g. #4457 tip) until it
  lands on main, then rebase

PR contains **component + tests only** — never `/dev/ponder`, registry, or PNGs.

### Pre-4.7 schema persistence mirror gate

`schema_tier: 0` means "no schema stack required" — **not** "hand-roll persistence
shapes forever." Before Stage 4.7 / visual QA, if the component hosts or re-exports
persistence-shaped facts (append-only runs, source snapshots, schedules, join views
that mirror web-db rows), pick one and record it:

| Decision | When |
|----------|------|
| `none` | Pure presentational props; no run/snapshot/schedule row mirrors |
| `same_pr_schema` | Thin `web-db` (+ enums/migration) lands on this PR, UI adopts generated types |
| `stacked_schema` | Bump `schema_tier: 1` / stack on schema tip; do not ship slug/string mirrors |

Write `.context/schema-persistence-ack.json`:

```json
{
  "ticket": "PARABLE-640",
  "decision": "same_pr_schema",
  "rationale": "ReportRunView joins ParableReportRun + snapshots; thin web-db contract on PR"
}
```

`stage_compliance_check.py --gate stage5-pr` fails closed without a valid ack when
campaign mode is active and `schema_tier` is `0`. Recovery:
`harness_recovery.py --from-check schema-persistence-ack`.

## Stage 4.75 — Mount into persistent harness (609 / `persistent_external` only)

Skip this stage when `harness.kind` is `app_route` (PARABLE-613+).

On `~/.agent/worktrees/parable-ponder-harness` (`local/parable-ponder-harness`):

1. Add `apps/web-app/src/routes/dev/ponder/regions/parable-XXX-<region>.ts`
2. Register it in `regions/index.ts` (cumulative; replaces only that region)
3. Seed matrix into ship-feature-state:

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode matrix-template --ticket PARABLE-XXX --region editor --force
```

4. Commit on the harness branch only:
   `harness(PARABLE-XXX): mount <region>`

## Stage 4.8 — Visual after proof

### `app_route` (PARABLE-613+)

Drive the **regular** admin app on the PR worktree — no `/dev/ponder` mounts.

1. Seed matrix (once):

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode matrix-template --ticket PARABLE-1045 --force
```

2. Start Vite on the **PR worktree** (`bun run dev:only` / worktree port).
3. Run Playwright against `/admin/ponder`:

```bash
cd <pr-worktree>/apps/web-app
PONDER_APP_ROUTE_TICKET=PARABLE-1045 \
bunx playwright test e2e/admin-ponder/run-results.spec.ts
```

4. Write + validate after (`harness.kind = app_route`):

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode after --ticket PARABLE-1045 --head-sha "$(git rev-parse HEAD)" \
  --workspace "$(pwd)" --force
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode after --ticket PARABLE-1045 --validate --head-sha "$(git rev-parse HEAD)"
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode cleanup-check --workspace <pr-worktree>
```

PNGs + `after.json` live under
`~/.cursor/ship-feature-state/parable-613/<ticket>/visual-proof/`.
Live Flight SQL rows may be skipped with a readiness gap if query-layer is down
— do not forge green.

### `persistent_external` (PARABLE-609)

Baseline remains ponder-admin `:5300` (Stage 0.6). After proof uses the
persistent harness at `http://127.0.0.1:5173/dev/ponder`.

1. Ensure harness Vite is up (see `~/.agent/notes/parable-ponder-harness.md`).
2. Run Playwright matrix capture from the harness worktree:

```bash
cd ~/.agent/worktrees/parable-ponder-harness/apps/web-app
PONDER_HARNESS_TICKET=PARABLE-XXX \
PONDER_HARNESS_REGION=editor \
bunx playwright test e2e/dev-ponder/ponder-regions.spec.ts
```

3. Write + validate after manifest (harness.kind = `persistent_external`):

```bash
# head-sha is the *PR branch* HEAD (component under review)
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode after --ticket PARABLE-XXX --head-sha "$(git -C <pr-worktree> rev-parse HEAD)" \
  --region editor --force
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode after --ticket PARABLE-XXX --validate --head-sha "$(git -C <pr-worktree> rev-parse HEAD)"
python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py \
  --mode cleanup-check --workspace <pr-worktree>
```

PNGs + `after.json` live under
`~/.cursor/ship-feature-state/parable-609/<ticket>/visual-proof/`.
Region-scoped AC assertions + screenshots; no pixel-diff vs ponder-admin.

## Stage 4.9 — Visual QA approval (HUMAN)

**STOP.** Present before/after + AC mapping. Wait for:

`APPROVE VISUAL QA PARABLE-XXX`

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py \
  --kind visual-qa --ticket PARABLE-XXX --approve \
  --quote 'APPROVE VISUAL QA PARABLE-XXX' \
  --proof ~/.cursor/ship-feature-state/parable-609/parable-xxx/visual-proof/after.json \
  --head-sha "$(git rev-parse HEAD)"
```

Then Stage 5 (`gh pr create`) is allowed only if
`stage_compliance_check.py --gate stage5-pr` passes.
