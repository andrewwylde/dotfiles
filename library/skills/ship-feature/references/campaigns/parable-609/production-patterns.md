# Main production patterns (schema-first)

1. Schema: TS classes in `platform-schemas/services/*/src/definitions/*.schema.ts` + `operations/*` → `make build-schemas` → never edit `platform-schemas/dist/`.
2. Frontend types: `@parable-platform/web-admin-api-types` + `parse*FromJSON` at wire boundaries.
3. SDK: `getClientAdminSdk().parableTemplates.*` via BFF — no custom `fetch`.
4. Tests: mock from `WebAdminApiSdk['parableTemplates']` namespace types.
5. Backend: route-impl + `services/pkg/parablegit`.
6. UI copy: say "Workspace", never "tenant" in user-facing strings.
7. Visual proof surface: persistent harness at `~/.agent/worktrees/parable-ponder-harness`
   route `/dev/ponder` (PARABLE-269 schema stack tip of #4732). Notes:
   `~/.agent/notes/parable-ponder-harness.md`.
8. Stage 4.75 mount → Stage 4.8 capture:
   - Implement component in harness worktree (`$lib/domains/parables/...`).
   - Apply component+tests only onto the PR branch (`children_meta.pr_base`).
   - On harness branch: register region mount + colocated fixture; commit
     `harness(PARABLE-XXX): mount <region>`.
   - Seed matrix: `visual_qa_gate.py --mode matrix-template --ticket ... --region ...`
   - Capture: Playwright `e2e/dev-ponder/ponder-regions.spec.ts` → PNGs in
     `~/.cursor/ship-feature-state/parable-609/<ticket>/visual-proof/`.
   - Write after manifest: `visual_qa_gate.py --mode after` (harness.kind =
     `persistent_external`). Human sign-off before Stage 5.
   - Never commit `/dev/ponder`, registry mounts, or PNGs to the child PR.
     `cleanup_check` scans the PR workspace only.
9. Planning (all 609 children) — keep these general rules in every plan:
   - **Absolute reference paths:** cite ponder-admin / scaffold files with full
     paths under the reference worktree (`…/3fmc/...`), not relative paths that
     only exist outside the PR checkout. See harness notes.
   - **Linear AC traceability table:** every Linear acceptance bullet →
     `in_scope` | `deferred(<existing or new 609 child>)` | `out_of_scope`.
   - **Deferral hygiene:** when thinning scope because a contract is missing,
     create/link a follow-up under PARABLE-609 with `blockedBy` set (e.g. 337
     for report-run types). Do not silently drop Linear AC. Do not open
     “migrate to generated types” tickets when the type already exists on main.
