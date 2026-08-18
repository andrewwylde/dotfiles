# Grilling brief: Local-wins overlay conflict rules

> Task Master tag `agent-sync` — Task #6  
> Type: grilling (HITL)  
> Sources: [wayfinder-agent-sync-map.md](./wayfinder-agent-sync-map.md), [CONTEXT.md](../../CONTEXT.md), README (`~/dotfiles-local` precedent)  
> Status: brief ready — do not treat as locked until grilling closes  
> Do **not** mark Task #6 done from this brief alone

---

## Why this grill exists

Wayfinder already locked:

> Private — gitignored in-clone + `~/dotfiles-local/library/` (**local wins**)

“Local wins” is underspecified. The Sync tool must know what happens when the same Library item name exists in both the public repo `library/` and `~/dotfiles-local/library/` — for **body**, **Manifest**, **overlays**, and **lifecycle ops** (add / override / delete / rename).

Today’s README precedent is path-based machine overrides (`~/dotfiles-local/.claude/skills/`, `*.local` files), not a second full Library tree. agent-sync introduces a real dual-Library merge; this grill locks the conflict table before implementers invent ad-hoc rules.

**Grill outcome (task `testStrategy`):** decision table covering add / override / delete / rename conflicts (plus Manifest + body granularity).

---

## Facts already settled (do not re-litigate)

- Library is the agent-neutral tree: `library/{skills,commands,agents,hooks}/` (glossary: CONTEXT.md).
- Private material is **not** committed: gitignored in-clone paths **and/or** `~/dotfiles-local/library/`.
- Fan-out installs into Target home dirs only (not committed).
- Hybrid install: symlink/copy; **Cursor always copy**.
- Vendor Cursor skills live under `library/skills/vendor/cursor/<name>/` — local overlay must not quietly claim that namespace without an explicit rule.
- Third-party discovery stays `npx skills`; local-wins is about **first-party / private Library items**, not npx canonicals.
- Manifest schema filename/shape is a separate grill — this brief talks about Manifest *as a concept* (targets, overlays, exclusions), not JSON keys.

### Assumed layout (for scenarios)

```
~/dotfiles/library/<kind>/<name>/          ← public (versioned)
~/dotfiles-local/library/<kind>/<name>/    ← machine-local (local wins)
```

Optional third bucket (already named in wayfinder): **gitignored in-clone** private under the repo. Round 1 should confirm whether that bucket merges with the same rules as `~/dotfiles-local/library/` or is a separate precedence tier.

---

## Design tree

```
Q1 Precedence model (whole-item vs field merge vs tombstones)
 ├─ Q1a Where do tombstones / deletes live?
 ├─ Q1b Gitignored in-clone vs ~/dotfiles-local — same rules or ordered tiers?
 └─ Q1c Manifest vs body — one rule or split?
Q2 Conflict table: add / override / delete / rename
 ├─ depends on Q1 (especially delete + rename)
 └─ Q2a Same name, different kind? (skills/foo vs commands/foo)
Q3 Operator UX when local shadows public
 └─ list / verify messaging; escape hatch to “use public”
```

**Round-1 frontier:** Q1 (model) can be asked now; Q2 table is recommended in this brief for ratification in the same round if Q1’s recommendation is accepted; Q3 is Round 2 after the table locks.

---

## Decision 1 — What “local wins” means structurally

### Options

| ID | Option | Summary |
|---|---|---|
| **A1** | **Whole-item replace** | If local defines `<kind>/<name>`, Fan-out uses the **entire** local item (body + Manifest + overlays). Public item for that key is ignored. |
| **A2** | **Field merge, local keys win** | Start from public item; deep-merge Manifest/overlays; local body file(s) replace same-relative paths; missing local fields inherit public. |
| **A3** | **Body-only local wins; Manifest always public** | Local may override skill/command body text; Targets/exclusions stay public-only (forces promoting Target changes to the repo). |
| **A4** | **A1 + explicit tombstones** | Like A1, plus a local marker that means “do not Fan-out this public name on this machine” (delete-without-deleting-public). |

### Tradeoffs

| | A1 Whole replace | A2 Field merge | A3 Body-only | A4 + tombstones |
|---|---|---|---|---|
| Mental model | Simple | Powerful, surprising | Simple, limited | Slightly more ops |
| Partial override (one file) | Copy whole item locally | Natural | Body yes / Manifest no | Same as A1 |
| Hide public item on one machine | Awkward (empty stub?) | Awkward | No | First-class |
| Manifest drift / merge bugs | None | Real risk | None | None |
| Matches “local wins” slogan | Yes | “Local keys win” | Partial | Yes + delete |

### Recommendation: **A4 — Whole-item replace + tombstones**

**Rationale**

1. **Predictable.** Whole-item replace matches how people already think about `~/dotfiles-local` overrides: a local copy is *the* item on this machine.
2. **Avoids Manifest merge footguns.** Overlay/array merge is still unspecified elsewhere; baking deep-merge into local-wins doubles that ambiguity.
3. **Tombstones close the delete gap.** Without them, “delete” on a machine either removes the public git file (wrong) or leaves the public item Fan-outing forever (local cannot win at absence).
4. **A2 is Round-2-only if needed.** If grilling later wants sparse overlays, graduate a separate “local patch” format — do not silently deep-merge in v1.
5. **A3 is too weak** for private Target exclusions / machine-only Manifest tweaks.

**Suggested tombstone shape (illustrative, not schema lock):** empty dir with a marker file, e.g. `~/dotfiles-local/library/skills/<name>/.agent-sync-tombstone`, or a side table under `~/dotfiles-local/library/_tombstones/`. Exact on-disk form can be an implementation detail once the *behavior* is locked.

**In-clone gitignored private:** treat as **same precedence class as `~/dotfiles-local/library/`**, with explicit order if both define the same name:

> `~/dotfiles-local/library/` > gitignored in-clone library > public `library/`

(Recommend local-home wins over in-clone so laptop/work splits stay outside the clone.)

---

## Decision 2 — Conflict decision table (recommended lock)

Identity key for conflicts: **`(kind, name)`** where `name` is the Library folder basename (Fan-out owner-prefix is a separate grill; local-wins is pre-Fan-out).

| # | Situation | Public `library/` | Local `~/dotfiles-local/library/` | Effective Library item | Notes |
|---|---|---|---|---|---|
| 1 | **Add (local-only)** | absent | present (full item) | **Local item** | Machine-only skill/command/agent/hook pack |
| 2 | **Add (public-only)** | present | absent | **Public item** | Normal shared Library |
| 3 | **Override (both present)** | present | present (full item) | **Local item entire** | No field merge; local Manifest replaces public Manifest |
| 4 | **Delete (tombstone)** | present | tombstone for `(kind,name)` | **Absent (skip Fan-out)** | Public stays in git; this machine does not install |
| 5 | **Delete (local-only removal)** | absent | was present, now removed | **Absent** | Trivial; nothing to Fan-out |
| 6 | **Delete public while local override exists** | removed in git | local still present | **Local item** | Local-only continues; warn on `verify` (“local orphan override”) |
| 7 | **Rename public** `a`→`b` | `b` present, `a` gone | still has `a` (or tombstone `a`) | See rows 1–4 for `a` and `b` separately | Rename is **not** a special op — treat as delete-old + add-new |
| 8 | **Rename local override** | public `a` | user renames local `a`→`b` | Public `a` returns; local `b` is add | Operator must tombstone `a` if they still want public `a` hidden |
| 9 | **Same name, different kind** | `skills/foo` | `commands/foo` | **Both** (independent keys) | No cross-kind collision |
| 10 | **Vendor path** | `skills/vendor/cursor/x` | local same path | **Local whole-item** (A4) | Discouraged; `verify` should warn — prefer not to shadow vendor |

### Operator rules of thumb

- **Override** = copy (or author) the full item under the local Library path with the same `(kind, name)`.
- **Delete on this machine** = tombstone, never edit public git to “win.”
- **Rename** = two keys; always reason about old and new names independently.
- **Promote local → public** = manual copy into repo `library/` + delete local copy (out of band; not a Sync-tool merge).

---

## Decision 3 — UX signals (Round 2 draft)

Recommend locking after the table:

| Command | Behavior |
|---|---|
| `agent-sync list` | Mark shadowed items (`local`, `tombstone`, `public`) |
| `agent-sync verify` | Fail or warn on: local orphan override (row 6); tombstone with no public; vendor shadow (row 10) |
| `agent-sync sync` | Resolve effective set via table; never write local Library into the git clone |

No escape-hatch flag required in v1 if tombstones + whole-item replace are enough; optional later: `--ignore-local` for debugging.

---

## Round 1 questions (for `/grilling`)

```
❓ **Q1** - **Local-wins model**: Whole-item replace, field-merge, body-only, or whole-item + tombstones?

Options: A1 Whole replace · A2 Field merge · A3 Body-only · A4 Whole replace + tombstones

➡️ A4 — predictable; avoids Manifest merge bugs; tombstones make “delete on this machine” real.
```

```
❓ **Q2** - **Conflict table**: Accept the recommended add/override/delete/rename table (rows 1–10), or change specific rows?

➡️ Accept table as-is; rename = delete+add on independent keys; cross-kind names do not collide; vendor shadow allowed but `verify` warns.
```

```
❓ **Q3** - **In-clone gitignored vs ~/dotfiles-local**: Same rules with local-home highest, or only one private root in v1?

➡️ Both allowed; precedence `~/dotfiles-local/library/` > in-clone gitignored library > public `library/`.
```

### Round 2 (after Round 1)

- Tombstone on-disk convention (marker file vs `_tombstones/` index).
- `verify` severity: warn vs fail for orphan overrides and vendor shadows.
- Whether Hook packs use the same `(kind, name)` table (`hooks/<pack>`).

---

## Downstream updates when grilling closes

Do **not** mark Task #6 done from this brief alone. After HITL lock:

1. Append gist to wayfinder **Decisions so far** (replace vague “local wins” with A4 + table pointer).
2. Link this brief (or a short ADR) from Task #6 when resolved.
3. Unblock Sync/resolve implementation and any Manifest grill that assumes overlay merge — local-wins is **not** deep-merge unless A2 wins.

---

## One-line recommended lock

**Local Library is whole-item replace over public `(kind, name)`, with tombstones for per-machine deletes; rename is delete+add; `~/dotfiles-local` beats in-clone private beats public.**
