# SSSF Harness Rules for Unreal Engine Projects

## Protected verification scripts

Treat these as harness code, not feature code:

- `scripts/adw_editor_verify.py`
- `scripts/ue_mcp.py`

They must be listed under `defaults.protected_files` in `adws/adw_sssf_config/sssf.config.yaml`. Agent phases may not overwrite them.

## Builder and verification responsibilities

The `builder_ue` agent writes code and applies editor changes. Deterministic code phases decide whether those changes pass.

- Editor or MCP unavailability is a verification-environment failure, not proof that correctly written source changes failed.
- Builders report `fail` for work they could not apply, invalid code, or write failures.
- Only the workflow's verification result controls whether the commit phase runs.

## Compilation gate

The canonical command is:

```text
uv run --with pyyaml python scripts/adw_editor_verify.py --verify-compilation
```

When the build envelope names changed files, pass them through `--changed-files` so unrelated dirty source does not trigger compilation decisions.

## Editor-state assertions

The planner writes `verify.yaml` into the run handoff. Its assertions must be falsifiable: they fail before the requested change and pass after it. The workflow invokes:

```text
uv run --with pyyaml python scripts/adw_editor_verify.py --spec <verify.yaml>
```

A missing verification spec means editor-state verification is unavailable; it must not be represented as visual or runtime proof.

## Binary assets

Never edit `.uasset` or `.umap` bytes directly. Use Unreal UCP/MCP tools. Snapshot binary hashes immediately before `builder_ue`; reject files whose bytes did not change when the envelope claims they did.

## Working tree safety

Run commit-producing ADWs only in a clean or isolated working tree. SSSF commit phases can stage changes beyond the files named by the agent. Unreal runtime paths (`Saved/`, `Intermediate/`, `DerivedDataCache/`, and build products) must be excluded from commits and tolerated by permission checks.
