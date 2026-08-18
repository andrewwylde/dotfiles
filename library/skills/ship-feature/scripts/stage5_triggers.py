#!/usr/bin/env python3
"""Shared Stage 5 CI trigger predicates (SSOT for gate / router / prefLights).

Keep "does this diff trigger job X?" in one place. Drift between stage5_push_gate,
commit_push_pr_preflight, and language prefLights caused deny-message loops
(PARABLE-451 review R2).
"""
from __future__ import annotations

RUST_TRIGGER_FILES: frozenset[str] = frozenset(
    {
        "rust-toolchain.toml",
        "rustfmt.toml",
        "clippy.toml",
    }
)

RUST_TRIGGER_PREFIXES: tuple[str, ...] = (
    "platform-schemas/services/",
    "utils/scalar-lib/core/",
)


def rust_paths_trigger(files: list[str]) -> bool:
    """True when branch/staged paths should produce a rust Stage 5 artifact."""
    for path in files:
        if (
            path.endswith(".rs")
            or path.endswith("Cargo.toml")
            or path.endswith("Cargo.lock")
        ):
            return True
        if path in RUST_TRIGGER_FILES:
            return True
        if any(path.startswith(prefix) for prefix in RUST_TRIGGER_PREFIXES):
            return True
    return False


def rust_has_crate_sources(files: list[str]) -> bool:
    """True when diff includes paths that map to workspace crates for clippy/test."""
    return any(path.endswith(".rs") or path.endswith("Cargo.toml") for path in files)
