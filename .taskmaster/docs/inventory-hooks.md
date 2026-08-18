# Inventory: hooks and shared scripts (agent-sync task 1.3)

> Parent: Task Master tag `agent-sync`, task **Inventory dual trees for migrate scope**, subtask **1.3 Inventory hooks and shared scripts**.  
> Date: 2026-08-17. **Configs were read only — not modified.**

Disposition legend (this subtask):

| Disposition | Meaning |
|---|---|
| **library** | Hook pack candidate → migrate into `library/hooks/<pack>/` |
| **machine-local** | Lives (or should stay) on the machine; merge state / personal tooling; do not commit as Library content |
| **abandon** | Not an agent Hook pack; out of migrate scope (or replace with `agent-sync`, not Library) |

---

## Summary

| Area | Finding |
|---|---|
| Repo Hook pack scripts | Only under `.cursor/skills/_shared/hooks/` (5 scripts + README). Companion: `_shared/skill_gate.py`. |
| In-repo Cursor hook config | **None** — no `.cursor/hooks.json`, no `.cursor/hooks/` directory in the repo. |
| Live Cursor config | **Readable:** `~/.cursor/hooks.json` + `~/.cursor/hooks/` (scripts + one symlink into the shared pack). |
| Claude hook scripts in repo | **None** — no `.claude/hooks/`. |
| Live Claude config | **Readable:** `~/.claude/settings.json` → `hooks`; scripts only under `~/.claude/hooks/` (plain files, not symlinked into dotfiles). |
| Skill sync entrypoints | `bin/sync-ai-assistants` + `hooks/post-up` (+ `setup/common.sh`) sync skills/commands/agents only — **do not install or merge hooks**. |

---

## 1. Repo: Cursor shared hook scripts

Path: `/Users/andrewwylde/dotfiles/.cursor/skills/_shared/hooks/`

| Path | Role | Live wiring (this machine) | Disposition |
|---|---|---|---|
| `block-worktree-remove.sh` | `beforeShellExecution`: ask before `git worktree remove/rm` or `rm` under `*/worktrees/*`; override `CURSOR_ALLOW_WORKTREE_REMOVE=1` | Yes — `~/.cursor/hooks/block-worktree-remove.sh` → symlink to this file; entry in `~/.cursor/hooks.json` | **library** (pack: worktree-safety / skill-gates adjacent) |
| `enforce-gate.sh` | `preToolUse`: run `skill_gate.py check`; block gated edits | **Not** in live `hooks.json` (README claims wiring; drift) | **library** (pack: skill-gates) |
| `block-root-writes.sh` | Shell guard for repo-root writes (`ROOT_WRITE_OK=1`) | Not in live `hooks.json` | **library** |
| `block-pr-diff-artifacts.sh` | Block accidental root-level PR diff artifacts via shell redirection | Not in live `hooks.json` | **library** |
| `guard-markdown-artifacts.sh` | Block unsupported new `.md`/`.mdx` creation | Not in live `hooks.json` | **library** |
| `README.md` | A/B notes + stale paths (claims in-repo `.cursor/hooks.json` / `.cursor/hooks/enforce-gate.sh`) | Docs only | **library** (pack docs; rewrite paths on migrate) |

Companion (not under `hooks/` but required by `enforce-gate.sh`):

| Path | Role | Disposition |
|---|---|---|
| `/Users/andrewwylde/dotfiles/.cursor/skills/_shared/skill_gate.py` | Phase gate runtime used by `enforce-gate.sh` | **library** (ship with skill-gates pack or shared runtime asset) |

Suggested pack split for later migrate (non-binding):

1. **skill-gates** — `enforce-gate.sh` + `skill_gate.py`
2. **shell-guards** — `block-root-writes.sh`, `block-pr-diff-artifacts.sh`, `guard-markdown-artifacts.sh`
3. **worktree-safety** — `block-worktree-remove.sh` (already live on Cursor)

---

## 2. Machine-local: Cursor hook config and scripts

### 2.1 `~/.cursor/hooks.json`

| Path | Readable? | Disposition |
|---|---|---|
| `/Users/andrewwylde/.cursor/hooks.json` | **Yes** (present; version `1`) | **machine-local** (merge target for agent-sync; never Library content — see `CONTEXT.md` Hook pack vs hooks.json) |

Events observed (commands summarized; absolute / third-party paths redacted to role):

| Event | Entrypoints present |
|---|---|
| `beforeSubmitPrompt` | Superconductor notify; Dashy/AIspend logger |
| `sessionStart` / `sessionEnd` / `stop` | Superconductor; local `./hooks/aw-log-*.sh`; AIspend (most events) |
| `beforeShellExecution` | Superconductor; **`./hooks/block-worktree-remove.sh`** (matcher); AIspend |
| `afterShellExecution` / `afterFileEdit` / `postToolUse` | Superconductor; aw-log wrappers; AIspend (varies) |
| `preToolUse` / `postToolUseFailure` / `afterAgentThought` / `afterAgentResponse` / `beforeReadFile` | Superconductor (± AIspend) |
| `subagentStart` / `subagentStop` | aw-log wrappers only |

**Not present in live file:** `enforce-gate.sh`, `block-root-writes.sh`, `block-pr-diff-artifacts.sh`, `guard-markdown-artifacts.sh`.

### 2.2 `~/.cursor/hooks/`

| Path | Notes | Disposition |
|---|---|---|
| `block-worktree-remove.sh` | Symlink → repo `_shared/hooks/…` | **machine-local** install surface (Library owns the script body) |
| `aw-log.sh` + `aw-log-*.sh` (7 wrappers) | ActivityWatch watcher; hard-codes path under `~/code/activitywatch/…` | **machine-local** |
| (directory itself) | Cursor user hook script dir | **machine-local** |

### 2.3 External commands referenced only from `hooks.json`

| Source | Disposition |
|---|---|
| `~/.superconductor/hooks/cursor-notify.sh` (many events) | **machine-local** |
| Dashy `uv run python …/aispend/cursor_hook_logger.py` | **machine-local** |

---

## 3. Machine-local: Claude settings hooks and scripts

### 3.1 `~/.claude/settings.json` → `hooks`

| Path | Readable? | Disposition |
|---|---|---|
| `/Users/andrewwylde/.claude/settings.json` | **Yes** | **machine-local** (merge target; preserve non-hook keys) |

Live wiring:

| Event | Matcher | Command |
|---|---|---|
| `SessionStart` | (none) | `bash ~/.claude/hooks/worktree-awareness-session-start.sh` |
| `SessionStart` | (none) | `bash ~/.claude/hooks/tts-state-sanity.sh` |
| `SessionStart` | (none) | `~/.claude/hooks/context-mode-cache-heal.mjs` |
| `PreToolUse` | `Read` | `bash ~/.claude/hooks/worktree-read-redirect.sh` |
| `PreToolUse` | `Bash` | `python3 ~/.claude/hooks/dangerous_command_safety.py` |
| `PreToolUse` | `Write\|Edit` | `python3 ~/.claude/hooks/file_safety.py` |
| `PreToolUse` | `Skill` | `bash ~/.claude/hooks/ppwt_preflight.sh` |
| `PostToolUse` | `Skill` | `bash ~/.claude/hooks/log-skill-usage.sh` |

### 3.2 `~/.claude/hooks/` (home only — not in repo)

| Script | Wired in settings? | Disposition notes |
|---|---|---|
| `worktree-awareness-session-start.sh` | Yes | **machine-local** today; strong **library** migrate candidate (pairs with worktree-awareness skill) |
| `worktree-read-redirect.sh` | Yes | same |
| `worktree_path_rewrite.py` | (helper, not direct entry) | **machine-local** / migrate with worktree pack |
| `dangerous_command_safety.py` | Yes | **machine-local** today; **library** candidate (safety pack) |
| `file_safety.py` | Yes | **machine-local** today; **library** candidate (safety pack) |
| `ppwt_preflight.sh` | Yes | **machine-local** (personal/preflight; likely stay private or local pack) |
| `tts-state-sanity.sh` | Yes | **machine-local** |
| `context-mode-cache-heal.mjs` | Yes | **machine-local** |
| `log-skill-usage.sh` | Yes | **machine-local** (telemetry-ish; optional pack) |
| `block_generated_edits.py` | **No** (orphan on disk) | **machine-local** / effectively **abandon** unless re-wired |

Repo path `.claude/hooks/`: **missing** — Claude hook bodies are not versioned in this clone today.

---

## 4. Docs / example config touchpoints (in repo)

| Path | What it is | Disposition |
|---|---|---|
| `.taskmaster/docs/research-hook-config-merge.md` | Merge algorithm, example snippets from live configs, draft `hook-pack.json` | Research artifact (not a pack) — informs Library schema |
| `.taskmaster/docs/research-target-install-path-matrix.md` | Cursor `hooks.json` + `~/.cursor/hooks/`; Claude `settings.json` hooks | Research |
| `.taskmaster/docs/wayfinder-agent-sync-map.md` | Links hook research; Hook packs decision | Map |
| `CONTEXT.md` | Glossary: Hook pack vs machine-local `hooks.json` | Domain |
| `.cursor/skills-cursor/create-hook/SKILL.md` | Product skill: how to author Cursor hooks | **abandon** for Hook pack migrate (vendor/product skill tree; do not manage as Library hooks) |
| `.cursor/skills/_shared/hooks/README.md` | Stale: claims `.cursor/hooks.json` and `.cursor/hooks/enforce-gate.sh` in repo | Fix on migrate; treat as pack docs |

No committed example `hooks.json` or Claude `settings.json` hooks block in the repo (only research docs).

---

## 5. Skill sync related (not agent Hook packs)

| Path | Behavior | Disposition for Hook inventory |
|---|---|---|
| `/Users/andrewwylde/dotfiles/bin/sync-ai-assistants` | Symlinks `.claude/{agents,skills,commands}` and `.cursor/{agents,skills,skills-cursor,commands}` — **no hooks paths** | **abandon** as hook installer; replace overall by `agent-sync` (see release research) |
| `/Users/andrewwylde/dotfiles/hooks/post-up` | rcm post-up: runs `sync-ai-assistants` from `~/dotfiles` or `~/dotfiles-local`, then vim-plug / misc | **abandon** as Hook pack; keep as setup wiring to retarget to `agent-sync sync` later |
| `/Users/andrewwylde/dotfiles/setup/common.sh` → `run_sync_ai_assistants` | Setup invokes same sync + `--verify` | Same as above |
| `README.md` (sync-ai-assistants / post-up section) | Documents current skill sync | Docs; update on cutover |

---

## 6. Explicitly out of scope (abandon for agent Hook packs)

| Path | Why |
|---|---|
| `git_template/hooks/*` | Git template hooks (ctags, commit-msg, …), not Cursor/Claude agent hooks |
| `.git/hooks/*` | Local git hooks |
| React/SDK `hooks.d.ts`, skill prose mentioning `hooks/useX.ts` | Unrelated “hooks” naming |

---

## 7. Migrate bill of materials (hooks only)

**Into `library/hooks/` (candidates from this inventory):**

1. From repo: entire `.cursor/skills/_shared/hooks/` script set + `skill_gate.py`.
2. Optional later pull from home (not in repo today): Claude `file_safety.py`, `dangerous_command_safety.py`, worktree SessionStart/Read redirect scripts — promote only if you want them portable across machines.

**Stay machine-local (merge targets + personal):**

- `~/.cursor/hooks.json`, `~/.claude/settings.json` hooks section  
- `aw-log*`, Superconductor, AIspend, TTS/context-mode/ppwt personal scripts  
- Symlinks / copies under `~/.cursor/hooks/` and `~/.claude/hooks/` after Fan-out  

**Abandon / do not treat as Library Hook packs:**

- `bin/sync-ai-assistants`, `hooks/post-up` (setup/sync, not packs)  
- `skills-cursor/create-hook`  
- git template hooks  
- Orphan `block_generated_edits.py` unless deliberately revived  

---

## 8. Drift / gaps to remember for migrate

1. Shared pack scripts exist in git, but only **worktree-remove** is live on Cursor; gate/markdown/root/PR guards are dormant.  
2. README under `_shared/hooks` documents in-repo `.cursor/hooks.json` that **does not exist**.  
3. Claude safety/worktree hooks are **home-only** — migrate must copy into Library explicitly or they stay machine-local forever.  
4. Current sync path never touches hooks; Hook Fan-out is net-new in `agent-sync`.
