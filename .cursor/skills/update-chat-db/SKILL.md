---
name: update-chat-db
description: Parse Cursor and Claude chats, deduplicate exports, analyze for inefficiencies, and populate the SQLite dashboard database. Use when the user asks to update, refresh, rebuild, or populate the chat database, run the chat analysis pipeline, or sync Cursor/Claude conversations to the dashboard.
---

# Update Chat Database

Full pipeline: raw Cursor + Claude chats → markdown → dedup → SQLite → inspect.

**Project root:** `~/code/andrew-status` (all relative paths below assume this).

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

Sources: `~/.claude/projects/**/*.jsonl` (excludes subagents)  
Output: `chats/claude/`

### 2. Deduplicate exports (Cursor only)

```bash
# Dry-run first (default)
uv run python scripts/dedup-cursor-chats.py

# Execute deletions
uv run python scripts/dedup-cursor-chats.py --execute
```

Groups by source path, keeps newest per group. Use `--keep-oldest` to reverse.

### 3. Analyze and populate SQLite

```bash
uv run python scripts/analyze-chats.py -i chats/cursor chats/claude --output-db chats/analysis/inefficiencies.db
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
cd ~/code/andrew-status
uv run python scripts/parse-cursor-chats.py -o chats/cursor -v && \
uv run python scripts/parse-claude-chats.py -o chats/claude -v && \
uv run python scripts/dedup-cursor-chats.py --execute && \
uv run python scripts/analyze-chats.py -i chats/cursor chats/claude --output-db chats/analysis/inefficiencies.db && \
uv run python scripts/inspect-dashboard-db.py chats/analysis/inefficiencies.db
```

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
