# Agent skill library sync

Personal dotfiles context for an agent-neutral skill/command/agent library and the tool that fans it out to coding agents.

## Language

**Library**:
The single agent-neutral tree in the repo that owns skills, commands, agents, and hooks before any Target sees them (`library/{skills,commands,agents,hooks}/`).
_Avoid_: Claude tree, canonical Claude, source of truth (ambiguous), package

**Target**:
A coding agent the Sync tool can install into. v1: Claude Code, Cursor, OpenCode, Pi.
_Avoid_: Agent (overloaded with subagent files), platform, harness, `.agents` as a Fan-out Target (npx territory)

**Wrapper**:
The thin, Target-specific layer generated around a shared body (frontmatter overlay, optional body_append) — not a full rewrite of the skill.
_Avoid_: Template expansion, fork, variant skill

**Overlay**:
The Target-keyed patch in a Manifest applied onto the shared body to produce a Wrapper (deep-merge frontmatter; optional body_append).
_Avoid_: template, variant, fork, patch file (ambiguous with git)

**Fan-out**:
Installing one Library item into one or more Targets via generate-then-link-or-copy, with install basename `andrew-<name>` (first-party) or `vendor-<origin>-<name>`.
_Avoid_: Sync (too broad alone), mirror, rsync

**Sync tool**:
The `agent-sync` CLI that generates Wrappers and fans the Library out to Targets; coexists with `npx skills` for third-party installs. Commands: `sync`, `verify`, `list`, `migrate`, `doctor`.
_Avoid_: sync-ai-assistants (deleted), skills CLI (ambiguous with npx)

**Manifest**:
Per-item opt-in `manifest.toml` in the Library that names exclusions, overlays, and (for hooks) pack entrypoints. Missing Manifest means fan out to all valid Targets with no overlay.
_Avoid_: package.json, skills-lock, skill.yaml, manifest.json

**Hook pack**:
Versioned hook scripts plus Target entrypoint templates in the Library that Fan-out installs via tagged `_as` merge into Cursor/Claude configs.
_Avoid_: hooks.json alone (that's machine-local merge state)

**Vendor skill**:
A third-party or product-managed skill kept under `library/skills/vendor/<origin>/` and Fan-out as `vendor-<origin>-<name>`.
_Avoid_: skills-cursor (do not manage), builtin, forked skill

**Tombstone**:
A local-only marker under `~/dotfiles-local/library/` that skips Fan-out for a public `(kind, name)` on this machine without deleting the public item.
_Avoid_: delete, gitignore (different mechanism)
