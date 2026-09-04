#!/usr/bin/env python3
"""Stage 5 provider-transformations-shell-test CI pre-flight.

Mirrors the provider-transformations-shell-test job in ci.yml: apply all
orchestration-db migrations on Postgres, then admission_loop + duroxide_shell
integration tests.

Usage (repo root, before git push / commit-push-pr):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/provider_transformations_shell_stage5_preflight.py \\
    --base origin/main \\
    --out .context/provider-transformations-shell-stage5-preflight.json

Exit 0 on pass or skip (not triggered); non-zero on failure.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_BY_SCRIPT = "provider_transformations_shell_stage5_preflight.py"

DEFAULT_DSN = (
    "postgres://postgres:postgres@localhost:5432/orchestration_test?sslmode=disable"
)

SCHEMAS_MARKER = Path("platform-schemas/dist/types/python/enums/pyproject.toml")


def schemas_present(root: Path) -> bool:
    return (root / SCHEMAS_MARKER).is_file()

def run(
    cmd: list[str],
    cwd: Path,
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        input=input_text,
        env=env,
    )


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
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def provider_transformations_affected(base: str, head: str, root: Path) -> bool:
    script = root / "scripts" / "ci" / "rust-affected-packages.py"
    if script.is_file():
        diff_lines = "\n".join(changed_files(base, head, root))
        proc = run([sys.executable, str(script)], root, input_text=diff_lines)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("affected="):
                    packages = json.loads(line.split("=", 1)[1])
                    if "provider-transformations" in packages:
                        return True
                    break
    for path in changed_files(base, head, root):
        if path.startswith("services/provider-transformations/"):
            return True
        if path.startswith("services/orchestration-db/migrations/"):
            return True
    return False


def postgres_reachable(dsn: str) -> bool:
    proc = run(
        ["psql", dsn, "-c", "SELECT 1"],
        Path.cwd(),
        env={**os.environ, "PGPASSWORD": _password_from_dsn(dsn)},
    )
    return proc.returncode == 0


def _password_from_dsn(dsn: str) -> str:
    # ponytail: minimal parse for postgres://user:pass@host/db
    if "://" not in dsn:
        return os.environ.get("PGPASSWORD", "")
    auth = dsn.split("://", 1)[1].split("@", 1)[0]
    if ":" in auth:
        return auth.split(":", 1)[1]
    return os.environ.get("PGPASSWORD", "")


def apply_migration(root: Path, dsn: str) -> subprocess.CompletedProcess[str]:
    migrations_dir = root / "services/orchestration-db/migrations/sql"
    if not migrations_dir.is_dir():
        raise SystemExit(f"migrations dir not found: {migrations_dir}")
    host_db = dsn.split("@", 1)[-1].split("?", 1)[0]
    host_port, db = host_db.rsplit("/", 1) if "/" in host_db else (host_db, "orchestration_test")
    host = host_port.split(":")[0]
    port = host_port.split(":")[1] if ":" in host_port else "5432"
    user = dsn.split("://", 1)[1].split(":", 1)[0] if "://" in dsn else "postgres"
    env = {**os.environ, "PGPASSWORD": _password_from_dsn(dsn)}
    last = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    for migration in sorted(migrations_dir.glob("*.up.sql")):
        last = run(
            [
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                host,
                "-p",
                port,
                "-U",
                user,
                "-d",
                db,
                "-f",
                str(migration),
            ],
            root,
            env=env,
        )
        if last.returncode != 0:
            return last
    return last


def write_artifact(root: Path, out_rel: str, payload: dict) -> None:
    out_path = root / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--out",
        default=".context/provider-transformations-shell-stage5-preflight.json",
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get(
            "PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL", DEFAULT_DSN
        ),
    )
    args = parser.parse_args()

    root = repo_root()
    if not provider_transformations_affected(args.base, args.head, root):
        write_artifact(
            root,
            args.out,
            {
                "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
                "passed": True,
                "skipped": True,
                "reason": "provider_transformations_not_affected",
                "head_sha": head_sha(root),
                "base": args.base,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "ci_job": "provider-transformations-shell-test",
            },
        )
        return

    if not postgres_reachable(args.dsn):
        write_artifact(
            root,
            args.out,
            {
                "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
                "passed": True,
                "skipped": True,
                "reason": "postgres_unreachable",
                "head_sha": head_sha(root),
                "base": args.base,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "ci_job": "provider-transformations-shell-test",
                "hint": (
                    "Start Postgres and apply orchestration migrations: "
                    "make start-postgres run-orchestration-migrations"
                ),
                "dsn": args.dsn,
            },
        )
        return

    steps: list[dict] = []
    mig = apply_migration(root, args.dsn)
    steps.append(
        {
            "step": "orchestration_migration",
            "ok": mig.returncode == 0,
            "returncode": mig.returncode,
        }
    )
    if mig.returncode != 0:
        sys.stderr.write(mig.stderr or mig.stdout)
        _fail(root, args, steps)

    if not schemas_present(root):
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

    env = {
        **os.environ,
        "PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL": args.dsn,
    }
    for test_target in (
        ["cargo", "test", "-p", "provider-transformations", "--test", "admission_loop", "--", "--nocapture"],
        ["cargo", "test", "-p", "provider-transformations", "--test", "duroxide_shell", "--", "--nocapture"],
    ):
        proc = run(test_target, root, env=env)
        label = test_target[5]
        steps.append(
            {
                "step": f"cargo_test_{label}",
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
            }
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or proc.stdout)
            _fail(root, args, steps)

    write_artifact(
        root,
        args.out,
        {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": True,
            "skipped": False,
            "reason": "ok",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "ci_job": "provider-transformations-shell-test",
            "steps": steps,
        },
    )


def _fail(root: Path, args: argparse.Namespace, steps: list[dict]) -> None:
    write_artifact(
        root,
        args.out,
        {
            "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
            "passed": False,
            "skipped": False,
            "reason": "preflight_failed",
            "head_sha": head_sha(root),
            "base": args.base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "ci_job": "provider-transformations-shell-test",
            "steps": steps,
        },
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
