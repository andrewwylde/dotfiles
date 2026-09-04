#!/usr/bin/env python3
"""Detect and load campaign context for ship-feature sessions (multi-campaign).

Usage:
  python3 campaign_context_gate.py --task parable-1045-plot-run
  python3 campaign_context_gate.py --ticket PARABLE-1045 --workspace /path/to/repo
  python3 campaign_context_gate.py --check-only --ticket PARABLE-644

Writes:
  ~/.cursor/ship-feature-state/<campaign>/<ticket>/campaign-snapshot.json
  <workspace>/.context/campaign-gate.json   (if --workspace provided)

Exit 0 always for non-triggered; exit 1 only on hard validation failure when triggered.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from campaign_paths import (  # noqa: E402
    children_meta,
    dirty_fingerprint,
    extract_ticket,
    git_sha,
    is_campaign_child,
    normalize_ticket,
    read_json,
    resolve_campaign,
    resolve_ponder_worktree,
    run,
    state_dir,
    utc_now,
    write_json,
)


def detect_ticket(args: argparse.Namespace) -> str | None:
    if args.ticket:
        return normalize_ticket(args.ticket)
    return extract_ticket(args.task or "", args.branch or "", args.linear_parent or "")


def check_prd_files(manifest: dict, worktree: Path | None) -> list[dict]:
    results = []
    for rel in manifest.get("prd_files", []):
        found = False
        path_tried = []
        candidates = []
        if worktree:
            candidates.append(worktree / rel)
            candidates.append(worktree.parent.parent / "code" / "parable-platform" / rel)
        candidates.append(Path.home() / "code" / "parable-platform" / rel)
        for c in candidates:
            path_tried.append(str(c))
            if c.is_file():
                found = True
                results.append({"path": rel, "status": "found", "resolved": str(c)})
                break
        if not found:
            results.append({
                "path": rel,
                "status": "missing",
                "resolved": None,
                "tried": path_tried,
                "note": "stories/ is gitignored; provide local PRD or record readiness gap",
            })
    return results


def check_reference_url(url: str) -> dict:
    if not url:
        return {"url": url, "reachable": False, "error": "no visual_url"}
    try:
        import urllib.request

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:  # nosec B310 - local admin URL
            return {"url": url, "reachable": True, "status": getattr(resp, "status", None)}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "reachable": False, "error": str(exc)}


def build_snapshot(ticket: str, workspace: Path | None, resolved: dict) -> dict:
    manifest = resolved["manifest"]
    campaign_id = resolved["campaign_id"]
    manifest_path = resolved["manifest_path"]
    harness_kind = children_meta(ticket, manifest).get("harness_kind") or manifest.get(
        "default_harness_kind", "persistent_external"
    )

    ponder = resolve_ponder_worktree(manifest)
    ref_sha = git_sha(ponder, "HEAD") if ponder else None
    dirty = dirty_fingerprint(ponder, manifest.get("reference_paths")) if ponder else None
    main_sha = None
    git_base = manifest.get("git_base") or manifest.get("stack_host") or "origin/main"
    if workspace and workspace.is_dir():
        main_sha = git_sha(workspace, git_base) or git_sha(workspace, "origin/main")
    elif ponder:
        main_sha = git_sha(ponder, "origin/main")

    prd = check_prd_files(manifest, ponder or workspace)
    visual = check_reference_url(manifest.get("visual_url", ""))

    readiness_gaps = []
    if harness_kind == "persistent_external":
        if not ponder:
            readiness_gaps.append("ponder-admin worktree not found")
        if not ref_sha:
            readiness_gaps.append("could not pin ponder-admin HEAD")
        if not visual.get("reachable"):
            readiness_gaps.append(
                f"reference URL unreachable: {manifest.get('visual_url')} "
                "(required for Stage 0.6 baseline; record explicit gap before continuing)"
            )
    elif harness_kind == "app_route":
        if workspace and not (workspace / "apps" / "web-app").is_dir():
            readiness_gaps.append("workspace missing apps/web-app for app_route harness")
        # visual_url probe is soft for app_route — app may not be up yet at activate
        if not visual.get("reachable"):
            readiness_gaps.append(
                f"app_route visual_url not reachable yet: {manifest.get('visual_url')} "
                "(start Vite on the PR worktree before Stage 4.8)"
            )

    if any(p["status"] == "missing" for p in prd):
        readiness_gaps.append("one or more PRD files missing locally")

    parent_md = manifest_path.parent / "parent.md"
    notes = [
        f"Campaign {campaign_id}; harness.kind={harness_kind}.",
        f"Git base / stack host: {git_base}.",
    ]
    if harness_kind == "app_route":
        notes.append(
            "Visual proof drives the regular /admin/ponder app on the PR worktree — "
            "do not add /dev/ponder region mounts."
        )
    else:
        notes.append(
            "Branches/PRs rebase onto origin/main; ponder-admin is reference-only."
        )

    return {
        "RUN_BY_SCRIPT": "campaign_context_gate.py",
        "triggered": True,
        "campaign": campaign_id,
        "ticket": ticket,
        "harness_kind": harness_kind,
        "generated_at": utc_now(),
        "git_base": git_base,
        "stack_host": manifest.get("stack_host") or git_base,
        "visual_url": manifest.get("visual_url"),
        "harness_route": manifest.get("harness_route"),
        "reference_branch": manifest.get("reference_branch"),
        "reference_worktree": str(ponder) if ponder else None,
        "reference_sha": ref_sha,
        "reference_sha_pinned": manifest.get("reference_sha_pinned"),
        "reference_dirty_fingerprint": dirty,
        "main_sha": main_sha,
        "main_baseline_sha_pinned": manifest.get("main_baseline_sha_pinned"),
        "ship_order": manifest.get("ship_order", []),
        "reference_paths": manifest.get("reference_paths", []),
        "scaffold_never_promote": manifest.get("scaffold_never_promote", []),
        "children_meta": children_meta(ticket, manifest),
        "prd_status": prd,
        "visual_probe": visual,
        "readiness_gaps": readiness_gaps,
        "parent_doc": str(parent_md) if parent_md.is_file() else None,
        "manifest_path": str(manifest_path),
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="Task id from ship-feature session")
    parser.add_argument("--ticket", help="Explicit Linear ticket id")
    parser.add_argument("--branch", help="Git branch name")
    parser.add_argument("--linear-parent", help="Parent Linear id if known")
    parser.add_argument("--workspace", type=Path, help="Repo/worktree root for .context write")
    parser.add_argument("--check-only", action="store_true", help="Do not write artifacts")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    ticket = detect_ticket(args)
    resolved = resolve_campaign(ticket) if ticket else None
    parent_resolved = (
        resolve_campaign(normalize_ticket(args.linear_parent))
        if args.linear_parent
        else None
    )
    triggered = resolved is not None or parent_resolved is not None

    if not triggered:
        payload = {
            "RUN_BY_SCRIPT": "campaign_context_gate.py",
            "triggered": False,
            "reason": "not a known campaign child",
            "ticket": ticket,
            "generated_at": utc_now(),
        }
        if args.workspace and not args.check_only:
            write_json(Path(args.workspace) / ".context" / "campaign-gate.json", payload)
        print(json.dumps(payload, indent=2))
        return 0

    if not ticket and parent_resolved:
        # Parent alone is not enough to write per-ticket state
        print(json.dumps({
            "RUN_BY_SCRIPT": "campaign_context_gate.py",
            "triggered": True,
            "error": "campaign triggered but ticket could not be resolved",
            "campaign": parent_resolved["campaign_id"],
        }, indent=2))
        return 1

    if not ticket or not resolved:
        print(json.dumps({
            "RUN_BY_SCRIPT": "campaign_context_gate.py",
            "triggered": True,
            "error": "campaign triggered but ticket could not be resolved",
        }, indent=2))
        return 1

    snapshot = build_snapshot(ticket, args.workspace, resolved)
    if not args.check_only:
        snap_path = state_dir(ticket) / "campaign-snapshot.json"
        write_json(snap_path, snapshot)
        snapshot["snapshot_path"] = str(snap_path)
        if args.workspace:
            write_json(Path(args.workspace) / ".context" / "campaign-gate.json", {
                "RUN_BY_SCRIPT": "campaign_context_gate.py",
                "triggered": True,
                "ticket": ticket,
                "campaign": resolved["campaign_id"],
                "harness_kind": snapshot["harness_kind"],
                "snapshot_path": str(snap_path),
                "readiness_gaps": snapshot["readiness_gaps"],
                "generated_at": utc_now(),
            })

    print(json.dumps(snapshot, indent=2))
    _ = (is_campaign_child, read_json, run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
