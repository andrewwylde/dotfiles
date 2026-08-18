---
name: deploy-release-notes
description: Generate release notes from a GitHub Actions production deploy run. Use this skill whenever the user mentions release notes, deploy diff, deployment changelog, "what shipped", "what's in this deploy", comparing deploys, or provides a GitHub Actions deploy run URL. Also trigger when the user asks what changed between two deployments or wants a summary of a production release.
---

# Deploy Release Notes

Generate per-service release notes by comparing a production deploy run against the previous successful deploy. The output is tailored by audience: product-friendly language for UI/frontend changes, engineering-focused detail for backend services and infrastructure.

## Workflow

### Step 1: Identify the deploy runs to compare

The user provides one of:
- A GitHub Actions run URL (e.g., `https://github.com/parable-work/parable-platform/actions/runs/23450747751`)
- A run ID (e.g., `23450747751`)
- A vague request like "what's in the latest deploy" — in this case, use the most recent run

Extract the **current deploy SHA** from the given run:

```bash
gh run view <RUN_ID> --repo parable-work/parable-platform --json headSha,conclusion,createdAt
```

Then find the **previous successful deploy SHA** by listing recent runs of the same workflow and picking the first one with `conclusion: success` that isn't the current run:

```bash
gh run list --repo parable-work/parable-platform \
  --workflow deploy-parable-apps-prod.yml \
  --limit 10 \
  --json headSha,conclusion,createdAt,databaseId
```

If the current run is still in progress, that's fine — note it in the output header but proceed with the diff.

### Step 2: Get the diff between the two SHAs

Use the GitHub compare API to get commits and changed files:

```bash
# Get commit summaries
gh api repos/parable-work/parable-platform/compare/<PREV_SHA>...<CURRENT_SHA> \
  --jq '.commits[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'

# Get changed files grouped by top-level directory
gh api repos/parable-work/parable-platform/compare/<PREV_SHA>...<CURRENT_SHA> \
  --jq '[.files[].filename]'
```

### Step 3: Map changes to services

Group the changed files into these service areas. Only include areas that actually have changes:

| Directory | Service Name | Audience |
|-----------|-------------|----------|
| `apps/web-app` | Web App | product |
| `apps/chart-generator` | Chart Generator | product |
| `apps/packages` | Shared UI Packages | product |
| `services/web-api` | Web API | engineering |
| `services/web-admin-api` | Web Admin API | engineering |
| `services/tenant-infra-api` | Tenant Infra API | engineering |
| `services/ingestion` | Ingestion Service | engineering |
| `services/platform-connectors` | Platform Connectors | engineering |
| `services/transformation-flows` | Transformation Flows | engineering |
| `services/web-db` | Database (Migrations) | engineering |
| `infrastructure/*` | Infrastructure | engineering |
| `services/pkg` | Shared Go Packages | engineering |

If a commit touches multiple services, it appears under each relevant service.

### Step 4: Enrich with PR context

For each commit, check if it came from a PR (most commits on main do). The commit message usually contains `(#NNNN)` — extract the PR number and fetch its title and body for richer context:

```bash
gh pr view <PR_NUMBER> --repo parable-work/parable-platform --json title,body,labels
```

This gives you the full picture beyond the commit subject line. Use the PR description to understand intent, not just what files changed.

### Step 5: Extract Linear ticket references

Scan commit messages and PR titles/bodies for Linear ticket patterns: `PARABLE-\d+`, `SYSTEM-\d+`, or any `[A-Z]+-\d+` pattern that looks like a ticket ID. Include these as links in the output:

The Linear workspace slug is **`parable`**. Always use this exact format — do not append the issue title to the URL:

Format: `[PARABLE-343](https://linear.app/parable/issue/PARABLE-343)`

Never use `linear.app/parablework/` or add slug suffixes like `/fix-form-state-...`.

### Step 6: Write the release notes

Write the output to `./.context/release-notes-<CURRENT_SHA_SHORT>.md` (e.g., `release-notes-0103f40.md`).

Create the `.context` directory if it doesn't exist.

#### Output structure

```markdown
# Release Notes — <CURRENT_SHA_SHORT>

**Deploy run**: <link to GitHub Actions run>
**Date**: <deploy timestamp>
**Comparison**: `<PREV_SHA_SHORT>` → `<CURRENT_SHA_SHORT>` (<N> commits)
**Status**: <completed | in progress>

---

## Product Changes

### Web App
- <Human-readable summary of change> ([PARABLE-343](https://linear.app/parable/issue/PARABLE-343)) — #1159
- ...

### Shared UI Packages
- ...

---

## Engineering Changes

### Platform Connectors
- <What changed and why, with enough detail for an engineer to understand impact> ([PARABLE-343](https://linear.app/parable/issue/PARABLE-343)) — #1159

### Database (Migrations)
- <Migration description — call out if there are schema changes that need attention>

### Infrastructure
- <What changed — flag if there are config/secret changes>

---

*Generated from [deploy run <RUN_ID>](<run_url>)*
```

#### Writing guidelines by audience

**Product changes** (apps/*, packages, design system):
- Lead with the user-visible outcome, not the implementation
- Use plain language a PM or exec would understand in a 30-second scan
- Good: "Added urgency banner to connector directory page"
- Bad: "feat(vendors): add urgency banner component to ConnectorDirectory.vue"
- Group related commits into a single bullet if they're part of the same feature

**Engineering changes** (services/*, infrastructure/*):
- Include technical detail — what component changed, what the fix addresses
- Call out breaking changes, migration requirements, or config changes explicitly
- Flag anything that affects on-call (new alerts, changed thresholds, infra changes)
- Good: "Fixed GCP log severity mapping and added proxy readiness check for LazyDB — previously health checks could pass before proxy was ready ([PARABLE-476](https://linear.app/parable/issue/PARABLE-476))"
- Bad: "Fixed some stuff in lazydb"

#### Edge cases

- **Commits that only touch tests, CI, or docs**: Include under engineering changes only if they're meaningful (e.g., a new CI workflow). Skip routine test additions.
- **Shared packages** (`services/pkg`, `apps/packages`): Include these under the services/apps that consume them, with a note about what changed in the shared code.
- **Empty diff**: If no commits exist between the two SHAs (e.g., a re-deploy of the same commit), say so clearly: "This deploy contains no new changes — it's a re-deploy of `<SHA>`."
- **Infra-only changes**: If there are no product or service code changes (only infrastructure), note that clearly so engineers know it's a config/infra-only deploy.

### Step 7: Confirm with the user

After writing the file, show a brief summary of what's in the release notes (service count, commit count) and the file path. Ask if they want to adjust anything or post it somewhere (e.g., Slack).
