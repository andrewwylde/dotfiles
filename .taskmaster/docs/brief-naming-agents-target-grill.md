# Grilling brief: Fan-out naming and `.agents` Target

> Task Master tag `agent-sync` — Task #11  
> Type: grilling (HITL)  
> Sources: [research-npx-skills-coexistence.md](./research-npx-skills-coexistence.md), [research-target-install-path-matrix.md](./research-target-install-path-matrix.md), [wayfinder-agent-sync-map.md](./wayfinder-agent-sync-map.md)  
> Status: brief ready — do not treat as locked until grilling closes

---

## Why this grill exists

Two locked decisions now conflict:

| Decision | Source | Tension |
|---|---|---|
| v1 Targets include `.agents` | Wayfinder charting | `.agents` skills path is also **npx skills’ global canonical store** |
| agent-sync never writes `.agents/skills/` | Coexistence research (Rule 1) | Keeping `.agents` as a Fan-out Target requires writing that store |

Separately, vendor Cursor skills are already locked as `vendor-cursor-<name>`, but first-party Library fan-out naming is still open. Naming is the main soft partition against `npx skills list` / interactive `remove` pollution and name-collision overwrites.

**Grill outcome (task `testStrategy`):** written decision = Target list amendment (if any) + naming table for first-party vs vendor fan-outs.

---

## Facts already settled (do not re-litigate)

- Library canonical lives under `library/`; npx canonical lives under `.agents/skills/` / `~/.agents/skills/`.
- `npx skills update` only touches lock-file entries → Library fan-outs are safe from update.
- `npx skills remove` **filesystem-scans** every agent skill dir → can delete Library fan-outs (`--all -y` is critical).
- `npx skills add` overwrites same-named paths regardless of owner.
- Cursor Fan-out is always **copy** (symlink discovery bug); coerce copy if Target parent is an npx symlink farm.
- Cursor product skills: `library/skills/vendor/cursor/<name>/` → `~/.cursor/skills/vendor-cursor-<name>/`; do not manage `skills-cursor`.
- OpenCode has its own `~/.config/opencode/…` paths (not `.agents`).
- Pi reads both `~/.pi/agent/skills/` and `~/.agents/skills/`.
- agents-cli (the `.agents` Target) also owns `commands/`, `subagents/`, and YAML hook bundles under `~/.agents/` — not only skills.

---

## Design tree

```
Q1 Keep vs drop `.agents` as Fan-out Target
 ├─ Drop → Q1a What still covers Pi / agents-cli users?
 │         Q1b Amend wayfinder v1 Target list wording
 └─ Keep → Q1c Skills-only vs full kinds under ~/.agents?
           Q1d How to reconcile Rule 1 (canonical isolation)?
Q2 Fan-out naming scheme (first-party + vendor)
 ├─ depends lightly on Q1 (prefix still needed even if .agents dropped,
 │   because Claude/Cursor dirs are still scanned by npx remove)
 └─ Q2a Exact owner token (andrew / awylde / …)
     Q2b Apply prefix to commands/agents/hooks path stems too?
```

**Round-1 frontier:** Q1 and Q2 can both be asked now (naming is required regardless of Target list). Q1a–Q1d and Q2a–Q2b wait on Round 1.

---

## Decision 1 — Keep vs drop `.agents` as Fan-out Target

### Options

| ID | Option | Summary |
|---|---|---|
| **A1** | **Drop `.agents` from v1 Targets** | Treat `~/.agents/` as **npx / agents-cli territory**. agent-sync fans out only to Claude Code, Cursor, OpenCode, Pi. |
| **A2** | Keep `.agents`, **skills-only**, prefixed | Fan out Library skills into `~/.agents/skills/<prefix>-<name>/` only; skip commands/agents/hooks for this Target in v1. Relies on name partition; explicitly weakens coexistence Rule 1. |
| **A3** | Keep `.agents`, **full kinds**, prefixed | Skills + commands + `subagents/` + hook YAML bundles under `~/.agents/`, all with owner/vendor naming. Maximum agents-cli coverage; maximum overlap with npx’s home. |
| **A4** | Keep `.agents` as a **pass-through / document-only** Target | Adapter exists in schema for future use, but v1 `sync` never writes `~/.agents/skills/`. Useful if Manifests already mention `.agents` before adapters land. |

### Tradeoffs

| | A1 Drop | A2 Skills-only | A3 Full kinds | A4 Schema-only |
|---|---|---|---|---|
| Coexistence Rule 1 | Honors hard rule | Breaks for skills | Breaks for skills (+ more) | Honors hard rule |
| agents-cli users get Library skills | No (unless they use Claude/Cursor copies) | Yes | Yes | No |
| Pi coverage | Via Pi Target (`~/.pi/agent/skills/`) | Via `.agents` *and/or* Pi | Same | Via Pi Target |
| `npx remove --all -y` blast radius | Smaller in `~/.agents/skills/` | Library names still deletable there | Same + commands/subagents risk surface | Smaller |
| Implementation complexity | Lowest | Medium | Highest (hook YAML + subagents map) | Low now, debt later |
| Wayfinder amendment | Yes — remove from v1 list | Soften Rule 1 + document | Soften Rule 1 + document | Yes — “listed but inactive” |

### Recommendation: **A1 — Drop `.agents` from v1 Targets**

**Rationale**

1. **Hard conflict with the coexistence contract.** Research Rule 1 says agent-sync must never write `.agents/skills/`. Keeping `.agents` as a real Fan-out Target forces either violating that rule or inventing a second “canonical” story that npx will still scan and may delete.
2. **OpenCode does not need `.agents`.** It has first-class paths under `~/.config/opencode/`. Universal-agent arguments for writing `.agents` do not apply to the OpenCode Target we already committed to.
3. **Pi is covered without `.agents`.** Matrix note: Pi loads `~/.pi/agent/skills/` independently. Fan-out to the Pi Target is enough for v1; dual-writing via `.agents` is convenience, not necessity.
4. **agents-cli is optional in this workflow.** Wayfinder’s destination is agent-sync + `npx skills` for third-party — not agents-cli as a second sync engine. Writing into agents-cli’s tree invites two sync tools fighting over the same names.
5. **Blast radius.** Even with prefixes, anything under `~/.agents/skills/` is in npx’s remove candidate pool. Not writing there is the only way to keep Library skills out of that pool for that tree.
6. **Reversible.** If agents-cli becomes primary later, re-add `.agents` with a documented Rule-1 exception and mandatory owner prefix (A2/A3). Dropping now does not burn the bridge.

**If A1 is rejected:** prefer **A2** over A3. Skills-only keeps the exception narrow; commands/subagents/hooks under `~/.agents/` add adapter work and more delete/overwrite surface without unlocking Claude/Cursor (those Targets already get full kinds).

**Do not choose A4** unless Manifest schema work is already blocked on the Target enum including `.agents`. Prefer amending the v1 list cleanly.

### Suggested locked wording (if A1)

> v1 Targets: Claude Code, Cursor, OpenCode, Pi.  
> `~/.agents/` is **npx skills (and agents-cli) territory** — agent-sync does not Fan-out there.  
> Pi Library skills install to `~/.pi/agent/skills/` only.

---

## Decision 2 — Naming scheme for Library Fan-outs

Already locked for vendor Cursor product skills:

```
library/skills/vendor/cursor/<name>/  →  <Target>/skills/vendor-cursor-<name>/
```

### Options

| ID | Option | First-party example | Vendor example |
|---|---|---|---|
| **B1** | **Owner prefix for first-party + `vendor-<origin>-*` for vendor** | `andrew-frontend-design` | `vendor-cursor-canvas` (unchanged) |
| **B2** | **Vendor prefix only** — first-party unprefixed | `frontend-design` | `vendor-cursor-canvas` |
| **B3** | **No prefix for anyone** (vendor path stays namespaced in Library only) | `frontend-design` | `canvas` or keep path namespace without install prefix |
| **B4** | Uniform `library-` / `as-` tool prefix (not personal) | `library-frontend-design` or `as-frontend-design` | `vendor-cursor-canvas` |

### Tradeoffs

| | B1 Owner + vendor | B2 Vendor only | B3 None | B4 Tool prefix |
|---|---|---|---|---|
| Collision with popular npx skill names | Low | **High** | **High** | Low |
| `npx list` / interactive `remove` readability | Clear (`andrew-*` vs upstream) | First-party looks like npx | Ambiguous | Clear but impersonal |
| Matches existing Cursor skill habit | Yes (`andrew-ship-feature` already) | Breaks consistency | Breaks | New convention |
| Aligns with wayfinder vendor-cursor lock | Yes (symmetric: owner vs vendor) | Asymmetric | Breaks vendor lock if unprefixed | Asymmetric |
| Rename cost if owner changes | Medium (token in Manifest) | None | None | Low |
| Slash / skill invocation length | Longer | Short | Short | Longer |

### Recommendation: **B1 — Owner prefix + keep `vendor-<origin>-*`**

**Rationale**

1. **Coexistence research Rule 2 is hard.** Prefix is the only practical soft partition when Claude/Cursor skill dirs share a namespace with npx-managed names. Dropping `.agents` (A1) does **not** remove this need — `npx skills remove` still scans `~/.claude/skills/` and `~/.cursor/skills/`.
2. **Symmetry with the locked vendor pattern.** Wayfinder already chose `vendor-cursor-<name>` so product skills never collide with first-party. First-party should get the mirror: `<owner>-<name>`. Research already proposed this extension.
3. **B2 is unsafe.** Unprefixed `frontend-design` (etc.) is exactly the S1 overwrite scenario: `npx skills add` replaces the Fan-out; agents silently get the third-party body.
4. **B3 is worse** — also destabilizes the vendor-cursor lock and maximizes collisions.
5. **Local precedent.** First-party Cursor skills already use `andrew-*` (e.g. `andrew-ship-feature`). Fan-out naming should match how skills are already invoked.
6. **B4** is acceptable if the owner token feels too personal for a shareable Library, but this repo is personal dotfiles — `andrew-` is accurate and greppable. Prefer B1 unless grilling prefers a neutral `library-` / `as-` token (then lock that token explicitly).

### Recommended naming table

| Library path | Kind | Fan-out basename | Notes |
|---|---|---|---|
| `library/skills/<name>/` | skills | `andrew-<name>` | Owner prefix; Library folder stays unprefixed |
| `library/skills/vendor/cursor/<name>/` | skills | `vendor-cursor-<name>` | Already locked |
| `library/skills/vendor/<origin>/<name>/` | skills | `vendor-<origin>-<name>` | Future vendors |
| `library/commands/<name>/` | commands | `andrew-<name>` (or `.md` stem) | Same token as skills |
| `library/agents/<name>/` | agents | `andrew-<name>` | `.agents` Target would map to `subagents/` — N/A if A1 |
| `library/hooks/<pack>/` | hooks | pack id stays internal; entrypoint tags use `_as` merge | Naming of scripts under Target hooks dirs should still avoid bare collisions |

**Config suggestion:** single Manifest/global setting `owner_prefix: "andrew"` (no trailing hyphen in config; join as `{prefix}-{name}`). Changing the token later is a `migrate` / re-sync concern, not a silent dual-write.

### Non-goals for this grill

- Renaming Library *source* directories to include the prefix (keep Library names short; prefix at Fan-out only).
- Replacing `npx skills` discovery.
- Deciding Manifest filename/schema (separate graduation).

---

## Round 1 questions (for `/grilling`)

Use grilling format. Recommended answers match this brief.

```
❓ **Q1** - **`.agents` Target**: Keep `.agents` as a v1 Fan-out Target, or drop it so `~/.agents/` stays npx/agents-cli-only?

Options: A1 Drop · A2 Keep skills-only · A3 Keep full kinds · A4 Schema-only inactive

➡️ A1 Drop — honors coexistence Rule 1; OpenCode/Pi already have own paths; reversible later.
```

```
❓ **Q2** - **Fan-out naming**: Owner prefix for first-party, vendor-cursor-* only (first-party bare), or no prefixes?

Options: B1 Owner + vendor-* · B2 Vendor only · B3 None · B4 Neutral tool prefix (`library-` / `as-`)

➡️ B1 — `andrew-<name>` for first-party; keep `vendor-cursor-<name>`; Fan-out-time prefix only.
```

### Round 2 (after Round 1)

If **A1**: confirm Pi-only path + wayfinder Target list edit; confirm no adapter stub required in v1.

If **A2/A3**: lock Rule-1 exception text; require prefix; decide copy vs symlink under `~/.agents/skills/`; state-file tracking mandatory.

If **B1**: lock owner token string (`andrew` vs other); confirm prefix applies to commands + agents stems; confirm Library source dirs stay unprefixed.

If **B4**: lock exact token (`library` vs `as`).

---

## Downstream updates when grilling closes

Do **not** mark Task #11 done from this brief alone. After HITL lock:

1. Append gist to wayfinder **Decisions so far**; remove the naming/`.agents` bullet from **Not yet specified**.
2. If A1: amend Destination / v1 Targets line (drop `.agents`).
3. If B1: add naming table to Decisions; note `owner_prefix` config.
4. Soften or footnote coexistence Rule 1 only if A2/A3 wins.
5. Unblock Manifest grill / adapter work that depends on Target enum + basename rules.

---

## One-line recommended lock

**Drop `.agents` from v1 Targets; Fan-out first-party as `andrew-<name>` and keep `vendor-cursor-<name>` (prefix at install time only).**
