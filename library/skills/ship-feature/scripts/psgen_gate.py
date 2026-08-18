#!/usr/bin/env python3
"""Detect psgen / schema-first scope for ship-feature Stages 3.7 and 6.65.

Always evaluates; full psgen-stage-details checklist runs only when triggered.
Prints JSON to stdout; exit 0 always.

Usage (from repo root):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/psgen_gate.py --mode plan --plan plans/foo.plan.md
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/psgen_gate.py --mode code --base origin/main
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PSGEN_SERVICE_PATH_RE = re.compile(
    r"platform-schemas/services/|platform-schemas/validate/|platform-schemas/build",
    re.I,
)

PLAN_SIGNAL_RES: list[tuple[str, re.Pattern[str]]] = [
    ("psgen_service_path", PSGEN_SERVICE_PATH_RE),
    ("psgen_toolchain", re.compile(r"utils/psgen/|@psgen/|psgen-toolchain", re.I)),
    ("schema_ts", re.compile(r"\.schema\.ts|schema\.config\.ts", re.I)),
    ("route_impl", re.compile(r"route-impl/", re.I)),
    ("build_schemas", re.compile(r"\bmake build-schemas\b|\bpsgen build\b", re.I)),
    ("schema_first", re.compile(r"\bschema-first\b|\bschema first\b", re.I)),
    ("new_endpoint", re.compile(r"\bnew (endpoint|mutation|query|route)\b", re.I)),
    ("new_entity", re.compile(r"\bnew (table|entity|db type)\b", re.I)),
    ("schema_change_agent", re.compile(r"\bschema-change\b", re.I)),
    ("generated_types", re.compile(r"@parable-platform/.*-(types|sdk)", re.I)),
    ("schema_renderer", re.compile(r"schema-renderer|parseSchema", re.I)),
]

CODE_PATH_RES: list[tuple[str, re.Pattern[str]]] = [
    ("psgen_service", re.compile(r"^platform-schemas/services/", re.I)),
    ("psgen_utils", re.compile(r"^utils/psgen/", re.I)),
    ("route_impl", re.compile(r"^services/[^/]+/internal/route-impl/", re.I)),
    ("platform_schemas_data", re.compile(r"^platform-schemas/data/", re.I)),
    ("web_db_migrations", re.compile(r"^services/web-db/migrations/", re.I)),
    ("schema_renderer_app", re.compile(r"^apps/.*/schema-renderer/", re.I)),
]

CODE_CONTENT_RES: list[tuple[str, re.Pattern[str]]] = [
    ("custom_fetch_api", re.compile(r"fetch\s*\(\s*[`'](/api|http)", re.I)),
    ("axios_api", re.compile(r"axios\.(get|post|put|patch|delete)\s*\(\s*[`'](/api|http)", re.I)),
    ("mirror_allowlist", re.compile(r"ALLOWED_[A-Z0-9_]*FIELDS|const\s+[A-Z_]+\s*=\s*\[", re.I)),
    ("vendored_generated", re.compile(r"internal/(config/)?generated/|/generated/", re.I)),
    ("json_parse_cast", re.compile(r"JSON\.parse\([^)]+\)\s+as\s+\{", re.I)),
    ("hand_route_register", re.compile(r"\.(Get|Post|Put|Patch|Delete)\(\s*[\"']/api", re.I)),
    ("dist_manual_edit", re.compile(r"^\+.*platform-schemas/dist/", re.I)),
    ("schema_import", re.compile(r"@parable-platform/[^\"']+-(types|sdk)", re.I)),
]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if result.returncode != 0:
        raise SystemExit(f"not a git repo: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def collect_signals(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    seen: list[str] = []
    for name, pattern in patterns:
        if pattern.search(text):
            seen.append(name)
    return seen


def product_code_paths(changed_files: list[str]) -> list[str]:
    """Paths that match schema-first product scope (exclude skill-only vendor diffs)."""
    out: list[str] = []
    for path in changed_files:
        for _, pattern in CODE_PATH_RES:
            if pattern.search(path):
                out.append(path)
                break
    return out


def diff_for_paths(full_diff: str, paths: list[str]) -> str:
    """Keep only diff hunks for the given paths (git diff -U0 format)."""
    if not paths:
        return ""
    path_set = set(paths)
    chunks: list[str] = []
    current: list[str] = []
    current_path: str | None = None
    for line in full_diff.splitlines():
        if line.startswith("diff --git "):
            if current and current_path in path_set:
                chunks.extend(current)
            current = [line]
            current_path = None
            continue
        if line.startswith("+++ b/"):
            current_path = line[6:].strip()
            current.append(line)
            continue
        if current:
            current.append(line)
    if current and current_path in path_set:
        chunks.extend(current)
    return "\n".join(chunks)


def evaluate_plan(plan_path: Path | None) -> dict:
    if plan_path is None or not plan_path.is_file():
        return {
            "triggered": False,
            "mode": "plan",
            "reason": "no_plan_file",
            "signals": [],
            "plan_path": None,
        }

    text = plan_path.read_text(encoding="utf-8", errors="replace")
    signals = collect_signals(text, PLAN_SIGNAL_RES)
    triggered = bool(signals)
    reason = "psgen_scope_in_plan" if triggered else "no_psgen_scope_in_plan"
    return {
        "triggered": triggered,
        "mode": "plan",
        "reason": reason,
        "signals": signals,
        "plan_path": str(plan_path),
    }


def evaluate_code(base: str, head: str, root: Path) -> dict:
    names = run(
        ["git", "diff", f"{base}...{head}", "--name-only"],
        root,
    )
    if names.returncode != 0:
        raise SystemExit(names.stderr.strip() or "git diff --name-only failed")

    changed_files = [ln for ln in names.stdout.splitlines() if ln.strip()]
    scoped_files = product_code_paths(changed_files)
    path_signals: list[str] = []
    for path in scoped_files:
        for name, pattern in CODE_PATH_RES:
            if pattern.search(path) and name not in path_signals:
                path_signals.append(name)

    diff = run(["git", "diff", f"{base}...{head}", "-U0"], root)
    if diff.returncode != 0:
        raise SystemExit(diff.stderr.strip() or "git diff failed")

    scoped_diff = diff_for_paths(diff.stdout, scoped_files)
    content_signals = collect_signals(scoped_diff, CODE_CONTENT_RES)
    signals = sorted(set(path_signals + content_signals))
    triggered = bool(signals)
    if not changed_files:
        reason = "empty_diff"
    elif triggered:
        reason = "psgen_scope_in_diff"
    else:
        reason = "no_psgen_scope_in_diff"

    return {
        "triggered": triggered,
        "mode": "code",
        "reason": reason,
        "signals": signals,
        "changed_files": len(changed_files),
        "base": base,
        "head": head,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("plan", "code"),
        required=True,
        help="plan = Stage 3.7 design gate; code = Stage 6.65 PR gate",
    )
    parser.add_argument("--plan", type=Path, default=None, help="Plan file for --mode plan")
    parser.add_argument("--base", default="origin/main", help="Diff base for --mode code")
    parser.add_argument("--head", default="HEAD", help="Diff head for --mode code")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write JSON (default: stdout only)",
    )
    args = parser.parse_args()

    root = repo_root()
    if args.mode == "plan":
        payload = evaluate_plan(args.plan)
    else:
        payload = evaluate_code(args.base, args.head, root)

    text = json.dumps(payload, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
