# Locked decisions: remaining agent-sync grills (auto-approved)

User standing order (2026-08-17): do not ask for review; approve recommended locks.

## Task 11 — Fan-out naming and `.agents` Target

- **Drop `.agents` from v1 Targets.** v1 = Claude Code, Cursor, OpenCode, Pi. `~/.agents/` is npx/agents-cli territory.
- **Owner prefix:** Fan-out basename `andrew-<name>` for first-party; Library dirs stay unprefixed.
- **Vendor:** keep `vendor-cursor-<name>` (and `vendor-<origin>-<name>` later).
- Config: `owner_prefix = "andrew"` (hyphen joined at install).
- Applies to skills, commands, agents stems; hooks use `_as` tags (pack id internal).

## Task 6 — Local-wins

- **A4:** whole-item replace + tombstones.
- Precedence: `~/dotfiles-local/library/` > in-clone gitignored private > public `library/`.
- Tombstone = skip Fan-out for `(kind,name)` on this machine without deleting public.
- Rename = delete-old + add-new (no special rename op).
- `verify` warns on vendor shadow and orphan overrides.
- Full table: [brief-local-wins-grill.md](./brief-local-wins-grill.md)

## Task 7 — Migrate UX

- Require `--dry-run` or `--write` (no bare `migrate`).
- Phases P0–P6 + gates G1–G9 from brief; UNKNOWN inventory blocks write.
- Fan-out failure on required Target = hard abort migrate.
- Always timestamped gitignored backup of repo paths migrate touches; Target snapshot opt-in via `--backup-targets`.
- Restore via explicit `--rollback <id>` (no silent auto-rollback).
- Checklist: [brief-migrate-ux-grill.md](./brief-migrate-ux-grill.md)

## Task 8 — Setup / rcup

- Install agent-sync from `common.sh` on **mac + WSL** (not Windows host).
- mac-setup gains install + `rcup` + sync parity with wsl-setup (soft-fail if rcm missing).
- post-up: `agent-sync sync` soft; bootstrap: sync + verify.
- Deprecate `sync-ai-assistants`: shim → cutover → delete (migrate-first).
- Details: [brief-setup-rcup-grill.md](./brief-setup-rcup-grill.md)
