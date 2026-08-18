# Research: npx skills coexistence with agent-sync Library fan-out

> Task Master tag `agent-sync` — Task #9  
> Primary source: vercel-labs/skills v1.5.x source + docs (August 2026)

---

## How npx skills manages its territory

### Directory ownership

`npx skills` owns two layers:

**Canonical store** — the single physical copy of every skill it manages:

| Scope | Path |
|---|---|
| Project | `.agents/skills/<name>/` |
| Global | `~/.agents/skills/<name>/` |

**Agent symlinks** — one symlink per non-universal agent, pointing back to the canonical store:

| Agent | Project path | Points to |
|---|---|---|
| Claude Code | `.claude/skills/<name>` | `.agents/skills/<name>` |
| Cursor | `.cursor/skills/<name>` | `.agents/skills/<name>` |
| OpenCode, Amp, Cline, Replit | `.agents/skills/<name>` | _same dir — universal agents read canonical directly_ |

Universal agents (those whose `skillsDir === '.agents/skills'`) share the canonical store without a separate symlink.

### Lock file ownership

`npx skills` maintains two lock files. Neither should be touched by agent-sync.

| File | Scope | Purpose |
|---|---|---|
| `skills-lock.json` (project root) | Project | Committed; tracks project-scoped installs with `computedHash` (SHA-256 of local files) |
| `~/.agents/.skill-lock.json` | Global | Tracks global installs with `skillFolderHash` (GitHub tree SHA for update detection) |

Lock entry shape (v3 schema):

```json
{
  "version": 3,
  "skills": {
    "frontend-design": {
      "source": "vercel-labs/agent-skills",
      "sourceType": "github",
      "sourceUrl": "https://github.com/vercel-labs/agent-skills",
      "skillPath": "skills/frontend-design",
      "skillFolderHash": "a3f2c1d9e8b7...",
      "installedAt": "2026-01-15T10:30:00.000Z",
      "updatedAt": "2026-01-20T14:45:00.000Z"
    }
  }
}
```

### Critical: remove scans the filesystem, not just the lock file

The most dangerous `npx skills` behavior for coexistence is how `remove` discovers installed skills. From `src/remove.ts`:

```ts
const scanDir = async (dir: string) => {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() || entry.isSymbolicLink()) {
      skillNamesSet.add(entry.name);   // ← adds every dir/symlink it finds
    }
  }
};

// Scans canonical store + every known agent's skill dir
await scanDir(getCanonicalSkillsDir(false, cwd));        // .agents/skills/
for (const agent of Object.values(agents)) {
  await scanDir(join(cwd, agent.skillsDir));              // .claude/skills/, .cursor/skills/, …
}
```

**Consequence**: `npx skills remove` enumerates every directory and symlink it finds in all agent skill dirs — including ones that agent-sync placed there. The resulting `installedSkills` list becomes the removal candidate pool.

- `npx skills remove` (interactive): shows the list and prompts. User can see Library-managed skill names and decline.
- `npx skills remove --all -y`: **silently deletes everything in the candidate pool**, including Library fan-outs.

### Update does NOT scan the filesystem

`npx skills update` only updates skills present in the lock file. Since Library-managed skills are never written to `skills-lock.json`, they are invisible to `update` and will not be overwritten or re-fetched. ✓

### Add can overwrite via name collision

`npx skills add <repo>` will install a skill at `.claude/skills/<name>` (symlink or copy). If the target path already exists, the installer removes it before creating the new entry (`src/installer.ts` cleanup step). Name collision = overwrite, regardless of who originally created the path.

---

## Conflict scenario matrix

| Scenario | npx operation | What npx does to Library fan-out | Severity |
|---|---|---|---|
| S1 — Name collision on add | `npx skills add repo` where repo has a skill with same name as a Library skill | Overwrites the agent-dir symlink; Library canonical is untouched but agents now see the third-party version | **HIGH** |
| S2 — Interactive remove | `npx skills remove` (no `--all -y`) | Lists Library skill names among candidates; user must consciously choose to delete them | Medium (user can refuse) |
| S3 — Automated remove | `npx skills remove --all -y` | Deletes every dir/symlink in all agent skill dirs including Library fan-outs | **CRITICAL** |
| S4 — Update (safe) | `npx skills update` | Only touches lock-file entries; Library skills are not in the lock file | None ✓ |
| S5 — List pollution | `npx skills list` | Shows Library skills among npx-managed skills; misleading but non-destructive | Low |
| S6 — Canonical store write | agent-sync writes to `.agents/skills/` | npx `remove` or `update` later treats it as an npx-owned skill | **HIGH** (if it happens) |
| S7 — Lock file write | agent-sync writes to `skills-lock.json` | npx `update` would attempt to fetch/update agent-sync Library skills from GitHub | **HIGH** (if it happens) |
| S8 — --copy conflict | npx installs with `--copy`; same-named Library skill exists as a symlink | npx replaces symlink with a real directory copy; future agent-sync `sync` creates duplicate | HIGH |
| S9 — Universal agent overlap | Library skill fan-out goes to `.agents/skills/<name>/`; npx also writes to canonical store | Direct filesystem collision in the canonical store | **CRITICAL** (if it happens) |

---

## Coexistence rules

### Rule 1 — Canonical stores must never overlap (HARD)

| Owner | Canonical path | Must NOT write to |
|---|---|---|
| agent-sync | `library/skills/`, `library/commands/`, `library/hooks/` | `.agents/skills/`, `~/.agents/skills/` |
| npx skills | `.agents/skills/`, `~/.agents/skills/` | `library/` |

agent-sync fans out from `library/` directly to agent dirs via symlinks. It has no reason to touch `.agents/skills/`.

**Why this matters for universal agents** (Amp, OpenCode, Cline, Replit): their `skillsDir` resolves to `.agents/skills/`. Fan-out for these Targets must use a _different mechanism_ (e.g., agent-sync writes copies or symlinks into each agent's own profile dir if one exists, or accepts that `.agents/` is shared and relies on naming to partition). See Rule 2.

### Rule 2 — Use a consistent naming prefix for all Library fan-out paths (HARD)

Every skill name that agent-sync writes into an agent dir must carry a prefix that is:
- Unique to the Library owner (e.g., an org handle or short project slug)  
- Not plausibly used by any third-party skill package  
- Applied **consistently** across all Targets so names are the same everywhere

**Example**: if the owner prefix is `andrew-`, then:

```
.claude/skills/andrew-frontend-design    → library/skills/frontend-design
.cursor/skills/andrew-frontend-design    → library/skills/frontend-design
```

Third-party skills installed by npx continue using their upstream names (e.g., `frontend-design`) with no prefix.

**Why a prefix alone is sufficient for S2 / S5**: the user sees `andrew-*` names in `npx skills remove` and `list` output and immediately knows they are Library-managed, not third-party.

**Why a prefix is necessary but not sufficient for S3**: `npx skills remove --all -y` bypasses the prompt. The prefix makes forensic recovery easier (agent-sync `verify` can detect the missing fan-outs) but does not prevent deletion.

**Consistency note**: the wayfinder map already uses `vendor-cursor-<name>` for Cursor product skills. Extend this pattern: first-party Library skills use `<owner>-<name>`; vendor skills use `vendor-<origin>-<name>`.

### Rule 3 — Never read or write npx lock files (HARD)

agent-sync must not:
- Parse `skills-lock.json`
- Write to `skills-lock.json`  
- Parse or write `~/.agents/.skill-lock.json`

agent-sync maintains its own state tracking (see Rule 5).

### Rule 4 — Detect foreign entries before writing (REQUIRED)

Before creating a fan-out path (symlink or copy) at any agent skill dir, agent-sync must inspect the existing filesystem entry:

```
Path does not exist          → safe to create
Path is a symlink to library/… → ours, safe to update
Path is a symlink to .agents/skills/… → npx-managed; skip + warn
Path is a real directory (not a symlink) → could be npx --copy install or manual; skip + warn unless --force
```

Detection heuristic for symlinks: resolve the link target and check whether it falls under `<cwd>/.agents/skills/` or `~/.agents/skills/`. If so, it belongs to npx.

### Rule 5 — agent-sync maintains its own state file (REQUIRED)

agent-sync must track every path it has created so that:
- `verify` can detect missing fan-outs (e.g., after `npx skills remove --all`)
- `sync` can safely re-create only paths it originally owned
- future `remove` of a Library skill knows which agent-dir entries to clean up

Suggested location: `.agent-sync-state.json` at the dotfiles repo root, gitignored (machine-local). Shape:

```json
{
  "version": 1,
  "fanouts": [
    {
      "library": "library/skills/frontend-design",
      "target": "claude-code",
      "agentPath": "/Users/andrewwylde/.claude/skills/andrew-frontend-design",
      "mode": "symlink",
      "createdAt": "2026-08-17T00:00:00Z"
    }
  ]
}
```

### Rule 6 — Forbid `npx skills remove --all -y` in automated contexts (PROCEDURAL)

- Document clearly in the dotfiles README that running `npx skills remove --all -y` in this repo will also delete Library fan-outs.
- If Cursor hooks or CI run `npx skills` commands automatically, never pass `--all -y` together.
- `agent-sync verify` should be the recovery path: it diffs the current state against the state file and re-runs fan-out for anything missing.

---

## Safe filesystem layout (both tools present)

```
dotfiles/
├── library/
│   └── skills/
│       └── frontend-design/      ← agent-sync canonical (committed)
│           └── SKILL.md
├── .agents/
│   └── skills/
│       └── emilkowalski-skills/  ← npx canonical (gitignored or committed separately)
│           └── SKILL.md
├── skills-lock.json              ← npx owned
└── .agent-sync-state.json        ← agent-sync owned (gitignored)

~/.claude/skills/
├── emilkowalski-skills           → dotfiles/.agents/skills/emilkowalski-skills  (npx symlink)
└── andrew-frontend-design        → dotfiles/library/skills/frontend-design      (agent-sync symlink)

~/.cursor/skills/
├── emilkowalski-skills           → dotfiles/.agents/skills/emilkowalski-skills  (npx symlink)
└── andrew-frontend-design        → dotfiles/library/skills/frontend-design      (agent-sync symlink)
```

Key properties of this layout:
- No path collision (different names)
- Symlink targets are distinguishable by inspection (`.agents/` vs `library/`)
- npx `update` ignores `andrew-frontend-design` (not in lock file)
- npx `list` shows both; names visually partition them
- npx `remove` (interactive) lists both; user sees `andrew-*` prefix and skips Library skills
- `agent-sync verify` detects and re-creates any missing `andrew-*` fan-outs

---

## Edge cases to document in implementation

### Copy-mode installs
When the user passes `--copy` to npx (or npx falls back to copy because symlinks fail), agent skills appear as real directories rather than symlinks. agent-sync's Rule 4 detection (`isSymbolicLink()`) correctly identifies these as foreign and skips them.

### Global vs project scope mismatch
`npx skills add -g` installs to `~/.agents/skills/` and creates symlinks in `~/.claude/skills/` etc. agent-sync fan-out (Library) operates on the same global agent dirs. If agent-sync also targets global dirs:
- The naming prefix (Rule 2) still partitions names
- Rule 4 still applies: check whether an existing path is a symlink to `~/.agents/skills/` before overwriting

### The `skills-lock.json` restore trap
Because npx `skills-lock.json` is committed, cloning the dotfiles repo and running `npx skills experimental_install` (or the future `skills install` command) will re-install all npx-tracked skills. This will NOT restore Library fan-outs — that requires `agent-sync sync`. These are complementary restore paths, not competing ones.

### Universal agents receiving Library skills
OpenCode, Amp, Cline, and other universal agents read directly from `.agents/skills/`. If agent-sync must deliver Library skills to these Targets, options are:
- **Avoid** writing to `.agents/skills/` (hard rule above). Universal agent support may require a per-agent config path if one exists outside `.agents/skills/`.  
- **Accept the shared dir with strict prefix**: if `.agents/skills/andrew-frontend-design/` is created by agent-sync and `.agents/skills/emilkowalski-skills/` is created by npx, they coexist by name — but agent-sync is still writing to npx's canonical store, which violates Rule 1.  
- **Recommended**: defer universal agent Library fan-out until there is a per-agent config path outside `.agents/skills/`, or document that Library skills are not delivered to universal agents in v1.

### Name collision recovery procedure
If a name collision occurs (S1 or S8):
1. `agent-sync verify` detects that `<agent-dir>/andrew-<name>` now points to `.agents/skills/` instead of `library/` (or is a copy)
2. `agent-sync sync --force` re-creates the symlink to `library/`
3. The npx-managed copy remains untouched in `.agents/skills/<name>/`; the npx lock entry is also untouched

---

## Summary: minimum viable coexistence contract

| Invariant | Owner | Enforcement |
|---|---|---|
| agent-sync never writes to `.agents/skills/` | agent-sync | Hard check in fan-out logic |
| agent-sync never writes to `skills-lock.json` / `~/.agents/.skill-lock.json` | agent-sync | No code path touches these files |
| All Library fan-out paths use a consistent owner prefix | Library Manifest / agent-sync codegen | Validated at sync time |
| agent-sync checks symlink target before writing | agent-sync | Rule 4 guard |
| agent-sync state file tracks all owned paths | agent-sync | State written on every sync |
| `verify` detects and reports missing fan-outs | agent-sync | Diff state file vs filesystem |
| `npx skills remove --all -y` is never run unattended in this repo | Operator / CI | Documentation + hook guard |
