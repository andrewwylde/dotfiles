#!/usr/bin/env python3
"""Open/close a delegation window so only subagents write phase artifacts.

Harness-first rule: delegated artifacts (plan review, adversarial, benchmarks,
PR review) cannot be written unless a delegation window is active for the
matching stage. The orchestrator runs `begin` before Task(subagent) and `end`
after the subagent returns.

Usage:
  python3 delegation_window.py begin --stage plan-review [--ttl 3600]
  python3 delegation_window.py end
  python3 delegation_window.py status
  python3 delegation_window.py check --path .context/reviews/plan_foo.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import path patterns from harness_recovery (same module family)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_recovery import delegation_stages_for_path  # noqa: E402

SESSION_NAME = "ship-feature-session.json"
DEFAULT_TTL_SECONDS = 3600


def session_path(workspace: Path) -> Path:
    return workspace / ".context" / SESSION_NAME


def load_session(workspace: Path) -> dict:
    path = session_path(workspace)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(workspace: Path, session: dict) -> None:
    path = session_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")


def delegation_active(session: dict) -> dict | None:
    delegation = session.get("delegation")
    if not isinstance(delegation, dict):
        return None
    expires = delegation.get("expires_at")
    if not expires:
        return delegation
    try:
        exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp:
            return None
    except ValueError:
        return None
    return delegation


def cmd_begin(workspace: Path, stage: str, ttl: int) -> int:
    session = load_session(workspace)
    if not session:
        print("FAIL  no ship-feature session — run activate_session.py first", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    session["delegation"] = {
        "stage": stage,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
    }
    save_session(workspace, session)
    print(f"OK  delegation window open: stage={stage} ttl={ttl}s")
    return 0


def cmd_end(workspace: Path) -> int:
    session = load_session(workspace)
    if "delegation" in session:
        del session["delegation"]
        save_session(workspace, session)
    print("OK  delegation window closed")
    return 0


def cmd_status(workspace: Path) -> int:
    session = load_session(workspace)
    delegation = delegation_active(session)
    if delegation:
        print(json.dumps({"active": True, **delegation}, indent=2))
        return 0
    print(json.dumps({"active": False}, indent=2))
    return 0


def cmd_check(workspace: Path, path: str) -> int:
    stages = delegation_stages_for_path(path)
    if not stages:
        print(json.dumps({"delegated": False, "allowed": True}, indent=2))
        return 0
    session = load_session(workspace)
    delegation = delegation_active(session)
    if not delegation:
        print(json.dumps({
            "delegated": True,
            "allowed": False,
            "reason": "no active delegation window",
            "required_stages": stages,
        }, indent=2))
        return 1
    active_stage = delegation.get("stage")
    allowed = active_stage in stages
    print(json.dumps({
        "delegated": True,
        "allowed": allowed,
        "active_stage": active_stage,
        "required_stages": stages,
    }, indent=2))
    return 0 if allowed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["begin", "end", "status", "check"])
    parser.add_argument("--stage", help="Delegation stage (begin)")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS)
    parser.add_argument("--path", help="File path to check (check)")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if args.command == "begin":
        if not args.stage:
            print("FAIL  --stage required for begin", file=sys.stderr)
            return 1
        return cmd_begin(workspace, args.stage, args.ttl)
    if args.command == "end":
        return cmd_end(workspace)
    if args.command == "status":
        return cmd_status(workspace)
    if args.command == "check":
        if not args.path:
            print("FAIL  --path required for check", file=sys.stderr)
            return 1
        return cmd_check(workspace, args.path)
    return 1


if __name__ == "__main__":
    sys.exit(main())
