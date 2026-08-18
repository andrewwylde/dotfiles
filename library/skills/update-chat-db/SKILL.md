---
name: update-chat-db
description: Parse Cursor and Claude chats, deduplicate exports, analyze for inefficiencies, and populate the SQLite dashboard database. Use when the user asks to update, refresh, rebuild, or populate the chat database, run the chat analysis pipeline, or sync Cursor/Claude conversations to the dashboard.
---

# Update Chat Database

Full pipeline: raw Cursor + Claude chats → markdown → dedup → SQLite → inspect.

**Project root:** `~/code/dashy` (all relative paths below assume this).

## Pipeline Steps

### 1. Parse raw chats to markdown

**Cursor:**
```bash
uv run python scripts/parse-cursor-chats.py -o chats/cursor -v
```

Sources: `~/.cursor/chats/**/store.db`, `~/.cursor/projects/**/agent-transcripts/*.jsonl`  
Output: `chats/cursor/`

**Claude Code:**
```bash
uv run python scripts/parse-claude-chats.py -o chats/claude -v
```

Sources: `~/.claude/projects/**/*.jsonl`  
Skips: `subagents/` directories, plus project dirs matching `*observer*` or `*claude-mem*` (noise).  
Output: `chats/claude/`

### 2. Deduplicate exports (Cursor only)

```bash
# Dry-run first (default)
uv run python scripts/dedup-cursor-chats.py

# Execute deletions
uv run python scripts/dedup-cursor-chats.py --execute
```

Groups by source path, keeps newest per group. Use `--keep-oldest` to reverse.

### 2b. Purge claude-mem / observer noise (optional but recommended)

```bash
uv run python scripts/purge-noise-chats.py --dry-run
uv run python scripts/purge-noise-chats.py --execute
```

Deletes markdown whose header `Source` / `project` contains `claude-mem` or `observer-sessions`. Safe after parse; analyze also skips these by default.

### 3. Analyze and populate SQLite

```bash
uv run python scripts/analyze-chats.py -i chats/cursor -i chats/claude --output-db chats/analysis/inefficiencies.db
```

This **drops and recreates** the DB each run. Tables created:

| Table | Content |
|-------|---------|
| `conversations` | id, file_path, total_tokens, message_count, model, created_at |
| `messages` | role, content, token_count per conversation |
| `tool_calls` | tool calls per conversation |
| `token_waste` | waste_score, estimated_wasted_tokens, severity |
| `workflow_issues` | read/write/debug counts, workflow_score |
| `iteration_loops` | multi-edits, multi-reads, loop_score |
| `summary` | key-value totals |

Useful flags:
- `--start-date` / `--end-date` — filter by date range
- `--exclude "README.md,cursor_chat_export*.md"` — skip files by basename
- `--exclude-path SUBSTR` — skip Source/project paths containing SUBSTR (repeatable)
- `--keep-noise` — include claude-mem / observer-sessions (default is to skip them)
- `--files-from FILE` — read paths from a file instead of globbing
- `-v` — verbose output

### 4. Inspect the database

```bash
uv run python scripts/inspect-dashboard-db.py chats/analysis/inefficiencies.db
```

Prints table counts, `created_at` range, and distribution.

## Quick Reference

### Full pipeline (one-shot)

```bash
cd ~/code/dashy
uv run python scripts/parse-cursor-chats.py -o chats/cursor -v && \
uv run python scripts/parse-claude-chats.py -o chats/claude -v && \
uv run python scripts/dedup-cursor-chats.py --execute && \
uv run python scripts/purge-noise-chats.py --execute && \
uv run python scripts/analyze-chats.py -i chats/cursor -i chats/claude --output-db chats/analysis/inefficiencies.db && \
uv run python scripts/inspect-dashboard-db.py chats/analysis/inefficiencies.db
```

Or: `./scripts/weekly-improvements-pipeline.sh` (also seeds the improvements inbox).

### Reset DB (with backup)

```bash
make dashboard-db-reset
# or
./scripts/reset-dashboard-db.sh
```

Backs up to `inefficiencies.db.bak`, then rebuilds and inspects.
Use `--no-backup` to skip the backup.

## Gotchas

- The analyze script **overwrites** the DB on each run — it does not append.
- `created_at` can be NULL for agent-transcript conversations missing `createdAt` metadata.
- Use `uv run python` (not bare `python3`) per project conventions.
- The `DASHBOARD_DB_PATH` env var overrides the default DB path in the dashboard server.
- Do **not** use `~/code/andrew-status` — that path is retired; the pipeline lives in `dashy`.
- **claude-mem / observer** exports: `parse-claude-chats.py` skips those project dirs for new exports; `analyze-chats.py` also skips Source/project paths containing `claude-mem` or `observer-sessions` by default. Stale markdown under `chats/claude/` can still exist — purge with `scripts/purge-noise-chats.py --execute`. Chats that merely *call* the claude-mem MCP are kept (real work).
