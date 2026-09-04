#!/usr/bin/env python3
"""Grade ship-feature eval responses against assertions (programmatic)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def grade_text(text: str, assertion: dict) -> tuple[bool, str]:
    t = text.lower()
    aid = assertion["id"]
    if aid == "re-review-required":
        ok = "plan-review" in t and ("re-delegate" in t or "re-run" in t or "again" in t or "/plan-review" in t)
        return ok, "plan-review re-delegation mentioned" if ok else "missing plan-review re-delegation"
    if aid == "stage375-before-4":
        ok = "3.75" in t or "test-benchmark plan" in t or "/test-benchmark plan" in t
        return ok, "stage 3.75 mentioned" if ok else "missing 3.75"
    if aid == "no-batch-gates":
        ok = ("batch" in t or "same turn" in t or "jump" in t or "forbidden" in t) and (
            "3.5" in t or "planning gate" in t or "stage 4" in t
        )
        return ok, "anti-batching stated" if ok else "missing anti-batching"
    if aid == "compliance-script":
        ok = "stage_compliance_check" in t
        return ok, "compliance script mentioned" if ok else "missing stage_compliance_check.py"
    if aid == "pr-review-first":
        ok = "pr-review-local" in t and ("before" in t or "first" in t or "only after" in t)
        return ok, "pr-review before gates" if ok else "missing ordering"
    if aid == "forbids-parallel-gates":
        ok = ("before" in t or "forbidden" in t or "violat" in t or "wrong" in t) and (
            "6.45" in t or "proof_harness" in t or "gate" in t
        )
        return ok, "parallel/forbidden gates" if ok else "missing parallel gate forbid"
    if aid == "stage6-complete-check":
        # legacy id — same as full-cmd
        aid = "stage6-complete-full-cmd"
    if aid == "stage6-complete-full-cmd":
        ok = (
            "stage_compliance_check.py" in t
            and "--gate stage6-complete" in t
            and "--pr" in t
            and ("exit code 1" in t or "exit code **1**" in t or "exit 1" in t)
        )
        return ok, "full stage6-complete command + stop rule" if ok else "missing full stage6-complete harness command"
    if aid == "harness-recovery-loop":
        ok = (
            "harness_recovery.py" in t
            or "harness recovery" in t
            or "self-heal" in t
            or "self_heal" in t
            or "next_action" in t
            or "max_self_heal_cycles" in t
        )
        return ok, "harness-first self-heal loop" if ok else "missing harness_recovery self-heal (skill-specific)"
    if aid == "provenance-pr-review":
        ok = "run_by_command: pr-review-local" in t
        return ok, "pr-review provenance marker" if ok else "missing RUN_BY_COMMAND: pr-review-local"
    if aid == "delegation-window":
        ok = "delegation_window.py" in t and ("begin" in t or "end" in t)
        return ok, "delegation window protocol" if ok else "missing delegation_window.py begin/end (skill-specific)"
    # fallback: substring match on assertion text
    words = re.findall(r"[a-z0-9./_-]+", assertion["text"].lower())
    hits = sum(1 for w in words if len(w) > 4 and w in t)
    ok = hits >= max(2, len(words) // 3)
    return ok, f"fallback keyword hits={hits}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--eval-id", type=int, required=True)
    parser.add_argument("--evals-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.evals_json.read_text())
    eval_def = next(e for e in data["evals"] if e["id"] == args.eval_id)
    text = args.response.read_text(encoding="utf-8")
    expectations = []
    for assertion in eval_def.get("assertions", []):
        passed, evidence = grade_text(text, assertion)
        expectations.append({"text": assertion["text"], "passed": passed, "evidence": evidence})

    passed = sum(1 for e in expectations if e["passed"])
    grading = {
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": len(expectations) - passed,
            "total": len(expectations),
            "pass_rate": round(passed / len(expectations), 4) if expectations else 0,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(grading, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(grading["summary"]))
    return 0 if passed == len(expectations) else 1


if __name__ == "__main__":
    sys.exit(main())
