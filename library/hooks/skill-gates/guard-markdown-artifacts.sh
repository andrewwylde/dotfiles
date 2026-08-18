#!/bin/bash
# Guard new markdown artifact creation.
# Allows edits to existing docs, but blocks unsupported new .md/.mdx files.

set -uo pipefail

emit_allow() {
  printf '{"permission":"allow"}
'
}

emit_deny() {
  local msg="${1:-Blocked by markdown guard}"
  python3 - "$msg" <<'PYJSON'
import json
import sys
msg = sys.argv[1] if len(sys.argv) > 1 else "Blocked by markdown guard"
print(json.dumps({
    "permission": "deny",
    "user_message": msg,
    "agent_message": msg,
}))
PYJSON
}

u() { printf '%s' "${1:-}"; }

TOOL="$(u "${1-}")"
FILE_ARG="$(u "${2-}")"
if [[ -z "$FILE_ARG" ]]; then
  FILE_ARG="unknown"
fi

HOOK_STDIN=""
if [[ -p /dev/stdin ]]; then
  HOOK_STDIN=$(cat || true)
fi

if [[ -z "$TOOL" && -n "$HOOK_STDIN" ]]; then
  IFS=$'	' read -r parsed_tool parsed_file <<EOSTDIN
$(printf '%s' "$HOOK_STDIN" | python3 -c '
import json, sys
import re
from pathlib import Path
raw = sys.stdin.read().strip()
if not raw:
    print("	")
    raise SystemExit(0)
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    print("	")
    raise SystemExit(0)
name = d.get("tool_name") or d.get("tool") or d.get("name") or ""
inp = d.get("tool_input") or d.get("input") or d.get("arguments") or {}
if isinstance(inp, str):
    try:
        inp = json.loads(inp)
    except json.JSONDecodeError:
        inp = {"patch": inp}
path = "unknown"
if isinstance(inp, dict):
    path = inp.get("path") or inp.get("file_path") or inp.get("file") or inp.get("target_file") or inp.get("notebook_path") or "unknown"
    if path == "unknown":
        patch = inp.get("patch") or inp.get("content") or ""
        if isinstance(patch, str) and patch:
            m = re.search(r"^\*\*\* (?:Add|Update) File: (.+)$", patch, flags=re.M)
            if m:
                path = Path(m.group(1).strip()).as_posix()
print(f"{name}	{path}")
' || true)
EOSTDIN
  if [[ -n "$parsed_tool" ]]; then
    TOOL="$parsed_tool"
  fi
  if [[ -n "$parsed_file" ]]; then
    FILE_ARG="$parsed_file"
  fi
fi

if [[ "$FILE_ARG" == "unknown" || -z "$FILE_ARG" ]]; then
  emit_allow
  exit 0
fi

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [[ "$FILE_ARG" == /* ]]; then
  CANDIDATE_ROOT="$(git -C "$(dirname "$FILE_ARG")" rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$CANDIDATE_ROOT" ]]; then
    WORKSPACE_ROOT="$CANDIDATE_ROOT"
  fi
fi

ABS_PATH=$(FILE_ARG="$FILE_ARG" python3 - <<'PYABS'
from pathlib import Path
import os
cwd = Path(os.getcwd())
p = Path(os.environ.get("FILE_ARG", "unknown"))
if p.is_absolute():
    print(p.resolve().as_posix())
else:
    print((cwd / p).resolve().as_posix())
PYABS
)

# Always allow edits in the global Cursor home directory.
case "$ABS_PATH" in
  "$HOME/.cursor/"*|"$HOME/.cursor")
    emit_allow
    exit 0
    ;;
esac

# Only apply workspace markdown manifest policy to in-workspace targets.
if [[ "$ABS_PATH" != "$WORKSPACE_ROOT"* ]]; then
  emit_allow
  exit 0
fi

REL_PATH=$(FILE_ARG="$FILE_ARG" python3 - <<'PYREL'
from pathlib import Path
import os
file_arg = os.environ.get('FILE_ARG', 'unknown')
workspace = Path(os.environ.get("WORKSPACE_ROOT", ".")).resolve()
p = Path(file_arg)
if p.is_absolute():
    try:
        print(p.resolve().relative_to(workspace).as_posix())
    except Exception:
        print(p.name)
else:
    abs_p = (Path.cwd() / p).resolve()
    try:
        print(abs_p.relative_to(workspace).as_posix())
    except Exception:
        print(p.as_posix())
PYREL
)

MODE="create"
if [[ -f "$FILE_ARG" || -f "$REL_PATH" ]]; then
  MODE="modify"
fi

DOC_FALLBACK_EXTS_REGEX='\.(txt|rst|adoc|asciidoc)$'
if [[ "$MODE" == "create" && "$REL_PATH" != */* && "$REL_PATH" =~ $DOC_FALLBACK_EXTS_REGEX ]]; then
  emit_deny "Blocked non-markdown root artifact '${REL_PATH}' to prevent markdown policy bypass; create an indexed markdown artifact instead."
  exit 0
fi

case "$REL_PATH" in
  *.md|*.mdx) ;;
  *)
    emit_allow
    exit 0
    ;;
esac

# Existing files are always allowed.
if [[ "$FILE_ARG" == /* ]]; then
  if [[ -f "$FILE_ARG" ]]; then
    emit_allow
    exit 0
  fi
elif [[ -f "$REL_PATH" ]]; then
  emit_allow
  exit 0
fi

RESOLVER="${HOME}/.cursor/scripts/manifest_markdown_resolver.py"
if [[ ! -f "$RESOLVER" ]]; then
  emit_allow
  exit 0
fi

RESOLVE_OUT="$(python3 "$RESOLVER" --path "$FILE_ARG" --mode "$MODE" --workspace "$WORKSPACE_ROOT" 2>/dev/null || true)"
if [[ -z "$RESOLVE_OUT" ]]; then
  emit_allow
  exit 0
fi

ALLOW_FLAG="$(printf '%s' "$RESOLVE_OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print("1" if d.get("allow") else "0")' 2>/dev/null || printf '1')"
REASON="$(printf '%s' "$RESOLVE_OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("reason",""))' 2>/dev/null || true)"
NORM_PATH="$(printf '%s' "$RESOLVE_OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("normalized_path",""))' 2>/dev/null || true)"

if [[ "$ALLOW_FLAG" == "1" ]]; then
  emit_allow
  exit 0
fi

emit_deny "Blocked markdown artifact '${NORM_PATH:-$REL_PATH}' by shared markdown policy: ${REASON:-deny:unknown}"
exit 0
