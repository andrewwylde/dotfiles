---
name: psgen-workflow
description: Run the psgen code generation pipeline after modifying .graphql schema files. Builds psgen CLI, scalar-lib, and regenerates all platform schemas (SQL, ORM, Go types, TS types, SDK, API routes). Use after editing any file in platform-schemas/schemas/.
---

# psgen Workflow

Run the full code generation pipeline after schema changes. This skill ensures the correct build order and validates output.

## When to Use

- After modifying any `.graphql` file in `platform-schemas/schemas/`
- After modifying `schema.json` config files
- After modifying scalar definitions or scalar-lib code
- After adding new directives

## Steps

### 1. Build the pipeline

Run the full build in correct dependency order:

```bash
cd "$CLAUDE_PROJECT_DIR" && make build-schemas
```

This runs: `build-psgen` → `build-scalar-lib` → `build-schemas` (via `build.py`).

If psgen itself was modified (files in `utils/psgen/`), first rebuild it explicitly:

```bash
cd "$CLAUDE_PROJECT_DIR" && make build-psgen
```

### 2. Check for errors

If the build fails:
- **Schema validation error**: Fix the `.graphql` source file. Common issues: missing `@key` on DB types, undeclared permissions in `@requirePermission`, missing audit fields.
- **Import resolution error**: Check `schema.json` dependencies — the schema you're importing from must be listed.
- **Scalar error**: If you added/changed a scalar, check `utils/psgen/internal/embedded/scalars.graphql`.

### 3. Verify generated output

After successful build, check that expected files were regenerated:

```bash
# For DB schema changes
ls -la "$CLAUDE_PROJECT_DIR/platform-schemas/dist/sql/web-db/"
ls -la "$CLAUDE_PROJECT_DIR/platform-schemas/dist/orm/web-db/"

# For API schema changes
ls -la "$CLAUDE_PROJECT_DIR/platform-schemas/dist/api/web-api/"
ls -la "$CLAUDE_PROJECT_DIR/platform-schemas/dist/types/typescript/"
ls -la "$CLAUDE_PROJECT_DIR/platform-schemas/dist/sdk/typescript/"
```

### 4. If DB schema changed — create a migration

If you modified `platform-schemas/schemas/web-db/`, you likely need a new migration. Use the `/create-migration` skill.

### 5. If API schema changed — check route-impl

New API endpoints generate interface stubs. Check if new route-impl files were scaffolded:

```bash
ls -lt "$CLAUDE_PROJECT_DIR/services/web-api/internal/route-impl/" | head -10
```

New scaffold files need business logic implementation.

### 6. Rebuild downstream consumers

After schema changes, downstream Go services need recompilation:

```bash
cd "$CLAUDE_PROJECT_DIR" && make build-go
```

For frontend type changes, the TypeScript packages are auto-linked via workspace, but verify:

```bash
cd "$CLAUDE_PROJECT_DIR/apps/web-app" && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | head -30
```

## Quick Reference

| What changed | Minimum command |
|---|---|
| `.graphql` schema only | `make build-schemas` |
| psgen code (`utils/psgen/`) | `make build-psgen && make build-schemas` |
| Scalar lib (`utils/psgen/scalar-lib/`) | `make build-scalar-lib && make build-schemas` |
| Everything | `make build` |
