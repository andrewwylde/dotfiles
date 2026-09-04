#!/usr/bin/env python3
"""Validate ponder-admin reference audit artifacts for PARABLE-609 children.

Usage:
  python3 reference_audit_gate.py --ticket PARABLE-644 --validate
  python3 reference_audit_gate.py --ticket PARABLE-644 --write --sha <ref_sha> --paths path1,path2
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
    load_manifest,
    normalize_ticket,
    resolve_campaign,
    state_dir,
    utc_now,
    write_json,
)

MARKER = "RUN_BY_SKILL: ship-feature"
REQUIRED_SECTIONS = [
    "## Reference SHA",
    "## Inspected paths",
    "## Preserve / migrate / discard",
    "## Intentional deviations",
]


def audit_path(ticket: str) -> Path:
    return state_dir(ticket) / "reference-audit.md"


def write_stub(ticket: str, ref_sha: str, paths: list[str], dirty_fp: str | None) -> Path:
    lines = [
        f"{MARKER}",
        "",
        f"# Reference audit: {normalize_ticket(ticket)}",
        "",
        "## Reference SHA",
        "",
        f"- branch: `ponder-admin`",
        f"- sha: `{ref_sha}`",
        f"- dirty_fingerprint: `{dirty_fp or 'clean-or-unknown'}`",
        f"- visual_url: `https://local.parable.work:5300/admin/ponder`",
        "",
        "## Inspected paths",
        "",
    ]
    for p in paths:
        lines.append(f"- `{p}` — TODO: classify preserve|migrate|discard")
    lines.extend([
        "",
        "## Preserve / migrate / discard",
        "",
        "| Path | Action | Notes |",
        "|------|--------|-------|",
        "| (fill) | preserve|migrate|discard | ... |",
        "",
        "## Intentional deviations",
        "",
        "- None yet. Detached component plans that ignore host interaction must be rejected.",
        "",
        f"Generated_at: {utc_now()}",
        "",
    ])
    path = audit_path(ticket)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def validate(ticket: str, expected_sha: str | None) -> dict:
    path = audit_path(ticket)
    if not path.is_file():
        return {"passed": False, "path": str(path), "errors": ["missing reference-audit.md"]}
    text = path.read_text(encoding="utf-8")
    errors = []
    if MARKER.lower() not in text.lower():
        errors.append(f"missing marker {MARKER}")
    for section in REQUIRED_SECTIONS:
        if section.lower() not in text.lower():
            errors.append(f"missing section {section}")
    resolved = resolve_campaign(ticket)
    manifest = resolved["manifest"] if resolved else load_manifest()
    found_paths = 0
    for p in manifest.get("reference_paths", []):
        leaf = Path(p).name
        if p in text or leaf in text:
            found_paths += 1
    if found_paths < 3:
        errors.append(
            "audit must mention at least 3 campaign reference paths "
            "(PonderAdminPage / Monaco / tree / picker / bottom-pane)"
        )
    if expected_sha and expected_sha not in text:
        errors.append(f"reference sha mismatch: expected {expected_sha} cited in audit")
    if "discard" not in text.lower() and "migrate" not in text.lower() and "preserve" not in text.lower():
        errors.append("must classify paths as preserve, migrate, or discard")
    return {"passed": len(errors) == 0, "path": str(path), "errors": errors, "paths_cited": found_paths}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write a stub audit for the agent to fill")
    parser.add_argument("--sha", help="Reference SHA to pin")
    parser.add_argument("--dirty-fp")
    parser.add_argument("--paths", help="Comma-separated inspected paths")
    parser.add_argument("--expect-sha")
    args = parser.parse_args()

    ticket = normalize_ticket(args.ticket)
    manifest = load_manifest()
    paths = [p.strip() for p in (args.paths.split(",") if args.paths else manifest.get("reference_paths", [])) if p.strip()]

    if args.write:
        path = write_stub(ticket, args.sha or "UNKNOWN", paths, args.dirty_fp)
        # Also write json gate sidecar
        write_json(state_dir(ticket) / "reference-audit-gate.json", {
            "RUN_BY_SCRIPT": "reference_audit_gate.py",
            "ticket": ticket,
            "audit_path": str(path),
            "generated_at": utc_now(),
        })
        print(json.dumps({"written": str(path)}, indent=2))
        return 0

    result = validate(ticket, args.expect_sha or args.sha)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
