# Grilling brief: setup + rcup integration (agent-sync Task #8)

**Tag:** `agent-sync` · **Task:** Grill setup and rcup integration points  
**Depends on:** Task #4 — [research-rust-release-cargo-fallback.md](./research-rust-release-cargo-fallback.md)  
**Do not:** mark Task Master tasks done · edit setup scripts in this grilling pass

---

## 1. Question this grill must lock

Which setup paths **download/build `agent-sync`** and which paths **run `sync` / `verify`**, and what replaces `bin/sync-ai-assistants`?

Success criteria (from task):

- Per-platform call graph agreed
- Deprecation plan for `sync-ai-assistants` agreed

---

## 2. Facts (current repo — do not re-ask)

### 2.1 What `sync-ai-assistants` does today

`bin/sync-ai-assistants`:

- Resolves `DOTFILES_DIR` (`$DOTFILES_DIR` → `~/dotfiles` → `~/dotfiles-local`)
- Manages **whole trees** under `~` via symlink to the repo:
  - `.claude/{agents,skills,commands}`
  - `.cursor/{agents,skills,skills-cursor,commands}`
- One-shot migrate: if dest is a real directory, rsync into repo then replace with symlink
- Flags: `--dry-run`, `--verify` (exit 1 if any managed path is missing or not the expected symlink)

This is **legacy Fan-out** (per-Target trees in the repo). Wayfinder destination is Library + `agent-sync` Fan-out; CONTEXT.md already marks `sync-ai-assistants` as the name to avoid.

### 2.2 Call graph today

```
setup.sh
├── Darwin     → mac-setup.sh
│                 ❌ does NOT source setup/common.sh
│                 ❌ does NOT run rcup
│                 ❌ does NOT run sync-ai-assistants
│                 (README: run rcup afterward)
│
├── Linux/WSL  → wsl-setup.sh
│                 sources setup/common.sh
│                 clone → ensure_dotfiles_local_gitconfig
│                 → run_rcup(DOTFILES_DIR)
│                 → run_sync_ai_assistants(DOTFILES_DIR)   # sync + --verify
│
└── MINGW/MSYS → setup.ps1
                  → windows-setup.ps1   (WSL + winget host tools only)
                  → optional: wsl -d Ubuntu → wsl-setup.sh
                  ❌ no agent binary / sync on Windows host

rcup (rcm)
└── hooks/post-up
      → prefers ~/dotfiles-local/bin/sync-ai-assistants
      → else ~/dotfiles/bin/sync-ai-assistants
      → sync only (no --verify)
      → continues on failure (echo warn)

setup/common.sh
├── run_rcup(dotfiles_dir)              # RCRC=… rcup
└── run_sync_ai_assistants(dotfiles_dir)
      → DOTFILES_DIR=… sync
      → DOTFILES_DIR=… sync --verify
```

`rcrc`: `DOTFILES_DIRS="$HOME/dotfiles-local $HOME/dotfiles"` — local wins for rcm, same pattern Library wants later.

### 2.3 README skill sync section (today)

Documents manual:

```bash
~/dotfiles/bin/sync-ai-assistants
~/dotfiles/bin/sync-ai-assistants --verify
~/dotfiles/bin/sync-ai-assistants --dry-run
```

States `hooks/post-up` runs sync after `rcup`. Platform table: mac / WSL / Windows host via `setup.ps1`. Notes mac-setup installs tools first; rcup is separate.

### 2.4 Research #4 integration sketch (§7)

Already proposed (not yet implemented):

1. `install_agent_sync` in `setup/common.sh` (curl `| bash` Unix installer; irm/iex on Windows)
2. End of setup: replace `bin/sync-ai-assistants` with `agent-sync sync`
3. After cutover: delete `bin/sync-ai-assistants`

Release semantics to assume for this grill: prefer GitHub Release friendly assets + sha256; cargo `--locked` fallback; checksum mismatch = hard abort (no cargo fallthrough). Install dir default `~/.cargo/bin` (or `AGENT_SYNC_INSTALL_DIR`).

### 2.5 Semantic gap (important for deprecation)

| Concern | `sync-ai-assistants` | `agent-sync` (destination) |
|---|---|---|
| Source | Repo `.claude` / `.cursor` trees | `library/` + Manifests |
| Action | Migrate dirs + symlink wholes | Generate Wrappers + Fan-out (hybrid symlink/copy) |
| Verify | Symlink target check | State file + Target path checks |
| One-shot migrate | Built into sync | Separate `migrate` command |

**Replacing the binary name is not enough** — migrate UX and Fan-out model must be sequenced (Task #7 migrate grill; this task only locks *where install/sync/verify are invoked*).

---

## 3. Proposed target call graph

### 3.1 Responsibility split

| Concern | Where | Command / helper |
|---|---|---|
| **Install** binary (once / upgrade) | Platform setup + optional manual | `install_agent_sync` → upstream `setup.sh` / `setup.ps1` (research §5–6) |
| **Sync** after every `rcup` | `hooks/post-up` | `agent-sync sync` (warn on failure, keep post-up soft) |
| **Sync + verify** on bootstrap | `setup/common.sh` after `run_rcup` | `run_agent_sync` → `sync` then `verify` |
| **Manual** after pull | README | `agent-sync sync` / `verify` / `migrate` |

### 3.2 Per-platform plugs (proposal)

```
macOS
  mac-setup.sh (or shared tail via common.sh)
    1. install_agent_sync          # NEW — after brew/path basics
    2. [optional this grill] run_rcup + run_agent_sync
       — today missing; recommend ADD so mac matches WSL

WSL / Linux
  wsl-setup.sh (after clone + gitconfig.local)
    1. install_agent_sync          # NEW — before rcup so post-up can find binary
    2. run_rcup                    # unchanged
    3. run_agent_sync              # NEW name; replaces run_sync_ai_assistants
       (post-up also syncs; explicit verify stays valuable)

Windows host
  windows-setup.ps1 / setup.ps1
    ❌ do NOT install agent-sync on host by default
    Agent sync runs inside WSL via wsl-setup (Cursor opens \\wsl$\…)
    Optional later: Install-AgentSync only if someone runs Windows-native Cursor
    against Windows %USERPROFILE% — out of v1 bootstrap

Every rcup
  hooks/post-up
    agent-sync sync   (DOTFILES / library root resolved by CLI, not bash DOTFILES_DIR)
    soft-fail like today

common.sh
  install_agent_sync()
  run_agent_sync(dotfiles_dir)   # sync + verify; skip/warn if binary missing
```

### 3.3 Install ordering (invariant)

`install_agent_sync` **before** first `rcup` on bootstrap paths, so `post-up` can invoke the binary. If install fails (no prebuilt, no cargo), `post-up` / `run_agent_sync` should **warn and skip**, not abort the whole machine setup (match today’s soft post-up).

Idempotent: if `agent-sync` already on `PATH`, skip download (research §7.1). Version pin via `AGENT_SYNC_VERSION` optional.

### 3.4 Where the binary lives vs where the Library lives

- Binary: `~/.cargo/bin/agent-sync` (PATH) — machine tool
- Library: repo `library/` (+ `~/dotfiles-local/library/` later) — content
- `agent-sync` must discover the dotfiles / Library root (env, cwd, or config). Grill should not invent schema; recommend: honor `DOTFILES_DIR` / run from repo / config file later — **default for setup hooks: set env to the same `dotfiles_dir` passed to `run_rcup`**.

---

## 4. Deprecation plan for `sync-ai-assistants`

### Phase A — Shim (while Library migrate incomplete)

1. Implement `agent-sync` with at least `sync` / `verify` (and `migrate` when ready).
2. Change `bin/sync-ai-assistants` to a thin wrapper:

   ```bash
   exec agent-sync "$@"   # map --dry-run / --verify to CLI flags when available
   ```

   Or: wrapper prints deprecation and calls `agent-sync sync`.

3. Keep `hooks/post-up` and `run_sync_ai_assistants` calling the wrapper path so old muscle memory / README still work.

### Phase B — Call-site cutover (this grill’s wiring)

1. `hooks/post-up` → invoke `agent-sync sync` directly (resolve binary via `command -v`).
2. `setup/common.sh` → `run_agent_sync`; `wsl-setup` (and mac if added) call it.
3. README skill section → document `agent-sync` only; one-line “former sync-ai-assistants”.

### Phase C — Remove

1. Delete `bin/sync-ai-assistants` after one stable release / personal confirmation on mac + WSL.
2. Do **not** add the path to `.gitignore` (research §7.3 said that — **reject**: gitignore doesn’t remove a tracked file and confuses “deleted on purpose”). Prefer delete + CHANGELOG/README note.
3. CONTEXT.md already discourages the old name — keep that.

### Cutover gate

Do not enter Phase C until:

- `agent-sync migrate` (or equivalent) has moved content into `library/`
- `agent-sync verify` green on primary machines
- No remaining docs/scripts require whole-tree symlink semantics for `.claude` / `.cursor` skills

Until then, Phase A shim may still need a **compat mode** that preserves old symlink behavior *or* migrate must run first on each machine — **prefer migrate-first, then Fan-out-only sync** (aligns with wayfinder “one-shot into Library”).

---

## 5. Recommended answers (Round 1 frontier)

Use `/grilling` format. These are the decisions that do not depend on unsettled Manifest/migrate UX details.

```
❓ **Q1** - **Install on which platforms?**: On a fresh machine, which scripts should download/build agent-sync?

Choices:
  A) common.sh helper + call from wsl-setup only (mac stays manual install)
  B) common.sh helper + wsl-setup + mac-setup (or shared setup tail)
  C) Also windows-setup.ps1 on the Windows host
  D) Install only via post-up / first sync (lazy)

➡️ **B.** Bootstrap must be reliable on both daily drivers. Windows host stays out (dev in WSL). Lazy install in post-up is a nice secondary recovery, not the primary path.
```

```
❓ **Q2** - **mac-setup and rcup?**: mac-setup today never runs rcup/sync. Should bootstrap grow `install_agent_sync` + `run_rcup` + `run_agent_sync`?

Choices:
  A) Yes — parity with wsl-setup
  B) Install binary only; leave rcup manual (README as today)
  C) No change to mac-setup; document `cargo`/`curl` install separately

➡️ **A.** README already admits the gap; closing it prevents “tools installed, harness never synced.” Keep soft-fail if rcm missing.
```

```
❓ **Q3** - **post-up vs explicit setup verify?**: Today post-up syncs without verify; wsl-setup syncs then verifies. Keep that split?

Choices:
  A) post-up: sync only (soft); bootstrap: sync + verify (harder fail OK)
  B) post-up: sync + verify (soft on both)
  C) Drop explicit bootstrap sync; trust post-up only

➡️ **A.** Every rcup should refresh Fan-out cheaply; verify is for bootstrap / CI / manual confidence. Soft post-up preserves rcup usability if agent-sync is temporarily broken.
```

```
❓ **Q4** - **Windows host agent-sync?**: Should setup.ps1 / windows-setup.ps1 install the Windows binary?

Choices:
  A) No — WSL-only for v1
  B) Yes — always install windows-amd64 for native Cursor
  C) Opt-in env flag (e.g. AGENT_SYNC_WINDOWS_HOST=1)

➡️ **A** for v1 (matches current architecture and README Cursor/`\\wsl$` guidance). **C** as a later escape hatch if needed — do not block this grill on it.
```

```
❓ **Q5** - **Deprecation shape?**: How do we retire sync-ai-assistants?

Choices:
  A) Hard cut: delete script when wiring lands; README only documents agent-sync
  B) Phased: shim → call-site cutover → delete (gates in §4)
  C) Keep forever as wrapper

➡️ **B.** Avoid breaking machines mid-migrate; reject “gitignore the script” from research §7.3; delete when verify-green.
```

```
❓ **Q6** - **Failure policy on bootstrap?**: If install_agent_sync fails (no binary, no cargo), should setup exit non-zero?

Choices:
  A) Warn + continue (rest of machine setup succeeds)
  B) Fail hard
  C) Fail hard only when AGENT_SYNC_REQUIRED=1

➡️ **A** for personal dotfiles bootstrap (network/cargo optional). Document manual install. Optional **C** later for strict CI images.
```

```
❓ **Q7** - **Who owns DOTFILES / Library root for hooks?**: post-up today sets DOTFILES_DIR when invoking the bash script. For agent-sync:

Choices:
  A) Export DOTFILES_DIR / AGENT_SYNC_ROOT in post-up and common.sh (same dirs as rcup)
  B) Require agent-sync config file in repo only
  C) Infer from cwd / git root only

➡️ **A** for setup/rcup paths (deterministic, matches rcm DOTFILES_DIRS priority: prefer local clone path used by run_rcup). Config-file inference can be additive later.
```

---

## 6. Later-round topics (blocked / do not ask in Round 1)

- Exact CLI flags for dry-run / verify (depends on CLI surface tasks)
- Whether post-up should call `migrate` (depends on Task #7 migrate grill)
- Compat mode inside shim that still whole-tree-symlinks `.claude` (depends on migrate timing)
- crates.io publish name / OWNER/repo for curl URL (release plumbing task)
- Signing / attestation beyond sha256 (wayfinder: optional, out of this grill)

---

## 7. Doc / code touch list (after grill agrees — implement in a later task)

| Path | Change |
|---|---|
| `setup/common.sh` | Add `install_agent_sync`, rename/replace `run_sync_ai_assistants` → `run_agent_sync` |
| `wsl-setup.sh` | Call install before `run_rcup`; use `run_agent_sync` |
| `mac-setup.sh` | Source common or shared tail; install + rcup + agent-sync (if Q2=A) |
| `hooks/post-up` | Invoke `agent-sync sync` (with root env); soft-fail |
| `setup.ps1` / `windows-setup.ps1` | No install (if Q4=A); maybe comment pointer to WSL |
| `bin/sync-ai-assistants` | Shim then delete (Q5=B) |
| `README.md` skill sync section | Document `agent-sync sync` / `verify`; note post-up |
| `CONTEXT.md` | Already OK |
| research §7.3 | Amend mentally: delete script, do not gitignore |

---

## 8. Suggested grill session opener

> Task #8 — lock where `agent-sync` is installed and where `sync`/`verify` run across mac, WSL, Windows host, and `rcup`/`post-up`. Current fact: only WSL bootstrap + `post-up` sync today; mac-setup never rcup/syncs; Windows host never touches the harness. Research #4 gives install mechanics. Round 1 is Q1–Q7 above; recommend B / A / A / A / B / A / A unless you override.

When frontier empties and answers are recorded, append a gist to [wayfinder-agent-sync-map.md](./wayfinder-agent-sync-map.md) under Decisions so far — still **do not** mark the Task Master task done from the brief-writing pass alone.
