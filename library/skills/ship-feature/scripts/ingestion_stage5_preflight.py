#!/usr/bin/env python3
"""Stage 5 ingestion CI pre-flight: contract test, dockerfile lint, mypy, optional Docker build.

Matches GitHub ingestion-test and E2E Full Pipeline docker steps before push.
Writes a gate artifact consumed by stage5_push_gate.py.

Usage (repo root, before git push / commit-push-pr):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/ingestion_stage5_preflight.py \\
    --base origin/main \\
    --out .context/ingestion-stage5-preflight.json

Exit 0 on pass; non-zero on first failing step.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_BY_SCRIPT = "ingestion_stage5_preflight.py"

CONTRACT_TEST = "scripts/ci/ingestion_sparse_checkout_test.py"
VALIDATE_DOCKERFILES = "scripts/validate-dockerfiles.sh"
INGESTION_DIR = "services/ingestion"
DOCKERFILE = "services/ingestion/Dockerfile"

TRIGGER_PREFIXES = (
    "services/ingestion/",
    "services/pkg/mapping-planner-ffi/",
    "scripts/ci/ingestion",
)

TRIGGER_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/_ci-test-python.yml",  # ingestion-test lives here (PARABLE-200)
    CONTRACT_TEST,
)


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


def changed_files(base: str, head: str, root: Path) -> list[str]:
    proc = run(["git", "diff", f"{base}...{head}", "--name-only"], root)
    if proc.returncode != 0:
        proc = run(["git", "diff", f"{base}...{head}", "--name-only"], root)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def ingestion_ci_wiring_in_diff(base: str, head: str, root: Path) -> bool:
    for path in changed_files(base, head, root):
        normalized = path.replace("\\", "/")
        if normalized in TRIGGER_FILES:
            return True
        if any(normalized.startswith(prefix) for prefix in TRIGGER_PREFIXES):
            return True
        if normalized == "Cargo.toml" and _cargo_touches_ingestion_maturin(root, base, head):
            return True
    return False


def _cargo_touches_ingestion_maturin(root: Path, base: str, head: str) -> bool:
    proc = run(
        ["git", "diff", f"{base}...{head}", "--", "Cargo.toml"],
        root,
    )
    if proc.returncode != 0:
        return False
    text = proc.stdout
    needles = (
        "mapping-planner-ffi",
        "mapping-planner-rs",
        "services/ingestion",
    )
    return any(needle in text for needle in needles)


def dockerfile_in_diff(base: str, head: str, root: Path) -> bool:
    return DOCKERFILE in changed_files(base, head, root)


def schemas_present(root: Path) -> bool:
    marker = root / "platform-schemas/dist/types/python/enums/pyproject.toml"
    return marker.is_file()


def preflight_script_path() -> Path:
    return Path(__file__).resolve()


def write_artifact(root: Path, out: str, payload: dict) -> None:
    out_path = root / out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--out",
        default=".context/ingestion-stage5-preflight.json",
        help="Gate artifact path (relative to repo root)",
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip PREBUILT docker build even when Dockerfile changed",
    )
    parser.add_argument(
        "--skip-build-schemas",
        action="store_true",
        help="Do not run make build-schemas when generated types are missing",
    )
    args = parser.parse_args()

    root = repo_root()
    if not ingestion_ci_wiring_in_diff(args.base, args.head, root):
        artifact = {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": True,
            "reason": "no_ingestion_ci_wiring_in_diff",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "steps": [],
        }
        write_artifact(root, args.out, artifact)
        return

    steps: list[dict] = []
    contract = root / CONTRACT_TEST
    if contract.is_file():
        proc = run(["python3", str(contract)], root)
        steps.append(
            {
                "step": "ingestion_sparse_checkout_contract",
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
            }
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or proc.stdout)
            _fail(root, args, steps)

    validate = root / VALIDATE_DOCKERFILES
    if validate.is_file():
        proc = run(["./scripts/validate-dockerfiles.sh"], root)
        steps.append(
            {
                "step": "validate_dockerfiles",
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
            }
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or proc.stdout)
            _fail(root, args, steps)

    if not schemas_present(root) and not args.skip_build_schemas:
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
            _fail(root, args, steps)

    ingest = root / INGESTION_DIR
    if ingest.is_dir():
        sync = run(["uv", "sync", "--frozen"], ingest)
        steps.append(
            {
                "step": "uv_sync_ingestion",
                "ok": sync.returncode == 0,
                "returncode": sync.returncode,
            }
        )
        if sync.returncode != 0:
            sys.stderr.write(sync.stderr or sync.stdout)
            _fail(root, args, steps)

        lint = run(["make", "lint"], ingest)
        steps.append(
            {
                "step": "ingestion_make_lint",
                "ok": lint.returncode == 0,
                "returncode": lint.returncode,
            }
        )
        if lint.returncode != 0:
            sys.stderr.write(lint.stderr or lint.stdout)
            _fail(root, args, steps)

    run_docker = dockerfile_in_diff(args.base, args.head, root) and not args.skip_docker
    if dockerfile_in_diff(args.base, args.head, root) and args.skip_docker:
        artifact = {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": True,
            "reason": "skip_docker_flag",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "docker_checked": False,
            "steps": steps,
        }
        write_artifact(root, args.out, artifact)
        return

    if run_docker and (root / DOCKERFILE).is_file():
        if shutil.which("docker") is None:
            write_artifact(
                root,
                args.out,
                {
                    "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
                    "passed": True,
                    "skipped": True,
                    "reason": "docker_unavailable",
                    "head_sha": head_sha(root),
                    "base": args.base,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "docker_checked": False,
                    "steps": steps,
                    "detail": "docker binary not found on PATH",
                },
            )
            return
        docker_cmd = [
            "docker",
            "build",
            "-f",
            DOCKERFILE,
            "--build-arg",
            "PREBUILT=true",
            "-t",
            "ingestion:stage5-preflight",
            ".",
        ]
        proc = run(docker_cmd, root)
        steps.append(
            {
                "step": "docker_build_ingestion_prebuilt",
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
            }
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or proc.stdout)
            _fail(root, args, steps)

    artifact = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": True,
        "skipped": False,
        "reason": "ok",
        "head_sha": head_sha(root),
        "base": args.base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "docker_checked": run_docker,
        "steps": steps,
    }
    write_artifact(root, args.out, artifact)


def _fail(root: Path, args: argparse.Namespace, steps: list[dict]) -> None:
    artifact = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": False,
        "skipped": False,
        "reason": "preflight_failed",
        "head_sha": head_sha(root),
        "base": args.base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
    }
    write_artifact(root, args.out, artifact)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
