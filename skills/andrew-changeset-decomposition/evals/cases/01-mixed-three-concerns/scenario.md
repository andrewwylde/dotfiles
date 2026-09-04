# Scenario 01 — mixed three concerns

**User message (paste verbatim after protocol prefix):**

---

My branch is huge. Split it into reviewable PRs with merge order. Here is `git diff main...HEAD --name-status` and `--stat`:

```
M  apps/web-app/src/lib/domains/billing/components/InvoiceTable.svelte
M  apps/web-app/src/lib/domains/billing/stores/invoiceStore.ts
A  apps/web-app/src/lib/domains/billing/components/InvoiceExportButton.svelte
M  services/web-api/internal/route-impl/billing_export.go
M  platform-schemas/schemas/billing.graphql
A  services/web-db/migrations/sql/20260514120000_add_exported_at.up.sql
A  services/web-db/migrations/sql/20260514120000_add_exported_at.down.sql
M  apps/web-app/src/lib/domains/auth/components/LoginForm.svelte
M  apps/web-app/src/lib/domains/auth/login.test.ts
M  infrastructure/pulumi/Pulumi.dev.yaml
M  Makefile
```

Stat summary (approximate):

```
 .../billing/InvoiceTable.svelte       | 40 ++++++
 .../billing/InvoiceExportButton.svelte | 120 ++++++
 .../billing/stores/invoiceStore.ts    | 25 ++-
 .../route-impl/billing_export.go       | 200 +++++-
 platform-schemas/schemas/billing.graphql | 15 +-
 .../20260514120000_add_exported_at.up.sql | 8 +
 .../auth/components/LoginForm.svelte   | 80 +++---
 .../domains/auth/login.test.ts        | 30 +-
 infrastructure/pulumi/Pulumi.dev.yaml | 2 +
 Makefile                              | 5 +
```

`CODEOWNERS` excerpt:

```
/apps/web-app/src/lib/domains/billing/  @team-revenue
/apps/web-app/src/lib/domains/auth/     @team-identity
/services/web-api/                      @team-platform
/platform-schemas/                      @team-platform
/services/web-db/migrations/            @team-platform
/infrastructure/                        @team-devops
```

Assume migrations match the GraphQL field `exportedAt` on `Invoice`. Assume `billing_export.go` uses generated types from the schema change. `Makefile` and `Pulumi.dev.yaml` only bump a dev-only flag unrelated to billing UI.

---
