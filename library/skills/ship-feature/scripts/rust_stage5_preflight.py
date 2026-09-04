#!/usr/bin/env python3
"""Stage 5 Rust CI pre-flight: fmt + clippy on touched crates and downstream deps.

Matches CI rust-workspace jobs before push. Writes a gate artifact consumed by
stage5_push_gate.py (beforeShellExecution when ship-feature is active).

Usage (repo root, before git push / commit-push-pr):
  python3 .claude/skills/ship-feature/scripts/rust_stage5_preflight.py \\
    --base origin/main \\
    --out .context/rust-stage5-preflight.json

Exit 0 on pass; non-zero on first failing step.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_BY_SCRIPT = "rust_stage5_preflight.py"

SERVICE_CRATE = {
    "query-layer": "query-layer",
    "provider-transformations": "provider-transformations",
    "dataplane-maintenance": "dataplane-maintenance",
}

# ponytail: static downstream map; widen when new workspace members depend on pkg crates
DOWNSTREAM: dict[str, list[str]] = {
    "parable-mapping-planner-rs": ["provider-transformations", "query-layer"],
    "provider-transformations": ["query-layer"],
    "parable-deltalake-rs": ["provider-transformations", "query-layer"],
    "parable-datafusion-ext-rs": ["query-layer"],
    "parable-scalar-lib": ["query-layer", "provider-transformations"],
}

CLIPPY_ARGS = ["--all-targets", "--", "-D", "warnings", "--force-warn", "clippy::cognitive_complexity"]

SCHEMAS_MARKER = Path("platform-schemas/dist/types/python/enums/pyproject.toml")


def schemas_present(root: Path) -> bool:
    return (root / SCHEMAS_MARKER).is_file()


def ensure_schemas(root: Path, steps: list[dict]) -> bool:
    if schemas_present(root):
        return True
    build = run(["make", "build-schemas"], root)
    steps.append(
        {
            "step": "make_build_schemas",
            "ok": build.returncode == 0,
            "returncode": build.returncode,
        }
    )
    if build.returncode != 0:
        sys.stderr.write(build.stderr or build.stdout)
        return False
    return True


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def repo_root() -> Path:
    proc = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "not a git repository")
    return Path(proc.stdout.strip())


def head_sha(root: Path) -> str:
    proc = run(["git", "rev-parse", "HEAD"], root)
    if proc.returncode != 0:
        raise SystemExit("git rev-parse HEAD failed")
    return proc.stdout.strip()


def crates_from_diff(base: str, head: str, root: Path) -> list[str]:
    names = run(["git", "diff", f"{base}...{head}", "--name-only", "--", "*.rs"], root)
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


def expand_downstream(crates: list[str]) -> list[str]:
    expanded: set[str] = set(crates)
    changed = True
    while changed:
        changed = False
        for crate in list(expanded):
            for downstream in DOWNSTREAM.get(crate, []):
                if downstream not in expanded:
                    expanded.add(downstream)
                    changed = True
    return sorted(expanded)


def rust_in_diff(base: str, head: str, root: Path) -> bool:
    proc = run(["git", "diff", f"{base}...{head}", "--name-only"], root)
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    from stage5_triggers import rust_paths_trigger  # noqa: PLC0415

    return rust_paths_trigger(files)


def changed_paths(base: str, head: str, root: Path) -> list[str]:
    proc = run(["git", "diff", f"{base}...{head}", "--name-only"], root)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--out",
        default=".context/rust-stage5-preflight.json",
        help="Gate artifact path (relative to repo root)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip cargo test (clippy-only, faster)",
    )
    parser.add_argument(
        "--skip-build-schemas",
        action="store_true",
        help="Do not run make build-schemas when generated types are missing",
    )
    args = parser.parse_args()

    root = repo_root()
    files = changed_paths(args.base, args.head, root)
    from stage5_triggers import rust_has_crate_sources, rust_paths_trigger  # noqa: PLC0415

    if not rust_paths_trigger(files):
        artifact = {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": True,
            "reason": "no_rust_files_in_diff",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "crates_checked": [],
        }
        out_path = root / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(artifact, indent=2))
        return

    if not rust_has_crate_sources(files):
        # Cargo.lock / toolchain / schema-only: defer clippy to CI (ENV_SKIP).
        artifact = {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": True,
            "reason": "tooling_only_in_diff",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "crates_checked": [],
        }
        out_path = root / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(artifact, indent=2))
        return

    primary = crates_from_diff(args.base, args.head, root)
    crates = expand_downstream(primary)
    if not crates:
        raise SystemExit("Rust files in diff but no workspace crates detected")

    steps: list[dict] = []

    if not args.skip_build_schemas and not ensure_schemas(root, steps):
        _fail(root, args, primary, crates, steps)

    fmt = run(["cargo", "fmt", "--all", "--", "--check"], root)
    steps.append(
        {
            "step": "cargo_fmt_check",
            "ok": fmt.returncode == 0,
            "returncode": fmt.returncode,
        }
    )
    if fmt.returncode != 0:
        sys.stderr.write(fmt.stderr or fmt.stdout)
        _fail(root, args, primary, crates, steps)

    for crate in crates:
        clippy = run(["cargo", "clippy", "-p", crate, *CLIPPY_ARGS], root)
        ok = clippy.returncode == 0
        steps.append(
            {
                "step": f"cargo_clippy_{crate}",
                "ok": ok,
                "returncode": clippy.returncode,
            }
        )
        if not ok:
            sys.stderr.write(clippy.stderr or clippy.stdout)
            _fail(root, args, primary, crates, steps)

        if not args.skip_tests:
            test = run(["cargo", "test", "-p", crate, "--all-targets"], root)
            steps.append(
                {
                    "step": f"cargo_test_{crate}",
                    "ok": test.returncode == 0,
                    "returncode": test.returncode,
                }
            )
            if test.returncode != 0:
                sys.stderr.write(test.stderr or test.stdout)
                _fail(root, args, primary, crates, steps)

    if args.skip_tests:
        artifact = {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": True,
            "reason": "skip_tests_flag",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "primary_crates": primary,
            "crates_checked": crates,
            "steps": steps,
        }
        out_path = root / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(artifact, indent=2))
        return

    artifact = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": True,
        "skipped": False,
        "reason": "ok",
        "head_sha": head_sha(root),
        "base": args.base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "primary_crates": primary,
        "crates_checked": crates,
        "steps": steps,
    }
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))


def _fail(
    root: Path,
    args: argparse.Namespace,
    primary: list[str],
    crates: list[str],
    steps: list[dict],
) -> None:
    artifact = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": False,
        "skipped": False,
        "reason": "preflight_failed",
        "head_sha": head_sha(root),
        "base": args.base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "primary_crates": primary,
        "crates_checked": crates,
        "steps": steps,
    }
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    raise SystemExit(1)


if __name__ == "__main__":
    main()
