#!/usr/bin/env bash
# Scan tracked/staged dotfiles for Parable-specific content before pushing to the public remote.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: leak-check.sh [--staged]

  Exit 1 if forbidden patterns appear in files git would publish.

  --staged   Scan only the index (staged files). Default: entire working tree
             that git tracks or would track after add.
EOF
}

staged_only=0
for arg in "$@"; do
  case "$arg" in
    -h | --help) usage; exit 0 ;;
    --staged) staged_only=1 ;;
    *) echo "leak-check.sh: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

patterns=(
  'parable-work/'
  'parable-platform'
  'askparable\.com'
  'parable\.work'
  'parable-development'
  'notion\.so/parablework'
  'parable-notes'
  'local\.parable\.work'
)

pathspec=(.)
exclude=(':!.gitignore' ':!bin/leak-check.sh')
if [[ "$staged_only" -eq 1 ]]; then
  pathspec=("${exclude[@]}")
  git diff --cached --name-only -z | grep -z . >/dev/null 2>&1 || {
    echo "leak-check: no staged files"
    exit 0
  }
fi

fail=0
for pattern in "${patterns[@]}"; do
  if [[ "$staged_only" -eq 1 ]]; then
    matches="$(git grep -n -E "$pattern" --cached -- . "${exclude[@]}" 2>/dev/null || true)"
  else
    matches="$(git grep -n -E "$pattern" -- . "${exclude[@]}" 2>/dev/null || true)"
  fi
  if [[ -n "$matches" ]]; then
    echo "FORBIDDEN pattern /${pattern}/:" >&2
    echo "$matches" >&2
    fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo "leak-check: FAILED — remove or gitignore Parable-specific content before push" >&2
  exit 1
fi

echo "leak-check: OK (no forbidden patterns)"
