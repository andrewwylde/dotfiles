#!/usr/bin/env bash
################################################################################
# Dotfiles setup router
#
# Detects the current platform and runs the matching setup script:
#   macOS  → mac-setup.sh
#   WSL    → wsl-setup.sh
#   Windows (Git Bash / MSYS) → setup.ps1 via PowerShell
#
# Usage:
#   ./setup.sh
#
# On Windows PowerShell (no bash):
#   .\setup.ps1
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo "[setup] $*"; }

run_script() {
  local target="$1"
  shift
  if [[ ! -f "$target" ]]; then
    echo "[setup] ERROR: missing ${target}" >&2
    exit 1
  fi
  if [[ ! -x "$target" ]]; then
    chmod +x "$target"
  fi
  log "Running $(basename "$target")..."
  exec "$target" "$@"
}

os="$(uname -s)"

case "$os" in
  Darwin)
    run_script "${SCRIPT_DIR}/mac-setup.sh" "$@"
    ;;
  Linux)
    if grep -qi microsoft /proc/version 2>/dev/null; then
      run_script "${SCRIPT_DIR}/wsl-setup.sh" "$@"
    else
      log "Linux (non-WSL) detected — using wsl-setup.sh (most steps still apply)"
      run_script "${SCRIPT_DIR}/wsl-setup.sh" "$@"
    fi
    ;;
  MINGW* | MSYS* | CYGWIN*)
    if command -v powershell.exe >/dev/null 2>&1; then
      log "Windows shell detected — delegating to setup.ps1"
      exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${SCRIPT_DIR}/setup.ps1" "$@"
    fi
    echo "[setup] ERROR: Run from PowerShell instead:" >&2
    echo "  powershell -ExecutionPolicy Bypass -File ${SCRIPT_DIR}/setup.ps1" >&2
    exit 1
    ;;
  *)
    echo "[setup] ERROR: Unsupported OS: ${os}" >&2
    echo "  macOS:   ./setup.sh" >&2
    echo "  WSL:     ./setup.sh" >&2
    echo "  Windows: .\\setup.ps1" >&2
    exit 1
    ;;
esac
