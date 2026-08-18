---
name: full-export
description: Export the complete conversation history across all sessions for the current project into a single readable file. Use when the user asks to "full export", "export all sessions", "export all conversations", "export full history", "export the full transcript", or wants to view or save the entire conversation chain including sessions that continued after context compression. Also use when the user asks about exporting conversation history across multiple context windows.
---

# Full Export

Export all Claude Code sessions for this project — including continuations after context compression — into a single readable file.

## How it works

Sessions for a project live in `~/.claude/projects/<hash>/` as `.jsonl` files. The hash is derived from the project working directory path. This skill finds all session files for the current project, sorts them chronologically, and concatenates them with session-break markers.

## Running the export

```bash
python3 <skill-base-dir>/scripts/export_sessions.py [output_path] [options]
```

**Options:**
- `output_path` — where to write (default: `~/.agent/sessions/full-export-<project>-<date>.txt`)
- `--cwd <path>` — project working directory for auto-detection (default: current dir)
- `--project-dir <path>` — manually specify `~/.claude/projects/<hash>/` if auto-detect fails
- `--no-tool-results` — omit tool result messages (cleaner reading, smaller file)
- `--no-system` — strip `<system-reminder>` and injected meta blocks

## Typical invocation

Always run from the project's working directory so auto-detection works:

```bash
python3 ~/.claude/skills/full-export/scripts/export_sessions.py ~/.agent/sessions/my-export.txt --no-system
```

If auto-detection fails, list available projects and let the user pick:

```bash
python3 ~/.claude/skills/full-export/scripts/export_sessions.py --project-dir nonexistent 2>&1 | grep -A 50 "Available projects"
```

## After running

Tell the user where the file was written. If they asked for a specific path, confirm it landed there. The output is plain text — they can open it in any editor or use `less`/`grep` on it.

## Notes

- Sessions are sorted by file modification time (oldest first)
- The current active session is not automatically included — it only contains messages committed to disk so far. For a complete export of the active session, the user should run `/export` first in a separate step.
- Tool call inputs are included by default (useful for understanding what happened); use `--no-tool-results` to strip the responses which are often noisy.
