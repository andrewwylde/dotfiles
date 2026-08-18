#!/usr/bin/env python3
"""Detect executable proof-harness scope for ship-feature Stage 0 preflight and 6.45.

Always evaluates; tier execution runs only when triggered (code mode) or checks
only infra (preflight mode). Prints JSON to stdout; exit 0 always.

Usage (from repo root):
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_gate.py --mode preflight
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_gate.py --mode code --base origin/main
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_gate.py --mode plan --plan plans/foo.plan.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
from pathlib import Path

RUN_MARKER = "RUN_BY_SCRIPT: proof_harness_gate.py"

PT_PATH = re.compile(r"^services/provider-transformations/", re.I)
TF_PATH = re.compile(r"^services/transformation-flows/", re.I)
INGEST_PATH = re.compile(r"^services/ingestion/|^platform-schemas/data/", re.I)
INGEST_CI_PATH = re.compile(
    r"^scripts/ci/ingestion|^services/pkg/mapping-planner-ffi/|^\.github/workflows/ci\.yml$",
    re.I,
)
GO_API_PATH = re.compile(r"^services/web-(api|admin-api)/", re.I)

PLAN_PT = re.compile(
    r"provider-transformations|promote worker|duroxide|walking.skeleton|local-maintenance",
    re.I,
)
PLAN_TF = re.compile(
    r"transformation-flows|medallion|bronze_i|bronze ii|silver|gold_partition|daily_fanout",
    re.I,
)
PLAN_INGEST = re.compile(
    r"services/ingestion|connector tap|prove-200s|run_connector_direct|platform-schemas/data",
    re.I,
)
BRANCH_PT = re.compile(
    r"provider|promote|duroxide|mnt|local.verification|parable|par-\d+",
    re.I,
)
BRANCH_TF = re.compile(
    r"transformation|medallion|bronze|silver|gold|fanout|prefect",
    re.I,
)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if result.returncode != 0:
        raise SystemExit(f"not a git repo: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def changed_files(base: str, root: Path) -> list[str]:
    result = run(["git", "diff", "--name-only", f"{base}...HEAD"], root)
    if result.returncode != 0:
        result = run(["git", "diff", "--name-only", base, "HEAD"], root)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def classify_paths(paths: list[str]) -> dict[str, bool]:
    flags = {
        "provider_transformations": False,
        "transformation_flows": False,
        "ingestion": False,
        "go_api": False,
    }
    for p in paths:
        if PT_PATH.search(p):
            flags["provider_transformations"] = True
        if TF_PATH.search(p):
            flags["transformation_flows"] = True
        if INGEST_PATH.search(p) or INGEST_CI_PATH.search(p):
            flags["ingestion"] = True
        if GO_API_PATH.search(p):
            flags["go_api"] = True
    return flags


def classify_plan_text(text: str) -> dict[str, bool]:
    return {
        "provider_transformations": bool(PLAN_PT.search(text)),
        "transformation_flows": bool(PLAN_TF.search(text)),
        "ingestion": bool(PLAN_INGEST.search(text)),
        "go_api": bool(re.search(r"web-api|web-admin-api|route-impl", text, re.I)),
    }


def makefile_has_targets(root: Path) -> dict[str, bool]:
    mk = root / "services/provider-transformations/Makefile"
    text = mk.read_text(encoding="utf-8") if mk.is_file() else ""
    return {
        "test-local-engine": "test-local-engine" in text,
        "test-local-queue": "test-local-queue" in text,
        "test-local-metadata": "test-local-metadata" in text,
        "test-local-seal-handshake": "test-local-seal-handshake" in text,
        "test-local-all": "test-local-all" in text,
    }


def pt_tiers(root: Path, paths: list[str]) -> list[dict]:
    targets = makefile_has_targets(root)
    tiers: list[dict] = []
    cwd = "services/provider-transformations"
    if targets["test-local-engine"]:
        tiers.append({
            "id": "engine",
            "command": f"cd {cwd} && make test-local-engine",
            "needs_postgres": False,
            "description": "Promote/compact/vacuum/stats on file:// Delta",
        })
    else:
        tiers.append({
            "id": "engine",
            "command": "cargo test -p provider-transformations --test local_maintenance -- --nocapture",
            "needs_postgres": False,
            "description": "local_maintenance integration (Makefile fallback)",
        })
    if targets["test-local-queue"]:
        tiers.append({
            "id": "queue",
            "command": f"cd {cwd} && make test-local-queue",
            "needs_postgres": True,
            "description": "Queue metadata SQL admission_loop",
        })
    else:
        tiers.append({
            "id": "queue",
            "command": (
                "cargo test -p provider-transformations --test admission_loop "
                "upsert_compact_unit record_catalog_annotations_merges -- --nocapture"
            ),
            "needs_postgres": True,
            "description": "admission_loop contract (Makefile fallback)",
        })
    if targets["test-local-metadata"]:
        tiers.append({
            "id": "metadata",
            "command": f"cd {cwd} && make test-local-metadata",
            "needs_postgres": True,
            "description": "duroxide shell walking skeleton promote chain",
        })
    else:
        tiers.append({
            "id": "metadata",
            "command": (
                "cargo test -p provider-transformations --test duroxide_shell "
                "walking_skeleton_promote_records_catalog_annotations_and_enqueues_stats "
                "-- --nocapture"
            ),
            "needs_postgres": True,
            "description": "duroxide_shell (Makefile fallback)",
        })
    seal_in_diff = any(re.search(r"seal_handshake", p, re.I) for p in paths)
    seal_fixture = root / "services/provider-transformations/tests/seal_handshake.rs"
    if targets["test-local-seal-handshake"] and (seal_in_diff or seal_fixture.is_file()):
        tiers.append({
            "id": "seal-handshake",
            "command": f"cd {cwd} && make test-local-seal-handshake",
            "needs_postgres": True,
            "description": "Seal planning labels through duroxide promote",
        })
    return tiers


def tf_tiers(root: Path, paths: list[str]) -> list[dict]:
    tiers = [
        {
            "id": "pytest",
            "command": "cd services/transformation-flows && uv run pytest tests/ -x --timeout=120 -q",
            "needs_postgres": False,
            "description": "transformation-flows unit+integration pytest",
        },
    ]
    medallion = any(
        re.search(r"medallion|bronze_i|metadata_window|partition_discovery", p, re.I)
        for p in paths
    )
    if medallion:
        tiers.append({
            "id": "medallion-audit-dry-run",
            "command": (
                "cd services/transformation-flows && "
                "./scripts/run_daily_medallion_audits.sh --help"
            ),
            "needs_postgres": False,
            "description": "Verify medallion audit script available; scope clients in proof log",
            "note": "Run with --clients/--layers from plan when executing Stage 6.45",
        })
    return tiers


def ingest_tiers(root: Path) -> list[dict]:
    tiers: list[dict] = []
    contract = root / "scripts/ci/ingestion_sparse_checkout_test.py"
    if contract.is_file():
        tiers.append(
            {
                "id": "ingestion-ci-contract",
                "command": "python3 scripts/ci/ingestion_sparse_checkout_test.py",
                "needs_postgres": False,
                "description": (
                    "Sparse checkout, mypy overrides, Dockerfile OpenSSL CI contract"
                ),
            }
        )
    return tiers + [
        {
            "id": "ingestion-unit",
            "command": "cd services/ingestion && uv run pytest tests/unit/ -q",
            "needs_postgres": False,
            "description": "Ingestion engine unit tests",
        },
        {
            "id": "prove-200s",
            "command": "see references/ingestion-stage-details.md prove-200s",
            "needs_postgres": False,
            "description": "Direct API probe when Class C/D connector change",
            "manual": True,
        },
    ]


def go_tiers(service: str) -> list[dict]:
    return [
        {
            "id": "go-test",
            "command": f"cd services/{service} && go test ./...",
            "needs_postgres": False,
            "description": f"{service} full test packages",
        },
    ]


def build_tiers(flags: dict[str, bool], root: Path, paths: list[str]) -> list[dict]:
    tiers: list[dict] = []
    if flags.get("provider_transformations"):
        tiers.extend(pt_tiers(root, paths))
    if flags.get("transformation_flows"):
        tiers.extend(tf_tiers(root, paths))
    if flags.get("ingestion"):
        tiers.extend(ingest_tiers(root))
    if flags.get("go_api") and not tiers:
        for svc in ("web-api", "web-admin-api"):
            if any(svc in p for p in paths):
                tiers.extend(go_tiers(svc))
                break
        if not tiers:
            tiers.extend(go_tiers("web-api"))
    return tiers


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def docker_available() -> bool:
    try:
        return run(["docker", "info"], Path.cwd()).returncode == 0
    except FileNotFoundError:
        return False


DOCKER_ORCHESTRATION_DSN = (
    "postgres://postgres:postgres@localhost:5432/orchestration_dev?sslmode=disable"
)


def homebrew_orchestration_dsn() -> str:
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "postgres"
    return f"postgres://{user}@localhost:5432/orchestration_dev?sslmode=disable"


def probe_psql_dsn(dsn: str) -> bool:
    """Return True when psql can connect with this DSN."""
    if run(["which", "psql"], Path.cwd()).returncode != 0:
        return False
    proc = run(["psql", dsn, "-c", "SELECT 1"], Path.cwd())
    return proc.returncode == 0


def resolve_orchestration_dsn() -> dict:
    """Pick Docker vs Homebrew DSN by probing psql, not guessing."""
    docker = DOCKER_ORCHESTRATION_DSN
    homebrew = homebrew_orchestration_dsn()
    if probe_psql_dsn(docker):
        return {
            "dsn": docker,
            "flavor": "docker",
            "auth_ok": True,
            "export": f"export PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL='{docker}'",
        }
    if probe_psql_dsn(homebrew):
        return {
            "dsn": homebrew,
            "flavor": "homebrew",
            "auth_ok": True,
            "export": (
                "export PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL="
                f"'{homebrew}'"
            ),
        }
    return {
        "dsn": docker,
        "flavor": "unverified",
        "auth_ok": False,
        "export": f"export PROVIDER_TRANSFORMATIONS_SHELL_TEST_DATABASE_URL='{docker}'",
    }


def preflight_checks(needs_postgres: bool) -> dict:
    resolved = resolve_orchestration_dsn() if needs_postgres else None
    return {
        "docker_available": docker_available(),
        "postgres_port_open": port_open("127.0.0.1", 5432) if needs_postgres else None,
        "recommended_dsn": DOCKER_ORCHESTRATION_DSN,
        "homebrew_dsn_hint": homebrew_orchestration_dsn(),
        "resolved_dsn": resolved["dsn"] if resolved else None,
        "dsn_flavor": resolved["flavor"] if resolved else None,
        "postgres_auth_ok": resolved["auth_ok"] if resolved else None,
        "shell_test_export": resolved["export"] if resolved else None,
        "bootstrap_script": (
            "~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_bootstrap.py"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["preflight", "plan", "code"], required=True)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--plan", type=Path, default=None)
    parser.add_argument("--branch", default="")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root = repo_root()
    paths: list[str] = []
    flags: dict[str, bool] = {
        "provider_transformations": False,
        "transformation_flows": False,
        "ingestion": False,
        "go_api": False,
    }

    if args.mode == "code":
        paths = changed_files(args.base, root)
        flags = classify_paths(paths)
    elif args.mode == "plan" and args.plan and args.plan.is_file():
        text = args.plan.read_text(encoding="utf-8", errors="replace")
        flags = classify_plan_text(text)
        paths = re.findall(r"`([^`]+)`", text)
    elif args.mode == "preflight":
        branch = args.branch or run(["git", "branch", "--show-current"], root).stdout.strip()
        joined = branch.replace("-", " ")
        flags = {
            "provider_transformations": bool(BRANCH_PT.search(branch)),
            "transformation_flows": bool(BRANCH_TF.search(branch)),
            "ingestion": bool(re.search(r"ingestion|connector", branch, re.I)),
            "go_api": bool(re.search(r"web-api|web-admin", branch, re.I)),
        }
        flags = {k: flags[k] or classify_plan_text(joined)[k] for k in flags}
        if args.plan and args.plan.is_file():
            flags2 = classify_plan_text(args.plan.read_text(encoding="utf-8", errors="replace"))
            for k in flags:
                flags[k] = flags[k] or flags2[k]

    tiers = build_tiers(flags, root, paths)
    triggered = len(tiers) > 0
    needs_postgres = any(t.get("needs_postgres") for t in tiers)

    if not triggered:
        reason = "no_proof_routed_paths_in_diff_or_plan"
    else:
        active = [k for k, v in flags.items() if v]
        reason = f"proof_routed:{','.join(active)}"

    payload: dict = {
        "RUN_BY_SCRIPT": "proof_harness_gate.py",
        "mode": args.mode,
        "triggered": triggered,
        "reason": reason,
        "flags": flags,
        "tiers": tiers,
        "needs_postgres": needs_postgres,
    }

    if args.mode == "preflight":
        checks = preflight_checks(needs_postgres)
        checks["postgres_ready"] = (
            (checks["postgres_port_open"] and checks.get("postgres_auth_ok"))
            if needs_postgres
            else True
        )
        payload["preflight"] = checks
        if needs_postgres and not checks["postgres_ready"]:
            payload["warnings"] = [
                "Postgres not reachable on localhost:5432 — Stage 6.45 must run proof_harness_bootstrap.py"
            ]

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
