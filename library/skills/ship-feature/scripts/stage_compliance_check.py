#!/usr/bin/env python3
"""Fail-closed compliance checks for /ship-feature stage sequencing and delegation.

Orchestrator MUST run this script before Stage 4 entry and before declaring
pipeline complete. Exit 0 = all checks pass; exit 1 = blocked with reasons.

Usage:
  python3 stage_compliance_check.py --gate stage4 [--task TASK_ID]
  python3 stage_compliance_check.py --gate stage6-complete [--pr PR_NUMBER]
  python3 stage_compliance_check.py --gate stage3-after-update [--plan PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from parable_609_paths import (  # type: ignore
        extract_ticket,
        is_campaign_child,
        load_manifest,
        normalize_ticket,
        read_json,
        state_dir,
    )
    from approval_gate import approval_path, validate_payload, hashes_still_match  # type: ignore
    from reference_audit_gate import validate as validate_reference_audit  # type: ignore
    from visual_qa_gate import validate_after, validate_baseline, cleanup_check  # type: ignore
    from parable_609_paths import sha256_file  # type: ignore

    CAMPAIGN_GATES_AVAILABLE = True
except ImportError:
    CAMPAIGN_GATES_AVAILABLE = False


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    recovery: str = ""


def recovery_for(name: str, detail: str) -> str:
    """Lazy import to avoid circular deps at module load."""
    try:
        from harness_recovery import RECOVERY_BY_CHECK

        action = RECOVERY_BY_CHECK.get(name)
        if action:
            return action.prompt
    except ImportError:
        # harness_recovery optional at import time — fall back to detail string.
        pass
    return detail


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"__READ_ERROR__:{exc}"


def has_marker(content: str, marker: str) -> bool:
    return marker.lower() in content.lower()


def task_matches(path: Path, task_id: str | None) -> bool:
    if not task_id:
        return True
    normalized = task_id.lower().replace("-", "_")
    name = path.name.lower().replace("-", "_")
    words = {w for w in normalized.split("_") if len(w) > 2}
    overlap = words & set(name.split("_"))
    return normalized in name or len(overlap) >= 2


def find_plan(task_id: str | None) -> Path | None:
    plans = sorted(Path("plans").glob("*.plan.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for plan in plans:
        if task_matches(plan, task_id):
            return plan
    return None


def find_plan_review(plan: Path | None, task_id: str | None) -> Path | None:
    if plan is None:
        return None
    stem = plan.stem.replace(".plan", "")
    reviews = sorted(Path(".context/reviews").glob("plan_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for review in reviews:
        if stem in review.name and task_matches(review, task_id):
            return review
    return None


def find_adversarial(plan: Path | None, task_id: str | None) -> Path | None:
    if plan is None:
        return None
    stem = plan.stem.replace(".plan", "")
    candidates = list(Path(".context/adversarial").glob("adversarial_*.md"))
    candidates += list(Path(".context/reviews").glob("adversarial_*.md"))
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        if stem in path.name and task_matches(path, task_id):
            return path
    return None


def find_plan_benchmark(task_id: str | None) -> Path | None:
    candidates = sorted(
        Path(".context/test-benchmarks").glob("*_plan-level.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if task_matches(path, task_id):
            return path
    return None


def find_deferral(task_id: str | None) -> Path | None:
    candidates = sorted(Path(".context/deferrals").glob("*_deferrals.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        if task_matches(path, task_id):
            return path
    return None


def find_pr_review(pr_number: int | None, task_id: str | None) -> Path | None:
    if pr_number:
        for pattern in (f"PR_REVIEW_#{pr_number}.md", f"PR_REVIEW_{pr_number}.md"):
            candidate = Path(".context/prs/reviews") / pattern
            if candidate.is_file():
                return candidate
        return None
    candidates = sorted(
        Path(".context/prs/reviews").glob("PR_REVIEW_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if task_id:
        for path in candidates:
            if task_matches(path, task_id):
                return path
        return None
    if len(candidates) == 1:
        return candidates[0]
    return None


def resolve_campaign_ticket(task_id: str | None) -> str | None:
    if not CAMPAIGN_GATES_AVAILABLE:
        return None
    ticket = extract_ticket(task_id or "")
    if ticket:
        return ticket
    session = Path(".context/ship-feature-session.json")
    if session.is_file():
        try:
            data = json.loads(session.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        ticket = extract_ticket(
            str(data.get("task_id", "")),
            str(data.get("task_description", "")),
            str(data.get("branch", "")),
            str(data.get("campaign_ticket", "")),
        )
        if ticket:
            return ticket
    gate = Path(".context/campaign-gate.json")
    if gate.is_file():
        try:
            data = json.loads(gate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if data.get("ticket"):
            return normalize_ticket(str(data["ticket"]))
    return None


def campaign_triggered(task_id: str | None) -> tuple[bool, str | None]:
    if not CAMPAIGN_GATES_AVAILABLE:
        return False, None
    ticket = resolve_campaign_ticket(task_id)
    gate_path = Path(".context/campaign-gate.json")
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            gate = {}
        if gate.get("triggered") is False:
            return False, ticket
        if gate.get("triggered") is True:
            return True, normalize_ticket(str(gate.get("ticket") or ticket or ""))
    if is_campaign_child(ticket):
        return True, ticket
    return False, ticket


def check_schema_persistence_ack(ticket: str) -> list[Check]:
    """schema_tier 0 children must ack how persistence-shaped UI types are handled."""
    checks: list[Check] = []
    if not CAMPAIGN_GATES_AVAILABLE:
        checks.append(Check("schema-persistence-ack", True, "campaign helpers unavailable; skipped"))
        return checks

    try:
        from campaign_paths import children_meta as _children_meta, resolve_campaign

        resolved = resolve_campaign(ticket)
        if not resolved:
            manifest = load_manifest()
            meta = (manifest.get("children_meta") or {}).get(ticket) or {}
        else:
            meta = _children_meta(ticket, resolved["manifest"])
    except Exception as exc:  # noqa: BLE001 — fail closed with detail
        checks.append(Check(
            "schema-persistence-ack",
            False,
            f"could not load campaign manifest: {exc}",
        ))
        return checks
    tier = meta.get("schema_tier", 0)
    if tier != 0:
        checks.append(Check(
            "schema-persistence-ack",
            True,
            f"schema_tier={tier}; persistence ack not required",
        ))
        return checks

    ack_path = Path(".context/schema-persistence-ack.json")
    if not ack_path.is_file():
        checks.append(Check(
            "schema-persistence-ack",
            False,
            "schema_tier 0: missing .context/schema-persistence-ack.json "
            "(decision: none | same_pr_schema | stacked_schema)",
            recovery=(
                "Write .context/schema-persistence-ack.json per "
                "parables-campaign-stage-details.md Stage 4.7, then re-run stage5-pr"
            ),
        ))
        return checks

    try:
        ack = json.loads(ack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(Check(
            "schema-persistence-ack",
            False,
            f"invalid schema-persistence-ack.json: {exc}",
        ))
        return checks

    allowed = {"none", "same_pr_schema", "stacked_schema"}
    errors: list[str] = []
    if normalize_ticket(str(ack.get("ticket") or "")) != normalize_ticket(ticket):
        errors.append(f"ack ticket mismatch (want {ticket})")
    decision = str(ack.get("decision") or "")
    if decision not in allowed:
        errors.append(f"decision must be one of {sorted(allowed)}")
    if not str(ack.get("rationale") or "").strip():
        errors.append("rationale required")

    checks.append(Check(
        "schema-persistence-ack",
        len(errors) == 0,
        errors[0] if errors else f"persistence ack ok ({decision})",
        recovery=(
            "Update .context/schema-persistence-ack.json — see Stage 4.7 in "
            "parables-campaign-stage-details.md"
        ),
    ))
    return checks


def check_campaign_stage4(task_id: str | None) -> list[Check]:
    """Conditional PARABLE-609 gates before Stage 4 source edits."""
    checks: list[Check] = []
    triggered, ticket = campaign_triggered(task_id)
    if not triggered:
        checks.append(Check("campaign-mode", True, "campaign mode inactive (non-PARABLE-609)"))
        return checks

    checks.append(Check("campaign-mode", True, f"PARABLE-609 campaign active for {ticket}"))
    if not ticket:
        checks.append(Check("campaign-ticket", False, "campaign triggered but ticket unresolved"))
        return checks

    snap = state_dir(ticket) / "campaign-snapshot.json"
    snap_data = read_json(snap)
    if not snap_data or snap_data.get("RUN_BY_SCRIPT") != "campaign_context_gate.py":
        checks.append(Check(
            "campaign-context",
            False,
            f"missing campaign snapshot — run campaign_context_gate.py for {ticket}",
            recovery=(
                "python3 ~/.cursor/skills/andrew-ship-feature/scripts/campaign_context_gate.py "
                f"--ticket {ticket} --workspace ."
            ),
        ))
    else:
        checks.append(Check("campaign-context", True, f"campaign snapshot present: {snap}"))

    baseline = validate_baseline(ticket)
    checks.append(Check(
        "reference-baseline",
        baseline["passed"],
        baseline["errors"][0] if baseline.get("errors") else f"baseline ok: {baseline.get('path')}",
        recovery=(
            "python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py "
            f"--mode baseline --ticket {ticket}"
        ),
    ))

    ref_sha = (snap_data or {}).get("reference_sha")
    audit = validate_reference_audit(ticket, ref_sha)
    checks.append(Check(
        "reference-audit",
        audit["passed"],
        audit["errors"][0] if audit.get("errors") else f"reference audit ok: {audit.get('path')}",
        recovery=(
            "Fill ~/.cursor/ship-feature-state/parable-609/<ticket>/reference-audit.md "
            "then re-run reference_audit_gate.py --validate"
        ),
    ))

    plan = find_plan(task_id)
    plan_hash = sha256_file(plan) if plan else None
    campaign_hash = sha256_file(snap) if snap.is_file() else None
    ref_fp = (snap_data or {}).get("reference_dirty_fingerprint")
    approval_file = approval_path(ticket, "implementation")
    payload = read_json(approval_file)
    if not payload:
        checks.append(Check(
            "implementation-approval",
            False,
            f"STOP: missing Stage 3.9 human approval at {approval_file}",
            recovery=(
                "Present plan + reference audit + baseline to the user. On approval, run:\n"
                "python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py "
                f"--kind implementation --ticket {ticket} --approve "
                f"--quote 'APPROVE IMPLEMENTATION {ticket}' "
                f"--plan <plan> --campaign-snapshot {snap}"
            ),
        ))
        return checks

    errors = validate_payload(payload, "implementation", ticket)
    expected = {
        k: v
        for k, v in {
            "plan_hash": plan_hash,
            "campaign_hash": campaign_hash,
            "reference_fingerprint": ref_fp,
        }.items()
        if v
    }
    errors.extend(hashes_still_match(payload, expected))
    checks.append(Check(
        "implementation-approval",
        len(errors) == 0,
        errors[0] if errors else f"implementation approved: {approval_file}",
        recovery="Plan/reference changed — invalidate approval and re-request Stage 3.9 sign-off",
    ))
    return checks


def check_stage5_pr(task_id: str | None, workspace: Path | None = None) -> list[Check]:
    """Block Stage 5 PR create until visual proof + human sign-off (campaign mode)."""
    checks: list[Check] = []
    triggered, ticket = campaign_triggered(task_id)
    if not triggered:
        checks.append(Check("campaign-mode", True, "campaign mode inactive; stage5-pr skipped"))
        return checks

    checks.append(Check("campaign-mode", True, f"PARABLE-609 stage5-pr active for {ticket}"))
    if not ticket:
        checks.append(Check("campaign-ticket", False, "ticket unresolved for visual gate"))
        return checks

    checks.extend(
        [c for c in check_campaign_stage4(task_id) if c.name == "implementation-approval"]
    )
    checks.extend(check_schema_persistence_ack(ticket))

    head = None
    root = workspace or Path.cwd()
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            head = proc.stdout.strip()
    except OSError:
        head = None

    after = validate_after(ticket, head)
    checks.append(Check(
        "visual-after",
        after["passed"],
        after["errors"][0] if after.get("errors") else f"after proof ok: {after.get('path')}",
        recovery=(
            "python3 ~/.cursor/skills/andrew-ship-feature/scripts/visual_qa_gate.py "
            f"--mode after --ticket {ticket} --head-sha $(git rev-parse HEAD)"
        ),
    ))

    approval_file = approval_path(ticket, "visual-qa")
    payload = read_json(approval_file)
    if not payload:
        checks.append(Check(
            "visual-approval",
            False,
            f"STOP: missing Stage 4.9 visual sign-off at {approval_file}",
            recovery=(
                "Present before/after visual proof to the user. On approval, run:\n"
                "python3 ~/.cursor/skills/andrew-ship-feature/scripts/approval_gate.py "
                f"--kind visual-qa --ticket {ticket} --approve "
                f"--quote 'APPROVE VISUAL QA {ticket}' "
                f"--proof {after.get('path')} --head-sha {head}"
            ),
        ))
    else:
        errors = validate_payload(payload, "visual-qa", ticket)
        expected = {
            k: v
            for k, v in {
                "proof_hash": after.get("proof_hash"),
                "head_sha": head,
            }.items()
            if v
        }
        errors.extend(hashes_still_match(payload, expected))
        checks.append(Check(
            "visual-approval",
            len(errors) == 0,
            errors[0] if errors else f"visual QA approved: {approval_file}",
            recovery="HEAD or proof changed — re-run Stage 4.8 and re-request visual sign-off",
        ))

    cleanup = cleanup_check(root)
    checks.append(Check(
        "visual-harness-cleanup",
        cleanup["passed"],
        cleanup["errors"][0] if cleanup.get("errors") else "no harness/screenshot residues in repo diff",
        recovery="Remove ephemeral visual harness and screenshots from the branch before PR create",
    ))
    return checks


def gate_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return data if "triggered" in data else None
    except (json.JSONDecodeError, OSError):
        return None


def check_stage4(task_id: str | None, root: Path | None = None) -> list[Check]:
    prev = Path.cwd()
    if root is not None:
        import os

        os.chdir(root)
    try:
        return _check_stage4_impl(task_id)
    finally:
        if root is not None:
            import os

            os.chdir(prev)


def _check_stage4_impl(task_id: str | None) -> list[Check]:
    checks: list[Check] = []
    plan = find_plan(task_id)
    review = find_plan_review(plan, task_id)

    if plan is None:
        checks.append(Check("plan", False, "No plan file in plans/"))
        # Still evaluate campaign gates so PARABLE-609 pauses surface in status.
        if CAMPAIGN_GATES_AVAILABLE:
            checks.extend(check_campaign_stage4(task_id))
        return checks
    plan_text = read_text(plan)
    checks.append(Check(
        "plan-provenance",
        has_marker(plan_text, "RUN_BY_COMMAND: plan-create"),
        "Plan must include RUN_BY_COMMAND: plan-create (delegate /plan-create)",
    ))

    if review is None:
        checks.append(Check("plan-review", False, "No plan review in .context/reviews/"))
    else:
        review_text = read_text(review)
        checks.append(Check(
            "plan-review-provenance",
            has_marker(review_text, "RUN_BY_COMMAND: plan-review"),
            "Plan review must include RUN_BY_COMMAND: plan-review (delegate /plan-review)",
        ))
        ready = "ready to execute" in review_text.lower() or "ready with changes" in review_text.lower()
        checks.append(Check("plan-review-ready", ready, "Plan review must be READY TO EXECUTE or READY WITH CHANGES"))
        if plan.stat().st_mtime > review.stat().st_mtime + 1:
            checks.append(Check(
                "plan-review-fresh",
                False,
                "Plan modified after review — delegate /plan-update then re-delegate /plan-review (forbidden to skip re-review)",
            ))
        else:
            checks.append(Check("plan-review-fresh", True, "Plan review is current"))

    adv = find_adversarial(plan, task_id)
    if adv is None:
        checks.append(Check("adversarial", False, "Missing adversarial review — delegate /de-adversarial-reviewer plan-gate"))
    else:
        adv_text = read_text(adv)
        checks.append(Check(
            "adversarial-provenance",
            has_marker(adv_text, "RUN_BY_SKILL: de-adversarial-reviewer"),
            "Adversarial review must include RUN_BY_SKILL: de-adversarial-reviewer",
        ))
        blocked = bool(re.search(r"(?:##\s*decision|decision:)[^\n]*\bblock\b", adv_text, re.I))
        approved = bool(re.search(r"(?:##\s*decision|decision:)[^\n]*approve", adv_text, re.I)) or (
            "approve with conditions" in adv_text.lower()
        )
        checks.append(Check("adversarial-approve", approved and not blocked, "Adversarial must APPROVE (not BLOCK)"))

    bench = find_plan_benchmark(task_id)
    if bench is None:
        checks.append(Check(
            "plan-benchmark",
            False,
            "Missing plan-level test benchmark — delegate `/test-benchmark plan <plan-file>` (Stage 3.75)",
        ))
    else:
        bench_text = read_text(bench)
        checks.append(Check(
            "plan-benchmark-provenance",
            has_marker(bench_text, "RUN_BY_SKILL: test-benchmark"),
            "Plan benchmark must include RUN_BY_SKILL: test-benchmark",
        ))

    psgen = gate_json(Path(".context/psgen-gate-plan.json"))
    checks.append(Check(
        "psgen-plan-gate",
        psgen is not None,
        "Run psgen_gate.py --mode plan --out .context/psgen-gate-plan.json (Stage 3.7)",
    ))

    scalar = gate_json(Path(".context/scalar-lib-gate-plan.json"))
    checks.append(Check(
        "scalar-plan-gate",
        scalar is not None,
        "Run scalar_lib_gate.py --mode plan --out .context/scalar-lib-gate-plan.json (Stage 3.8)",
    ))

    deferral = find_deferral(task_id)
    if deferral is None:
        checks.append(Check(
            "deferral-register",
            False,
            "Missing deferral register — orchestrator writes .context/deferrals/{task}_deferrals.md after Stage 3.5b adjudication",
        ))
    else:
        deferral_text = read_text(deferral)
        checks.append(Check(
            "deferral-provenance",
            has_marker(deferral_text, "RUN_BY_SKILL: ship-feature"),
            "Deferral register must include RUN_BY_SKILL: ship-feature",
        ))

    # PARABLE-609 user-scoped campaign gates (no-op when not triggered)
    if CAMPAIGN_GATES_AVAILABLE:
        checks.extend(check_campaign_stage4(task_id))

    return checks


def stage4_ok(task_id: str | None = None, root: Path | None = None) -> bool:
    return all(c.passed for c in check_stage4(task_id, root))


def stage6_ok(pr_number: int | None = None, root: Path | None = None) -> bool:
    prev = Path.cwd()
    if root is not None:
        import os

        os.chdir(root)
    try:
        checks = check_stage6_complete(pr_number)
    finally:
        if root is not None:
            import os

            os.chdir(prev)
    return all(c.passed for c in checks)


def list_stage_status(task_id: str | None = None) -> dict[str, bool]:
    """Return which planning/phase-6 artifacts exist (for prove harness)."""
    plan = find_plan(task_id)
    review = find_plan_review(plan, task_id)
    return {
        "plan": plan is not None,
        "plan_review": review is not None,
        "plan_review_fresh": (
            review is not None
            and plan is not None
            and plan.stat().st_mtime <= review.stat().st_mtime + 1
        ),
        "adversarial": find_adversarial(plan, task_id) is not None,
        "plan_benchmark": find_plan_benchmark(task_id) is not None,
        "psgen_plan_gate": gate_json(Path(".context/psgen-gate-plan.json")) is not None,
        "scalar_plan_gate": gate_json(Path(".context/scalar-lib-gate-plan.json")) is not None,
        "deferral": find_deferral(task_id) is not None,
        "pr_review": bool(list(Path(".context/prs/reviews").glob("PR_REVIEW_*.md"))),
        "proof_gate": gate_json(Path(".context/proof-harness-gate.json")) is not None,
        "code_benchmark": bool(list(Path(".context/test-benchmarks").glob("*_code-level.md"))),
        "campaign_gate": Path(".context/campaign-gate.json").is_file(),
        "implementation_approval": (
            CAMPAIGN_GATES_AVAILABLE
            and (lambda t: bool(t and (state_dir(t) / "implementation-approval.json").is_file()))(
                resolve_campaign_ticket(task_id)
            )
        ),
        "visual_approval": (
            CAMPAIGN_GATES_AVAILABLE
            and (lambda t: bool(t and (state_dir(t) / "visual-qa-approval.json").is_file()))(
                resolve_campaign_ticket(task_id)
            )
        ),
    }


def check_stage3_after_update(plan_path: Path) -> list[Check]:
    checks: list[Check] = []
    if not plan_path.is_file():
        return [Check("plan", False, f"Plan not found: {plan_path}")]

    plan_text = read_text(plan_path)
    checks.append(Check(
        "plan-update-provenance",
        has_marker(plan_text, "RUN_BY_COMMAND: plan-update"),
        "Updated plan must include RUN_BY_COMMAND: plan-update from delegated /plan-update subagent",
    ))

    review = find_plan_review(plan_path, None)
    if review is None:
        checks.append(Check("plan-review-after-update", False, "Re-delegate /plan-review after every /plan-update"))
    elif plan_path.stat().st_mtime > review.stat().st_mtime + 1:
        checks.append(Check(
            "plan-review-after-update",
            False,
            "Plan newer than review — re-delegate /plan-review before Stage 3.5",
        ))
    else:
        review_text = read_text(review)
        checks.append(Check(
            "plan-review-after-update",
            has_marker(review_text, "RUN_BY_COMMAND: plan-review"),
            "Fresh plan review required after plan-update",
        ))
    return checks


def check_stage6_complete(pr_number: int | None, task_id: str | None = None) -> list[Check]:
    checks: list[Check] = []

    review_path = find_pr_review(pr_number, task_id)

    if review_path is None:
        checks.append(Check("pr-review", False, "Missing PR review — delegate `/pr-review-local <PR>` before any Stage 6.45+ gate"))
        return checks

    review_text = read_text(review_path)
    has_pr_review = (
        has_marker(review_text, "RUN_BY_COMMAND: pr-review-local")
        or has_marker(review_text, "RUN_BY_SKILL: pr-review")
    )
    checks.append(Check(
        "pr-review-provenance",
        has_pr_review,
        "PR review must come from delegated /pr-review-local subagent",
    ))

    proof = gate_json(Path(".context/proof-harness-gate.json"))
    if proof is None:
        checks.append(Check("proof-gate-json", False, "Missing .context/proof-harness-gate.json — run Stage 6.45 gate AFTER Stage 6"))
    else:
        checks.append(Check("proof-gate-json", True, "proof-harness gate JSON present"))
        if proof.get("triggered"):
            log = Path(".context/implementation/proof-harness-log.md")
            log_text = read_text(log) if log.is_file() else ""
            ran_tiers = "PASS" in log_text or "FAIL" in log_text or "tier" in log_text.lower()
            checks.append(Check(
                "proof-tiers-executed",
                log.is_file() and ran_tiers,
                "Proof harness triggered but tiers not logged — orchestrator must run tiers (not gate-only)",
            ))

    code_bench = list(Path(".context/test-benchmarks").glob("*_code-level.md"))
    checks.append(Check(
        "code-benchmark",
        bool(code_bench),
        "Missing code-level benchmark — delegate `/test-benchmark <PR>` (Stage 6.5)",
    ))

    for label, path in (
        ("rust-complexity-gate", Path(".context/rust-cognitive-complexity-gate.json")),
        ("psgen-code-gate", Path(".context/psgen-gate-code.json")),
        ("scalar-code-gate", Path(".context/scalar-lib-gate-code.json")),
    ):
        checks.append(Check(label, gate_json(path) is not None, f"Missing {path} — run Stage 6.6/6.65/6.7 gate script"))

    if review_path:
        for section in ("Stage 6.45", "Stage 6.5", "Stage 6.6", "Stage 6.65", "Stage 6.7"):
            checks.append(Check(
                f"pr-review-{section.lower().replace(' ', '-')}",
                section in review_text,
                f"PR review missing {section} section — append harness results before GitHub comment",
            ))

    return checks


def emit(checks: list[Check], as_json: bool = False) -> int:
    failed = [c for c in checks if not c.passed]
    if as_json:
        import json as _json

        payload = {
            "passed": len(failed) == 0,
            "failed_count": len(failed),
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "detail": c.detail,
                    "recovery": c.recovery or recovery_for(c.name, c.detail),
                }
                for c in checks
            ],
        }
        print(_json.dumps(payload, indent=2))
        return 0 if not failed else 1
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status}  {check.name}: {check.detail}")
        if not check.passed:
            rec = check.recovery or recovery_for(check.name, check.detail)
            print(f"       -> RECOVER: {rec}")
    if failed:
        print(f"\nBLOCKED: {len(failed)} compliance check(s) failed")
        print("Run: python3 ~/.cursor/skills/andrew-ship-feature/scripts/harness_recovery.py --gate auto")
        return 1
    print(f"\nOK: all {len(checks)} compliance checks passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        required=True,
        choices=["stage4", "stage3-after-update", "stage6-complete", "stage5-pr"],
    )
    parser.add_argument("--task", help="Task id for artifact matching")
    parser.add_argument("--plan", type=Path, help="Plan path (stage3-after-update)")
    parser.add_argument("--pr", type=int, help="PR number (stage6-complete)")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args()

    if args.gate == "stage4":
        return emit(check_stage4(args.task), as_json=args.json)
    if args.gate == "stage5-pr":
        return emit(check_stage5_pr(args.task), as_json=args.json)
    if args.gate == "stage3-after-update":
        plan = args.plan or find_plan(args.task)
        if plan is None:
            if args.json:
                import json as _json

                print(_json.dumps({"passed": False, "checks": [{"name": "plan", "passed": False, "detail": "no plan file found"}]}))
            else:
                print("FAIL  plan: no plan file found")
            return 1
        return emit(check_stage3_after_update(plan), as_json=args.json)
    return emit(check_stage6_complete(args.pr, args.task), as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
