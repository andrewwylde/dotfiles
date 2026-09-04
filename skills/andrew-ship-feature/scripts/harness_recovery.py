#!/usr/bin/env python3
"""Harness-first recovery router for /ship-feature.

On any compliance or hook failure, returns the ONE next action the orchestrator
must take — usually a delegated slash command, sometimes an orchestrator-run
gate script.

PARABLE-609 campaign exception: checks whose action_type is `human_pause` are
NOT auto-recoverable. Stop and present the approval prompt to the user.

Usage:
  python3 harness_recovery.py --gate stage4 [--task TASK]
  python3 harness_recovery.py --gate stage5-pr [--task TASK]
  python3 harness_recovery.py --gate stage6-complete [--pr N]
  python3 harness_recovery.py --from-check plan-review-fresh [--plan PATH]
  python3 harness_recovery.py --gate auto   # picks stage4 vs stage6 from workspace
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

COMPLIANCE = Path(__file__).resolve().parent / "stage_compliance_check.py"


@dataclass
class RecoveryAction:
    check: str
    action_type: str  # delegation | orchestrator_script | orchestrator_write | human_pause
    stage: str
    prompt: str
    verify: str
    max_cycles: int = 3

    def to_dict(self) -> dict:
        return asdict(self)


# Map compliance check names -> recovery (harness-first: objective pass/fail + fix command)
RECOVERY_BY_CHECK: dict[str, RecoveryAction] = {
    "plan": RecoveryAction(
        "plan",
        "delegation",
        "plan-create",
        "Delegate Stages 1+2: subagent runs /plan-create then /plan-review (see Command Delegation Protocol)",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "plan-provenance": RecoveryAction(
        "plan-provenance",
        "delegation",
        "plan-create",
        "Re-delegate /plan-create — orchestrator must not write plans/*.plan.md directly",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "plan-review": RecoveryAction(
        "plan-review",
        "delegation",
        "plan-review",
        "/plan-review plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "plan-review-provenance": RecoveryAction(
        "plan-review-provenance",
        "delegation",
        "plan-review",
        "Re-delegate /plan-review — artifact must include RUN_BY_COMMAND: plan-review",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "plan-review-ready": RecoveryAction(
        "plan-review-ready",
        "delegation",
        "plan-update",
        "/plan-update plans/<plan-file>.plan.md --from-review .context/reviews/plan_<name>.md",
        "Then re-delegate /plan-review; run stage_compliance_check --gate stage3-after-update",
    ),
    "plan-review-fresh": RecoveryAction(
        "plan-review-fresh",
        "delegation",
        "plan-update",
        "/plan-update plans/<plan-file>.plan.md --from-review .context/reviews/plan_<name>.md",
        "Then re-delegate /plan-review (two subagents, same turn sequence)",
    ),
    "plan-review-after-update": RecoveryAction(
        "plan-review-after-update",
        "delegation",
        "plan-review",
        "/plan-review plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage3-after-update --plan <plan>",
    ),
    "plan-update-provenance": RecoveryAction(
        "plan-update-provenance",
        "delegation",
        "plan-update",
        "/plan-update plans/<plan-file>.plan.md --from-review .context/reviews/plan_<name>.md",
        "Then re-delegate /plan-review",
    ),
    "adversarial": RecoveryAction(
        "adversarial",
        "delegation",
        "de-adversarial-reviewer",
        "/de-adversarial-reviewer plan-gate plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "adversarial-provenance": RecoveryAction(
        "adversarial-provenance",
        "delegation",
        "de-adversarial-reviewer",
        "Re-delegate /de-adversarial-reviewer plan-gate plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "adversarial-approve": RecoveryAction(
        "adversarial-approve",
        "delegation",
        "plan-update",
        "/plan-update plans/<plan-file>.plan.md to address BLOCK/conditions, then re-run 3.5",
        "Re-delegate /de-adversarial-reviewer after plan-update + plan-review cycle",
    ),
    "plan-benchmark": RecoveryAction(
        "plan-benchmark",
        "delegation",
        "test-benchmark-plan",
        "/test-benchmark plan plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "plan-benchmark-provenance": RecoveryAction(
        "plan-benchmark-provenance",
        "delegation",
        "test-benchmark-plan",
        "Re-delegate /test-benchmark plan plans/<plan-file>.plan.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "psgen-plan-gate": RecoveryAction(
        "psgen-plan-gate",
        "orchestrator_script",
        "psgen-gate-plan",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/psgen_gate.py --mode plan --out .context/psgen-gate-plan.json",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "scalar-plan-gate": RecoveryAction(
        "scalar-plan-gate",
        "orchestrator_script",
        "scalar-lib-gate-plan",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/scalar_lib_gate.py --mode plan --out .context/scalar-lib-gate-plan.json",
        "If triggered: delegate /scalar-lib-it Design; else re-run stage4 compliance",
    ),
    "deferral-register": RecoveryAction(
        "deferral-register",
        "orchestrator_write",
        "deferral-adjudication",
        "Orchestrator: Stage 3.5b deferral adjudication -> .context/deferrals/{task-id}_deferrals.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "deferral-provenance": RecoveryAction(
        "deferral-provenance",
        "orchestrator_write",
        "deferral-adjudication",
        "Rewrite deferral register with RUN_BY_SKILL: ship-feature header",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "campaign-context": RecoveryAction(
        "campaign-context",
        "orchestrator_script",
        "campaign-context",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/campaign_context_gate.py --ticket <TICKET> --workspace .",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task <task-id>",
    ),
    "reference-baseline": RecoveryAction(
        "reference-baseline",
        "orchestrator_script",
        "visual-baseline",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py --mode baseline --ticket <TICKET>",
        "Ensure https://local.parable.work:5300/admin/ponder is up, then re-validate baseline",
    ),
    "reference-audit": RecoveryAction(
        "reference-audit",
        "orchestrator_write",
        "reference-audit",
        "Inspect ponder-admin reference paths; fill reference-audit.md (preserve|migrate|discard)",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/reference_audit_gate.py --ticket <TICKET> --validate",
    ),
    "implementation-approval": RecoveryAction(
        "implementation-approval",
        "human_pause",
        "3.9",
        "STOP: present plan + reference audit + baseline. Wait for user: APPROVE IMPLEMENTATION <TICKET>",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py --kind implementation --ticket <TICKET> --validate",
    ),
    "visual-after": RecoveryAction(
        "visual-after",
        "orchestrator_script",
        "4.8",
        "Run faithful local harness, capture after proof, cleanup harness from repo diff",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py --mode after --ticket <TICKET> --validate --head-sha $(git rev-parse HEAD)",
    ),
    "visual-approval": RecoveryAction(
        "visual-approval",
        "human_pause",
        "4.9",
        "STOP: present before/after visual proof. Wait for user: APPROVE VISUAL QA <TICKET>",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py --kind visual-qa --ticket <TICKET> --validate",
    ),
    "visual-harness-cleanup": RecoveryAction(
        "visual-harness-cleanup",
        "orchestrator_write",
        "4.8-cleanup",
        "Delete ephemeral harness/screenshot files from the branch; keep proof under ~/.cursor/ship-feature-state/",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py --mode cleanup-check --workspace .",
    ),
    "schema-persistence-ack": RecoveryAction(
        "schema-persistence-ack",
        "orchestrator_write",
        "4.7-schema-ack",
        "Write .context/schema-persistence-ack.json with ticket, decision "
        "(none|same_pr_schema|stacked_schema), and rationale. For persistence-shaped "
        "UI (runs/snapshots), land thin web-db schema on the PR or bump schema_tier.",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage5-pr --task <TICKET>",
    ),
    "pr-review": RecoveryAction(
        "pr-review",
        "delegation",
        "pr-review-local",
        "/pr-review-local <PR_NUMBER>",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    ),
    "pr-review-provenance": RecoveryAction(
        "pr-review-provenance",
        "delegation",
        "pr-review-local",
        "Re-delegate /pr-review-local <PR_NUMBER> — no inline review synthesis",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    ),
    "proof-gate-json": RecoveryAction(
        "proof-gate-json",
        "orchestrator_script",
        "proof-harness-gate",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/proof_harness_gate.py --mode code --out .context/proof-harness-gate.json",
        "Run AFTER /pr-review-local artifact exists; then execute tiers if triggered",
    ),
    "proof-tiers-executed": RecoveryAction(
        "proof-tiers-executed",
        "orchestrator_script",
        "proof-harness-tiers",
        "Orchestrator: run proof tiers + bootstrap (proof_harness_bootstrap.py); log to .context/implementation/proof-harness-log.md",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    ),
    "code-benchmark": RecoveryAction(
        "code-benchmark",
        "delegation",
        "test-benchmark-code",
        "/test-benchmark <PR_NUMBER>",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    ),
    "rust-complexity-gate": RecoveryAction(
        "rust-complexity-gate",
        "orchestrator_script",
        "rust-complexity",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/rust_cognitive_complexity_gate.py --base origin/main | tee .context/rust-cognitive-complexity-gate.json",
        "If triggered: delegate /code-simplifier then re-run gate",
    ),
    "psgen-code-gate": RecoveryAction(
        "psgen-code-gate",
        "orchestrator_script",
        "psgen-gate-code",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/psgen_gate.py --mode code --base origin/main --out .context/psgen-gate-code.json",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    ),
    "scalar-code-gate": RecoveryAction(
        "scalar-code-gate",
        "orchestrator_script",
        "scalar-lib-gate-code",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/scalar_lib_gate.py --mode code --base origin/main --out .context/scalar-lib-gate-code.json",
        "If triggered: delegate /scalar-lib-it code",
    ),
}

# Phase 6 PR review section checks
for section in ("stage-6.45", "stage-6.5", "stage-6.6", "stage-6.65", "stage-6.7"):
    key = f"pr-review-{section}"
    RECOVERY_BY_CHECK[key] = RecoveryAction(
        key,
        "orchestrator_write",
        "pr-review-append",
        f"Append {section.replace('-', ' ').upper()} harness results to PR review artifact",
        "python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage6-complete --pr <N>",
    )

DELEGATED_ARTIFACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("plan-create", re.compile(r"^plans/[^/]+\.plan\.md$")),
    ("plan-update", re.compile(r"^plans/[^/]+\.plan\.md$")),
    ("plan-review", re.compile(r"^\.context/reviews/plan_.+\.md$")),
    ("de-adversarial-reviewer", re.compile(r"^\.context/adversarial/adversarial_.+\.md$")),
    ("de-adversarial-reviewer", re.compile(r"^\.context/reviews/adversarial_.+\.md$")),
    ("test-benchmark-plan", re.compile(r"^\.context/test-benchmarks/.+_plan-level\.md$")),
    ("test-benchmark-code", re.compile(r"^\.context/test-benchmarks/.+_code-level\.md$")),
    ("pr-review-local", re.compile(r"^\.context/prs/reviews/PR_REVIEW_.+\.md$")),
    ("scalar-lib-it-plan", re.compile(r"^\.context/scalar-lib-audits/.+_design\.md$")),
    ("scalar-lib-it-code", re.compile(r"^\.context/scalar-lib-audits/.+_code\.md$")),
]

DELEGATION_BLOCKED_RECOVERY = RecoveryAction(
    "delegated-artifact-without-window",
    "delegation",
    "<stage>",
    "Run: python3 ~/.cursor/skills/andrew-ship-feature/scripts/delegation_window.py begin --stage <stage>",
    "Then Task(subagent) with prompt ONLY the slash command; then delegation_window.py end",
)


def normalize_path(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def delegation_stages_for_path(path: str) -> list[str]:
    p = normalize_path(path)
    stages: list[str] = []
    for stage, pattern in DELEGATED_ARTIFACT_PATTERNS:
        if pattern.match(p) and stage not in stages:
            stages.append(stage)
    return stages


def run_compliance(gate: str, task_id: str | None, pr: int | None) -> tuple[int, list[dict]]:
    cmd = ["python3", str(COMPLIANCE), "--gate", gate, "--json"]
    if task_id and gate == "stage4":
        cmd.extend(["--task", task_id])
    if pr and gate == "stage6-complete":
        cmd.extend(["--pr", str(pr)])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
        return proc.returncode, payload.get("checks", [])
    except json.JSONDecodeError:
        return proc.returncode, []


def load_task_id(workspace: Path) -> str | None:
    session = workspace / ".context/ship-feature-session.json"
    if not session.is_file():
        return None
    try:
        return json.loads(session.read_text()).get("task_id")
    except (json.JSONDecodeError, OSError):
        return None


def first_failed_recovery(checks: list[dict]) -> RecoveryAction | None:
    for check in checks:
        if check.get("passed"):
            continue
        name = check.get("name", "")
        if name in RECOVERY_BY_CHECK:
            action = RECOVERY_BY_CHECK[name]
            return RecoveryAction(
                action.check,
                action.action_type,
                action.stage,
                check.get("recovery") or action.prompt,
                action.verify,
                action.max_cycles,
            )
        recovery_text = check.get("recovery") or check.get("detail", "Complete missing stage")
        return RecoveryAction(name, "unknown", name, recovery_text, f"Re-run compliance for {name}")
    return None


def recovery_for_delegation_block(path: str) -> RecoveryAction:
    stages = delegation_stages_for_path(path)
    stage = stages[0] if stages else "plan-review"
    action = RECOVERY_BY_CHECK.get(
        {
            "plan-create": "plan-provenance",
            "plan-update": "plan-update-provenance",
            "plan-review": "plan-review-provenance",
            "de-adversarial-reviewer": "adversarial-provenance",
            "test-benchmark-plan": "plan-benchmark-provenance",
            "test-benchmark-code": "code-benchmark",
            "pr-review-local": "pr-review-provenance",
        }.get(stage, "plan-review"),
        DELEGATION_BLOCKED_RECOVERY,
    )
    begin = f"python3 ~/.cursor/skills/andrew-ship-feature/scripts/delegation_window.py begin --stage {stage}"
    prompt = action.prompt if action.prompt.startswith("/") else f"/{stage.replace('-plan','').replace('-code','')} ..."
    return RecoveryAction(
        "delegated-artifact-blocked",
        "delegation",
        stage,
        f"{begin}\nThen delegate subagent prompt ONLY: {prompt}\nThen: python3 ~/.cursor/skills/andrew-ship-feature/scripts/delegation_window.py end",
        action.verify,
    )


def emit_text(action: RecoveryAction, gate: str) -> None:
    print("HARNESS_RECOVERY")
    print(f"gate: {gate}")
    print(f"failed_check: {action.check}")
    print(f"action_type: {action.action_type}")
    print(f"delegation_stage: {action.stage}")
    print(f"next_action: {action.prompt}")
    print(f"verify: {action.verify}")
    print(f"max_self_heal_cycles: {action.max_cycles}")
    print("")
    print("SELF_HEAL_LOOP: execute next_action -> verify -> repeat until PASS (no user prompt)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", default="auto", choices=["auto", "stage4", "stage5-pr", "stage3-after-update", "stage6-complete"])
    parser.add_argument("--task")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--from-check")
    parser.add_argument("--blocked-path", help="Path that triggered delegation-window block")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    workspace = Path.cwd()
    task_id = args.task or load_task_id(workspace)

    if args.blocked_path:
        action = recovery_for_delegation_block(args.blocked_path)
        if args.format == "json":
            print(json.dumps({"gate": "delegation-window", "recovery": action.to_dict()}, indent=2))
        else:
            emit_text(action, "delegation-window")
        return 0

    if args.from_check:
        action = RECOVERY_BY_CHECK.get(args.from_check)
        if not action:
            print(json.dumps({"error": f"unknown check {args.from_check}"}))
            return 1
        if args.format == "json":
            print(json.dumps({"recovery": action.to_dict()}, indent=2))
        else:
            emit_text(action, args.from_check)
        return 0

    gate = args.gate
    if gate == "auto":
        code4, checks4 = run_compliance("stage4", task_id, None)
        if code4 != 0:
            gate = "stage4"
            checks = checks4
        else:
            code6, checks6 = run_compliance("stage6-complete", task_id, args.pr)
            if code6 != 0:
                gate = "stage6-complete"
                checks = checks6
            else:
                ok = {"gate": "auto", "status": "PASS", "message": "All compliance checks pass"}
                print(json.dumps(ok, indent=2) if args.format == "json" else "HARNESS_OK: all compliance gates pass")
                return 0
    elif gate == "stage3-after-update":
        cmd = ["python3", str(COMPLIANCE), "--gate", "stage3-after-update", "--json"]
        if args.plan:
            cmd.extend(["--plan", str(args.plan)])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        try:
            payload = json.loads(proc.stdout)
            checks = payload.get("checks", [])
        except json.JSONDecodeError:
            checks = []
    else:
        _, checks = run_compliance(gate, task_id, args.pr)

    action = first_failed_recovery(checks)
    if not action:
        print(json.dumps({"gate": gate, "status": "PASS"}) if args.format == "json" else f"HARNESS_OK: {gate} passes")
        return 0

    if args.format == "json":
        print(json.dumps({"gate": gate, "status": "BLOCKED", "recovery": action.to_dict(), "checks": checks}, indent=2))
    else:
        emit_text(action, gate)
    return 1


if __name__ == "__main__":
    sys.exit(main())
