---
name: gap-analysis
description: Produce a verified gap analysis for a Parable project milestone or Linear ticket. Maps what exists (on main), what's in flight (open PRs), and what's missing (no ticket, no owner) across all pipeline layers. Use when the user says "gap analysis", "where are we on M1", "what's missing for PARABLE-XXX", "map the gaps", "what's left to ship", or provides a Linear ticket or milestone to analyze. Do NOT use for PR reviews, code reviews, or architecture reviews (use swarm-review, parable-pr-swarm, or arch-review instead).
license: CC-BY-4.0
metadata:
  author: andrew-parable
  version: 1.0.0
---

# Gap Analysis

Produce a verified, layer-by-layer gap analysis for a Parable project milestone or ticket. Output: a markdown document listing what's done, what's in flight, and what's missing -- with every claim verified against GitHub, Linear, and the codebase.

## Inputs

The user provides one of:
- A Linear ticket ID (e.g., `PARABLE-482`, `SYSTEM-1171`)
- A milestone label (e.g., "M1", "Core Time Donut")
- A project name (e.g., "Team Time Spend")

If the input is ambiguous, use `AskUserQuestion` to clarify scope before proceeding.

## Phase 1: Scope

Fetch the Linear ticket or milestone to understand what "done" looks like.

1. Use Linear MCP tools to fetch the ticket. Extract: title, description, acceptance criteria, status, assignee, child tickets, blocking/blocked-by relations, project, milestone.
2. If the input is a milestone label, search Linear for the project and milestone, then list all tickets under it with their statuses.
3. From the ticket/milestone description and child tickets, identify which **pipeline layers** are involved. Read `references/parable-layers.md` for the layer definitions and what to search for in each.
4. Write a brief scope statement: "This analysis covers layers X, Y, Z for milestone M. The goal is [from ticket description]."

Output of this phase: a list of layers to investigate and the Linear ticket tree.

## Phase 2: Gather

Launch parallel subagents to collect data from all sources. Each agent gets a focused brief. **All agents must use the `targeted-file-read` skill for any file likely over 200 lines** (specs, EDRs, migrations, GraphQL schemas). See "Large File Handling" below for the short rules each agent brief must include.

### Agent 1: Linear + Slack

Prompt the agent with:
- The ticket IDs and milestone from Phase 1
- Instructions to fetch every ticket in the milestone with: status, assignee, due date, PR attachments, blocking relations, recent comments (last 7 days)
- Instructions to search Slack `#squad-team-time-spend` (or the relevant squad channel) for: status updates, scope changes, blockers, and ownership discussions from the last 7 days
- Instructions to note any tickets completed TODAY (they may have been in-progress when earlier data was gathered)

### Agent 2: GitHub + Codebase

Prompt the agent with:
- The layer list from Phase 1 and the search targets from `references/parable-layers.md`
- Instructions to find all open PRs related to the project: `gh pr list --repo parable-work/parable-platform --search "<keywords>" --state open`
- Instructions to find recently merged PRs (last 14 days): `gh pr list --search "<keywords>" --state merged`
- For each layer, search the codebase for existing artifacts using Glob and Grep (not Read on large files)
- Report for each artifact: file path, what it defines, whether it's on main or only in a PR, completeness status

### Agent 3: Specs and Docs (only if specs exist for this project)

Prompt the agent with:
- Instructions to find relevant specs: `Glob docs/internal/specs/*<project>*` and `Glob docs/internal/edr/*<project>*`
- For each spec found, extract a structured summary using Grep and targeted Read (not full-file Read): entities defined, endpoints proposed, tables referenced, milestone sequence, acceptance criteria
- Compare spec expectations against what Agent 2 found in the codebase

**Important:** If any project area has no specs, no PRs, and no code, that's a finding -- not an error. Report it as a gap.

### Large File Handling

Agents MUST use the `targeted-file-read` skill for any spec, EDR, migration, or schema file. In each agent brief, include:

> "Use the `targeted-file-read` skill for any file in `docs/internal/specs/`, `docs/internal/edr/`, `docs/internal/analysis/`, `services/web-db/migrations/sql/`, or `platform-schemas/schemas/`. Pass the layer's search targets as search terms. Return the skill's Extract verbatim -- do not re-summarize or expand it."

The `targeted-file-read` skill handles Grep-first scoping, offset/limit pagination, and produces citation-backed extracts bounded at ~1,500 tokens. Do not reimplement its logic.

## Phase 3: Synthesize

Combine the agent results into the gap analysis document. Use the template in `references/output-template.md`.

**Synthesis operates on the Phase 2 extracts only.** Do not re-Read specs, EDRs, migrations, or schemas during synthesis -- if you need more detail, re-invoke `targeted-file-read` with narrower search terms. The distilled extracts with their `file:line` citations are the source of truth for this phase.

**Every architectural claim in the output must cite its source**: a `file:line` from a spec extract, a PR number, a Linear ticket ID, or `origin/main:<path>`. Uncited architectural claims get flagged by Phase 4 verification.

### Settled Decisions

Before listing anything as "open," check for decisions already settled by the spec or by prior conversation. Open a `## Settled Decisions` section in the output:

- Each entry: the decision (one line) + its authoritative source citation
- Examples: "REST endpoint path is `/api/tenant/{id}/dimensions` (docs/internal/specs/0017-tts.mdx:142)", "Read-time join over denormalization (PR #2051 merged)"
- Anything in this section MUST NOT also appear under "Open questions" or "Missing items."
- On subsequent gap-analysis runs in the same session, consult this section first. If a question was settled earlier, do not re-open it without new evidence.

For each pipeline layer involved:

1. List every artifact with status: **DONE** (on main), **IN REVIEW** (open PR), **MISSING** (no code, no PR)
2. Note the owner (from Linear assignee or PR author) and any due dates
3. Flag items where the spec expects something that doesn't exist in code or PRs

Then build:

### Cross-Layer Schema Compatibility

When artifacts exist at both the producing layer (dbt/Delta) and consuming layer (frontend queries), verify column-level compatibility:

1. **Extract consumer columns.** Grep the frontend query files for column names in SELECT, WHERE, GROUP BY, and ORDER BY clauses.
2. **Extract producer schema.** For Delta tables with known GCS paths, read the `_delta_log/00000000000000000000.json` and parse the `metaData.schemaString` to list columns. For dbt models, read the `.yml` contract file's column definitions.
3. **Diff.** Flag any column referenced by the consumer that does not exist in the producer schema. These are **SCHEMA GAPS** -- the artifact exists but the contract is incomplete.
4. **Check code comments.** Grep the consumer files for TODO, "not yet", "will be added" comments that document known schema gaps.

Schema gaps are often more critical than missing artifacts -- they cause silent runtime failures (empty results, SQL errors) rather than obvious "file not found" errors.

### Critical Path
Identify the sequential chain of blocking items. For each step: what it is, who owns it, what blocks it, and its current status. Order by dependency -- each step blocks the next.

### Missing Items List
The most important output. For each item that doesn't exist anywhere (not on main, not in any PR):
- What it is and why it's needed
- Which layer it belongs to
- Whether any ticket tracks it (if no ticket: flag as "no ticket, no owner")
- What it blocks downstream

Rank missing items by criticality: items on the critical path first, nice-to-haves last.

### Alternative Paths
If there's a shortcut that bypasses part of the critical path (e.g., backfill from existing data instead of building the full pipeline), document it with: what it skips, what it requires, and whether any work exists for it.

## Phase 4: Verify

Before presenting findings, launch one verification agent to disprove each claim.

Prompt the agent with the draft analysis and instructions to:

1. **Verify every PR state.** For each PR mentioned as "merged" or "open": `gh pr view <number> --repo parable-work/parable-platform --json state,title`
2. **Verify every "on main" claim.** For each file claimed to exist on main: `git show origin/main:<path> 2>/dev/null | head -5`
3. **Verify every "MISSING" claim.** For each item claimed missing: search broadly with Grep and Glob using multiple naming conventions (camelCase, snake_case, kebab-case). Check open PRs for the item. Confirm it truly doesn't exist.
4. **Verify ticket statuses.** For each Linear ticket mentioned: fetch current status from Linear MCP. Flag any that changed since the gather phase.
5. **Search for new PRs opened today** that the analysis might have missed: `gh pr list --search "<keywords>" --state open --json number,title,createdAt`

The verification agent returns:
- **CONFIRMED**: claims that check out
- **INCORRECT**: claims that are wrong (with correct state)
- **STALE**: claims that changed during the session
- **MISSING FROM ANALYSIS**: things found that the analysis doesn't mention

Incorporate all corrections into the final document before presenting.

## Phase 5: Present

### Default output: Markdown document

Save to `~/.agent/reviews/<ticket-id>/gap-analysis.md` (or `~/.agent/reviews/<milestone-slug>/gap-analysis.md` if no single ticket).

The document must include a verification note at the bottom: "Verified [date] against GitHub, Linear, and codebase. Corrections from verification: [list any]."

### Opt-in: HTML visualization

If the user asks for a visualization, use the `visual-explainer:generate-web-diagram` skill. Pass it the completed markdown document and request a pipeline status diagram with done/in-review/missing indicators. Save to `~/.agent/diagrams/`.

### Opt-in: Slack summary

If the user asks for a Slack-ready version, produce a condensed version:
- Lead with the biggest finding (usually the missing items list)
- Use ASCII tables for the inventory (Slack doesn't render markdown tables)
- Frame gaps as questions, not accusations ("does anyone own X?" not "nobody owns X")
- Keep under 3000 characters

## Error Handling

### Linear ticket not found
If the ticket ID doesn't resolve, search Linear by keyword. If still not found, ask the user to verify the ID.

### No specs or docs exist
This is valid for early-stage projects. Skip Phase 2 Agent 3 and note "no specs found" in the analysis. The gap analysis still works from Linear tickets + codebase + PRs.

### Agent returns empty results
If a gather agent finds nothing for a layer, that's a finding: the layer has no artifacts. Don't retry -- report it as a gap.

### Stale data from verification
If verification finds items that changed during the session, update the document and add a note: "[Item] status changed during analysis -- verified as [new status] at [time]."
