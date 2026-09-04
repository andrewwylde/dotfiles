---
name: sssf-unreal
description: Use when adding or operating Unreal Engine editor workflows in an SSSF-enabled repository, including UCP asset mutation, Live Coding compilation, editor-state assertions, bounded repair loops, or UE-specific SSSF onboarding.
---

# SSSF Unreal Extension

## Overview

Extend an existing SSSF installation with repository-stamped Unreal workflows. Do not invent a replacement Unreal plugin: this extension orchestrates the project's existing `UnrealClientProtocol` plugin and keeps agent work separate from deterministic verification.

## Install

1. Confirm core SSSF exists: `adws/adw_modules/agents.py`, `adws/adw_sssf_config/sssf.config.yaml`, and `justfile`.
2. Resolve `scripts/install.py` relative to this skill's installed directory.
3. From the target repository root, run:

```text
uv run <this-skill>/scripts/install.py
```

The installer adds:

- `adw_plan_build_verify_ue.py`, `adw_build_verify_ue.py`, and `adw_character_design.py`
- `adw_modules/ue_gates.py` and `ue_quality.py`
- `scripts/adw_editor_verify.py`, `ue_mcp.py`, and `sssf_onboarding.py`
- dedicated `planner_ue` and `builder_ue` prompts and roster entries
- UE harness rules and `just` recipes

Existing extension-owned files are skipped. Use `--force` only after reviewing and backing up target-owned customizations.

## Run

```text
just sssf-ue-onboarding
just ue-sdlc "<task requiring live editor changes>"
just ue-build "specs/<approved-plan>.md"
just character-design "<character brief>"
```

The editor workflow is `planner_ue` → `builder_ue` → Live Coding compile → editor-state assertions → bounded repairs → commit. A commit occurs only after all applicable checks pass.

## Safety Contract

- Keep `scripts/adw_editor_verify.py` and `scripts/ue_mcp.py` protected from agents.
- Never edit `.uasset` or `.umap` bytes directly; mutate them through Unreal tooling.
- Treat editor/MCP connectivity as verification environment state, not proof that source edits failed.
- Require a falsifiable `verify.yaml`: it must fail before the requested change and pass afterward.
- Snapshot binary assets before the build and reject unchanged binary files claimed as modified.
- Run committing workflows only from a clean or isolated working tree because SSSF commit phases may stage unrelated changes.
- Never migrate runtime state: `.env`, `sssf.db`, sessions, handoffs, `Saved/`, `Intermediate/`, or `Binaries/`.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Building a new bridge/plugin | Use the existing `UnrealClientProtocol` integration. |
| Running UE workflows without core SSSF | Install the `sssf` skill first. |
| Hardcoding an engine or `.uproject` path | Discover both from the target environment. |
| Letting the builder decide whether tests passed | Keep compilation and state checks in deterministic code phases. |
