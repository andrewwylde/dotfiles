#!/usr/bin/env python3
"""Persist ship-feature stage compliance checks to .context and manifest.

Called from enforce-gate.sh on every ship-feature write/strreplace attempt.
No human action required — artifacts are written and registered automatically.

Usage (hook-internal):
  python3 record_stage_compliance.py \\
    --workspace /path/to/repo \\
    --action strreplace \\
    --file services/foo/bar.rs \\
    --allowed 0
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COMPLIANCE_SCRIPT = Path(__file__).resolve().parent / "stage_compliance_check.py"
MANIFEST = Path.home() / ".cursor/scripts/manifest.py"
GATE_PREFIXES = ("services/", "apps/", "infrastructure/", "utils/", "platform-schemas/")


def is_gated_source(path: str) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    if p.startswith("plans/") or p.startswith(".context/"):
        return False
    return any(p.startswith(prefix) or f"/{prefix}" in p for prefix in GATE_PREFIXES)


def load_task_id(workspace: Path) -> str | None:
    session = workspace / ".context/ship-feature-session.json"
    if not session.is_file():
        return None
    try:
        data = json.loads(session.read_text())
        return data.get("task_id")
    except (json.JSONDecodeError, OSError):
        return None


def run_compliance(gate: str, workspace: Path, task_id: str | None) -> dict:
    cmd = ["python3", str(COMPLIANCE_SCRIPT), "--gate", gate]
    if task_id and gate == "stage4":
        cmd.extend(["--task", task_id])
    proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
    lines = (proc.stdout or "").strip().splitlines()
    checks = []
    for line in lines:
        if line.startswith("PASS  ") or line.startswith("FAIL  "):
            status, rest = line.split("  ", 1)
            name, _, detail = rest.partition(": ")
            checks.append({"name": name, "passed": status == "PASS", "detail": detail})
    return {
        "gate": gate,
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "checks": checks,
        "raw_tail": "\n".join(lines[-6:]),
    }


def register_manifest(workspace: Path, rel_path: str, task_id: str | None, tags: str) -> None:
    if not MANIFEST.is_file():
        return
    cmd = [
        "python3",
        str(MANIFEST),
        "register",
        "--skill",
        "ship-feature",
        "--path",
        rel_path,
        "--type",
        "compliance-gate",
        "--tags",
        tags,
    ]
    if task_id:
        cmd.extend(["--task", task_id])
    subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)


def write_artifacts(
    workspace: Path,
    task_id: str | None,
    action: str,
    target_file: str,
    allowed: bool,
    stage4: dict,
    stage6: dict | None,
    next_action: dict | None = None,
) -> tuple[Path, Path]:
    out_dir = workspace / ".context/ship-feature-gates"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = (task_id or "unknown-task").replace("/", "-")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    payload = {
        "RUN_BY_SCRIPT": "record_stage_compliance.py",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "action": action,
        "target_file": target_file,
        "hook_allowed": allowed,
        "stage4": stage4,
        "stage6": stage6,
        "next_action": next_action,
    }

    json_path = out_dir / f"{slug}_compliance_{ts}.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    latest_json = out_dir / "latest-compliance.json"
    latest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "RUN_BY_SCRIPT: record_stage_compliance.py",
        "",
        "# Ship-Feature Compliance Gate Record",
        "",
        f"**Recorded:** {payload['recorded_at']}",
        f"**Task:** {task_id or 'unknown'}",
        f"**Action:** {action} on `{target_file}`",
        f"**Hook allowed:** {allowed}",
        "",
        "## Stage 4",
        f"**Passed:** {stage4['passed']} (exit {stage4['exit_code']})",
        "",
    ]
    for check in stage4.get("checks", []):
        mark = "x" if check["passed"] else " "
        md_lines.append(f"- [{mark}] {check['name']}: {check['detail']}")
    if next_action:
        md_lines.extend([
            "",
            "## Self-heal (harness-first)",
            f"**Next action:** {next_action.get('prompt', '')}",
            f"**Verify:** {next_action.get('verify', '')}",
        ])
    if stage6:
        md_lines.extend(["", "## Stage 6 (snapshot)", f"**Passed:** {stage6['passed']}", ""])
        for check in stage6.get("checks", []):
            mark = "x" if check["passed"] else " "
            md_lines.append(f"- [{mark}] {check['name']}: {check['detail']}")

    md_path = out_dir / f"{slug}_compliance_{ts}.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    (out_dir / "latest-compliance.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    index_path = out_dir / "index.json"
    index: list[dict] = []
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text())
        except json.JSONDecodeError:
            index = []
    index.append(
        {
            "task_id": task_id,
            "timestamp": ts,
            "json": str(json_path.relative_to(workspace)),
            "markdown": str(md_path.relative_to(workspace)),
            "hook_allowed": allowed,
            "stage4_passed": stage4["passed"],
        }
    )
    index_path.write_text(json.dumps(index[-50:], indent=2) + "\n", encoding="utf-8")
    register_manifest(workspace, str(json_path.relative_to(workspace)), task_id, "compliance,stage4,hook")
    register_manifest(workspace, str(md_path.relative_to(workspace)), task_id, "compliance,stage4,hook")
    register_manifest(workspace, str(latest_json.relative_to(workspace)), task_id, "compliance,latest")
    register_manifest(workspace, ".context/ship-feature-gates/index.json", task_id, "compliance,index")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--action", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--allowed", type=int, choices=[0, 1], required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not is_gated_source(args.file):
        return 0

    task_id = load_task_id(workspace)
    stage4 = run_compliance("stage4", workspace, task_id)
    stage6 = run_compliance("stage6-complete", workspace, task_id)

    recovery_script = Path(__file__).resolve().parent / "harness_recovery.py"
    next_action: dict | None = None
    if not stage4["passed"]:
        proc = subprocess.run(
            ["python3", str(recovery_script), "--gate", "stage4", "--format", "json"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        try:
            next_action = json.loads(proc.stdout).get("recovery")
        except (json.JSONDecodeError, AttributeError):
            next_action = None

    write_artifacts(workspace, task_id, args.action, args.file, bool(args.allowed), stage4, stage6, next_action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
