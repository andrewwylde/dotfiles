#!/usr/bin/env python3
"""Executable proof that ship-feature stage compliance + hook enforcement work.

Runs synthetic workspaces (no network/subagents) and asserts:
  - Incomplete planning blocks Stage 4 source edits via skill_gate
  - Full planning artifact chain passes stage4 and allows source edits
  - Partial Phase 6 blocks stage6-complete
  - pipeline_status detects all planning stages

Exit 0 when all cases pass; 1 on any failure.

Also see tests/test_parable_609_gates.py for PARABLE-609 campaign fail-closed cases
(implementation approval, visual sign-off, harness cleanup).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
COMPLIANCE = SKILL_ROOT / "scripts" / "stage_compliance_check.py"
PIPELINE_STATUS = SKILL_ROOT / "scripts" / "pipeline_status.py"
GATE = Path.home() / ".cursor/skills/_shared/skill_gate.py"
TASK = "prove-ship-stages"
PLAN = "plans/prove_ship_stages_ab12cd34.plan.md"


def run(cmd: list[str], cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != expect:
        raise AssertionError(
            f"{' '.join(cmd)} expected exit {expect}, got {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_workspace(base: Path) -> None:
    from datetime import datetime, timezone

    write(base / ".context" / ".active_skill", "ship-feature\n")
    session = {
        "task_id": TASK,
        "branch": "feature/prove-ship-stages",
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(base.resolve()),
    }
    write(base / ".context" / "ship-feature-session.json", json.dumps(session, indent=2) + "\n")
    write(
        base / ".context/vibetest/prove_ship_stages_2026-07-08.md",
        "# Vibe Test\n\n## Gaps\n\nProceed to planning.\n",
    )
    (base / "plans").mkdir(parents=True, exist_ok=True)
    (base / "services" / "demo").mkdir(parents=True, exist_ok=True)
    write(base / "services" / "demo" / "lib.rs", "// stub\n")


def gate_check(cwd: Path, action: str, file_path: str, expect_allowed: bool) -> None:
    proc = subprocess.run(
        ["python3", str(GATE), "check", "--skill", "ship-feature", "--action", action, "--file", file_path],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    allowed = proc.returncode == 0
    if allowed != expect_allowed:
        raise AssertionError(
            f"skill_gate {action} {file_path}: expected allowed={expect_allowed}, got {allowed}\n{proc.stdout}{proc.stderr}"
        )


def compliance(cwd: Path, gate: str, expect: int) -> None:
    cmd = ["python3", str(COMPLIANCE), "--gate", gate, "--task", TASK]
    run(cmd, cwd, expect=expect)


def write_full_stage4_artifacts(base: Path, *, stale_review: bool = False) -> None:
    now = time.time()
    plan_body = """RUN_BY_COMMAND: plan-create

# Prove Ship Stages

## Assumption Ledger
| ID | Assumption | Decision |
|----|------------|----------|
| A1 | test | use generated types |
"""
    write(base / PLAN, plan_body)
    review_body = """RUN_BY_COMMAND: plan-review

## Decision
READY TO EXECUTE

## Assumption Audit
All verified.
"""
    review_path = base / ".context/reviews/plan_prove_ship_stages_ab12cd34.md"
    write(review_path, review_body)
    adv = """RUN_BY_SKILL: de-adversarial-reviewer

## Decision
APPROVE WITH CONDITIONS
"""
    write(base / ".context/adversarial/adversarial_prove_ship_stages_ab12cd34.md", adv)
    bench = """RUN_BY_SKILL: test-benchmark

## Score
Score: 8/10

Plan-level benchmark.
"""
    write(base / ".context/test-benchmarks/prove_ship_stages_plan-level.md", bench)
    write(
        base / ".context/psgen-gate-plan.json",
        json.dumps({"triggered": False, "mode": "plan", "reason": "no schema"}) + "\n",
    )
    write(
        base / ".context/scalar-lib-gate-plan.json",
        json.dumps({"triggered": False, "mode": "plan", "reason": "no scalar"}) + "\n",
    )
    write(
        base / ".context/deferrals/prove-ship-stages_deferrals.md",
        "RUN_BY_SKILL: ship-feature\n\nNo approved deferrals.\n",
    )
    if stale_review:
        plan_path = base / PLAN
        plan_path.touch()
        import os

        os.utime(plan_path, (now + 10, now + 10))


def write_full_stage6_artifacts(base: Path) -> None:
    pr_review = """RUN_BY_COMMAND: pr-review-local

## Summary
Review complete.

## Findings
None blocking.

Stage 6.45 PASS
Stage 6.5 PASS
Stage 6.6 PASS
Stage 6.65 PASS
Stage 6.7 PASS
"""
    write(base / ".context/prs/reviews/PR_REVIEW_prove_ship_stages_9999.md", pr_review)
    write(
        base / ".context/proof-harness-gate.json",
        json.dumps({"triggered": False, "reason": "not routed"}) + "\n",
    )
    write(
        base / ".context/rust-cognitive-complexity-gate.json",
        json.dumps({"triggered": False}) + "\n",
    )
    write(
        base / ".context/psgen-gate-code.json",
        json.dumps({"triggered": False, "mode": "code"}) + "\n",
    )
    write(
        base / ".context/scalar-lib-gate-code.json",
        json.dumps({"triggered": False, "mode": "code"}) + "\n",
    )
    write(
        base / ".context/test-benchmarks/prove_ship_stages_code-level.md",
        "RUN_BY_SKILL: test-benchmark\n\nCode-level score: 8/10\n",
    )


def case_incomplete_planning_blocks_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write(
            base / PLAN,
            "RUN_BY_COMMAND: plan-create\n\n# Plan\n\n## Assumption Ledger\n| A1 | x | y |\n",
        )
        compliance(base, "stage4", expect=1)
        gate_check(base, "strreplace", "services/demo/lib.rs", expect_allowed=False)


def case_stale_review_blocks_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage4_artifacts(base, stale_review=True)
        compliance(base, "stage4", expect=1)
        gate_check(base, "write", "services/demo/lib.rs", expect_allowed=False)


def case_full_planning_allows_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage4_artifacts(base)
        compliance(base, "stage4", expect=0)
        gate_check(base, "strreplace", "services/demo/lib.rs", expect_allowed=True)


def case_missing_stage375_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage4_artifacts(base)
        (base / ".context/test-benchmarks/prove_ship_stages_plan-level.md").unlink()
        compliance(base, "stage4", expect=1)


def case_stage6_incomplete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage4_artifacts(base)
        write(
            base / ".context/prs/reviews/PR_REVIEW_prove_ship_stages_9999.md",
            "RUN_BY_COMMAND: pr-review-local\n\n## Summary\npartial\n",
        )
        compliance(base, "stage6-complete", expect=1)


def case_stage6_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage6_artifacts(base)
        compliance(base, "stage6-complete", expect=0)


def case_pipeline_status_lists_planning_stages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        write_full_stage4_artifacts(base)
        proc = subprocess.run(
            ["python3", str(PIPELINE_STATUS), "--branch", "feature/prove-ship-stages"],
            cwd=base,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(f"pipeline_status failed: {proc.stderr}")
        # JSON on stdout
        data = json.loads(proc.stdout)
        found = {a["name"]: a["found"] for a in data["artifacts"]}
        required = [
            "plan",
            "plan-review",
            "DE adversarial",
            "test benchmark (plan-level)",
            "psgen (plan)",
            "scalar-lib-it (plan)",
            "deferral register",
        ]
        missing = [name for name in required if not found.get(name)]
        if missing:
            raise AssertionError(f"pipeline_status missing stages: {missing}\nfound={found}")


def case_delegation_window_blocks_orchestrator_synthesis() -> None:
    """Harness-first: orchestrator cannot write plan review without delegation window."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        review_path = ".context/reviews/plan_prove_ship_stages_ab12cd34.md"
        gate_check(base, "write", review_path, expect_allowed=False)
        # Open delegation window — subagent path allowed
        run(
            ["python3", str(SKILL_ROOT / "scripts/delegation_window.py"), "begin", "--stage", "plan-review"],
            base,
        )
        gate_check(base, "write", review_path, expect_allowed=True)
        run(["python3", str(SKILL_ROOT / "scripts/delegation_window.py"), "end"], base)
        gate_check(base, "write", review_path, expect_allowed=False)


def case_harness_recovery_returns_delegation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        init_workspace(base)
        proc = subprocess.run(
            ["python3", str(SKILL_ROOT / "scripts/harness_recovery.py"), "--gate", "stage4", "--format", "json"],
            cwd=base,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            raise AssertionError("expected stage4 recovery to fail on empty workspace")
        data = json.loads(proc.stdout)
        if data.get("status") != "BLOCKED" or "recovery" not in data:
            raise AssertionError(f"unexpected recovery payload: {proc.stdout}")
        if data["recovery"].get("action_type") not in ("delegation", "orchestrator_script", "orchestrator_write", "unknown"):
            raise AssertionError(f"bad action_type: {data['recovery']}")


def main() -> int:
    cases = [
        ("incomplete_planning_blocks_source", case_incomplete_planning_blocks_source),
        ("stale_review_blocks_source", case_stale_review_blocks_source),
        ("full_planning_allows_source", case_full_planning_allows_source),
        ("missing_stage375_detected", case_missing_stage375_detected),
        ("stage6_incomplete", case_stage6_incomplete),
        ("stage6_complete", case_stage6_complete),
        ("pipeline_status_lists_planning_stages", case_pipeline_status_lists_planning_stages),
        ("delegation_window_blocks_orchestrator_synthesis", case_delegation_window_blocks_orchestrator_synthesis),
        ("harness_recovery_returns_delegation", case_harness_recovery_returns_delegation),
    ]
    failed: list[str] = []
    for name, fn in cases:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as exc:  # noqa: BLE001 — aggregate proof failures
            print(f"FAIL  {name}: {exc}")
            failed.append(name)
    if failed:
        print(f"\nPROVE FAILED: {len(failed)}/{len(cases)} cases")
        return 1
    print(f"\nPROVE OK: all {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
