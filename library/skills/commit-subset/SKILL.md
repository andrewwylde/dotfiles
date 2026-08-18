---
name: commit-subset
description: >
  Isolate and commit only matching path globs from a dirty worktree that also
  contains unrelated WIP. Use when the user asks to commit a subset of changes,
  commit only certain paths while other files are dirty, or when pre-commit
  stash/restore loops hide commit failure. Do not use for ordinary clean-tree
  commits.
---

# Commit Subset

Commit only the paths the user named while preserving unrelated dirty WIP.

## When to use

- Working tree has many unrelated changes and the user wants a narrow commit
- Prior `git commit` claimed success but `git status` still shows the same paths
- Large generated/unrelated files would be sucked into a normal `git add -A`

## Procedure

1. **Capture HEAD before any commit:**
   ```bash
   BEFORE=$(git rev-parse HEAD)
   ```
2. **Resolve path globs** with the user (or from their message). Dry-run:
   ```bash
   git status --porcelain -- <paths...>
   git diff --stat HEAD -- <paths...>
   ```
3. **Isolate** (prefer patch over hard-reset when possible):
   - Save a patch of only the target paths:
     ```bash
     git diff HEAD -- <paths...> > /tmp/commit-subset.patch
     git diff --cached -- <paths...> >> /tmp/commit-subset.patch   # if staged
     ```
   - Stash *everything else* (including untracked if needed):
     ```bash
     git stash push -u -m "commit-subset: unrelated WIP" -- <inverse or use stash -u then restore patch>
     ```
   Practical pattern that works on dirty trees:
   ```bash
   # Stash all, re-apply only target paths from the saved patch
   git stash push -u -m "commit-subset: park WIP"
   git checkout "$BEFORE" -- . 2>/dev/null || true
   git apply --3way /tmp/commit-subset.patch || git apply /tmp/commit-subset.patch
   ```
4. **Stage and commit only those paths:**
   ```bash
   git add -- <paths...>
   git commit -m "$(cat <<'EOF'
   <message>
   EOF
   )"
   ```
5. **Verify HEAD advanced (required):**
   ```bash
   AFTER=$(git rev-parse HEAD)
   test "$BEFORE" != "$AFTER" || { echo "COMMIT FAILED: HEAD unchanged"; git status -sb; exit 1; }
   git log -1 --oneline
   ```
   If pre-commit printed `Restored working directory` / stash restore and HEAD
   did not move, treat as failure — do **not** claim success. Fix the hook
   issue or re-isolate and retry (never `--no-verify` unless the user asks).
6. **Restore unrelated WIP:**
   ```bash
   git stash pop
   ```
   Resolve conflicts carefully; target paths should already be committed.

## Anti-patterns

- `git add -A` on a mixed dirty tree
- Claiming "committed" without comparing `BEFORE`/`AFTER` SHAs
- Hard-reset discarding WIP without a recoverable stash/patch
- Using `--no-verify` to skip hook failures without user approval
