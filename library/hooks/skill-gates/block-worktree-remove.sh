#!/usr/bin/env bash
# beforeShellExecution: require manual override before destroying git worktrees.
# Allow when CURSOR_ALLOW_WORKTREE_REMOVE=1 is set in the command environment
# (agent must only set this after explicit user confirmation in the same turn).
#
# Important: do not substring-match "rm " — paths like ".../parable-platform worktree add ..."
# contain the letters "rm " inside "platform ".

set -uo pipefail

emit() {
  printf '%s\n' "$1"
}

input="$(cat || true)"

python3 - "$input" <<'PY'
import json
import re
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    d = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    d = {}

command = d.get("command") or d.get("cmd") or ""
if not command:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

if "CURSOR_ALLOW_WORKTREE_REMOVE=1" in command:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

cmd_lc = command.lower()

# Destructive git worktree subcommands only (not add/list/lock/unlock/move/repair)
if re.search(r"\bworktree\s+(remove|rm)\b", cmd_lc):
    risky = True
else:
    # rm as a command word (not the "rm " inside "platform ")
    rm_cmd = bool(re.search(r"(?:^|[\s;|&])(?:/bin/)?rm(?:\s|$)", cmd_lc))
    worktree_path = bool(
        re.search(
            r"(?:\.cursor|\.claude|\.agent|\.superconductor|\.git)/worktrees\b",
            cmd_lc,
        )
    )
    risky = rm_cmd and worktree_path

if not risky:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

msg = (
    "Blocked: worktree removal requires manual override. "
    "Inventory path|branch|dirty|last-commit, get explicit user confirmation, "
    "then re-run with CURSOR_ALLOW_WORKTREE_REMOVE=1 in the command env "
    "(e.g. CURSOR_ALLOW_WORKTREE_REMOVE=1 git worktree remove --force <path>)."
)
print(json.dumps({
    "permission": "ask",
    "user_message": msg,
    "agent_message": msg,
}))
PY
exit 0
