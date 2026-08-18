#!/usr/bin/env python3
"""Validate human approval artifacts for PARABLE-609 ship-feature gates.

Kinds:
  implementation  — Stage 3.9 before source edits
  visual-qa       — Stage 4.9 before PR create

Usage:
  python3 approval_gate.py --kind implementation --ticket PARABLE-644 --approve \\
    --quote "APPROVE IMPLEMENTATION PARABLE-644" --plan-hash abc --campaign-hash def --ref-fp ghi
  python3 approval_gate.py --kind implementation --ticket PARABLE-644 --validate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from parable_609_paths import (  # noqa: E402
    normalize_ticket,
    read_json,
    sha256_file,
    sha256_text,
    state_dir,
    utc_now,
    write_json,
)

KIND_IMPL = "implementation"
KIND_VISUAL = "visual-qa"
VALID_KINDS = {KIND_IMPL, KIND_VISUAL}


def approval_path(ticket: str, kind: str) -> Path:
    ticket = normalize_ticket(ticket)
    if kind == KIND_IMPL:
        return state_dir(ticket) / "implementation-approval.json"
    return state_dir(ticket) / "visual-qa-approval.json"


def validate_payload(payload: dict, kind: str, ticket: str) -> list[str]:
    errors: list[str] = []
    if payload.get("HUMAN_APPROVAL") != kind:
        errors.append(f"HUMAN_APPROVAL must be '{kind}'")
    if normalize_ticket(str(payload.get("TICKET", ""))) != normalize_ticket(ticket):
        errors.append("TICKET mismatch")
    quote = str(payload.get("APPROVAL_QUOTE", "")).strip()
    if len(quote) < 20:
        errors.append("APPROVAL_QUOTE must be >= 20 characters (verbatim user sentence)")
    if payload.get("RUN_BY_SKILL") != "ship-feature":
        errors.append("RUN_BY_SKILL must be ship-feature")
    if not payload.get("APPROVED_AT"):
        errors.append("APPROVED_AT missing")
    if kind == KIND_IMPL:
        for key in ("plan_hash", "campaign_hash", "reference_fingerprint"):
            if not payload.get(key):
                errors.append(f"{key} required for implementation approval")
    if kind == KIND_VISUAL:
        for key in ("proof_hash", "head_sha"):
            if not payload.get(key):
                errors.append(f"{key} required for visual-qa approval")
    if payload.get("self_signed"):
        errors.append("self_signed approvals are rejected")
    return errors


def hashes_still_match(payload: dict, expected: dict) -> list[str]:
    errors = []
    for key, expected_val in expected.items():
        if expected_val is None:
            continue
        if payload.get(key) != expected_val:
            errors.append(f"stale approval: {key} changed (re-approve required)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--approve", action="store_true", help="Write approval artifact")
    parser.add_argument("--validate", action="store_true", help="Validate existing approval")
    parser.add_argument("--quote", help="Verbatim user approval sentence")
    parser.add_argument("--plan-hash")
    parser.add_argument("--campaign-hash")
    parser.add_argument("--ref-fp", dest="reference_fingerprint")
    parser.add_argument("--proof-hash")
    parser.add_argument("--head-sha")
    parser.add_argument("--plan", type=Path, help="Plan file to hash for approve/validate")
    parser.add_argument("--campaign-snapshot", type=Path)
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--expect-plan-hash")
    parser.add_argument("--expect-campaign-hash")
    parser.add_argument("--expect-ref-fp")
    parser.add_argument("--expect-proof-hash")
    parser.add_argument("--expect-head-sha")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ticket = normalize_ticket(args.ticket)
    path = approval_path(ticket, args.kind)

    if args.approve:
        plan_hash = args.plan_hash or (sha256_file(args.plan) if args.plan else None)
        campaign_hash = args.campaign_hash or (
            sha256_file(args.campaign_snapshot) if args.campaign_snapshot else None
        )
        proof_hash = args.proof_hash or (sha256_file(args.proof) if args.proof else None)
        payload = {
            "RUN_BY_SKILL": "ship-feature",
            "HUMAN_APPROVAL": args.kind,
            "TICKET": ticket,
            "APPROVED_AT": utc_now(),
            "APPROVAL_QUOTE": args.quote or "",
            "self_signed": False,
            "SCOPE": (
                "implement plan as reviewed; no scope substitution"
                if args.kind == KIND_IMPL
                else "visual proof accepted for this HEAD; do not create PR without this"
            ),
        }
        if args.kind == KIND_IMPL:
            payload.update({
                "plan_hash": plan_hash,
                "campaign_hash": campaign_hash,
                "reference_fingerprint": args.reference_fingerprint,
            })
        else:
            payload.update({
                "proof_hash": proof_hash,
                "head_sha": args.head_sha,
            })
        errors = validate_payload(payload, args.kind, ticket)
        if errors:
            print(json.dumps({"passed": False, "errors": errors}, indent=2))
            return 1
        write_json(path, payload)
        print(json.dumps({"passed": True, "path": str(path), "payload": payload}, indent=2))
        return 0

    # validate (default)
    payload = read_json(path)
    if not payload:
        result = {
            "passed": False,
            "path": str(path),
            "errors": [f"missing approval artifact: {path}"],
        }
        print(json.dumps(result, indent=2))
        return 1

    errors = validate_payload(payload, args.kind, ticket)
    expected = {}
    if args.kind == KIND_IMPL:
        expected = {
            "plan_hash": args.expect_plan_hash or (sha256_file(args.plan) if args.plan else None),
            "campaign_hash": args.expect_campaign_hash
            or (sha256_file(args.campaign_snapshot) if args.campaign_snapshot else None),
            "reference_fingerprint": args.expect_ref_fp or args.reference_fingerprint,
        }
    else:
        expected = {
            "proof_hash": args.expect_proof_hash or (sha256_file(args.proof) if args.proof else None),
            "head_sha": args.expect_head_sha or args.head_sha,
        }
    # Drop Nones so validate-only without expect_* still passes structural checks
    expected = {k: v for k, v in expected.items() if v is not None}
    errors.extend(hashes_still_match(payload, expected))

    result = {
        "passed": len(errors) == 0,
        "path": str(path),
        "errors": errors,
        "payload": payload,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    _ = sha256_text
    sys.exit(main())
