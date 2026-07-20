---
description: "Morning daily planning assistant that gathers context from GitHub PRs, Linear issues, and Slack channels, then creates a Notion journal entry and draft Slack status message. Use this skill every morning to start your day, when you say 'daily plan', 'morning plan', 'start my day', 'what's on my plate', 'daily standup prep', 'morning check-in', or any variation of planning your workday. Also use when the user asks to catch up on what happened overnight or since they last checked in."
alwaysApply: false
---

# Daily Planning Assistant

Gather context from GitHub, Linear, and Slack, then produce a Notion journal entry and a draft Slack status message. This is a read-heavy workflow: the only writes are the Notion journal page and a local timestamp file.

**Safety rules:**
- Do NOT send any Slack messages. Only produce draft text for the user to copy-paste.
- Do NOT modify any Linear issues. Read only.
- Do NOT modify any GitHub PRs. Read only.
- The Notion journal entry and the timestamp file are the only write operations.

---

## Step 0: Load Required Tool Schemas

Before gathering any data, load all MCP tool schemas in a single batch call:

```
ToolSearch("select:mcp__claude_ai_Linear__list_issues,mcp__claude_ai_Linear__list_comments,mcp__claude_ai_Slack__slack_search_channels,mcp__claude_ai_Slack__slack_read_channel,mcp__notion__notion-create-pages,mcp__notion__notion-fetch")
```

This avoids multiple sequential ToolSearch calls blocking progress later.

---

## Step 1: Load Last Check Timestamp

Read the file `~/.agent/daily-plan-last-check.json`. If the directory or file does not exist, create the directory and default to the last business day at 9:00 AM local time (if today is Monday, default to Friday; if Sunday, default to Friday; if Saturday, default to Friday).

The file schema:

```json
{
  "last_check": "2026-04-07T09:00:00Z",
  "last_journal_url": "https://notion.so/...",
  "notion_data_source_id": "494af84b-7d2a-4da7-a370-d5ba3b06b129",
  "seen_prs": {}
}
```

Parse `last_check` as the cutoff timestamp. Also read `notion_data_source_id` if present -- it will be used in Step 6 to skip Notion database discovery. Load `seen_prs` (default `{}`) -- a dict mapping PR number strings to the ISO date they were first seen. All "since last check" filtering uses this value.

Store the cutoff as both an ISO-8601 string and a Unix epoch timestamp (Slack tools need epoch format for `oldest` parameter).

**Before gathering any data**, verify the Notion MCP token is live with a lightweight fetch. Use `mcp__notion__notion-fetch` on the journal database URL (`https://www.notion.so/33b6ab92e44081698486f76e7b8ecef3`). If it fails with an auth error, warn the user immediately and stop -- do not proceed through all data-gathering steps only to fail at journal creation.

---

## Step 2: Gather GitHub PR Context

Fetch raw PR data to a temp file, then run the persistent filter script:

```bash
gh pr list --repo parable-work/parable-platform --state open \
  --json number,title,author,files,reviewRequests,updatedAt,url,additions,deletions \
  > /tmp/prs_raw.json

# Recreate filter script if missing
[ -f ~/.agent/scripts/filter_prs.py ] || mkdir -p ~/.agent/scripts && \
  cp /dev/null ~/.agent/scripts/filter_prs.py  # placeholder; will be written by improve-skill

TODAY=$(date +%Y-%m-%d)
SEEN='<SEEN_JSON>'  # substitute the seen_prs JSON string from Step 1 (use '{}' if empty)
python3 ~/.agent/scripts/filter_prs.py '<CUTOFF_ISO>' "$SEEN" "$TODAY" /tmp/prs_raw.json
```

Replace `<CUTOFF_ISO>` with the actual cutoff ISO string and `<SEEN_JSON>` with the `seen_prs` object from last-check.json (JSON-encoded, single-quoted or written to a temp var).

The script outputs `{"prs": [...], "seen_prs": {...}}`. Save `seen_prs` from the output -- it will be persisted in Step 7.

**This script is the only source for the PR Review Queue.** Do not supplement with `gh search prs --review-requested` or similar search APIs. GitHub search returns stale or historical review requests (e.g. SAML, CICDv2, authoring WIP) that are not on the PR's current `reviewRequests` list.

**Two-tier PR inclusion rules (filter_prs.py):**
1. **Explicit**: `andrew-parable` is on the PR's current `reviewRequests` -- include regardless of paths.
2. **Team + overlap**: `platform` or `product-engineering` is a reviewer AND PR touches `services/web-api/`, `services/web-admin-api/`, or `apps/web-app/` -- include only if not in an excluded lane (below).

**Always exclude own-authored PRs** (`author.login == andrew-parable`). Those belong in Task Log as shepherding items, not the PR Review Queue.

**Excluded lanes (team tier only; explicit reviewer bypasses):**
| Class | Examples | Why excluded |
|-------|----------|--------------|
| chore/deps | dependabot consolidations, `chore(deps):` | platform hygiene, not Andrew's review lane |
| CI/tooling | affected Go modules, daily CI runner, `.github/`, `scripts/ci/` | platform CI ownership |
| infra/docs | `infrastructure/`, `docs(edr):`, `docs/internal/` | outside web-app/API product surface |

**No awareness tier.** PRs that only touch overlap paths without a current review request are noise -- omit entirely.

**Staleness handling in synthesis (Step 5):**
- `days_carried == 0`: new since last check -- show first in queue
- `days_carried 1-2` (explicit): show with `[+N days]` marker
- `days_carried 3+` (non-explicit): move to Tomorrow Problems section, not PR Review Queue

Size heuristic: S = <50 lines changed, M = 50-300, L = 300-1000, XL = >1000.

---

## Step 3: Gather Linear Issues

Use the Linear MCP tool `mcp__claude_ai_Linear__list_issues` with `assignee: "me"` to fetch all issues assigned to the authenticated user. Exclude issues with state type `completed` or `canceled` — focus on active work.

For each issue, capture:
- Title, identifier (e.g., PARABLE-583), status name, priority (1=Urgent, 2=High, 3=Normal, 4=Low)

Then, for issues that are In Progress or In Review, fetch recent comments using `mcp__claude_ai_Linear__list_comments` with the issue ID. Check comment timestamps against the last-check cutoff to identify new activity.

Group issues by status category:
- **In Progress**: issues with state type `started`
- **In Review**: issues with state name containing "review"
- **Blocked / Other**: everything else that's active (backlog, triage, todo)

Note any blockers mentioned in recent comments or issue descriptions (look for keywords: "blocked", "waiting", "depends on", "need input").

---

## Step 4: Gather Slack Activity

Read recent messages from these channels since the last check.

Rationale: morning digest should surface threads that shape today's product/apps work — not security-alert noise. Prefer eng pulse, apps/UI, TTS squad, platform/API, and design.

- `#tech-general`
- `#guild-apps`
- `#squad-team-time-spend`
- `#guild-platform`
- `#product-design`

For each channel:

1. Use `mcp__claude_ai_Slack__slack_search_channels` with the channel name (e.g., query: "tech-general") to get the channel ID.
2. Use `mcp__claude_ai_Slack__slack_read_channel` with the channel ID and `oldest` set to the Unix epoch timestamp of the last check to read messages since then.
3. Summarize: key discussions, decisions made, questions asked, anything requiring the user's attention or input.
4. Flag any messages that directly mention or are relevant to the user's active Linear tickets.

If a channel cannot be found or history fails (missing OAuth scopes, bot not in channel), skip it and add one footnote in the Slack Digest: "Slack history unavailable (integration)." Do not add MCP scope fixes to Task Log or Tomorrow Problems -- that is integration config, not daily work.

To speed things up, search for all five channels in parallel if possible -- the channel lookups are independent of each other.

---

## Step 5: Synthesize Daily Plan

From the gathered data, produce these sections:

### Today's Focus (2-3 bullets)
Derived from: highest priority Linear issues in "In Progress", any PRs with requested reviews, any Slack threads needing response. Frame as "what would make today successful."

### PR Review Queue
Ordered list from `filter_prs.py` output only (`category` = `explicit` or `team_overlap`). PR number, title, author, why it's relevant (`explicit` vs `team_overlap`), size (S/M/L/XL). Target 2-5 items; if more, keep explicit first, then team_overlap by recency.

### Ticket Progress Summary
Each active Linear ticket: ID, title, current status, what happened since last check (new comments, status changes), next action needed.

### Slack Digest
Per-channel summary of notable activity since last check. Threads requiring response highlighted.

### Decisions/Questions
Open questions surfaced from Slack threads, PR comments, or Linear ticket comments that need the user's input.

### Draft Slack Status Message
Short bullets categorized by ticket. Under 200 words. Blockers and questions highlighted at the top or with a distinct marker.

Format example:
```
Morning update:
* PARABLE-583: continuing schema-defined time spend routes, targeting PR today
* POV-548: DB schema for admin config -- need input on [specific question]
* PR reviews: #1542 (connector auth), #1538 (migration fix)
* Blocker: waiting on [X] for [Y]
```

---

## Step 6: Create Notion Journal Entry

**First, discover whether Notion MCP tools are available.** Search for any tool with "notion" in the name (e.g., tools prefixed with `mcp__notion` or similar). The exact tool names may vary depending on the user's MCP configuration.

### If Notion MCP is available

Read `notion_data_source_id` from the timestamp file loaded in Step 1. If present, use it directly as the `data_source_id` parent for page creation -- skip fetching the database to discover it.

If absent (first run), fetch the journal database (database ID: `33b6ab92e44081698486f76e7b8ecef3`) to discover the data source ID from the `<data-source url="collection://...">` tag, then persist it in the timestamp file (Step 7) for future runs.

Create a new page using the data source ID as the parent.

**Page title**: today's date in `YYYY-MM-DD` format.

**Page content** — use this exact template structure, pre-filling from gathered data where indicated:

```markdown
### Today's focus

- [derived focus item 1 from synthesis]
- [derived focus item 2]
- What would make today feel successful: [derived from highest-impact items]

---

### Log

**Morning check-in**

- Energy / mood:
- What feels easy:
- What feels hard or unclear: [pre-fill with any identified blockers or ambiguous items from Linear/Slack]

**Midday snapshot**

- What actually happened:
- Surprises or blockers:
- Quick decisions made (if any):

**End-of-day reflection**

- What I moved forward:
- What's still open:
- What I learned / noticed:

---

### Decisions, Questions, Ideas

**Decisions**

- [ ] [any pending decisions surfaced from Slack/Linear/PRs]

**Questions**

- [ ] [any open questions surfaced from Slack/Linear/PRs]

**Idea seeds**

- [any ideas that emerged from the synthesis, or leave blank]

---

### Task Log

- [ ] Review PR #NNNN: [title] ([author])
- [ ] [ticket ID]: [next action from synthesis]
- [ ] [any other concrete actions identified]

---

### Tomorrow Problems

- [ ] [anything identified as not-today but needs attention soon]
```

Pre-fill what you can from the gathered data. Leave user-reflective sections (energy/mood, what feels easy, midday/end-of-day) blank for the user to fill manually.

Capture the URL of the created Notion page for the timestamp file and final output.

### If Notion MCP is NOT available

Output the full journal content as formatted markdown in the conversation. Tell the user:

```
Notion MCP is not configured. Here's your journal entry as markdown — you can paste it into Notion manually.
```

Set the journal URL to `null` in the timestamp file.

---

## Step 7: Update Last Check Timestamp

Write the current time, journal URL, Notion data source ID, and updated `seen_prs` to `~/.agent/daily-plan-last-check.json`:

```json
{
  "last_check": "<current ISO-8601 timestamp>",
  "last_journal_url": "<notion page URL or null>",
  "notion_data_source_id": "<data source ID used or discovered>",
  "seen_prs": "<seen_prs from filter script output>"
}
```

`seen_prs` comes from the `seen_prs` key in the filter script output (Step 2). It maps PR number strings to the ISO date they were first included. PRs no longer in the open list are automatically absent from next run's output -- no explicit pruning needed.

Include `notion_data_source_id` so subsequent runs skip the discovery fetch. Create the `~/.agent/` directory first if it does not exist.

---

## Step 8: Present Summary

Output to the user:

1. **Notion journal link** (if created) or note that markdown was output instead
2. **Draft Slack status message** — formatted and ready to copy-paste. Remind the user this was NOT sent.
3. **Brief summary**: PR count in review queue (from filter script only), active ticket count, notable Slack activity highlights. Do not report total open PRs or stale search hits.
4. **Link to previous journal** (from the loaded timestamp file, if it existed)

End with a note like: "Draft status message is ready to copy-paste — it has not been sent. Edit your Notion journal throughout the day."
