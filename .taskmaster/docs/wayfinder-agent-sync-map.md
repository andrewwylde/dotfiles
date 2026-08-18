# Wayfinder map: agent-sync Library fan-out

> Tracker: Task Master tag `agent-sync` (tasks + subtasks). This file is the map index only — decisions live on their tasks.

## Destination

A working `agent-sync` Rust CLI in this repo that owns an agent-neutral `library/`, generates light per-Target Wrappers from Manifests, and fans out skills, commands, agents, and hooks to Claude Code, Cursor, OpenCode, and Pi (hybrid symlink/copy; Cursor always copy). Coexists with `npx skills` for third-party installs. `~/.agents/` is npx territory (not a v1 Fan-out Target).

## Notes

- Domain glossary: repo-root `CONTEXT.md`
- Tracker: Task Master tag **`agent-sync`**
- **Standing preference:** auto-approve recommended locks; do not pause for HITL review unless the user re-opens grilling
- Plan until the route is clear; prototype may produce a throwaway Fan-out demo, not production migrate
- Locks: [locked-manifest-schema.md](./locked-manifest-schema.md), [locked-grills-batch.md](./locked-grills-batch.md)
- Prototype asset (task 10): [prototype-one-skill-fan-out.md](./prototype-one-skill-fan-out.md) · `.taskmaster/prototype-fanout/run.sh`

## Decisions so far

- Destination — working `agent-sync` tool
- Library — `library/{skills,commands,agents,hooks}/`
- Generation — shared body + Manifest overlays
- Install — hybrid; **Cursor always copy**; coerce copy if parent is symlink
- v1 Targets — Claude Code, Cursor, OpenCode, Pi (**not** `.agents`)
- Fan-out names — `andrew-<name>`; vendor `vendor-cursor-<name>`; Library dirs unprefixed
- Manifest — opt-in `manifest.toml`; dir-per-item; exclude-only; frontmatter deep-merge + `body_append`; see [locked-manifest-schema.md](./locked-manifest-schema.md)
- Local-wins — whole-item replace + tombstones; local > in-clone private > public
- Migrate UX — `--dry-run`|`--write`; backups + explicit `--rollback`
- Setup — mac+WSL install via common.sh; mac-setup rcup/sync parity; `sync-ai-assistants` deleted after migrate cutover
- Migration — one-shot into Library; stop versioning per-Target trees
- CLI — Rust; `sync` / `verify` / `migrate` / `list` / `doctor`; Release binaries + cargo fallback
- Output — Target home dirs only
- Hooks — tagged `_as` merge; packs in Library
- Third-party — `npx skills`
- Research + inventory — see prior task answers / `.taskmaster/docs/research-*.md` + [inventory-migrate-scope.md](./inventory-migrate-scope.md)
- [Prototype one skill fan-out to two Targets](../tasks/tasks.json) — shape accepted; see [prototype-one-skill-fan-out.md](./prototype-one-skill-fan-out.md)
- Production migrate — Library populated; dual trees emptied in clone; home Target dirs detached from repo symlinks

## Not yet specified

- Release signing / attestation (optional)
- Tombstone on-disk marker exact path (behavior locked)

## Follow-ons (before megaPR)

- Copy `agent-sync/ci/agent-sync-release.yml` → `.github/workflows/` when the push token has `workflow` scope; tag `agent-sync-v*`
- Open one megaPR `sync/harness-and-tools` → `main`

## Out of scope

- Replacing `npx skills` for third-party discovery/install
- Windsurf / Codex / Copilot / `.agents` as v1 Fan-out Targets
- Committing generated Target trees into git
- Versioning Cursor’s reserved `skills-cursor/` tree
