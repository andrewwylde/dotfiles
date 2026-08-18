#!/bin/bash
# Block accidental root-level PR diff artifacts created via shell redirection.

set -euo pipefail

emit_allow() {
  printf '{"permission":"allow"}\n'
}

emit_deny() {
  local msg="${1:-Blocked shell command}"
  python3 - "$msg" <<'PYJSON'
import json
import sys

msg = sys.argv[1] if len(sys.argv) > 1 else "Blocked shell command"
print(json.dumps({
    "permission": "deny",
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

read_json_field() {
  local key="$1"
  HOOK_JSON="$HOOK_STDIN" python3 - "$key" <<'PY'
import json
import os
import sys

key = sys.argv[1]
raw = os.environ.get("HOOK_JSON", "").strip()
if not raw:
    print("")
    raise SystemExit(0)
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)
print(data.get(key, "") or "")
PY
}

COMMAND="$(read_json_field command)"
if [[ -z "$COMMAND" ]]; then
  emit_allow
  exit 0
fi

if ! python3 - "$COMMAND" <<'PY'
import re
import sys

cmd = sys.argv[1] if len(sys.argv) > 1 else ""

# Match " > pr2186.diff", ">> ./pr2186.diff", or "| tee pr2186.diff"
redirect_match = re.search(r'(?:^|[\s;|])>>?\s*(?:\./)?(pr\d+\.diff)(?:\s|$)', cmd, flags=re.I)
tee_match = re.search(r'\|\s*tee(?:\s+-a)?\s+(?:\./)?(pr\d+\.diff)(?:\s|$)', cmd, flags=re.I)

sys.exit(0 if (redirect_match or tee_match) else 1)
PY
then
  emit_allow
  exit 0
fi

emit_deny "Blocked command that creates root-level PR diff artifact (*.diff). Save PR diffs under .context/prs/ instead."
exit 0
