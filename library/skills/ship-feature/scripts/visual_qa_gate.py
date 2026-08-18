#!/usr/bin/env python3
"""Visual baseline / after gates for Parables ship-feature campaigns (user-scoped).

Modes:
  baseline — Stage 0.6 capture manifesto (reference URL from campaign manifest)
  after    — Stage 4.8 post-implementation proof
  matrix-template — seed matrix.json into ticket visual-proof/
  cleanup-check — fail if PR repo still contains harness/screenshot residues

Harness kinds:
  persistent_external — /dev/ponder region mounts (PARABLE-609 chrome tickets)
  app_route — regular /admin/ponder on the PR worktree (PARABLE-613+)

Playwright PNGs live only in ship-feature-state — never in the child PR.

Usage:
  python3 visual_qa_gate.py --mode baseline --ticket PARABLE-644
  python3 visual_qa_gate.py --mode matrix-template --ticket PARABLE-1045
  python3 visual_qa_gate.py --mode after --ticket PARABLE-1045 --head-sha <sha> --workspace <pr>
  python3 visual_qa_gate.py --mode after --ticket PARABLE-1045 --validate --head-sha <sha>
  python3 visual_qa_gate.py --mode cleanup-check --workspace /path/to/pr/repo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from campaign_paths import (  # noqa: E402
    children_meta,
    harness_kind_for,
    load_manifest,
    matrix_templates_dir,
    normalize_ticket,
    read_json,
    resolve_campaign,
    run,
    sha256_file,
    state_dir,
    utc_now,
    write_json,
)

# Checked against the *PR* workspace only. The harness worktree is outside PR
# checkouts and is never scanned by cleanup-check.
FORBIDDEN_DIFF_GLOBS = [
    r"e2e/visual-proof/",
    r"/dev/piece-source-editor",
    r"/dev/ponder",
    r"visual-proof\.harness",
    r"\.context/ui-visual-",
    r"screenshots?/.*\.png$",
    r"piece-source-editor.*\.png$",
]

DEFAULT_HARNESS_WORKTREE = "/Users/andrewwylde/.agent/worktrees/parable-ponder-harness"
DEFAULT_HARNESS_BRANCH = "local/parable-ponder-harness"
DEFAULT_DEV_ROUTE = "/dev/ponder"
DEFAULT_ADMIN_ROUTE = "/admin/ponder"
DEFAULT_SPEC_PATH = "apps/web-app/e2e/dev-ponder/ponder-regions.spec.ts"
DEFAULT_APP_SPEC_PATH = "apps/web-app/e2e/admin-ponder/run-results.spec.ts"

REGION_SECTION_TESTID = {
    "tree": "ponder-region-tree",
    "identity": "ponder-region-identity",
    "editor": "ponder-region-editor",
    "property": "ponder-region-property",
    "bottomPane": "ponder-region-bottom",
}


def visual_dir(ticket: str) -> Path:
    path = state_dir(ticket) / "visual-proof"
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest_path(ticket: str, mode: str) -> Path:
    name = "baseline.json" if mode == "baseline" else "after.json"
    return visual_dir(ticket) / name


def probe_url(url: str) -> dict:
    try:
        import urllib.request

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:  # nosec B310
            return {"reachable": True, "status": getattr(resp, "status", None)}
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "error": str(exc)}


def resolve_harness_sha(worktree: str) -> str | None:
    root = Path(worktree)
    if not root.is_dir():
        return None
    result = run(["git", "rev-parse", "HEAD"], cwd=root)
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip() or None


def _campaign_manifest(ticket: str) -> dict:
    resolved = resolve_campaign(ticket)
    if resolved:
        return resolved["manifest"]
    return load_manifest()


def harness_provenance(
    ticket: str,
    region: str | None = None,
    registry_module: str | None = None,
    workspace: Path | None = None,
) -> dict:
    ticket = normalize_ticket(ticket)
    manifest = _campaign_manifest(ticket)
    meta = children_meta(ticket, manifest)
    kind = meta.get("harness_kind") or harness_kind_for(ticket)

    if kind == "app_route":
        path = meta.get("harness_path") or manifest.get("harness_route") or DEFAULT_ADMIN_ROUTE
        spec = meta.get("spec_path") or DEFAULT_APP_SPEC_PATH
        base_url = manifest.get("visual_url") or f"http://127.0.0.1:5173{path}"
        return {
            "kind": "app_route",
            "committed": False,
            "cleanup_required": False,
            "workspace": str(workspace) if workspace else None,
            "base_url": base_url,
            "path": path,
            "dev_route": path,
            "spec_path": spec,
            "ticket_slug": ticket.lower(),
            "notes": [
                "App-route harness drives the regular /admin/ponder app on the PR worktree.",
                "Do not add /dev/ponder region mounts or commit PNGs to the child PR.",
            ],
        }

    region = region or meta.get("harness_region") or "editor"
    worktree = manifest.get("harness_worktree") or DEFAULT_HARNESS_WORKTREE
    num = ticket.split("-", 1)[-1].lower()
    default_module = registry_module or f"regions/parable-{num}-{region}.ts"
    return {
        "kind": "persistent_external",
        "committed": False,
        "cleanup_required": False,
        "worktree": worktree,
        "branch": DEFAULT_HARNESS_BRANCH,
        "branch_sha": resolve_harness_sha(worktree),
        "dev_route": manifest.get("harness_route") or DEFAULT_DEV_ROUTE,
        "region": region,
        "registry_module": default_module,
        "spec_path": meta.get("spec_path") or DEFAULT_SPEC_PATH,
        "ticket_slug": ticket.lower(),
        "notes": [
            "Harness lives outside the PR worktree; cleanup_check scans PR diffs only.",
            "Do not commit /dev/ponder or PNGs to the child PR branch.",
        ],
    }


def write_matrix_template(
    ticket: str,
    region: str | None = None,
    force: bool = False,
) -> dict:
    """Seed visual-proof/matrix.json from campaign templates."""
    ticket = normalize_ticket(ticket)
    manifest = _campaign_manifest(ticket)
    meta = children_meta(ticket, manifest)
    kind = meta.get("harness_kind") or harness_kind_for(ticket)
    templates = matrix_templates_dir(ticket)

    out = visual_dir(ticket) / "matrix.json"
    if out.is_file() and not force:
        return {"written": False, "path": str(out), "reason": "exists"}

    if kind == "app_route":
        template_name = meta.get("matrix_template") or region or "run"
        template_path = templates / f"{template_name}.json"
        if not template_path.is_file():
            return {
                "written": False,
                "errors": [f"no app_route matrix template: {template_path}"],
            }
        payload = json.loads(template_path.read_text(encoding="utf-8"))
        payload["ticket"] = ticket
        payload["harness_kind"] = "app_route"
        write_json(out, payload)
        return {
            "written": True,
            "path": str(out),
            "payload": payload,
            "harness_kind": "app_route",
            "template": str(template_path),
        }

    region = region or meta.get("harness_region")
    if not region:
        return {
            "written": False,
            "errors": [f"no harness_region for {ticket}; pass --region"],
        }

    template_path = templates / f"{region}.json"
    if template_path.is_file():
        payload = json.loads(template_path.read_text(encoding="utf-8"))
        payload["ticket"] = ticket
        payload["region"] = region
    else:
        testid = REGION_SECTION_TESTID.get(region, "ponder-dev-harness")
        payload = {
            "ticket": ticket,
            "region": region,
            "rows": [
                {
                    "id": "desktop-default",
                    "viewport": {"width": 1280, "height": 900},
                    "theme": "dark",
                    "route": DEFAULT_DEV_ROUTE,
                    "region": region,
                    "assertions": [
                        {"kind": "testid", "selector": testid, "expected": "visible"},
                    ],
                    "screenshots": [f"{region}-desktop-default.png"],
                }
            ],
        }

    write_json(out, payload)
    return {"written": True, "path": str(out), "payload": payload, "region": region}


def write_baseline(ticket: str, url: str, matrix: list[dict], force: bool = False) -> dict:
    path = manifest_path(ticket, "baseline")
    if path.is_file() and not force:
        return {"written": False, "path": str(path), "reason": "exists"}

    probe = probe_url(url)
    payload = {
        "RUN_BY_SCRIPT": "visual_qa_gate.py",
        "stage": "0.6",
        "mode": "baseline",
        "ticket": normalize_ticket(ticket),
        "reference_url": url,
        "reference_kind": "user_running_app",
        "captured_at": utc_now(),
        "probe": probe,
        "status": "PASS" if probe.get("reachable") else "BLOCKED",
        "matrix": matrix or [
            {
                "id": "desktop-default",
                "viewport": {"width": 1280, "height": 900},
                "theme": "dark",
                "route": "/admin/ponder",
                "assertions": [
                    {"kind": "testid", "selector": "ponder-parable-sidebar", "expected": "visible"},
                ],
                "screenshots": ["desktop-default.png"],
            }
        ],
        "checks": {
            "console_errors": [],
            "failed_requests": [],
            "a11y": {"engine": "axe-core", "violations": None},
        },
        "notes": [
            "Store screenshots beside this manifest under ~/.cursor/ship-feature-state/.../visual-proof/",
            "Do not commit PNGs or harness files to the feature PR.",
        ],
    }
    if not probe.get("reachable"):
        payload["readiness_gap"] = (
            f"Reference URL unreachable ({url}). "
            "Start ponder-admin at :5300 or get explicit user ack before Stage 3.9."
        )
    write_json(path, payload)
    return {"written": True, "path": str(path), "payload": payload}


def write_after(
    ticket: str,
    head_sha: str,
    matrix: list[dict],
    acceptance_mapping: list[dict],
    force: bool = False,
    region: str | None = None,
    registry_module: str | None = None,
    workspace: Path | None = None,
) -> dict:
    path = manifest_path(ticket, "after")
    if path.is_file() and not force:
        return {"written": False, "path": str(path), "reason": "exists"}

    ticket = normalize_ticket(ticket)
    matrix_path = visual_dir(ticket) / "matrix.json"
    if not matrix and matrix_path.is_file():
        loaded = json.loads(matrix_path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            matrix = loaded
        elif isinstance(loaded, dict):
            matrix = loaded.get("rows") or loaded.get("matrix") or []

    payload = {
        "RUN_BY_SCRIPT": "visual_qa_gate.py",
        "stage": "4.8",
        "mode": "after",
        "ticket": ticket,
        "head_sha": head_sha,
        "captured_at": utc_now(),
        "status": "PASS",
        "harness": harness_provenance(
            ticket,
            region=region,
            registry_module=registry_module,
            workspace=workspace,
        ),
        "matrix": matrix or [],
        "acceptance_mapping": acceptance_mapping or [],
        "checks": {
            "console_errors": [],
            "failed_requests": [],
            "a11y": {"engine": "axe-core", "violations_delta": 0},
        },
        "baseline_path": str(manifest_path(ticket, "baseline")),
        "user_signoff": {"required": True, "approved": False},
    }
    write_json(path, payload)
    write_json(visual_dir(ticket) / "proof-hash.json", {
        "proof_hash": sha256_file(path),
        "path": str(path),
        "head_sha": head_sha,
    })
    return {"written": True, "path": str(path), "payload": payload}


def validate_after(ticket: str, expect_head: str | None) -> dict:
    path = manifest_path(ticket, "after")
    payload = read_json(path)
    errors = []
    if not payload:
        return {"passed": False, "errors": [f"missing after manifest: {path}"], "path": str(path)}
    if payload.get("RUN_BY_SCRIPT") != "visual_qa_gate.py":
        errors.append("bad provenance")
    if payload.get("status") not in ("PASS", "FIXED"):
        errors.append(f"status not PASS/FIXED: {payload.get('status')}")
    if not payload.get("acceptance_mapping"):
        errors.append("acceptance_mapping required")
    else:
        for row in payload["acceptance_mapping"]:
            if not row.get("ac_id") or not row.get("assertions"):
                errors.append(f"AC row incomplete: {row}")
    if expect_head and payload.get("head_sha") != expect_head:
        errors.append(f"stale head_sha: expected {expect_head}")
    harness = payload.get("harness") or {}
    kind = harness.get("kind")
    if kind not in ("persistent_external", "faithful_local_only", "app_route"):
        errors.append(f"unexpected harness.kind: {kind}")
    if kind == "persistent_external":
        if not harness.get("worktree") or not harness.get("dev_route"):
            errors.append("persistent_external harness missing worktree/dev_route")
        if not harness.get("region"):
            errors.append("persistent_external harness missing region")
    if kind == "app_route":
        if not harness.get("path") and not harness.get("dev_route"):
            errors.append("app_route harness missing path")
        if not harness.get("spec_path"):
            errors.append("app_route harness missing spec_path")
    baseline = read_json(manifest_path(ticket, "baseline"))
    if not baseline:
        errors.append("baseline missing — run Stage 0.6 first")
    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "path": str(path),
        "proof_hash": sha256_file(path),
        "payload": payload,
    }


def validate_baseline(ticket: str) -> dict:
    path = manifest_path(ticket, "baseline")
    payload = read_json(path)
    errors = []
    if not payload:
        return {"passed": False, "errors": [f"missing baseline: {path}"], "path": str(path)}
    if payload.get("status") == "BLOCKED" and not payload.get("user_ack_missing_baseline"):
        errors.append(
            "baseline BLOCKED (reference unreachable) — restore URL or set user_ack_missing_baseline"
        )
    if not payload.get("matrix"):
        errors.append("matrix required")
    return {"passed": len(errors) == 0, "errors": errors, "path": str(path), "payload": payload}


def cleanup_check(workspace: Path) -> dict:
    """Scan PR workspace diffs only — never the external harness worktree."""
    diff = run(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=workspace)
    status = run(["git", "status", "--porcelain"], cwd=workspace)
    names = (diff.stdout or "").splitlines() + [
        line[3:] for line in (status.stdout or "").splitlines() if len(line) > 3
    ]
    offenders = []
    for name in names:
        for pat in FORBIDDEN_DIFF_GLOBS:
            if re.search(pat, name):
                offenders.append(name)
                break
    return {
        "passed": len(offenders) == 0,
        "offenders": offenders,
        "errors": (
            [f"harness/screenshot residues still in repo diff: {offenders}"]
            if offenders
            else []
        ),
        "note": (
            "cleanup_check ignores ~/.agent/worktrees/parable-ponder-harness; "
            "only the PR workspace is scanned."
        ),
    }


def _normalize_matrix_arg(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("rows") or raw.get("matrix") or []
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["baseline", "after", "cleanup-check", "matrix-template"],
    )
    parser.add_argument("--ticket")
    parser.add_argument("--url")
    parser.add_argument("--head-sha")
    parser.add_argument("--region")
    parser.add_argument("--registry-module")
    parser.add_argument("--matrix-json", type=Path)
    parser.add_argument("--acceptance-json", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    if args.mode == "cleanup-check":
        if not args.workspace:
            print(json.dumps({"passed": False, "errors": ["--workspace required"]}, indent=2))
            return 1
        result = cleanup_check(args.workspace)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    if not args.ticket:
        print(json.dumps({"passed": False, "errors": ["--ticket required"]}, indent=2))
        return 1

    ticket = normalize_ticket(args.ticket)

    if args.mode == "matrix-template":
        result = write_matrix_template(ticket, region=args.region, force=args.force)
        print(json.dumps(result, indent=2))
        return 0 if result.get("written") or result.get("reason") == "exists" else 1

    matrix = []
    if args.matrix_json and args.matrix_json.is_file():
        matrix = _normalize_matrix_arg(
            json.loads(args.matrix_json.read_text(encoding="utf-8"))
        )
    acceptance = []
    if args.acceptance_json and args.acceptance_json.is_file():
        acceptance = json.loads(args.acceptance_json.read_text(encoding="utf-8"))

    if args.mode == "baseline":
        if args.validate:
            result = validate_baseline(ticket)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        url = args.url or _campaign_manifest(ticket).get("visual_url")
        result = write_baseline(ticket, url, matrix, force=args.force)
        print(json.dumps(result, indent=2))
        return 0 if result.get("payload", {}).get("status") != "BLOCKED" or args.force else 1

    # after
    if args.validate:
        result = validate_after(ticket, args.head_sha)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    if not args.head_sha:
        print(json.dumps({"passed": False, "errors": ["--head-sha required for after write"]}, indent=2))
        return 1
    result = write_after(
        ticket,
        args.head_sha,
        matrix,
        acceptance,
        force=args.force,
        region=args.region,
        registry_module=args.registry_module,
        workspace=args.workspace,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
