#!/bin/bash
# Global skill gate hook at ~/.cursor/skills/_shared/hooks/enforce-gate.sh
# Supports Cursor preToolUse payloads via args OR stdin JSON.

set -uo pipefail

emit_allow() {
  printf '{"permission":"allow"}
'
}

emit_deny() {
  local msg="${1:-Blocked by skill gate}"
  python3 - "$msg" <<'PYJSON'
import json
import sys
msg = sys.argv[1] if len(sys.argv) > 1 else "Blocked by skill gate"
print(json.dumps({
    "permission": "deny",
    "user_message": msg,
    "agent_message": msg,
}))
PYJSON
}

u() { printf '%s' "${1:-}"; }

is_markdown_target() {
  local p="${1:-}"
  case "$p" in
    *.md|*.mdx) return 0 ;;
    *) return 1 ;;
  esac
}

is_parable_platform_workspace() {
  local root="${1:-}"
  [[ -d "$root/platform-schemas/schemas" && -d "$root/services" ]]
}

is_source_write_action() {
  case "${1:-}" in
    strreplace|write|applypatch) return 0 ;;
    *) return 1 ;;
  esac
}

is_gated_source_path() {
  local p="${1:-}"
  local root="${2:-}"
  local norm="$p"
  if [[ "$norm" == "$root"/* ]]; then
    norm="${norm#"$root"/}"
  fi
  case "$norm" in
    services/*|apps/*|utils/*|platform-schemas/*|infrastructure/*) return 0 ;;
    *) return 1 ;;
  esac
}

active_skill_marker_valid() {
  local marker_skill="${1:-}"
  local session_file="${2:-.context/ship-feature-session.json}"
  [[ -n "$marker_skill" && -f "$session_file" ]] || return 1
  python3 - "$marker_skill" "$session_file" <<'PY'
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

marker = sys.argv[1].strip()
session_path = Path(sys.argv[2])
try:
    session = json.loads(session_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
if session.get("status") == "completed":
    raise SystemExit(1)
if session.get("skill") and session.get("skill") != marker:
    raise SystemExit(1)
activated_at = session.get("activated_at")
if activated_at:
    try:
        ts = datetime.fromisoformat(str(activated_at).replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - ts > timedelta(hours=24):
            raise SystemExit(1)
    except Exception:
        raise SystemExit(1)
raise SystemExit(0)
PY
}

path_exists_mode() {
  local p="${1:-}"
  if [[ -n "$p" && -f "$p" ]]; then
    printf 'modify'
  else
    printf 'create'
  fi
}

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
  IFS=$'	' read -r parsed_tool parsed_file parsed_prompt <<EOF
$(printf '%s' "$HOOK_STDIN" | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
if not raw:
    print("		")
    raise SystemExit(0)
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    print("		")
    raise SystemExit(0)
name = d.get("tool_name") or d.get("tool") or d.get("name") or ""
inp = d.get("tool_input") or d.get("input") or d.get("arguments") or {}
if isinstance(inp, str):
    try:
        inp = json.loads(inp)
    except json.JSONDecodeError:
        inp = {}
path = "unknown"
prompt = ""
if isinstance(inp, dict):
    path = inp.get("path") or inp.get("file_path") or inp.get("file") or inp.get("target_file") or inp.get("notebook_path") or "unknown"
    prompt = inp.get("prompt") or inp.get("task") or inp.get("description") or inp.get("command") or ""
prompt = str(prompt).replace("\t", " ").replace("\n", " ")[:4000]
print(f"{name}	{path}	{prompt}")
' || true)
EOF
  if [[ -n "$parsed_tool" ]]; then
    TOOL="$parsed_tool"
  fi
  if [[ -n "$parsed_file" ]]; then
    FILE_ARG="$parsed_file"
  fi
  PROMPT_ARG="${parsed_prompt:-}"
fi

PROMPT_ARG="${PROMPT_ARG:-}"

if [[ -z "$TOOL" ]]; then
  echo "enforce-gate: no tool name from args/stdin; allowing (fail-open)." >&2
  emit_allow
  exit 0
fi

# === EXEMPTIONS: Files that should never be gated ===

# Always exempt edits inside the global Cursor home directory ($HOME/.cursor).
# User hooks run with cwd=$HOME/.cursor, which defeats the workspace-detection
# logic below (it can treat ~/.cursor as the "workspace" and then run the
# manifest-backed markdown policy, which denies non-indexed skill files).
if [[ "$FILE_ARG" == /* ]]; then
  ABS_FILE_ARG="$FILE_ARG"
else
  ABS_FILE_ARG="$(cd "$(dirname "$FILE_ARG")" 2>/dev/null && pwd)/$(basename "$FILE_ARG")"
fi
case "$ABS_FILE_ARG" in
  "$HOME/.cursor/"*|"$HOME/.cursor")
    echo "enforce-gate: EXEMPT - global Cursor home: $ABS_FILE_ARG" >&2
    emit_allow
    exit 0
    ;;
esac

# Exempt writes outside the current workspace (not subject to workflow gates)
WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [[ "$FILE_ARG" == /* ]]; then
  CANDIDATE_ROOT="$(git -C "$(dirname "$FILE_ARG")" rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$CANDIDATE_ROOT" ]]; then
    WORKSPACE_ROOT="$CANDIDATE_ROOT"
  fi
fi
if [[ "$FILE_ARG" == /* ]] && [[ "$FILE_ARG" != "$WORKSPACE_ROOT"* ]]; then
  echo "enforce-gate: EXEMPT - file outside workspace: $FILE_ARG" >&2
  emit_allow
  exit 0
fi

# === END EXEMPTIONS ===

tool_lc=$(printf '%s' "$TOOL" | tr '[:upper:]' '[:lower:]')
case "$tool_lc" in
  strreplace|str_replace) ACTION=strreplace ;;
  write) ACTION=write ;;
  editnotebook|edit_notebook) ACTION=write ;;
  applypatch|apply_patch) ACTION=write ;;
  *subagent*|task)
    prompt_lc=$(printf '%s' "$PROMPT_ARG" | tr '[:upper:]' '[:lower:]')
    if [[ "$prompt_lc" == *"plan-create"* && "$prompt_lc" == *"plan-review"* ]]; then
      ACTION=task_plan
    elif [[ "$prompt_lc" == *"plan-update"* ]]; then
      ACTION=task_update
    elif [[ "$prompt_lc" == *"de-adversarial-reviewer"* || "$prompt_lc" == *"/de-adversarial-reviewer"* ]]; then
      ACTION=task_adversarial
    elif [[ "$prompt_lc" == *"test-benchmark"* || "$prompt_lc" == *"/test-benchmark"* ]]; then
      ACTION=task_benchmark
    elif [[ "$prompt_lc" == *"pr-review"* || "$prompt_lc" == *"/pr-review"* ]]; then
      ACTION=task_pr_review
    elif [[ "$prompt_lc" == *"vibe-test"* || "$prompt_lc" == *"/vibe-test"* ]]; then
      ACTION=task_vibetest
    else
      ACTION=task_delegate
    fi
    ;;
  *) ACTION="$tool_lc" ;;
esac

# Shared markdown policy check for write-like operations.
if [[ "$ACTION" == "write" || "$ACTION" == "strreplace" ]] && is_markdown_target "$FILE_ARG"; then
  RESOLVER="${HOME}/.cursor/scripts/manifest_markdown_resolver.py"
  if [[ -f "$RESOLVER" ]]; then
    MODE="$(path_exists_mode "$FILE_ARG")"
    RESOLVE_OUT="$(python3 "$RESOLVER" --path "$FILE_ARG" --mode "$MODE" --workspace "$WORKSPACE_ROOT" 2>/dev/null || true)"
    if [[ -n "$RESOLVE_OUT" ]]; then
      allow_flag="$(printf '%s' "$RESOLVE_OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print("1" if d.get("allow") else "0")' 2>/dev/null || printf '1')"
      reason="$(printf '%s' "$RESOLVE_OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("reason",""))' 2>/dev/null || true)"
      if [[ "$allow_flag" != "1" ]]; then
        emit_deny "Blocked by markdown policy: ${reason:-deny:unknown}"
        exit 0
      fi
    fi
  fi
fi

TARGET_SKILL=""
TARGET_SKILL_SOURCE="none"

# Priority 1: Explicit active skill context (env vars)
if [[ -n "${CURSOR_ACTIVE_SKILL:-}" ]]; then
  TARGET_SKILL="$CURSOR_ACTIVE_SKILL"
  TARGET_SKILL_SOURCE="env:CURSOR_ACTIVE_SKILL"
elif [[ -n "${ACTIVE_SKILL:-}" ]]; then
  TARGET_SKILL="$ACTIVE_SKILL"
  TARGET_SKILL_SOURCE="env:ACTIVE_SKILL"

# Priority 2: Active skill marker file (must match a live, non-completed session)
elif [[ -f ".context/.active_skill" ]]; then
  MARKER_SKILL="$(tr -d '[:space:]' < .context/.active_skill 2>/dev/null || true)"
  if active_skill_marker_valid "$MARKER_SKILL" ".context/ship-feature-session.json"; then
    TARGET_SKILL="$MARKER_SKILL"
    TARGET_SKILL_SOURCE="file:.context/.active_skill"
  else
    echo "enforce-gate: stale or completed .active_skill marker ignored" >&2
  fi

# Priority 3: Directory heuristics (fallback)
elif [[ "$(pwd)" == *"/ship-feature-workspace/"* ]] || [[ "$(pwd)" == *"/ship-feature/"* ]]; then
  TARGET_SKILL="ship-feature"
  TARGET_SKILL_SOURCE="pwd:ship-feature"
elif [[ "$(pwd)" == *"/spec-driven/"* ]]; then
  TARGET_SKILL="spec-driven"
  TARGET_SKILL_SOURCE="pwd:spec-driven"
elif [[ "$(pwd)" == *"/investigate-workspace/"* ]] || [[ "$(pwd)" == *"/investigate/"* ]]; then
  TARGET_SKILL="investigate"
  TARGET_SKILL_SOURCE="pwd:investigate"
fi

# Validate target skill (only gate these specific workflow skills)
case "$TARGET_SKILL" in
  ship-feature|spec-driven|investigate) ;;
  *) TARGET_SKILL="" ;;
esac

if [[ -z "$TARGET_SKILL" ]]; then
  if is_parable_platform_workspace "$WORKSPACE_ROOT" \
    && is_source_write_action "$ACTION" \
    && is_gated_source_path "$FILE_ARG" "$WORKSPACE_ROOT"; then
    echo "enforce-gate: BLOCKED - parable-platform source edit without active ship-feature session" >&2
    emit_deny "Blocked: run activate_session.py before editing source under services/, apps/, utils/, platform-schemas/, or infrastructure/."
    exit 0
  fi
  echo "enforce-gate: no gated skill context; allowing tool=$TOOL action=$ACTION." >&2
  emit_allow
  exit 0
fi

echo "enforce-gate: tool=$TOOL action=$ACTION skill=$TARGET_SKILL source=$TARGET_SKILL_SOURCE file=$FILE_ARG cwd=$(pwd)" >&2

GATE_SCRIPT="${HOME}/.cursor/hooks/as-skill-gates-skill_gate.py"
if [[ ! -f "$GATE_SCRIPT" ]]; then
  echo "enforce-gate: gate script missing; allowing." >&2
  emit_allow
  exit 0
fi

if python3 "$GATE_SCRIPT" check --skill "$TARGET_SKILL" --action "$ACTION" --file "$FILE_ARG" >/dev/null 2>&1; then
  GATE_EXIT=0
else
  GATE_EXIT=1
fi

# Persist compliance artifacts for ship-feature source edits (manifest-indexed)
if [[ "$TARGET_SKILL" == "ship-feature" && ( "$ACTION" == "strreplace" || "$ACTION" == "write" || "$ACTION" == "applypatch" ) ]]; then
  RECORD_SCRIPT="${HOME}/.cursor/skills/ship-feature/scripts/record_stage_compliance.py"
  if [[ -f "$RECORD_SCRIPT" ]]; then
    python3 "$RECORD_SCRIPT" \
      --workspace "$WORKSPACE_ROOT" \
      --action "$ACTION" \
      --file "$FILE_ARG" \
      --allowed "$GATE_EXIT" 2>&1 | tail -3 >&2 || true
  fi
fi

if [[ "$GATE_EXIT" -eq 0 ]]; then
  echo "enforce-gate: gate check passed" >&2
  emit_allow
  exit 0
fi

echo "enforce-gate: BLOCKED by skill gate (skill=$TARGET_SKILL source=$TARGET_SKILL_SOURCE action=$ACTION)" >&2
python3 "$GATE_SCRIPT" state --skill "$TARGET_SKILL" 2>&1 | cat >&2
HARNESS_RECOVERY="${HOME}/.cursor/skills/ship-feature/scripts/harness_recovery.py"
if [[ "$TARGET_SKILL" == "ship-feature" && -f "$HARNESS_RECOVERY" ]]; then
  echo "enforce-gate: harness recovery (self-heal loop — no user prompt):" >&2
  if [[ "$FILE_ARG" != "unknown" && "$FILE_ARG" == *".context/"* || "$FILE_ARG" == plans/* ]]; then
    python3 "$HARNESS_RECOVERY" --blocked-path "$FILE_ARG" --format text 2>&1 | cat >&2 || true
  else
    python3 "$HARNESS_RECOVERY" --gate auto --format text 2>&1 | cat >&2 || true
  fi
fi
echo "Run: python3 ~/.cursor/skills/_shared/skill_gate.py state --skill $TARGET_SKILL" >&2
emit_deny "Blocked by skill gate for $TARGET_SKILL ($ACTION). Run harness_recovery.py next_action — do not ask the user."
exit 0
