#!/usr/bin/env python3
"""Backward-compatible re-exports for PARABLE-609 ship-feature gates.

New code should import from campaign_paths.py (multi-campaign).
"""
from __future__ import annotations

from campaign_paths import (  # noqa: F401
    CAMPAIGN_ID,
    MANIFEST_PATH,
    SKILL_ROOT,
    STATE_ROOT,
    dirty_fingerprint,
    expand_home,
    extract_ticket,
    git_sha,
    is_campaign_child,
    load_manifest,
    normalize_ticket,
    read_json,
    resolve_ponder_worktree,
    run,
    sha256_file,
    sha256_text,
    state_dir,
    utc_now,
    write_json,
)
