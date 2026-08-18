# Inventory: `.cursor` trees (agent-sync task 1.2)

> Generated: 2026-08-17
> Scope: every top-level item under `.cursor/skills/`, `.cursor/skills-cursor/`, `.cursor/commands/`, `.cursor/agents/`.
> Dispositions: `library` | `vendor/cursor` | `gitignore-private` | `abandon`.
> No files were moved or copied.
> Companion: [inventory-claude.md](./inventory-claude.md), [inventory-hooks.md](./inventory-hooks.md).

## Summary counts

| Kind | Total | library | vendor/cursor | gitignore-private | abandon |
|------|------:|--------:|--------------:|------------------:|--------:|
| skill (`.cursor/skills/`) | 10 | 7 | 0 | 0 | 3 |
| skill (`.cursor/skills-cursor/`) | 24 | 0 | 0 | 0 | 24 |
| command | 14 | 12 | 0 | 1 | 1 |
| agent | 1 | 1 | 0 | 0 | 0 |
| **all** | **49** | **20** | **0** | **1** | **28** |

Skills-cursor total includes `babysit` (tracked in HEAD, deleted on disk). Manifest JSON files under `skills-cursor/` are gitignored Cursor product state, not counted as skills.

### Notable findings

- **Stop versioning `skills-cursor/`.** Locked map: do not manage Cursor’s reserved tree. Working-tree diffs vs HEAD are **product sync**, not local forks (Automations Slack ID rules, canvas SDK, CLI config fields, babysit removal). None customized → **abandon** each product skill (optional later pin: `library/skills/vendor/cursor/<name>/` → `~/.cursor/skills/vendor-cursor-<name>/`).
- **Broken `grill-me` skill symlink:** `.cursor/skills/grill-me` → `.claude/skills/grill-me` → `.agents/skills/grill-me` (missing). Matches Claude inventory **abandon**. The **command** `.cursor/commands/grill-me.md` is intact and identical to Claude.
- **Same name, different body:** `.cursor/skills/_shared` is hook scripts + `skill_gate.py`; `.claude/skills/_shared` is `prose-clarity.md`. Do not merge as one Library item.
- **Empty / leftover dirs:** `ship-feature/` (scripts only, subset of `andrew-ship-feature`), `swarm-test-review/` (empty; Claude copy is gitignore-private), `implementation-loop.md` (0 bytes), `commands/.cursor/` (empty).
- **Gitignore-private:** only `.cursor/commands/implement-and-review-loop.md` (Parable MCP loop). Differs from the Claude command of the same name.
- **Most first-party Cursor skills are untracked** (`andrew-ship-feature`, `gh-stack`, voice skills, `writing-branch-stories`, `_shared`). Tracked today: `update-chat-db`, the `grill-me` symlink, commands (except `personal-voice-mcp-daily.md`), `bob.md`, and the older `skills-cursor` set.

## Disposition legend

| Disposition | Meaning for migrate |
|-------------|---------------------|
| `library` | Candidate to move into repo-root `library/{skills,commands,agents,hooks}/` |
| `vendor/cursor` | Cursor product skill to pin under `library/skills/vendor/cursor/<name>/` (not `skills-cursor/`) |
| `gitignore-private` | Parable/private; keep gitignored; fan-out via local / `~/dotfiles-local/library/` if needed |
| `abandon` | Do not migrate (product tree, empty stubs, broken links, leftover copies) |

## Same-name overlaps with `.claude`

| Cursor path | Claude path | Relation |
|-------------|-------------|----------|
| `.cursor/skills/_shared` | `.claude/skills/_shared` | **Name only.** Cursor = hooks/`skill_gate.py`; Claude = `prose-clarity.md` |
| `.cursor/skills/gh-stack` | `.claude/skills/gh-stack` | **Identical** `SKILL.md` (GitHub `gh-stack` v0.0.9). Cursor copy untracked |
| `.cursor/skills/grill-me` | `.claude/skills/grill-me` (+ `.claude/commands/grill-me.md`) | Skill: both broken `.agents` chain. Command: identical |
| `.cursor/skills/swarm-test-review` | `.claude/skills/swarm-test-review` | Cursor empty; Claude gitignore-private (has content) |
| `.cursor/skills/personal-voice-mcp-daily` | `.claude/commands/personal-voice-mcp-daily.md` | Skill is Cursor-only; command exists in both (wrapper differs) |
| `.cursor/commands/*.md` (12 names) | `.claude/commands/` same filenames | See command table. 7 identical; 4 differ; 1 gitignore-private |
| `.cursor/commands/super-review.md` | — | Cursor-only |
| `.cursor/commands/implementation-loop.md` | — | Cursor-only empty stub |
| `.cursor/agents/bob.md` | — | Cursor-only (`bob-the-builder`) |
| `.cursor/skills-cursor/*` | — | **No** same-name Claude skills |
| `.cursor/skills/{update-chat-db,personal-voice-model,writing-branch-stories,andrew-ship-feature,ship-feature}` | — | Cursor-only skill dirs |

Command files that share a name with Claude:

| File | Bytes / identity |
|------|------------------|
| `deslop.md`, `flesh-out-ticket.md`, `generate-review-doc.md`, `grill-me.md`, `prepare-pr.md`, `restore.md`, `snapshot.md`, `update-ticket.md` | **Identical** |
| `incorporate-feedback.md` | Differs (~65 diff lines): Cursor uses `gh pr view --json reviewThreads`; Claude uses REST `gh api` |
| `pr-review.md` | Differs (~24 diff lines): Claude has extra “Save to PR Reviews viewer” step; Cursor ends earlier |
| `personal-voice-mcp-daily.md` | Differs (~13 lines): Cursor adds `alwaysApply: false` and names `slack_search_public_and_private` |
| `implement-and-review-loop.md` | **Different products** (Parable MCP vs Claude-native subagents); both gitignore-private |

---

## Skills (`.cursor/skills/`)

| path | kind | git | disposition | notes |
|------|------|-----|-------------|-------|
| `.cursor/skills/_shared` | skill (shared pack, no SKILL.md) | untracked | library | 5 hook scripts + README + `skill_gate.py`. Same name as Claude `_shared` but different files. Hook details: [inventory-hooks.md](./inventory-hooks.md) |
| `.cursor/skills/andrew-ship-feature` | skill | untracked | library | Personal `/ship-feature` overlay + Parables 609/613 campaign refs (42 files). If campaign internals must stay private, split or treat as gitignore-private instead |
| `.cursor/skills/gh-stack` | skill | untracked | library | Identical to `.claude/skills/gh-stack` |
| `.cursor/skills/grill-me` | skill | tracked symlink | abandon | Broken: → `../../.claude/skills/grill-me` → `../../.agents/skills/grill-me` (missing). Command of same name is library |
| `.cursor/skills/personal-voice-mcp-daily` | skill | untracked | library | Cursor skill; Claude has command only. Slash command wrapper also under `.cursor/commands/` |
| `.cursor/skills/personal-voice-model` | skill | untracked | library | Cursor-only (scripts, templates, ollama guide). No Claude skill |
| `.cursor/skills/ship-feature` | leftover | untracked | abandon | No SKILL.md. 8 scripts, all duplicated under `andrew-ship-feature/scripts/` |
| `.cursor/skills/swarm-test-review` | empty dir | untracked (empty) | abandon | Empty. Claude dir of same name is gitignore-private with content |
| `.cursor/skills/update-chat-db` | skill | tracked (modified) | library | Cursor-only. Pipeline for `~/code/dashy` chat DB |
| `.cursor/skills/writing-branch-stories` | skill | untracked | library | Cursor-only (scripts + tests + template) |

### `_shared` contents (library; not a SKILL.md)

| path | role |
|------|------|
| `_shared/skill_gate.py` | Phase-gate runtime for `enforce-gate.sh` |
| `_shared/hooks/block-worktree-remove.sh` | Live on this machine via `~/.cursor/hooks/` |
| `_shared/hooks/enforce-gate.sh` | Not in live `hooks.json` |
| `_shared/hooks/block-root-writes.sh` | Not in live `hooks.json` |
| `_shared/hooks/block-pr-diff-artifacts.sh` | Not in live `hooks.json` |
| `_shared/hooks/guard-markdown-artifacts.sh` | Not in live `hooks.json` |
| `_shared/hooks/README.md` | A/B notes; stale in-repo `hooks.json` paths |

---

## Skills (`.cursor/skills-cursor/`) — Cursor product

**Tree disposition: abandon.** Stop committing this directory. Cursor owns it (`/.cursor/.gitignore` already ignores `.cursor-managed-skills-manifest.json` and `.sync-manifest.json`). Agent-sync must not write here.

Customization check (vs git HEAD + on-disk product sync): **none are local forks.** Modified files are upstream product edits. Six skills exist on disk but were never committed (new product inventory). `babysit` was removed by product.

| path | git | customized? | disposition | notes |
|------|-----|-------------|-------------|-------|
| `.cursor/skills-cursor/automate` | tracked, modified | no (product) | abandon | Slack DM/`D…` ID rules updated by Cursor |
| `.cursor/skills-cursor/autopilot` | untracked | n/a (new product) | abandon | Keep PR merge-ready |
| `.cursor/skills-cursor/babysit` | tracked, **deleted** | n/a | abandon | Product removed; drop from git |
| `.cursor/skills-cursor/canvas` | tracked, modified | no (product) | abandon | Includes `sdk/*.d.ts` |
| `.cursor/skills-cursor/create-hook` | tracked, clean | no | abandon | Product authoring skill (not a Hook pack) |
| `.cursor/skills-cursor/create-rule` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/create-skill` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/create-subagent` | tracked, clean | no | abandon | Not the same as `.claude/skills/{subagent-creator,cursor-subagent-creator}` |
| `.cursor/skills-cursor/loop` | tracked, modified | no (product) | abandon | Recurring `/loop` |
| `.cursor/skills-cursor/migrate-to-skills` | tracked, clean | no | abandon | Commands→skills converter |
| `.cursor/skills-cursor/new-repo` | untracked | n/a (new product) | abandon | |
| `.cursor/skills-cursor/onboard` | untracked | n/a (new product) | abandon | |
| `.cursor/skills-cursor/origin` | untracked | n/a (new product) | abandon | origin CLI |
| `.cursor/skills-cursor/rename-chat` | untracked | n/a (new product) | abandon | |
| `.cursor/skills-cursor/review` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/review-bugbot` | tracked, modified | no (product) | abandon | Dropped `readonly: true` |
| `.cursor/skills-cursor/review-security` | tracked, modified | no (product) | abandon | |
| `.cursor/skills-cursor/sdk` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/share` | untracked | n/a (new product) | abandon | |
| `.cursor/skills-cursor/shell` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/split-to-prs` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/statusline` | tracked, clean | no | abandon | |
| `.cursor/skills-cursor/update-cli-config` | tracked, modified | no (product) | abandon | `subagentModels` / channel enum |
| `.cursor/skills-cursor/update-cursor-settings` | tracked, clean | no | abandon | |

Gitignored product state (not skills; do not migrate):

| path | disposition |
|------|-------------|
| `.cursor/skills-cursor/.cursor-managed-skills-manifest.json` | abandon (Cursor-managed; gitignored) |
| `.cursor/skills-cursor/.sync-manifest.json` | abandon (Cursor-managed; gitignored) |

**vendor/cursor:** none required for this migrate. Use that disposition later only if a product skill must be pinned into the Library for Fan-out to other Targets. Unmodified Cursor-only skills (canvas, origin, onboard, …) should stay product-managed.

---

## Commands (`.cursor/commands/`)

Cursor slash commands are legacy (prefer skills path on Fan-out; see path-matrix research). Inventory still lists each file as it exists today.

| path | git | disposition | `.claude` overlap | notes |
|------|-----|-------------|-------------------|-------|
| `.cursor/commands/deslop.md` | tracked | library | identical | |
| `.cursor/commands/flesh-out-ticket.md` | tracked | library | identical | |
| `.cursor/commands/generate-review-doc.md` | tracked | library | identical | |
| `.cursor/commands/grill-me.md` | tracked | library | identical | Invokes `grill-me` skill (skill dir is abandon/broken) |
| `.cursor/commands/implement-and-review-loop.md` | gitignored | gitignore-private | same name, **different body** | Listed in repo `.gitignore`. Parable MCP (`implement_and_review`) vs Claude-native loop |
| `.cursor/commands/implementation-loop.md` | tracked | abandon | none | **Empty** (0 bytes) |
| `.cursor/commands/incorporate-feedback.md` | tracked | library | differs | Cursor overlay: `reviewThreads` JSON vs Claude REST |
| `.cursor/commands/personal-voice-mcp-daily.md` | untracked | library | differs | Thin wrapper over Cursor skill; Claude command is slightly shorter |
| `.cursor/commands/pr-review.md` | tracked | library | differs | Cursor omits Mintlify PR-reviews viewer step |
| `.cursor/commands/prepare-pr.md` | tracked | library | identical | |
| `.cursor/commands/restore.md` | tracked | library | identical | |
| `.cursor/commands/snapshot.md` | tracked | library | identical | |
| `.cursor/commands/super-review.md` | tracked | library | none | Cursor-only; hard-codes `~/code/engineering-onboarding/pr-review-agent/…` |
| `.cursor/commands/update-ticket.md` | tracked | library | identical | |

Not a command (abandon artifact): empty directory `.cursor/commands/.cursor/`.

---

## Agents (`.cursor/agents/`)

| path | git | disposition | `.claude` overlap | notes |
|------|-----|-------------|-------------------|-------|
| `.cursor/agents/bob.md` | tracked | library | none | Frontmatter name `bob-the-builder`. Implementation specialist |

---

## Other `.cursor` files (not skills/commands/agents)

| path | notes |
|------|-------|
| `.cursor/.gitignore` | Ignores `.DS_Store`, `node_modules`, and the two skills-cursor manifests |

No in-repo `.cursor/hooks.json` or `.cursor/hooks/` (see hooks inventory).

---

## Migrate bill of materials (Cursor trees only)

**Into `library/` (candidates):**

- Skills: `_shared` (as Hook pack / shared runtime), `andrew-ship-feature`, `gh-stack` (dedupe with Claude copy), `personal-voice-mcp-daily`, `personal-voice-model`, `update-chat-db`, `writing-branch-stories`
- Commands: the 12 library rows above (identical ones share one body; the three differs need Cursor Manifest overlays)
- Agents: `bob.md`

**gitignore-private:**

- `.cursor/commands/implement-and-review-loop.md`

**Abandon (do not migrate / stop versioning):**

- Entire `.cursor/skills-cursor/` (24 product skills including deleted `babysit`)
- Broken `grill-me` skill symlink
- Leftover `ship-feature/` scripts dir
- Empty `swarm-test-review/`
- Empty `implementation-loop.md`
- Empty `commands/.cursor/`

**vendor/cursor:** none from this snapshot (no customized product skills).
