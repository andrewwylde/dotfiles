---
name: career-growth-evidence
description: >
  Fetches and summarizes GitHub, Linear, and Slack activity for a date range
  through a performance-review lens, producing a structured evidence ledger.
  Use for "gather my accomplishments", "what did I ship this cycle", "evidence
  for self-review", "activity for direct report review", brag doc inputs, or
  before competency mapping or review drafting.
disable-model-invocation: true
---

# Career growth evidence

Collect objective work signals from GitHub, Linear, and Slack for a review period. Output is an [evidence ledger](../references/evidence-ledger-schema.md) for downstream skills.

## Modes

| Mode | Subject |
|------|---------|
| Self-review | The logged-in user (confirm identity before fetching) |
| Manager review | A named direct report (requires identifiers below) |

## Inputs

| Input | Required | Notes |
|-------|----------|-------|
| `period_start`, `period_end` | yes | `YYYY-MM-DD` |
| `github_login` | optional | Defaults to authenticated `gh` user in self-review |
| `linear_user_id` or email | optional | For manager mode or non-default Linear user |
| `slack_user_id` or username | optional | For `from:` filters in Slack search |
| `themes` | optional | Project/theme labels to tag entries |
| `repos` | optional | Limit GitHub scope (org/repo list) |

## Outputs

YAML evidence ledger per [evidence-ledger-schema.md](../references/evidence-ledger-schema.md). Print a short human summary table (source, count, top themes) then the full YAML.

## Human judgment

This skill gathers facts only. It does not rate performance or infer competency levels.

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | none |
| Downstream | `career-growth-competency`, `career-growth-accomplishments`, `career-growth-self-review`, `career-growth-manager-review`, `career-growth-promotion-packet` |

## Workflow

### Phase 1: Confirm scope

1. Confirm mode (self vs manager) and subject identifiers.
2. Confirm date range and theme list.
3. If manager mode and identifiers are missing, stop and ask.

### Phase 2: GitHub

Use `gh` CLI. For large output, use context-mode `ctx_execute` instead of raw Bash dumps.

```bash
# Merged PRs in period (adjust org/repo)
gh search prs --author=@me --merged --merged-at YYYY-MM-DD..YYYY-MM-DD --limit 50 --json title,url,mergedAt,repository

# Issues closed by user (optional)
gh search issues --author=@me --closed --closed YYYY-MM-DD..YYYY-MM-DD --limit 30 --json title,url,closedAt

# Review activity (manager lens: reviews given)
gh api graphql -f query='...'  # only if needed; keep queries small
```

For a direct report, replace `@me` with their `github_login`. If `gh` cannot access their data, record a gap -- do not invent PRs.

### Phase 3: Linear

1. List tools on MCP server `plugin-linear-linear` (read tool schemas before calling).
2. If Linear MCP is not authenticated, ask the user to paste exported issues or authenticate.
3. Query issues assigned to the user completed or updated in the period. Capture: identifier, title, state, project, URL.

### Phase 4: Slack

MCP server `plugin-slack-slack`. Prefer `slack_search_public` (no extra consent) unless the user approves private search.

Example queries (adjust user and dates):

```
from:<@USER_ID> after:YYYY-MM-DD before:YYYY-MM-DD
from:username in:#engineering after:YYYY-MM-DD
```

Run multiple narrow searches rather than one broad query. Summarize threads that show leadership, collaboration, incidents, or customer impact -- not every message.

For private-channel content required for a review, use `slack_search_public_and_private` only after user consent.

### Phase 5: Normalize ledger

1. Deduplicate across sources (same work in Linear + GitHub).
2. Write one `summary` + optional `impact` per entry; perf-review lens (behavior + outcome).
3. Tag `theme_ids` where possible.
4. Record all source failures under `gaps`.

## Failure modes

| Condition | Action |
|-----------|--------|
| Missing date range | Ask; do not proceed |
| Auth failure on a source | Record in `gaps`; continue other sources |
| Zero results | Return empty `entries` with gaps noted; suggest user add manual entries |
| Ambiguous subject (manager mode) | Ask for explicit login/IDs |
