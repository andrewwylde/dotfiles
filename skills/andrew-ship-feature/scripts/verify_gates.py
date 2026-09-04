#!/usr/bin/env python3
"""Verify ship-feature gate scripts (psgen, scalar-lib, rust complexity, pipeline_status).

Smoke harness for CI and local preflight. Runs gate scripts against stub inputs
and asserts expected trigger/skip behavior on skill-only diffs.

Usage (from repo root):
  python3 .claude/skills/ship-feature/scripts/verify_gates.py
  python3 ~/.cursor/skills/andrew-ship-feature/scripts/verify_gates.py \\
    --out .context/ship-feature-gate-verify.json

Exit 0 when all checks pass; 1 on failure.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"not a git repo: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def run_json(cmd: list[str], cwd: Path) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def assert_eq(name: str, got: object, expected: object) -> None:
    if got != expected:
        raise AssertionError(f"{name}: got {got!r}, expected {expected!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default="origin/main",
        help="Git diff base for code-mode gate checks (default: origin/main)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON report to this path (default: stdout only)",
    )
    args = parser.parse_args()

    root = repo_root()
    errors: list[str] = []
    results: list[dict] = []

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".plan.md",
        delete=False,
        encoding="utf-8",
    ) as plan_file:
        plan_file.write(
            "# Add endpoint in platform-schemas/services/web-api\n"
            "Run make build-schemas and use @parable-platform/web-api-sdk\n"
        )
        plan_stub = Path(plan_file.name)

    try:
        checks: list[tuple[str, Callable[[], dict]]] = [
            (
                "psgen-plan-no-file",
                lambda: run_json(
                    ["python3", str(SCRIPTS / "psgen_gate.py"), "--mode", "plan"],
                    root,
                ),
            ),
            (
                "psgen-plan-triggered",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "psgen_gate.py"),
                        "--mode",
                        "plan",
                        "--plan",
                        str(plan_stub),
                    ],
                    root,
                ),
            ),
            (
                "psgen-code-skill-only",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "psgen_gate.py"),
                        "--mode",
                        "code",
                        "--base",
                        args.base,
                    ],
                    root,
                ),
            ),
            (
                "scalar-plan-skip",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "scalar_lib_gate.py"),
                        "--mode",
                        "plan",
                        "--plan",
                        str(plan_stub),
                    ],
                    root,
                ),
            ),
            (
                "scalar-code-skill-only",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "scalar_lib_gate.py"),
                        "--mode",
                        "code",
                        "--base",
                        args.base,
                    ],
                    root,
                ),
            ),
            (
                "rust-complexity-skip",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "rust_cognitive_complexity_gate.py"),
                        "--base",
                        args.base,
                    ],
                    root,
                ),
            ),
            (
                "ingestion-preflight-json",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "ingestion_stage5_preflight.py"),
                        "--base",
                        args.base,
                    ],
                    root,
                ),
            ),
            (
                "proof-harness-preflight",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "proof_harness_gate.py"),
                        "--mode",
                        "preflight",
                        "--branch",
                        "docs/readme-only",
                    ],
                    root,
                ),
            ),
            (
                "proof-harness-code",
                lambda: run_json(
                    [
                        "python3",
                        str(SCRIPTS / "proof_harness_gate.py"),
                        "--mode",
                        "code",
                        "--base",
                        args.base,
                    ],
                    root,
                ),
            ),
        ]

        for name, fn in checks:
            try:
                payload = fn()
                results.append({"name": name, "passed": True, "payload": payload})
            except Exception as exc:  # noqa: BLE001 — harness aggregates failures
                results.append({"name": name, "passed": False, "error": str(exc)})
                errors.append(f"{name}: {exc}")

        by_name = {r["name"]: r for r in results if r.get("passed")}
        expectations = [
            ("psgen-plan-no-file triggered", "psgen-plan-no-file", "triggered", False),
            ("psgen-plan-triggered", "psgen-plan-triggered", "triggered", True),
            ("psgen-code-skill-only", "psgen-code-skill-only", "triggered", False),
            ("scalar-plan-skip", "scalar-plan-skip", "triggered", False),
            ("scalar-code-skill-only", "scalar-code-skill-only", "triggered", False),
            ("rust-complexity-skip", "rust-complexity-skip", "triggered", False),
            ("proof-harness-preflight", "proof-harness-preflight", "triggered", False),
            ("proof-harness-code", "proof-harness-code", "triggered", False),
        ]
        for label, key, field, expected in expectations:
            if key not in by_name:
                continue
            try:
                assert_eq(label, by_name[key]["payload"][field], expected)
            except AssertionError as exc:
                errors.append(str(exc))

        ingestion_ref = SKILL_ROOT / "references/ingestion-stage-details.md"
        if not ingestion_ref.is_file():
            errors.append(f"missing reference: {ingestion_ref}")
        else:
            text = ingestion_ref.read_text(encoding="utf-8")
            for needle in (
                "Class E",
                "ingestion_stage5_preflight.py",
                "ingestion_sparse_checkout_test.py",
            ):
                if needle not in text:
                    errors.append(f"ingestion-stage-details.md missing: {needle}")

        psgen_ref = SKILL_ROOT / "references/psgen-stage-details.md"
        if not psgen_ref.is_file():
            errors.append(f"missing reference: {psgen_ref}")
        else:
            text = psgen_ref.read_text(encoding="utf-8")
            for needle in (
                "make build-scalar-lib",
                "make build-schemas",
                "typecheck-psgen-toolchain",
                "Stage 3.7",
                "Stage 6.65",
            ):
                if needle not in text:
                    errors.append(f"psgen-stage-details.md missing: {needle}")

        proof_ref = SKILL_ROOT / "references/proof-harness-stage-details.md"
        if not proof_ref.is_file():
            errors.append(f"missing reference: {proof_ref}")

        status = subprocess.run(
            ["python3", str(SCRIPTS / "pipeline_status.py")],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = status.stdout + status.stderr
        if "Stage 3.7" not in combined or "Stage 6.65" not in combined:
            errors.append("pipeline_status missing Stage 3.7 or 6.65")

        prove = subprocess.run(
            ["python3", str(SCRIPTS / "stage_compliance_prove.py")],
            capture_output=True,
            text=True,
        )
        results.append({
            "name": "stage-compliance-prove",
            "passed": prove.returncode == 0,
            "payload": {"exit_code": prove.returncode},
        })
        if prove.returncode != 0:
            errors.append(f"stage_compliance_prove failed:\n{prove.stdout}\n{prove.stderr}")
    finally:
        plan_stub.unlink(missing_ok=True)

    report = {
        "passed": not errors and all(r["passed"] for r in results),
        "checks": results,
        "errors": errors,
        "skill_root": str(SKILL_ROOT),
        "repo_root": str(root),
    }
    text = json.dumps(report, indent=2) + "\n"
    print(text, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
