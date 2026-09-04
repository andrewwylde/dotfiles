#!/usr/bin/env python3
"""
Task-scoped session activation for /ship-feature.

This script MUST run before any other ship-feature actions. It:
1. Creates .context/.active_skill with skill name
2. Creates .context/ship-feature-session.json with task identity
3. Ensures the gate system knows which task we're working on

The gate system will then only consider artifacts FOR THIS TASK, not
artifacts from old unrelated tasks.

Usage:
    python activate_session.py --task-desc "Gold path resolution fix"
    python activate_session.py --from-branch  # derive from current branch
    python activate_session.py --from-branch --task-desc "fallback when branch is main"
    python activate_session.py --task-id "gold-resolver-fix"

Exit codes:
    0 = Session activated
    1 = Error (missing args, can't derive task ID)
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def get_branch_name() -> str | None:
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def derive_task_id_from_branch(branch: str) -> str:
    """Extract task identifier from branch name."""
    for prefix in ["feature/", "fix/", "bug/", "chore/", "docs/", "refactor/"]:
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
            break
    task_id = branch.lower().replace("_", "-")
    if len(task_id) > 50:
        task_id = task_id[:50]
    return task_id


def derive_task_id_from_description(desc: str) -> str:
    """Generate task ID from description."""
    normalized = desc.lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    words = normalized.split()[:5]
    base = "-".join(words)
    hash_suffix = hashlib.sha256(desc.encode()).hexdigest()[:8]
    return f"{base}-{hash_suffix}"


def normalize_intent_text(text: str) -> str:
    """Normalize free-text task descriptions for intent matching."""
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    words = normalized.split()[:24]
    return " ".join(words)


def intent_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two normalized intents."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def append_fork_suffix(task_id: str) -> str:
    """Create a unique fork task ID when needed."""
    return f"{task_id}-fork-{uuid4().hex[:6]}"


def find_matching_artifacts(task_id: str, workspace: Path) -> dict:
    """Find artifacts that match the current task ID."""
    matching = {}

    plans_dir = workspace / "plans"
    if plans_dir.exists():
        for plan_file in plans_dir.glob("*.plan.md"):
            name = plan_file.stem.lower().replace("_", "-")
            task_words = set(task_id.split("-"))
            plan_words = set(name.split("-"))
            overlap = task_words & plan_words
            if len(overlap) >= 2 or task_id in name:
                matching["plan"] = str(plan_file)
                break

    reviews_dir = workspace / ".context" / "reviews"
    if reviews_dir.exists():
        for review_file in reviews_dir.glob("*.md"):
            name = review_file.stem.lower().replace("_", "-")
            task_words = set(task_id.split("-"))
            review_words = set(name.split("-"))
            overlap = task_words & review_words
            if len(overlap) >= 2 or task_id in name:
                matching["review"] = str(review_file)
                break

    return matching


def main():
    parser = argparse.ArgumentParser(description="Activate ship-feature session")
    parser.add_argument("--task-desc", help="Task description")
    parser.add_argument("--task-id", help="Explicit task ID")
    parser.add_argument("--from-branch", action="store_true", help="Derive task ID from branch")
    parser.add_argument("--workspace", default=".", help="Workspace root")
    parser.add_argument("--force", action="store_true", help="Overwrite existing session")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Keep current session if task ID differs (default: replace for explicit --task-desc)",
    )
    parser.add_argument(
        "--fork-from-existing",
        action="store_true",
        help="Create a child session linked to existing task when IDs differ",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing session when IDs differ",
    )
    parser.add_argument(
        "--deactivate",
        action="store_true",
        help="Clear .active_skill marker and mark session completed (run at pipeline end)",
    )

    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()

    context_dir = workspace / ".context"
    context_dir.mkdir(parents=True, exist_ok=True)

    if args.deactivate:
        session_file = context_dir / "ship-feature-session.json"
        active_skill_file = context_dir / ".active_skill"
        env_hint_file = context_dir / ".active_skill_env"
        session: dict = {}
        if session_file.exists():
            with open(session_file) as f:
                session = json.load(f)
        session["status"] = "completed"
        session["completed_at"] = datetime.now(timezone.utc).isoformat()
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)
        for path in (active_skill_file, env_hint_file):
            if path.exists():
                path.unlink()
        print(json.dumps({"deactivated": True, "session": session}, indent=2))
        sys.exit(0)

    task_id = None
    task_source = None
    session_action = "new"
    parent_task_id = None

    if args.task_id:
        task_id = args.task_id
        task_source = "explicit"
    elif args.from_branch:
        branch = get_branch_name()
        if branch and branch not in ("main", "master", "HEAD"):
            task_id = derive_task_id_from_branch(branch)
            task_source = f"branch:{branch}"
        elif args.task_desc:
            task_id = derive_task_id_from_description(args.task_desc)
            task_source = "description"
    elif args.task_desc:
        task_id = derive_task_id_from_description(args.task_desc)
        task_source = "description"

    if not task_id:
        print("ERROR: Cannot determine task ID. Provide --task-id, --task-desc, or --from-branch", file=sys.stderr)
        sys.exit(1)

    context_dir = workspace / ".context"
    context_dir.mkdir(parents=True, exist_ok=True)

    session_file = context_dir / "ship-feature-session.json"
    if session_file.exists() and not args.force:
        with open(session_file) as f:
            existing = json.load(f)
        if existing.get("task_id") != task_id:
            if args.reuse_existing:
                print(f"WARNING: Existing session for task '{existing.get('task_id')}' found.", file=sys.stderr)
                print(f"New task ID would be: '{task_id}'", file=sys.stderr)
                print("Using existing session due to --reuse-existing.", file=sys.stderr)
                print(json.dumps(existing, indent=2))
                sys.exit(0)

            should_fork = False
            should_replace = False

            if args.fork_from_existing:
                should_fork = True
            elif args.replace_existing:
                should_replace = True
            elif args.task_desc and not args.task_id:
                # For explicit descriptions, infer whether this is a fork of the same intent.
                new_intent = normalize_intent_text(args.task_desc)
                existing_desc = existing.get("task_description") or existing.get("task_id") or ""
                existing_intent = normalize_intent_text(existing_desc)
                similarity = intent_similarity(new_intent, existing_intent)
                if similarity >= 0.55:
                    should_fork = True
                    print(
                        f"INFO: Similar intent detected (similarity={similarity:.2f}); auto-forking from '{existing.get('task_id')}'.",
                        file=sys.stderr,
                    )
                else:
                    should_replace = True
                    print(
                        f"INFO: Divergent intent detected (similarity={similarity:.2f}); replacing existing session '{existing.get('task_id')}'.",
                        file=sys.stderr,
                    )

            if should_fork:
                parent_task_id = existing.get("task_id")
                session_action = "fork"
                if task_id == parent_task_id:
                    task_id = append_fork_suffix(task_id)
                    print(f"INFO: Fork requested with identical task ID. Using unique fork ID '{task_id}'.", file=sys.stderr)
                print(f"INFO: Creating forked session '{task_id}' from parent '{parent_task_id}'.", file=sys.stderr)
            elif should_replace:
                session_action = "replace"
                print(f"INFO: Replacing existing session '{existing.get('task_id')}' with '{task_id}'.", file=sys.stderr)
            else:
                print(f"WARNING: Existing session for task '{existing.get('task_id')}' found.", file=sys.stderr)
                print(f"New task ID would be: '{task_id}'", file=sys.stderr)
                print(
                    "Use --force to overwrite, --reuse-existing to keep current session, "
                    "--fork-from-existing to branch, or --replace-existing to replace.",
                    file=sys.stderr,
                )
                print(json.dumps(existing, indent=2))
                sys.exit(0)

    matching_artifacts = find_matching_artifacts(task_id, workspace)

    # Campaign context (multi-campaign, user-scoped). Never auto-jump past human gates.
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    campaign_ticket = None
    campaign_info = {"triggered": False}
    awaiting_human_gate = None
    try:
        from campaign_paths import extract_ticket, resolve_campaign, state_dir
        from campaign_context_gate import build_snapshot, detect_ticket
        import json as _json

        class _Args:
            ticket = None
            task = task_id
            branch = get_branch_name() or ""
            linear_parent = None

        campaign_ticket = detect_ticket(_Args()) or extract_ticket(
            task_id, args.task_desc or "", get_branch_name() or ""
        )
        resolved = resolve_campaign(campaign_ticket) if campaign_ticket else None
        if resolved:
            snap = build_snapshot(campaign_ticket, workspace, resolved)
            snap_path = state_dir(campaign_ticket) / "campaign-snapshot.json"
            snap_path.write_text(_json.dumps(snap, indent=2) + "\n", encoding="utf-8")
            gate_payload = {
                "RUN_BY_SCRIPT": "campaign_context_gate.py",
                "triggered": True,
                "ticket": campaign_ticket,
                "campaign": resolved["campaign_id"],
                "harness_kind": snap.get("harness_kind"),
                "snapshot_path": str(snap_path),
                "readiness_gaps": snap.get("readiness_gaps", []),
                "git_base": snap.get("git_base"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            (context_dir / "campaign-gate.json").write_text(
                _json.dumps(gate_payload, indent=2) + "\n", encoding="utf-8"
            )
            campaign_info = gate_payload
            impl_ok = (state_dir(campaign_ticket) / "implementation-approval.json").is_file()
            visual_ok = (state_dir(campaign_ticket) / "visual-qa-approval.json").is_file()
            if not impl_ok:
                awaiting_human_gate = "implementation"
            elif not visual_ok:
                awaiting_human_gate = None
    except Exception as exc:  # noqa: BLE001 - campaign load must not block activation
        campaign_info = {"triggered": False, "error": str(exc)}

    resume_stage = 0
    resume_reason = "No matching artifacts found for this task"

    if matching_artifacts.get("review"):
        # Do NOT resume directly to Stage 4 when campaign implementation approval is missing.
        if campaign_info.get("triggered") and awaiting_human_gate == "implementation":
            resume_stage = 39  # Stage 3.9 human gate
            resume_reason = (
                f"Found matching review ({matching_artifacts['review']}) but "
                "Stage 3.9 implementation approval is missing — stop before Stage 4"
            )
        else:
            resume_stage = 4
            resume_reason = f"Found matching review: {matching_artifacts['review']}"
    elif matching_artifacts.get("plan"):
        resume_stage = 2
        resume_reason = f"Found matching plan: {matching_artifacts['plan']}"

    session = {
        "skill": "ship-feature",
        "task_id": task_id,
        "task_source": task_source,
        "task_description": args.task_desc or "",
        "intent_fingerprint": normalize_intent_text(args.task_desc or task_id),
        "session_action": session_action,
        "parent_task_id": parent_task_id,
        "branch": get_branch_name(),
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace),
        "matching_artifacts": matching_artifacts,
        "resume_stage": resume_stage,
        "resume_reason": resume_reason,
        "campaign": campaign_info,
        "campaign_ticket": campaign_ticket,
        "awaiting_human_gate": awaiting_human_gate,
    }

    with open(session_file, "w") as f:
        json.dump(session, f, indent=2)

    active_skill_file = context_dir / ".active_skill"
    with open(active_skill_file, "w") as f:
        f.write("ship-feature")

    env_hint_file = context_dir / ".active_skill_env"
    with open(env_hint_file, "w") as f:
        f.write("export CURSOR_ACTIVE_SKILL=ship-feature\n")
        f.write(f"export SHIP_FEATURE_TASK_ID={task_id}\n")

    print(json.dumps(session, indent=2))

    print("\n=== Ship-Feature Session Activated ===", file=sys.stderr)
    print(f"Task ID: {task_id}", file=sys.stderr)
    print(f"Source: {task_source}", file=sys.stderr)
    print(f"Resume Stage: {resume_stage}", file=sys.stderr)
    print(f"Reason: {resume_reason}", file=sys.stderr)
    if campaign_info.get("triggered"):
        camp = campaign_info.get("campaign") or "CAMPAIGN"
        print(f"\n=== {camp} CAMPAIGN MODE ===", file=sys.stderr)
        print(f"Ticket: {campaign_ticket}", file=sys.stderr)
        print(f"Harness kind: {campaign_info.get('harness_kind')}", file=sys.stderr)
        print(f"Git base: {campaign_info.get('git_base') or 'origin/main'}", file=sys.stderr)
        print(
            "Mandatory pauses: Stage 3.9 (implementation approval) and Stage 4.9 (visual QA)",
            file=sys.stderr,
        )
        if campaign_info.get("readiness_gaps"):
            print("Readiness gaps:", file=sys.stderr)
            for gap in campaign_info["readiness_gaps"]:
                print(f"  - {gap}", file=sys.stderr)
        if awaiting_human_gate:
            print(f"AWAITING HUMAN GATE: {awaiting_human_gate}", file=sys.stderr)
        print(
            "See ~/.cursor/skills/andrew-ship-feature/references/parables-campaign-stage-details.md",
            file=sys.stderr,
        )
    if matching_artifacts:
        print("Matching artifacts:", file=sys.stderr)
        for kind, path in matching_artifacts.items():
            print(f"  - {kind}: {path}", file=sys.stderr)
    print(f"\nSession file: {session_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
