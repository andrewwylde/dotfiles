---
name: verify-git-commit
description: >
  After any git commit, verify HEAD advanced before claiming success. Use
  whenever committing, when pre-commit hooks may stash/restore, or when the
  user asks whether a commit landed. Pair with commit-subset for dirty trees.
---

# Verify Git Commit

Pre-commit hooks can print success-looking messages while restoring a stash and
leaving HEAD unchanged. Never claim a commit succeeded without a SHA check.

## Required check

```bash
BEFORE=$(git rev-parse HEAD)   # capture before git commit
# ... run git commit ...
AFTER=$(git rev-parse HEAD)
git log -1 --oneline
git status -sb
```

- If `BEFORE == AFTER`: **commit failed**. Report hook output, status, and next fix.
- If pre-commit says it restored the working directory / popped a stash, re-check
  status — target files may still be uncommitted (`MM`, staged+unstaged).
- Do not say "committed" or "landed" until `AFTER` differs from `BEFORE`.

## With commit-subset

When isolating path globs from unrelated WIP, use the `commit-subset` skill and
still apply this BEFORE/AFTER gate as the final step.
