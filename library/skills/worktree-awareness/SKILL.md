---
name: worktree-awareness
description: Use when working inside a git worktree to ensure all file operations, searches, and subagent prompts use the worktree path instead of the original repository root. Activate this skill whenever the environment indicates a worktree (e.g., the working directory contains `.claude/worktrees/` or `git rev-parse --show-toplevel` differs from the original clone). Also use when spawning subagents from a worktree session — the subagent prompt MUST include the worktree path so the subagent doesn't default to the original repo.
---

# Worktree Path Awareness

## The Problem

Git worktrees are isolated copies of a repository at a different filesystem path. When working inside a worktree, every file operation must use the **worktree path**, not the original repository root. Models frequently default to the original repo path because it's shorter, more familiar, or inferred from import paths and documentation.

**Example failure:** The worktree is at:
```
/Users/me/code/my-project/.claude/worktrees/feature-branch/
```
But tools incorrectly target:
```
/Users/me/code/my-project/
```
These are **different filesystem trees**. Reading from the original repo gets stale or wrong content. Writing to it corrupts the main workspace.

## Detecting Your Working Directory

At the start of any session, determine your root:

```bash
git rev-parse --show-toplevel
```

This returns the worktree root, not the original clone. Store this mentally as `$REPO_ROOT` and use it for everything.

**Check the environment section** of your system prompt — if it says "This is a git worktree", the working directory listed there is your `$REPO_ROOT`. Use it exactly.

## Rules

### 1. Never hardcode or guess the repo path

Do not construct paths from memory, import statements, or package names. Always derive paths relative to `$REPO_ROOT` (your current working directory).

**Wrong:**
```
Read /Users/me/code/my-project/src/index.ts
```

**Right:**
```
Read /Users/me/code/my-project/.claude/worktrees/feature-branch/src/index.ts
```

### 2. Use relative paths or the working directory for tools

When using Glob, Grep, Read, or Bash, either:
- Omit the `path` parameter (defaults to cwd, which is correct in a worktree), or
- Use the full worktree path explicitly

### 3. Subagent prompts MUST include the worktree path

When spawning subagents via the Agent tool, always include the worktree root in the prompt. Subagents start with no filesystem context — if you don't tell them the path, they will guess wrong.

**Template for subagent prompts:**
```
Working directory: <full worktree path>
IMPORTANT: All file paths must be relative to or under this directory.
Do NOT use <original repo path>.

<your actual task description>
```

### 4. Bash commands stay in the worktree

Do not `cd` to the original repo. If a command needs an absolute path, use `$REPO_ROOT`. Prefer running commands without `cd` since the shell's cwd is already the worktree.

## Quick Self-Check

Before any file operation, ask: "Does this path contain my worktree directory?" If the path points to the original repo root, it's wrong — prepend the worktree prefix or use relative paths.

## Common Traps

| Trap | Why it happens | Fix |
|------|---------------|-----|
| Using the shorter original repo path | It's more "natural" looking | Always derive from cwd or `git rev-parse` |
| `find /Users/me/code/project -type f` | Hardcoded the original root | Use `.` or `$REPO_ROOT` instead |
| Subagent reads wrong files | Prompt didn't include worktree path | Always include worktree path in Agent prompts |
| `ls /original/repo/path/dist/` | Copied path from docs or imports | Replace with worktree-relative path |

## Frontend bootstrap (parable-platform worktrees)

Path awareness alone does not make Vitest / Svelte / generated TS consumers work.
After schemas exist, run the ship-feature Stage 0 frontend steps from the
**worktree root** (never symlink `node_modules` from the main checkout):

```bash
make build-scalar-lib
make build-schemas
make install-deps
(cd apps && bun run link-schemas)
```

`make install-deps` should link schemas when `platform-schemas/dist` exists.
Vitest and many agent commands skip `apps` `predev`/`prebuild`, so
`link-schemas` is required for component tests even when `bun run dev` would
have done it. Re-run `link-schemas` after any regenerating `make build-schemas`.

Full checklist: project `ship-feature` → `references/psgen-stage-details.md`
Stage 0.
