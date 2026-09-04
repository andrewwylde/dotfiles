#!/usr/bin/env python3
"""Detect actionable clippy cognitive_complexity warnings in a Rust PR diff.

Actionable = warning line overlaps a changed line in git diff(base..HEAD).
Pre-existing warnings in untouched files/lines are skipped.

Usage (from repo root):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/rust_cognitive_complexity_gate.py
  python3 .../rust_cognitive_complexity_gate.py --base origin/main

Exit 0 always; prints JSON to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

WARNING_RE = re.compile(
    r"warning: the function has a cognitive complexity of \((\d+)/(\d+)\)\s*"
    r"\n\s*--> (.+):(\d+):",
    re.MULTILINE,
)

# services/<dir>/ or services/pkg/<dir>/
SERVICE_CRATE = {
    "query-layer": "query-layer",
    "provider-transformations": "provider-transformations",
    "dataplane-maintenance": "dataplane-maintenance",
}


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if result.returncode != 0:
        raise SystemExit(f"not a git repo: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def changed_rs_lines(base: str, head: str, root: Path) -> dict[str, set[int]]:
    diff = run(["git", "diff", f"{base}...{head}", "-U0", "--", "*.rs"], root)
    if diff.returncode != 0:
        raise SystemExit(diff.stderr.strip() or "git diff failed")

    per_file: dict[str, set[int]] = {}
    current: str | None = None
    for line in diff.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            per_file.setdefault(current, set())
            continue
        if current is None or not line.startswith("@@"):
            continue
        # @@ -old,count +new,count @@
        m = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2) or "1")
        if count == 0:
            continue
        for n in range(start, start + count):
            per_file[current].add(n)
    return per_file


def crates_from_diff(base: str, head: str, root: Path) -> list[str]:
    names = run(
        ["git", "diff", f"{base}...{head}", "--name-only", "--", "*.rs"],
        root,
    )
    crates: set[str] = set()
    for raw in names.stdout.splitlines():
        if not raw.startswith("services/"):
            continue
        parts = Path(raw).parts
        if len(parts) < 2:
            continue
        if parts[1] == "pkg" and len(parts) >= 3:
            manifest = root / "services" / "pkg" / parts[2] / "Cargo.toml"
            if manifest.is_file():
                text = manifest.read_text(encoding="utf-8")
                m = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
                if m:
                    crates.add(m.group(1))
            continue
        service = parts[1]
        if service in SERVICE_CRATE:
            crates.add(SERVICE_CRATE[service])
    return sorted(crates)


def clippy_warnings(crate: str, root: Path) -> list[dict]:
    proc = run(
        ["cargo", "clippy", "-p", crate, "--all-targets"],
        root,
    )
    out = proc.stdout + proc.stderr
    warnings: list[dict] = []
    for m in WARNING_RE.finditer(out):
        score, threshold, path, line = m.groups()
        warnings.append(
            {
                "crate": crate,
                "file": path,
                "line": int(line),
                "score": int(score),
                "threshold": int(threshold),
            }
        )
    return warnings


def is_actionable(w: dict, changed: dict[str, set[int]]) -> bool:
    file_lines = changed.get(w["file"], set())
    if not file_lines:
        return False
    return w["line"] in file_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Diff base ref")
    parser.add_argument("--head", default="HEAD", help="Diff head ref")
    parser.add_argument(
        "--threshold",
        type=int,
        default=15,
        help="Expected clippy cognitive complexity threshold",
    )
    args = parser.parse_args()

    root = repo_root()
    changed = changed_rs_lines(args.base, args.head, root)
    if not changed:
        print(
            json.dumps(
                {
                    "triggered": False,
                    "reason": "no_rust_files_in_diff",
                    "actionable": [],
                    "skipped_preexisting": [],
                },
                indent=2,
            )
        )
        return

    crates = crates_from_diff(args.base, args.head, root)
    if not crates:
        print(
            json.dumps(
                {
                    "triggered": False,
                    "reason": "no_workspace_crates_in_diff",
                    "actionable": [],
                    "skipped_preexisting": [],
                },
                indent=2,
            )
        )
        return

    all_warnings: list[dict] = []
    for crate in crates:
        all_warnings.extend(clippy_warnings(crate, root))

    actionable = [w for w in all_warnings if is_actionable(w, changed)]
    skipped = [w for w in all_warnings if w not in actionable]

    over = [w for w in actionable if w["score"] > args.threshold]
    triggered = len(over) > 0

    print(
        json.dumps(
            {
                "triggered": triggered,
                "reason": "actionable_over_threshold" if triggered else "clean_or_preexisting",
                "crates_checked": crates,
                "actionable": over,
                "skipped_preexisting": skipped,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
