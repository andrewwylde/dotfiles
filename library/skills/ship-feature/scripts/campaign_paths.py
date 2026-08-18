#!/usr/bin/env python3
"""Multi-campaign path helpers for user-scoped ship-feature gates.

Discovers manifests under references/campaigns/*/manifest.json and resolves
a ticket to its campaign. PARABLE-609 and PARABLE-613 (and future campaigns)
share this loader.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGNS_DIR = SKILL_ROOT / "references" / "campaigns"
TICKET_RE = re.compile(r"PARABLE-(\d+)", re.I)

# Backward-compat aliases used by older scripts/tests.
CAMPAIGN_ID = "PARABLE-609"
MANIFEST_PATH = CAMPAIGNS_DIR / "parable-609" / "manifest.json"
STATE_ROOT = Path.home() / ".cursor" / "ship-feature-state" / "parable-609"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expand_home(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def normalize_ticket(ticket: str) -> str:
    ticket = ticket.strip().upper()
    if ticket.startswith("PARABLE-"):
        return ticket
    m = TICKET_RE.search(ticket)
    if m:
        return f"PARABLE-{m.group(1)}"
    return ticket


def extract_ticket(*texts: str) -> str | None:
    for text in texts:
        if not text:
            continue
        m = TICKET_RE.search(text)
        if m:
            return f"PARABLE-{m.group(1)}"
    return None


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


@lru_cache(maxsize=1)
def list_campaign_manifests() -> tuple[Path, ...]:
    if not CAMPAIGNS_DIR.is_dir():
        return ()
    paths = sorted(CAMPAIGNS_DIR.glob("*/manifest.json"))
    return tuple(paths)


def load_manifest_from(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(campaign: str | None = None) -> dict:
    """Load a campaign manifest. Default: PARABLE-609 (backward compatible)."""
    if campaign is None or normalize_ticket(campaign) == "PARABLE-609":
        return load_manifest_from(MANIFEST_PATH)
    resolved = resolve_campaign(campaign)
    if not resolved:
        raise FileNotFoundError(f"no campaign manifest for {campaign}")
    return resolved["manifest"]


def _campaign_id(manifest: dict, path: Path) -> str:
    raw = manifest.get("campaign") or path.parent.name
    return normalize_ticket(str(raw))


def resolve_campaign(ticket: str | None) -> dict | None:
    """Return {campaign_id, manifest, manifest_path, state_root} for a ticket."""
    if not ticket:
        return None
    ticket = normalize_ticket(ticket)
    for path in list_campaign_manifests():
        try:
            manifest = load_manifest_from(path)
        except (json.JSONDecodeError, OSError):
            continue
        campaign_id = _campaign_id(manifest, path)
        children = {normalize_ticket(c) for c in manifest.get("children", [])}
        meta_keys = {normalize_ticket(k) for k in (manifest.get("children_meta") or {})}
        if ticket == campaign_id or ticket in children or ticket in meta_keys:
            state_root_raw = manifest.get("state_root") or f"~/.cursor/ship-feature-state/{campaign_id.lower()}"
            return {
                "campaign_id": campaign_id,
                "manifest": manifest,
                "manifest_path": path,
                "state_root": expand_home(state_root_raw),
            }
    return None


def is_campaign_child(ticket: str | None, manifest: dict | None = None) -> bool:
    """True if ticket belongs to any known campaign (or the given manifest)."""
    if not ticket:
        return False
    ticket = normalize_ticket(ticket)
    if manifest is not None:
        campaign_id = normalize_ticket(str(manifest.get("campaign", "")))
        children = {normalize_ticket(c) for c in manifest.get("children", [])}
        return ticket == campaign_id or ticket in children
    return resolve_campaign(ticket) is not None


def children_meta(ticket: str, manifest: dict | None = None) -> dict:
    ticket = normalize_ticket(ticket)
    if manifest is None:
        resolved = resolve_campaign(ticket)
        manifest = resolved["manifest"] if resolved else {}
    meta = manifest.get("children_meta") or {}
    return dict(meta.get(ticket) or {})


def state_dir(ticket: str, campaign_id: str | None = None) -> Path:
    ticket = normalize_ticket(ticket)
    resolved = resolve_campaign(ticket)
    if resolved:
        root = resolved["state_root"]
    elif campaign_id:
        root = Path.home() / ".cursor" / "ship-feature-state" / normalize_ticket(campaign_id).lower()
    else:
        root = STATE_ROOT
    path = root / ticket.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


def matrix_templates_dir(ticket: str | None = None, campaign_id: str | None = None) -> Path:
    if ticket:
        resolved = resolve_campaign(ticket)
        if resolved:
            return resolved["manifest_path"].parent / "matrix-templates"
    if campaign_id:
        slug = normalize_ticket(campaign_id).lower().replace("_", "-")
        # campaign folders use parable-609 style
        for path in list_campaign_manifests():
            if _campaign_id(load_manifest_from(path), path) == normalize_ticket(campaign_id):
                return path.parent / "matrix-templates"
        return CAMPAIGNS_DIR / slug / "matrix-templates"
    return CAMPAIGNS_DIR / "parable-609" / "matrix-templates"


def resolve_ponder_worktree(manifest: dict | None = None) -> Path | None:
    manifest = manifest or load_manifest()
    hint_raw = manifest.get("reference_worktree_hint", "")
    if not hint_raw:
        return None
    hint = expand_home(hint_raw)
    ref_branch = manifest.get("reference_branch", "ponder-admin")
    if hint.is_dir() and ((hint / ".git").exists() or (hint / ".git").is_file()):
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=hint)
        if branch.returncode == 0 and branch.stdout.strip() == ref_branch:
            return hint
    wt = run(["git", "worktree", "list", "--porcelain"])
    if wt.returncode != 0:
        return hint if hint.is_dir() else None
    current_path = None
    for line in wt.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.split(" ", 1)[1])
        elif line.startswith("branch ") and ref_branch in line and current_path:
            return current_path
    return hint if hint.is_dir() else None


def git_sha(cwd: Path, ref: str = "HEAD") -> str | None:
    result = run(["git", "rev-parse", ref], cwd=cwd)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def dirty_fingerprint(cwd: Path, paths: list[str] | None = None) -> str:
    cmd = ["git", "status", "--porcelain"]
    if paths:
        cmd.append("--")
        cmd.extend(paths)
    status = run(cmd, cwd=cwd)
    diff_cmd = ["git", "diff", "HEAD"]
    if paths:
        diff_cmd.append("--")
        diff_cmd.extend(paths)
    diff = run(diff_cmd, cwd=cwd)
    return sha256_text((status.stdout or "") + "\n" + (diff.stdout or ""))


def harness_kind_for(ticket: str) -> str:
    meta = children_meta(ticket)
    if meta.get("harness_kind"):
        return str(meta["harness_kind"])
    resolved = resolve_campaign(ticket)
    if resolved:
        default = (resolved["manifest"].get("default_harness_kind")
                   or ("app_route" if resolved["campaign_id"] != "PARABLE-609" else "persistent_external"))
        return str(default)
    return "persistent_external"
