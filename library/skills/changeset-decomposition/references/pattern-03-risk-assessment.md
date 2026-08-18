# Pattern 3: Risk and Complexity Assessment

Score each candidate PR node from Pattern 2 for reviewer effort, deployment risk, and rollback complexity. Risk scores drive two decisions in Pattern 4: (1) whether a risky change should be split further, and (2) how much review isolation is warranted.

## Goal

Produce a risk/complexity score for each candidate PR node. Identify which candidates are high-risk and should be reviewed in isolation (never bundled with unrelated changes), and which are safe to merge quickly without special precautions.

## Risk dimensions

Score each candidate on a 1-3 scale per dimension, then sum for a total risk score (3-15).

### Dimension 1: Change type risk (1-3)

| Score | Type | Examples |
| ----- | ---- | ------- |
| 3 | Schema / contract change | .graphql mutation, DB migration, API breaking change |
| 2 | Logic change with side effects | New business rule, auth flow change, data mutation |
| 1 | Refactor, config, docs, test-only | No behavior change, purely additive, documentation |

### Dimension 2: Blast radius (1-3)

How many users, tenants, or systems are affected if this breaks?

| Score | Blast radius | Examples |
| ----- | ------------ | ------- |
| 3 | All tenants / all users / core infrastructure | Auth, billing entitlements, API gateway config |
| 2 | Subset of users or specific feature area | A single feature flag, one connector type |
| 1 | Developer-only or internal tooling | CI config, dev tooling, admin-only panel |

### Dimension 3: Rollback complexity (1-3)

How hard is it to undo this change after it merges?

| Score | Rollback cost | Examples |
| ----- | ------------- | ------- |
| 3 | Requires data migration to reverse | DB migration with data backfill, schema removal |
| 2 | Requires a revert PR and redeploy | Logic change with downstream side effects |
| 1 | Instant rollback (feature flag, config) | Env var, feature flag, documentation only |

### Dimension 4: Test coverage confidence (1-3)

How much automated coverage exists for this change?

| Score | Coverage confidence | Examples |
| ----- | ------------------- | ------- |
| 3 | Untested or manual-only | New UI with no component tests, new flow with no E2E |
| 2 | Partial coverage | Unit tests exist but no integration or E2E coverage |
| 1 | Well-tested | Full unit + integration coverage, existing E2E suite covers it |

### Dimension 5: Reviewer familiarity (1-3)

How familiar is the typical reviewer with this area?

| Score | Familiarity | Examples |
| ----- | ----------- | ------- |
| 3 | Niche / specialized knowledge required | psgen schema DSL, Prefect pipeline internals, crypto primitives |
| 2 | Moderate context needed | Domain-specific business rules, non-obvious data flows |
| 1 | Generally understandable | Standard CRUD, UI components, config changes |

## Step-by-Step Process

### Step 1: Score each candidate node

For each candidate PR node from Pattern 2, score all 5 dimensions:

```markdown
## Risk Scores

| Candidate PR | Change Type | Blast Radius | Rollback | Test Coverage | Familiarity | TOTAL |
| ------------ | ----------- | ------------ | -------- | ------------- | ----------- | ----- |
| billing-schema | 3 | 3 | 3 | 2 | 3 | 14 |
| billing-backend | 2 | 2 | 2 | 2 | 2 | 10 |
| billing-frontend | 1 | 2 | 1 | 3 | 1 | 8 |
| auth-refactor | 1 | 3 | 2 | 1 | 2 | 9 |
| design-system | 2 | 2 | 1 | 2 | 1 | 8 |
| infra-chore | 1 | 1 | 1 | 1 | 1 | 5 |
```

### Step 2: Classify by risk tier

| Tier | Score | Meaning | Implication |
| ---- | ----- | ------- | ----------- |
| HIGH | 11-15 | Needs maximum isolation and review | Must not be bundled with other changes; warrants dedicated reviewer |
| MEDIUM | 7-10 | Needs focused review | OK to bundle only with closely related low-risk changes |
| LOW | 3-6 | Low-friction merge | Can be bundled or fast-tracked |

```markdown
## Risk Tiers

HIGH (11-15): billing-schema (14)
MEDIUM (7-10): billing-backend (10), auth-refactor (9), billing-frontend (8), design-system (8)
LOW (3-6): infra-chore (5)
```

### Step 3: Flag high-risk candidates for size check

Any HIGH-tier candidate must be evaluated for further splitting before Pattern 4. High-risk + large diff is the worst-case scenario for reviewers.

For each HIGH-tier node:
- **If diff > 200 lines:** Consider whether it can be split into a schema-only PR and a logic PR, or a migration-only PR and an application-code PR.
- **If untested (test coverage score = 3):** Flag that tests must be part of this PR (not a follow-up PR) before it can merge.
- **If rollback complexity = 3 (irreversible):** Flag for explicit mention in PR description — reviewer must consciously accept the cost.

### Step 4: Identify review strategy per tier

```markdown
## Review Strategy

billing-schema [HIGH - 14]:
  - Dedicated reviewer with schema/psgen familiarity required
  - Cannot bundle with other changes
  - Must include rollback plan in PR description (irreversible migration)
  - Tests must be included, not deferred

billing-backend [MEDIUM - 10]:
  - Can merge after billing-schema
  - Prefer reviewer who knows route-impl layer
  - Include integration test evidence

auth-refactor [MEDIUM - 9]:
  - Independent — high blast radius but low change type risk (refactor only)
  - Recommend merging during low-traffic window
  - Must have before/after behavior equivalence proof

billing-frontend [MEDIUM - 8]:
  - Standard review — Svelte component changes
  - Storybook/screenshot comparison encouraged

design-system [MEDIUM - 8]:
  - Brief focused review; design token changes affect all tenants

infra-chore [LOW - 5]:
  - Fast-track; trivial rollback; no business logic
```

## Anti-patterns

- **Bundling a HIGH-risk change with LOW-risk changes:** Reviewers must context-switch, and the high-risk change gets less scrutiny. Always isolate HIGH-tier candidates.
- **Splitting a single high-risk change across two PRs to reduce "apparent" risk:** The risk doesn't decrease by splitting; it becomes harder to reason about. Keep atomic high-risk units together.
- **Treating "small diff" as equivalent to "low risk":** A 3-line DB migration that drops a column is LOW in size and HIGH in risk. Use the scoring rubric, not intuition.

## Checklist

- [ ] All 5 dimensions scored for each candidate node
- [ ] Risk totals calculated
- [ ] Tier classification (HIGH/MEDIUM/LOW) assigned
- [ ] HIGH-tier nodes checked for further splitting
- [ ] HIGH-tier nodes checked for test coverage completeness
- [ ] Review strategy note written for each candidate
- [ ] Any irreversible changes flagged explicitly
