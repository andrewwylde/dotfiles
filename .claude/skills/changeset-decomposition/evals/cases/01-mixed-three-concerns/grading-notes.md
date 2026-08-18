# Case 01 — grader notes

## Must

- Separate **auth** work (`LoginForm`, `login.test.ts`) from **billing** work — different CODEOWNERS teams unless explicitly justified.
- Put **infra/Makefile** in its own small PR or clearly independent first wave; must not be buried inside billing feature PR.
- Schema + migrations (`billing.graphql`, `*.sql`) must not land in the same PR as `billing_export.go` **unless** the plan includes regenerated `platform-schemas/dist/` in that same PR and explains merge order (Pattern 4 allows schema+migration+generated together; not schema+hand-written Go without codegen in between). Prefer: schema PR before backend PR.
- Inventory lists all paths from scenario.

## Must not

- Single PR titled "billing and auth cleanup" covering both domains.
- Merge order that puts backend before schema when backend uses generated types from schema.

## Expected treatment shape (not exact titles)

1. Chore: Makefile + Pulumi (independent).
2. Auth: LoginForm + tests (independent of billing if no imports cross — assume independent).
3. Billing schema: graphql + migrations (+ generated if mentioned).
4. Billing backend: `billing_export.go`.
5. Billing frontend: Svelte + store + new component.

Baseline often merges (3+4+5) or misses infra separation.
