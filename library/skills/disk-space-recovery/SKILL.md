---
name: disk-space-recovery
description: Free disk space safely on macOS by inventorying reclaimable caches and junk, then cleaning in gated phases. Use when the user is low on disk ("out of space", "disk full", "free up space", "clean caches", df shows little free). Never treat git worktrees as safe Phase 1 reclaimables — inventory and get explicit confirmation first.
---

# Disk Space Recovery

Recover free space without destroying valuable work. Prefer caches and disposable installer junk first; gate anything that can hold uncommitted WIP.

## Process

### Step 1: Measure baseline

```bash
df -h /System/Volumes/Data
```

Record free space before any deletes.

### Step 2: Inventory heavy hitters (targeted, not full-home)

Prefer short, targeted `du` on known paths. Avoid `du ~` / full-home walks — they hang for minutes and fight other scans.

Check at least:

| Path | Typical reclaim |
|------|-----------------|
| `~/Library/Caches` (go-build, Homebrew, Playwright, pip, poetry) | high / safe |
| `~/.npm/_cacache`, `~/.bun/install/cache` | high / safe |
| Docker (`docker system df`) + unused Colima (`~/.colima`) | high / careful |
| `~/Downloads` installers / `.xip` / old zips | medium / review |
| Cursor `state.vscdb.backup`, `Cursor/logs` | medium / safer |
| Cursor `state.vscdb` (live) | high / careful (Phase 2) |
| `~/.cursor/worktrees`, other `*/worktrees/*` | high / **gated** |
| Claude `vm_bundles`, Notion Partitions | medium / Phase 2 |

Use absolute binaries in long scripts (`/opt/homebrew/bin/git`, `/bin/rm`, `/usr/bin/du`) — shell PATH can break mid-loop in agent sessions.

### Step 3: Classify into phases

**Phase 1 — safe (no confirmation beyond plan approval):**
- `npm cache clean --force`
- `go clean -cache`
- `brew cleanup -s`
- Clear bun / Playwright caches
- `docker builder prune` / unused image prune (confirm no needed volumes before `--volumes`)
- Unused Colima only if Docker Desktop is the active context
- Cursor `state.vscdb.backup` + `Cursor/logs` (prefer Cursor quit)
- Obvious Downloads junk (old `.dmg`/`.pkg`/`.xip`, duplicate zips already extracted elsewhere)

**Phase 2 — careful (explicit confirmation each bucket):**
- Live Cursor `state.vscdb` vacuum/reset
- Claude `vm_bundles`, Notion cache/partitions
- Signal / app media stores

**Never Phase 1 — worktrees:**
- Any `git worktree remove`, or `rm` under `.cursor/worktrees`, `.claude/worktrees`, `.agent/worktrees`, `.superconductor/worktrees`

### Step 4: Worktree gate (mandatory)

Before removing **any** worktree:

1. Run `git worktree list` from the main repo.
2. Present a table for each candidate:

   `path | branch | dirty? | last commit | size`

   Dirty check: `git -C <path> status --porcelain`
3. Stop and ask which paths (if any) to remove. Do not batch-remove "stale agent" worktrees by naming convention alone.
4. Reminder: `git worktree remove` deletes the working tree; **branches usually remain**, but **uncommitted WIP does not**.
5. Only after explicit confirmation, re-run with override:

```bash
CURSOR_ALLOW_WORKTREE_REMOVE=1 git worktree remove --force <path>
```

A `beforeShellExecution` hook asks for manual override on worktree removals; do not try to bypass it without user approval.

### Step 5: Execute Phase 1, then verify

Run approved Phase 1 commands. Re-check:

```bash
df -h /System/Volumes/Data
```

Report recovered GB. Offer Phase 2 / worktree review only if still tight.

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| `du -sh ~/*` as first step | Targeted paths from the table |
| Treat `.cursor/worktrees/*` as caches | Inventory + confirm |
| `git worktree remove --force` in a loop | One confirmed path at a time (with override env) |
| Delete live `state.vscdb` in Phase 1 | Backup/logs only first |
| Assume Colima + Docker Desktop both needed | Check `docker context ls`; remove unused runtime |

## Constraints

- One post-cleanup `df` report to the user with before/after free space.
- Do not commit, push, or modify project source as part of cleanup.
- Prefer the user's Trash emptying for user-facing files when unsure.
