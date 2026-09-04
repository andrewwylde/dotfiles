#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${PERSONAL_VOICE_ROOT:-$HOME/.agent/personal-voice-model}"

DAYS=""
REFINE_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="${2:?}"
      shift 2
      ;;
    --root)
      ROOT="${2:?}"
      shift 2
      ;;
    --refine-only)
      REFINE_ONLY=1
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        DAYS="$1"
        shift
      else
        echo "usage: $0 [--days N] [--root PATH] [--refine-only]" >&2
        exit 2
      fi
      ;;
  esac
done

if [[ -z "$DAYS" ]]; then
  DAYS="$(python3 -c "import json; print(json.load(open('${ROOT}/config.json')).get('backfill_days', 180))" 2>/dev/null || echo 180)"
fi

LOG_DIR="$ROOT/logs"
BACKFILL="$ROOT/harvest/backfill"
mkdir -p "$LOG_DIR" "$BACKFILL"
LOG="$LOG_DIR/backfill-$(date +%Y%m%d).log"

exec >>"$LOG" 2>&1
echo "=== backfill days=$DAYS refine_only=$REFINE_ONLY $(date -Iseconds) ==="

if ! curl -sf "${OLLAMA_HOST:-http://127.0.0.1:11434}/api/tags" >/dev/null; then
  echo "Ollama not reachable; start with: brew services start ollama"
  exit 1
fi

MANIFEST="$BACKFILL/manifest.json"

if [[ "$REFINE_ONLY" -eq 0 ]]; then
  python3 "$SKILL_DIR/harvest_slack.py" --root "$ROOT" --days "$DAYS" --chunk weeks
else
  echo "refine-only: skipping harvest_slack.py (expect MCP/prebuilt shards)"
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "missing manifest: $MANIFEST"
  exit 1
fi

python3 - "$SKILL_DIR" "$ROOT" "$MANIFEST" <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

# line-buffer logs when stdout is redirected to a file
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

skill, root, manifest_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
manifest = json.loads(manifest_path.read_text())
windows = sorted(manifest.get("windows") or [], key=lambda w: w.get("after") or "")
refine = skill / "refine_ollama.py"
env = {**os.environ, "PYTHONUNBUFFERED": "1"}

for i, w in enumerate(windows):
    if w.get("refined"):
        print(f"skip refine {w.get('label')} (already refined)", flush=True)
        continue
    path = Path(w["path"])
    if not path.exists():
        print(f"missing shard {path}", flush=True)
        sys.exit(1)
    is_last = i == len(windows) - 1
    cmd = ["python3", "-u", str(refine), "--root", str(root), "--harvest", str(path)]
    if not is_last:
        cmd.append("--no-decay")
    print(" ".join(cmd), flush=True)
    subprocess.check_call(cmd, env=env)
    w["refined"] = True
    manifest["windows"] = windows
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"marked refined {w.get('label')} ({sum(1 for x in windows if x.get('refined'))}/{len(windows)})", flush=True)

print("backfill refine complete", flush=True)
PY

echo "=== done $(date -Iseconds) ==="
