# Pattern 4: PR Boundary Definition

Draw the final lines between PRs. Use the inventory (Pattern 1), dependency graph (Pattern 2), and risk scores (Pattern 3) to produce a named PR list with concrete file assignments.

## Goal

Produce a list of named PRs where each PR:
- Is independently deployable (no broken intermediate state on main)
- Has a coherent scope (one logical thing)
- Has its own tests (behavior changes ship with verification)
- Is bounded in size (a reviewer can hold its full context in their head)

## Decision framework

Work through these questions in order for each candidate node from Pattern 2:

```
Is this node a HIGH-risk candidate (score 11-15 from Pattern 3)?
    YES -> It gets its own PR, never bundled. Stop here for this node.
    NO  -> Continue.

Does this node have a HARD dependency on another node?
    YES -> These nodes must be in separate PRs in dependency order, OR bundled
           together if they are small and tightly coupled (see bundling rules below).
    NO  -> Continue.

Is this node completely independent (no edges in the dependency graph)?
    YES -> It is a natural standalone PR. Could also fast-track or be pre-merged.
    NO  -> Continue.

Does this node share ownership (CODEOWNERS, reviewer domain) with another node
AND have only SOFT dependencies between them AND both are MEDIUM/LOW risk?
    YES -> Consider bundling them into one PR if total diff stays under 300 lines.
    NO  -> Give each its own PR.
```

## Bundling rules

Bundle two changes into the same PR ONLY when ALL of these hold:

1. They share the same reviewer domain (same CODEOWNERS owners or same team).
2. They have only SOFT dependencies between them (neither is strictly blocked without the other).
3. The combined diff stays under ~300 net lines (a rough cognitive limit for a thorough review).
4. Neither is HIGH-risk.
5. A reviewer seeing both at once produces better signal than seeing each separately.

**Do NOT bundle:**
- A schema change with any downstream consumer (even if small) — the schema must land and psgen must run first.
- A refactor with a feature — reviewers cannot verify behavior equivalence while also evaluating new behavior.
- A high-blast-radius change (auth, billing entitlements) with unrelated work.
- A DB migration with any application code reading the new column.

## Special handling: cross-cutting files

Cross-cutting files identified in Pattern 1 (shared utilities, design tokens, generated outputs) need explicit assignment:

- **Shared utility introduced for the first time:** Goes in the PR that introduces the utility, not the PR that first uses it. Or, if used by multiple PRs, it gets its own "foundation" PR.
- **Generated files (dist/, tokens.*):** Always go in the same PR as the source change that triggered regeneration. Do not create a PR that only contains generated file updates.
- **Package manifest changes (package.json, go.mod):** Assign to the PR whose feature required the new dependency. If two PRs need the same new dependency, the first PR to merge carries it.

## Step-by-Step Process

### Step 1: Start from the dependency graph nodes

Use the node list from Pattern 2. For each node, apply the decision framework above.

### Step 2: Name each PR

Give each PR a descriptive name in the format: `[type]: [scope] — [one-line description]`

- `feat: billing — add invoice status field and UI`
- `refactor: auth — remove deprecated login path`
- `chore: infra — add INVOICE_STATUS_ENABLED env var`
- `feat: design-system — add destructive Button variant`

This naming is used in Pattern 5 for the sequencing plan and feeds directly into `split-to-prs` for PR titles.

### Step 3: Assign files to each PR

For each named PR, list the exact files (or file patterns) it owns. Every changed file from the Pattern 1 inventory must appear in exactly one PR.

```markdown
## PR Definitions

### PR-1: chore: infra — add INVOICE_STATUS_ENABLED env var
**Files:**
- services/web-api/.env.example  (add new var)
- apps/web-app/.env.example      (add new var)
- make/config.mk                 (if relevant)

### PR-2: feat: billing-schema — add invoice_status to billing schema
**Files:**
- platform-schemas/schemas/billing.graphql
- services/web-db/migrations/sql/20260515HHMMSS_add_invoice_status.up.sql
- services/web-db/migrations/sql/20260515HHMMSS_add_invoice_status.down.sql
- platform-schemas/dist/**  (regenerated — include but note as generated)

### PR-3: feat: billing-backend — implement invoice status logic
**Files:**
- services/web-api/internal/route-impl/billing_invoice_status.go
- services/web-api/internal/route-impl/billing_invoice_status_test.go

### PR-4: feat: design-system — add destructive Button variant
**Files:**
- apps/packages/design-system/src/lib/atoms/button/Button.component.svelte
- apps/packages/design-system/src/lib/atoms/button/Button.types.ts

### PR-5: feat: billing-frontend — invoice status UI
**Files:**
- apps/web-app/src/lib/domains/billing/components/invoice-status/**
- apps/web-app/src/lib/domains/billing/components/invoice-status.test.ts

### PR-6: refactor: auth — remove deprecated login path
**Files:**
- apps/web-app/src/lib/domains/auth/components/login/**  (modified)
- apps/web-app/src/routes/auth/+page.svelte  (modified)
```

### Step 4: Verify coverage and independence

**Coverage check:** Every file from Pattern 1's inventory appears in exactly one PR definition above. No file is missing or duplicated.

**Independence check:** For each PR, ask: "If this is the only PR that has merged, does main still build and pass tests?" If NO, either the PR needs its dependency listed (handled in Pattern 5) or the boundary is wrong.

**Test coverage check:** For each PR where `change type != refactor AND change type != chore AND change type != docs`, verify that at least one test file is included in the same PR.

## Output format

```markdown
## Final PR Definitions

| PR | Name | Files | Risk | Depends On |
| -- | ---- | ----- | ---- | ---------- |
| PR-1 | chore: infra — env vars | 3 | LOW | none |
| PR-2 | feat: billing-schema | 4 (+ generated) | HIGH | PR-1 |
| PR-3 | feat: billing-backend | 2 | MEDIUM | PR-2 |
| PR-4 | feat: design-system | 2 | MEDIUM | none |
| PR-5 | feat: billing-frontend | 3 | MEDIUM | PR-2, PR-4 |
| PR-6 | refactor: auth | 3 | MEDIUM | none |

**Coverage:** 17/17 changed files assigned (+ generated outputs)
**Independent PRs (no dependencies):** PR-1, PR-4, PR-6
```

## Anti-patterns in boundary definition

| Anti-pattern | Problem | Fix |
| ------------ | ------- | --- |
| "All tests in one PR, all logic in another" | Tests without logic are meaningless; logic without tests is unverifiable | Keep tests with the code they test |
| "One PR per file type (.graphql, .go, .svelte)" | Layer-based split creates artificial dependency chains | Split by feature/domain, not by file type |
| "Bundle schema + backend + frontend because they're all for one feature" | One PR, three risk levels, three reviewer domains, 500+ lines | Split by layer; sequence by dependency |
| "Defer tests to a follow-up PR" | Allows behavior changes to merge unverified indefinitely | Tests must ship with the logic |
| "Put generated files in their own PR" | Generated files are outputs, not changes; they belong with their source | Generated files go with the source that triggers regeneration |

## Checklist

- [ ] Each candidate node assigned to exactly one PR
- [ ] Every file from Pattern 1 inventory assigned to exactly one PR
- [ ] No file is in two PRs
- [ ] HIGH-risk nodes each have their own PR (not bundled)
- [ ] Bundled PRs satisfy all 5 bundling rules
- [ ] Schema changes are not bundled with consumers
- [ ] Each PR with behavior changes includes tests
- [ ] Generated files assigned to the PR that triggered their regeneration
- [ ] Cross-cutting files explicitly assigned
- [ ] PR names written in `[type]: [scope] — [description]` format
- [ ] Independence check passed for each PR
