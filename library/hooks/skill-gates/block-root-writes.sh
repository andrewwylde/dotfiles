#!/bin/bash
# Guard shell commands that write files in repository root.
# Default behavior: allow all commands except likely root-file writes.
# Clean override: prefix command with ROOT_WRITE_OK=1.

set -euo pipefail

emit_allow() {
  printf '{"permission":"allow"}\n'
}

emit_ask() {
  local msg="${1:-Root write detected}"
  python3 - "$msg" <<'PYJSON'
import json
import sys

msg = sys.argv[1] if len(sys.argv) > 1 else "Root write detected"
print(json.dumps({
    "permission": "ask",
    "user_message": msg,
    "agent_message": msg,
}))
PYJSON
}

HOOK_STDIN=""
if [[ -p /dev/stdin ]]; then
  HOOK_STDIN="$(cat || true)"
fi

if [[ -z "$HOOK_STDIN" ]]; then
  emit_allow
  exit 0
fi

COMMAND="$(HOOK_JSON="$HOOK_STDIN" python3 - <<'PY'
import json
import os

raw = os.environ.get("HOOK_JSON", "").strip()
if not raw:
    print("")
    raise SystemExit(0)
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)
print((data.get("command") or "").strip())
PY
)"

if [[ -z "$COMMAND" ]]; then
  emit_allow
  exit 0
fi

# Explicit one-shot override for intentional root writes.
if [[ "$COMMAND" == ROOT_WRITE_OK=1* ]] || [[ "$COMMAND" == *" ROOT_WRITE_OK=1 "* ]]; then
  emit_allow
  exit 0
fi

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

SHOULD_ASK="$(python3 - "$COMMAND" "$WORKSPACE_ROOT" <<'PY'
import re
import shlex
import sys
from pathlib import Path

cmd = sys.argv[1]
workspace_root = Path(sys.argv[2]).resolve()

safe_roots = {".context", "plans", ".cursor"}

def is_root_file_path(path_text: str) -> bool:
    p = path_text.strip()
    if not p:
        return False
    if p.startswith(("http://", "https://")):
        return False
    if p.startswith("/"):
        try:
            rel = Path(p).resolve().relative_to(workspace_root)
            p = rel.as_posix()
        except Exception:
            return False
    if p.startswith("./"):
        p = p[2:]
    if "/" in p:
        top = p.split("/", 1)[0]
        return top in safe_roots and False
    # root-level filename like pr2186.diff or notes.txt
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", p))

targets = []

# Redirection targets: > file, >> file, 1> file, 2>> file
for match in re.finditer(r"(?:^|[\s;|])(?:\d+)?>>?\s*([^\s;|]+)", cmd):
    targets.append(match.group(1).strip("'\""))

# tee targets: | tee file, | tee -a file
for match in re.finditer(r"\|\s*tee(?:\s+-a)?\s+([^\s;|]+)", cmd):
    targets.append(match.group(1).strip("'\""))

try:
    tokens = shlex.split(cmd)
except Exception:
    tokens = []

# Direct file-write commands with root-level filename args.
write_cmds = {"touch", "truncate"}
for idx, token in enumerate(tokens):
    if token in write_cmds:
        for arg in tokens[idx + 1:]:
            if arg.startswith("-"):
                continue
            targets.append(arg.strip("'\""))
            break

ask = any(is_root_file_path(t) for t in targets)
print("1" if ask else "0")
PY
)"

if [[ "$SHOULD_ASK" == "1" ]]; then
  emit_ask "Root file write detected in shell command. Default policy blocks root artifacts; approve explicitly or write to a subdirectory (for example .context/prs/...). To bypass once, prefix with ROOT_WRITE_OK=1."
  exit 0
fi

emit_allow
exit 0
