# Case 02 — grader notes

## Critical (V1)

- Must **not** propose a PR with `tenant_settings.go` or `TenantSettingsForm.svelte` on `main` without either (a) same PR as schema+dist+migration, or (b) schema+migration+dist PR merged first and consumer PRs after. Hand-written Go/TS that imports generated types cannot merge before generated types exist on main.

## Must

- Explicit **HARD** edges: schema+migration+dist → backend → frontend (or equivalent).
- Call out that `dist/` belongs with `tenant.graphql` change, not alone.

## Must not

- PR that is "frontend only" if it still imports types that do not exist until schema PR merges — sequencing must fix this (stack or order).

## Baseline failure mode

One PR "tenant grace period" with all files, or frontend PR before schema without stacking.
