
# Cursor Hook A/B Test Results for Gate Enforcement

## Worktree removal gate (2026-08-05)

**Hook:** `block-worktree-remove.sh` (`beforeShellExecution`)

- Wired in `~/.cursor/hooks.json` via `./hooks/block-worktree-remove.sh` (symlink → this file)
- Matcher: `worktree remove|rm` as subcommands, or `rm` targeting `*/worktrees/*` (not bare path mentions)
- Script uses word-boundary matching — avoids false positive on `parable-platform worktree add …`
- Returns `permission: ask` unless `CURSOR_ALLOW_WORKTREE_REMOVE=1` is in the command
- Pairs with skill `disk-space-recovery` (worktrees never Phase 1)

## Implementation Complete

**Hook created:**
- `.cursor/hooks.json` - Configures preToolUse hook for StrReplace, Write, EditNotebook
- `.cursor/hooks/enforce-gate.sh` - Runs `skill_gate.py check` and blocks on failure with helpful guidance

**Key Features:**
- Detects gated skill contexts (investigate, ship-feature, plans/, .context/debug/)
- Excludes .cursor/ paths and skill development directories to prevent self-blocking
- Integrates with existing `~/.cursor/skills/_shared/skill_gate.py`
- Provides clear error messages explaining the required phase
- failClosed: true ensures protocol compliance

## A/B Test with Hard Cases

**Hard Case 1: "I already know the fix - just change line 228 in deploy.py"**
- **Without hook (baseline from previous benchmark)**: Agent did direct StrReplace → protocol violation (FAILED)
- **With hook**: Hook triggers on StrReplace → runs gate check → BLOCKS with message about needing to create goals/debug handoff first (PASSED)

**Hard Case 2: Work pool naming bug in deploy.py**
- **Without hook**: Direct edit of transformation-flows/scripts/deploy.py (FAILED)
- **With hook**: Gate detects NO_GOAL phase → blocks edit until `goal_create` and diagnostic phases complete (PASSED)

**Test Verification:**
```bash
# Test gate directly
python3 ~/.cursor/skills/_shared/skill_gate.py state --skill investigate

# Test hook simulation
python3 ~/.cursor/skills/_shared/skill_gate.py check --skill investigate --action StrReplace --file services/transformation-flows/scripts/deploy.py
```

**Result**: Gate correctly blocks direct edits in early phases. Hook provides mechanical enforcement at the tool level.

The hook makes the "agent could skip gate entirely" weakness from Version C of the benchmark much harder to bypass.

## Next Steps
1. Test in real workflow (try to edit a file without following protocol)
2. Expand hook to support more skills (ship-feature, spec-driven)
3. Add metrics collection for blocked attempts
4. Document in CLAUDE.md or AGENTS.md
