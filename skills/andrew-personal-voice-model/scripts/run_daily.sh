#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${PERSONAL_VOICE_ROOT:-$HOME/.agent/personal-voice-model}"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR" "$ROOT/harvest/backfill"
LOG="$LOG_DIR/refine-$(date +%Y%m%d).log"

exec >>"$LOG" 2>&1
echo "=== daily refine $(date -Iseconds) ==="

if ! curl -sf "${OLLAMA_HOST:-http://127.0.0.1:11434}/api/tags" >/dev/null; then
  echo "Ollama not reachable; start with: brew services start ollama"
  exit 1
fi

python3 "$SKILL_DIR/harvest_slack.py" --root "$ROOT" --days "${LOOKBACK_DAYS:-7}"
python3 "$SKILL_DIR/refine_ollama.py" --root "$ROOT"
echo "=== done $(date -Iseconds) ==="
