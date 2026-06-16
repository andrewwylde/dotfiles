#!/usr/bin/env bash
# Smoke-check agent output for required pipeline artifacts (structure only).
# Usage: score-markdown.sh path/to/response.md
# Exit 0 if all patterns match; exit 1 with missing list otherwise.
set -euo pipefail

f="${1:?usage: score-markdown.sh <markdown-file>}"
missing=()

match() {
  local label="$1"
  shift
  if ! grep -qiE "$@" "$f"; then
    missing+=("$label")
  fi
}

# Loose patterns — human graders still use RUBRIC.md for points.
match "P1-inventory-or-file-table" '(^|\n)(#+ +|\*\*)?(changeset +)?inventory|file +path|name-status|\| +file +\|'
match "P2-dependency" '(dependency|depend(s|encies)|hard +dep|soft +dep|edge(s)?|graph|mermaid)'
match "P3-risk" '(risk|HIGH|MEDIUM|LOW|blast|rollback)'
match "P4-PR-boundaries" '(PR-[0-9]|pull request|### +PR|## +PR|named PR)'
match "P5-sequence" '(merge +order|wave|sequen|topolog|stack|base: +main|split-to-prs|hand-?off)'

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "MISSING (${#missing[@]}): ${missing[*]}"
  exit 1
fi
echo "OK: all smoke patterns matched for $f"
exit 0
