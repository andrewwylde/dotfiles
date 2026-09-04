# Proof Harness Stage Details (Stage 6.45 + Stage 0 preflight)

Load when `/ship-feature` Stage 6.45 runs or Stage 0 infrastructure preflight
is needed. Implements the Datadog harness-first pattern: executable proof with
explicit invariants, bootstrap retry, and red→`/spec-driven`→green loops.

Source analysis: `.context/vibetest/ship-feature-stage6-proof-datadog_2026-07-06.md`

## Why this exists

Stage 6 (`/pr-review-local`) and Stage 6.5 (`/test-benchmark`) evaluate *reviews
and test code quality*. They do not mandate *running* proof commands in the
orchestrator session. Stage 6.45 closes that gap.

**Orchestrator runs proof; subagents do not.** Proof harness is not delegatable —
the main agent must execute commands, capture exit codes, and loop fixes.

## Stage 0 vs Stage 6.45

| When | What runs | Purpose |
|------|-----------|---------|
| **Stage 0 preflight** | `proof_harness_gate.py --mode preflight` | Detect if proof will be needed; check Docker/Postgres reachability; log DSN hints. **Does not run proof tiers.** |
| **Stage 6.45** | `proof_harness_gate.py --mode code` then execute tiers | Run proof commands on PR diff; bootstrap infra with retry; loop `/spec-driven` on failure |

Stage 0 preflight is **conditional** — run when `preflight.triggered` is true
(plan, branch, or task description touches proof-routed paths). Record artifact:

`.context/proof-harness-preflight.json`

This prevents Stage 6.45 from cold-starting Docker diagnosis. If Stage 0
preflight failed (Docker down), Stage 6.45 must retry bootstrap — not skip.

## Language router

| Diff / plan touches | Proof tiers | Reference |
|--------------------|-------------|-----------|
| `services/provider-transformations/` | engine, queue, metadata | PR #4199 Makefile targets; fallback `cargo test` crates |
| `services/transformation-flows/` | unit+integration, optional medallion | Service `make test`; medallion audit for bronze/silver metadata PRs |
| `services/ingestion/`, `platform-schemas/data/` | prove-200s, engine tests | `references/ingestion-stage-details.md` |
| Go API only | `go test ./...` in service | No three-tier model |
| Docs/skills only | skip | `triggered: false` |

## Stage 6.45 procedure (orchestrator)

1. **Detect** (repo root, after Stage 6 completes):
   ```bash
   python3 ~/.cursor/skills/ship-feature/scripts/proof_harness_gate.py \
     --mode code \
     --base origin/main \
     --out .context/proof-harness-gate.json
   ```

2. **When `triggered: false`** — append to PR review:
   `Stage 6.45 SKIPPED: {reason}`. Proceed to Stage 6.5.

3. **When `triggered: true`** — orchestrator executes (not a subagent):

   a. Load tier list from gate JSON `tiers[]`.
   b. **Bootstrap** if any tier `needs_postgres: true`:
      ```bash
      python3 ~/.cursor/skills/ship-feature/scripts/proof_harness_bootstrap.py \
        --max-attempts 3 \
        --log .context/implementation/proof-harness-log.md
      ```
      On failure after 3 attempts: classify as `environment`; log to Linear/issue;
      **do not** write "CI-only gap" and proceed — stop or `/spec-driven` env fix
      if fixable (wrong DSN, migrations not applied).

   c. Run each tier command; append row to proof log with exit code, duration,
      skipped count, failure test names.

   d. **On any tier failure** — Stage 6 action resolution:
      - Add rows to `.context/implementation/stage-6-action-queue.md` (source:
        `proof-harness`, severity: `blocking`)
      - Run `/spec-driven` fix batch (max **3** cycles per Stage 6.45 — one more
        than review fixes because harness failures are executable truth)
      - Re-run failed tiers only
      - Push fix commits before re-run

   e. Append **Proof harness** section to PR review artifact (table template in
      `references/pr-review-github-comment.md`).

4. **Harness completion check** before Stage 6.5:
   ```bash
   test -f .context/proof-harness-gate.json \
     && grep -q '"triggered"' .context/proof-harness-gate.json \
     && echo "PASS: Stage 6.45 gate artifact" || echo "FAIL: run Stage 6.45"
   ```

   When `triggered: true`, also require proof log with all tiers PASS or
   ticketed deferral (security/data-safety deferrals forbidden).

## Provider-transformations tiers (PR #4199)

When `services/provider-transformations/Makefile` exists:

```bash
cd services/provider-transformations
make test-local-engine      # no Postgres
make test-local-queue       # Postgres + orchestration_dev
make test-local-metadata    # Postgres + duroxide_shell walking skeleton
# or: make test-local-all
```

**Fallback** when Makefile targets absent (pre-PR4199 merge):

```bash
cargo test -p provider-transformations --test local_maintenance -- --nocapture
export PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL="${PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL:-postgres://postgres:postgres@localhost:5432/orchestration_dev?sslmode=disable}"
cargo test -p provider-transformations --test admission_loop upsert_compact_unit record_catalog_annotations_merges -- --nocapture
cargo test -p provider-transformations --test duroxide_shell walking_skeleton_promote_records_catalog_annotations_and_enqueues_stats -- --nocapture
```

Prerequisites (from repo root):

```bash
make start-postgres
make run-orchestration-migrations   # when orchestration-db migrations required
```

Homebrew Postgres override (macOS) — **auto-detected** by `proof_harness_bootstrap.py`
when `role "postgres" does not exist`:

```bash
python3 ~/.cursor/skills/ship-feature/scripts/proof_harness_bootstrap.py
# prints: export PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL='postgres://<user>@...'
```

When `tests/seal_handshake.rs` is in the diff and Makefile has
`test-local-seal-handshake`, Stage 6.45 runs that tier after queue/metadata.

## Transformation-flows tiers

```bash
cd services/transformation-flows
make fmt && make lint && make type-check
uv run pytest tests/ -x --timeout=120 -q
```

When diff touches `bronze_i`/`silver` metadata or partition discovery:

```bash
cd services/transformation-flows
./scripts/run_daily_medallion_audits.sh --clients <from-plan> --layers <layer> --dry-run
```

Use `--dry-run` in Stage 6.45 unless plan explicitly requires live GCS reads
(user-approved). Record client/layer scope in proof log.

## Ingestion tiers

Follow `references/ingestion-stage-details.md` prove-200s rule. Minimum:

```bash
cd services/ingestion
uv run pytest tests/unit/ -q --timeout=120
# Class C/D: direct API probe + run_connector_direct when harness works
```

## Stage 0 preflight procedure

Run after schema bootstrap when activation session or branch suggests proof paths:

```bash
python3 ~/.cursor/skills/ship-feature/scripts/proof_harness_gate.py \
  --mode preflight \
  --branch "$(git branch --show-current)" \
  --out .context/proof-harness-preflight.json
```

Optional `--plan plans/foo.plan.md` when plan exists (re-run after Stage 1).

Preflight checks:
- Docker daemon (`docker info` or skip if Homebrew Postgres-only)
- TCP `localhost:5432` (if postgres tier likely)
- `orchestration_dev` / `orchestration_test` database exists (optional `psql` probe)
- Records recommended `PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL`

**Does not fail Stage 0** on infra down — records `postgres_ready: false` so
Stage 6.45 knows to bootstrap early. WARN in session todos if preflight triggered
but postgres not ready.

## Provenance markers

| Artifact | Marker |
|----------|--------|
| Gate JSON (code) | `RUN_BY_SCRIPT: proof_harness_gate.py` |
| Gate JSON (preflight) | `RUN_BY_SCRIPT: proof_harness_gate.py` |
| Proof log | `RUN_BY_SKILL: ship-feature` (Stage 6.45) |

## Anti-patterns (forbidden)

- Delegating proof tiers to a subagent with a context pack
- "CI-only gap" without 3 bootstrap attempts logged
- Grep-based "75% shipped" as proof substitute
- Proceeding to Stage 6.5 while a triggered tier is RED without fix or ticket
- Rubber-stamping PASS without command output in proof log
