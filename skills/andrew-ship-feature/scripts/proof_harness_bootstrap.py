#!/usr/bin/env python3
"""Bootstrap Postgres/Docker for Stage 6.45 proof harness with retry loop.

Resolves PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL by probing psql:
Docker DSN first, then Homebrew (current user) when role postgres is absent.

Usage (from repo root):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_bootstrap.py \
    --max-attempts 3 \
    --log .context/implementation/proof-harness-log.md

Eval the printed export in the same shell before running make test-local-* tiers.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

DOCKER_ORCHESTRATION_DSN = (
    "postgres://postgres:postgres@localhost:5432/orchestration_dev?sslmode=disable"
)
ENV_VAR = "PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if result.returncode != 0:
        raise SystemExit(f"not a git repo: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def homebrew_orchestration_dsn() -> str:
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "postgres"
    return f"postgres://{user}@localhost:5432/orchestration_dev?sslmode=disable"


def probe_psql_dsn(dsn: str) -> bool:
    if run(["which", "psql"], Path.cwd()).returncode != 0:
        return False
    return run(["psql", dsn, "-c", "SELECT 1"], Path.cwd()).returncode == 0


def resolve_orchestration_dsn() -> tuple[str, str]:
    if probe_psql_dsn(DOCKER_ORCHESTRATION_DSN):
        return DOCKER_ORCHESTRATION_DSN, "docker"
    homebrew = homebrew_orchestration_dsn()
    if probe_psql_dsn(homebrew):
        return homebrew, "homebrew"
    return DOCKER_ORCHESTRATION_DSN, "unverified"


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("RUN_BY_SKILL: ship-feature\n\n# Proof Harness Log\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def try_bootstrap(root: Path, attempt: int) -> tuple[bool, str]:
    steps: list[str] = []

    if not port_open("127.0.0.1", 5432):
        steps.append("postgres port closed — running make start-postgres")
        proc = run(["make", "start-postgres"], root)
        if proc.returncode != 0:
            return False, f"make start-postgres failed: {proc.stderr.strip()[:500]}"
        for _ in range(15):
            if port_open("127.0.0.1", 5432):
                break
            time.sleep(1)
        if not port_open("127.0.0.1", 5432):
            return False, "postgres port still closed after start-postgres"

    mig = run(["make", "run-orchestration-migrations"], root)
    if mig.returncode != 0:
        steps.append(f"run-orchestration-migrations non-zero (rc={mig.returncode}); continuing")

    dsn, flavor = resolve_orchestration_dsn()
    os.environ[ENV_VAR] = dsn
    if flavor == "unverified":
        return False, (
            f"postgres port open but psql auth failed for docker and homebrew DSNs; "
            f"tried {DOCKER_ORCHESTRATION_DSN} and {homebrew_orchestration_dsn()}"
        )
    steps.append(f"dsn={flavor} ({ENV_VAR} set)")
    return True, "; ".join(steps) if steps else f"postgres up; dsn={flavor}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--log", type=Path, default=Path(".context/implementation/proof-harness-log.md"))
    args = parser.parse_args()

    root = repo_root()
    ts = datetime.now(timezone.utc).isoformat()

    for attempt in range(1, args.max_attempts + 1):
        ok, detail = try_bootstrap(root, attempt)
        append_log(
            args.log,
            f"- {ts} bootstrap attempt {attempt}/{args.max_attempts}: "
            f"{'OK' if ok else 'FAIL'} — {detail}",
        )
        if ok:
            dsn = os.environ.get(ENV_VAR, "")
            flavor = "docker" if "postgres:postgres" in dsn else "homebrew"
            print(f"bootstrap OK (attempt {attempt}): {detail}")
            print(f"export {ENV_VAR}='{dsn}'  # {flavor}")
            return
        time.sleep(2)

    append_log(args.log, f"- {ts} bootstrap EXHAUSTED after {args.max_attempts} attempts")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
