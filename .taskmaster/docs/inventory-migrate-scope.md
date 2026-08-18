# Inventory: migrate bill of materials (agent-sync task 1)

> Synthesized 2026-08-17 from:
> - [inventory-claude.md](./inventory-claude.md)
> - [inventory-cursor.md](./inventory-cursor.md)
> - [inventory-hooks.md](./inventory-hooks.md)
>
> Dispositions: `library` | `vendor/cursor` | `gitignore-private` | `abandon` | `machine-local`.
> No files were moved.

## Headline counts

| Source | Total items | library | gitignore-private | vendor/cursor | abandon | machine-local |
|--------|------------:|--------:|------------------:|-------------:|--------:|--------------:|
| `.claude` | 251 | 188 | 18 | — | 45 | — |
| `.cursor` | 49 | 20 | 1 | 0 | 28 | — |
| Hooks / sync entrypoints | (see hooks doc) | pack scripts | — | — | sync-ai-assistants / post-up as packs | live configs |

**Migrate into `library/` (first pass):** ~208 public Claude items + Cursor-only library items after de-dupe + one Hook pack family from `_shared/hooks` + `skill_gate.py`.

**Do not migrate:** broken `.agents` symlink stubs (35), empty/leftover dirs, entire `.cursor/skills-cursor/` (24 unmodified product skills), sync tooling itself.

## Disposition rules for migrate

| Disposition | Action |
|-------------|--------|
| `library` | Move into `library/{skills,commands,agents,hooks}/`; prefer Claude copy when Claude/Cursor bodies match; keep Cursor-only uniques |
| `gitignore-private` | Stay out of public Library; optional later `~/dotfiles-local/library/` or in-clone gitignore under `library/` |
| `vendor/cursor` | **None found** — skills-cursor unmodified → **abandon** tree (optional future pin only if you customize) |
| `abandon` | Delete or stop tracking; do not Fan-out |
| `machine-local` | `~/.cursor/hooks.json`, `~/.claude/settings.json` hooks — merge targets only, never Library source |

## Critical migrate notes

1. **Dedup:** Same-name Claude/Cursor commands often identical — one Library command. Skills: `_shared` differs (Cursor hooks vs Claude prose) → **two Library items** (e.g. hooks pack vs `prose-clarity` skill material).
2. **Broken symlinks:** 35 Claude skills + Cursor `grill-me` → abandon stubs; real content may live under `~/.agents/skills/` (out of repo inventory).
3. **`nx-workspace`:** treat as `library`; fix false-positive `**/*-workspace/` gitignore later.
4. **`skills-cursor/`:** abandon entirely for migrate (aligns with map: do not manage reserved tree; no vendor pins needed until customized).
5. **Hooks:** Library pack from `.cursor/skills/_shared/hooks/*` + `skill_gate.py`; live JSON stays machine-local; several scripts not wired in live `hooks.json` (drift).
6. **Untracked Cursor first-party skills** (`andrew-ship-feature`, voice, etc.): still `library` candidates — ensure migrate picks up working tree, not only git-tracked.

## Artifact index

| Doc | Role |
|-----|-------|
| [inventory-claude.md](./inventory-claude.md) | Full `.claude` table |
| [inventory-cursor.md](./inventory-cursor.md) | Full `.cursor` table + overlaps |
| [inventory-hooks.md](./inventory-hooks.md) | Hook packs + live config touchpoints |

## Answer to task question

- **Move to Library:** dispositions marked `library` (+ hook pack scripts).
- **Stay private:** `gitignore-private` (+ machine-local hook configs).
- **Abandon:** skills-cursor tree, broken stubs, empties, leftover copies.
- **vendor/cursor:** none in current trees.
