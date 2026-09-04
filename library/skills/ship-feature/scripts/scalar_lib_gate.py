#!/usr/bin/env python3
"""Detect whether /scalar-lib-it should run for ship-feature Stages 3.8 and 6.7.

Always evaluates; full scalar-lib-it audit runs only when triggered is true.
Prints JSON to stdout; exit 0 always.

Usage (from repo root):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/scalar_lib_gate.py --mode plan --plan plans/foo.plan.md
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/scalar_lib_gate.py --mode code --base origin/main
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SCALAR_LIB_PATH_RE = re.compile(
    r"(utils/psgen/scalar-lib|platform-schemas/.+scalars|scalar-lib/)",
    re.I,
)

PLAN_SIGNAL_RES: list[tuple[str, re.Pattern[str]]] = [
    ("scalar_lib_path", SCALAR_LIB_PATH_RE),
    ("scalar_keyword", re.compile(r"\bscalar[- ]?lib\b", re.I)),
    ("parse_hook", re.compile(r"\bParse[A-Z][A-Za-z0-9_]*\b|\bparse_[a-z0-9_]+\b")),
    ("coerce_boundary", re.compile(r"\bcoerce_(lenient|strict)\b|typing boundary|boundary typing", re.I)),
    ("platform_scalar", re.compile(r"\b(Contact\.Email|Identity\.UUID|Temporal\.|Generic\.JSON|CronExpression)\b")),
    ("new_scalar", re.compile(r"\bnew scalar\b|proposed scalar\b|register.*scalar", re.I)),
    ("csv_typing", re.compile(r"\bCSV\b.*\b(parse|coerce|type|column)\b|\bcoerce.*CSV\b", re.I)),
]

CODE_PATH_RES: list[tuple[str, re.Pattern[str]]] = [
    ("scalar_lib_tree", re.compile(r"^utils/psgen/scalar-lib/", re.I)),
    ("scalars_graphql", re.compile(r"scalars\.graphql$", re.I)),
    ("scalar_import_go", re.compile(r"github\.com/parable-platform/scalar-lib|parable_scalars|parable-scalar-lib|parable_scalar_lib", re.I)),
]

CODE_CONTENT_RES: list[tuple[str, re.Pattern[str]]] = [
    ("hand_rolled_email", re.compile(r"toLowerCase|to_lower|TrimSpace.*email|email.*trim", re.I)),
    ("hand_rolled_uuid", re.compile(r"base62|base64.*uuid|uuid.*encode", re.I)),
    ("hand_rolled_cron", re.compile(r"isValidCron|cron.*regex|CronExpression.*match", re.I)),
    ("scalar_import", re.compile(r"scalar-lib|parable_scalars|parable_scalar_lib|ParseEmail|ParseUUID|\.parse\(", re.I)),
    ("mirror_allowlist", re.compile(r"ALLOWED_.*FIELDS|scalar.*map|ScalarMetadata", re.I)),
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
    out: list[str] = []
    for path in changed_files:
        for _, pattern in CODE_PATH_RES:
            if pattern.search(path):
                out.append(path)
                break
    return out


def diff_for_paths(full_diff: str, paths: list[str]) -> str:
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
    reason = "scalar_scope_in_plan" if triggered else "no_scalar_scope_in_plan"
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
        reason = "scalar_scope_in_diff"
    else:
        reason = "no_scalar_scope_in_diff"

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
        help="plan = Stage 3.8 design gate; code = Stage 6.7 PR gate",
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
