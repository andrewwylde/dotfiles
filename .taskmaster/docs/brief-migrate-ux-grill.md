# Grilling brief: Migrate dry-run, verify gates, and rollback UX

> Task Master tag `agent-sync` — Task #7  
> Type: grilling (HITL)  
> Sources: [wayfinder-agent-sync-map.md](./wayfinder-agent-sync-map.md), [CONTEXT.md](../../CONTEXT.md), legacy README (`sync-ai-assistants --dry-run` / `--verify`)  
> Depends on: Task #1 *Inventory dual trees for migrate scope* (**still in progress** — keep scenarios generic)  
> Status: brief ready — do not treat as locked until grilling closes  
> Do **not** mark Task #7 done from this brief alone

---

## Why this grill exists

Wayfinder locked:

> Migration — **one-shot** into Library; stop versioning per-Target trees  
> CLI — `sync` / `verify` / `migrate` / `list`

“One-shot” is not a UX. Operators need a safe story for:

1. **Dry-run** — what will move / abandon / stay private before anything changes  
2. **Verify gates** — what must pass before mutate and after Fan-out  
3. **Rollback** — what happens if Fan-out fails mid-way or the operator panics

Task #1 inventory is **not finished**. This grill must lock **behavior contracts**, not path lists. Concrete inventory rows plug into the same UX later.

**Grill outcome (task `testStrategy`):** agreed migrate UX checklist `agent-sync migrate` must implement.

---

## Facts already settled (do not re-litigate)

- Destination is a working Sync tool with a real `migrate` command (not docs-only).
- After migrate, the Library owns skills/commands/agents/hooks; per-Target trees in the repo stop being the versioned source.
- Fan-out writes **Target home dirs only** (not committed).
- Unsupported Target×kind pairs **skip**; `verify` reports (not silent success-as-error).
- Cursor product skills → vendor namespace; do **not** manage `skills-cursor`.
- Private stays gitignored in-clone and/or `~/dotfiles-local/library/` (local-wins rules: Task #6).
- Legacy UX already taught dry-run + verify for the old assistant sync binary — migrate should feel at least as safe.

### Inventory status (do not block Round 1)

Task #1 dispositions (when ready) will classify each path as roughly:

`library | vendor/cursor | gitignore-private | dotfiles-local | abandon`

Until that artifact exists, grilling uses **placeholders**:

| Placeholder | Meaning |
|---|---|
| `INVENTORY_MOVE` | Path that will become a Library item |
| `INVENTORY_VENDOR` | Path that will land under `library/.../vendor/...` |
| `INVENTORY_PRIVATE` | Stays gitignore / dotfiles-local — not promoted |
| `INVENTORY_ABANDON` | Stop managing (e.g. `skills-cursor`) |
| `INVENTORY_UNKNOWN` | Unclassified — **hard stop** for real migrate |

---

## Design tree

```
Q1 Migrate phases + dry-run contract
 ├─ Q1a Required flags (--dry-run default? --write?)
 └─ Q1b Output shape (plan table vs narrative)
Q2 Verify gates (pre / mid / post)
 ├─ depends on Q1 phase list
 └─ Q2a Unknown inventory / dirty git policy
Q3 Rollback model
 ├─ Q3a What is rolled back (repo trees vs Target homes vs both)?
 └─ Q3b Backup medium (copy tree, tarball, git stash/branch)
Q4 Idempotency / re-run after partial failure
```

**Round-1 frontier:** Q1–Q3 can all be asked now (inventory-generic). Q4 after phases lock.

---

## Decision 1 — Phased migrate + dry-run

### Recommended phase pipeline

| Phase | Name | Mutates repo? | Mutates Targets? | Dry-run shows |
|---|---|---|---|---|
| **P0** | **Plan** | No | No | Full action table from inventory + live scan |
| **P1** | **Preflight verify** | No | No | Gate results (pass/fail) |
| **P2** | **Backup** | Yes (backup dir / tag only) | No | Backup path + size estimate |
| **P3** | **Library materialize** | Yes — write `library/` (+ private moves) | No | Copy/move map `src → dest`, abandon list |
| **P4** | **Repo tree retire** | Yes — stop versioning dual trees (delete/move aside) | No | Paths removed or relegated |
| **P5** | **Fan-out** | No | Yes — Target homes | Per-Target install plan |
| **P6** | **Post verify** | No | No | Diff vs expected state file / Manifest set |

**Dry-run (`migrate --dry-run`):** run P0 + P1 (+ simulated P2–P6 plan lines). **No** Library writes, **no** Target writes, **no** repo deletes.

**Apply (`migrate --write` or `migrate --apply`):** require explicit mutate flag. Default invocation with no flag = dry-run **or** error asking for `--dry-run` / `--write` (pick one in Q1; recommendation below).

### Options — default invocation

| ID | Option | Summary |
|---|---|---|
| **A1** | **Default = dry-run**; `--write` required to mutate | Safest; matches “show me first” habit |
| **A2** | **Default = refuse**; must pass exactly one of `--dry-run` \| `--write` | No accidental either way |
| **A3** | Default = write after confirmation prompt | Interactive; bad for scripts / CI |

### Recommendation: **A2 — Refuse unless `--dry-run` or `--write`**

Scripts stay non-interactive; humans cannot “forget” which mode they are in. Print a one-line hint listing both flags.

### Recommended dry-run table columns

```
disposition | kind | source_path | dest_path | action | notes
```

Example rows (generic):

| disposition | kind | source_path | dest_path | action | notes |
|---|---|---|---|---|---|
| MOVE | skill | `.claude/skills/example` | `library/skills/example` | copy→library | INVENTORY_MOVE |
| VENDOR | skill | `.cursor/skills/canvas` | `library/skills/vendor/cursor/canvas` | copy→vendor | INVENTORY_VENDOR |
| PRIVATE | skill | `.claude/skills/work-only` | `~/dotfiles-local/library/skills/work-only` | relocate-private | INVENTORY_PRIVATE |
| ABANDON | skill | `.cursor/skills-cursor/*` | — | leave / stop managing | INVENTORY_ABANDON |
| UNKNOWN | ? | `.claude/skills/mystery` | — | **block** | INVENTORY_UNKNOWN |

Exit code: **non-zero** if any UNKNOWN or preflight gate fails — even in dry-run — so automation can gate on “plan is clean.”

---

## Decision 2 — Verify gates

### Preflight (must pass before P2+)

| Gate | Rule | On fail |
|---|---|---|
| **G1 Inventory complete** | No `INVENTORY_UNKNOWN` (or `--allow-unknown` explicitly declined for v1) | Abort; print unknowns |
| **G2 Git clean enough** | No uncommitted changes under managed dual-tree paths **or** operator passed `--allow-dirty` | Abort (default) |
| **G3 Destination empty/conflict** | `library/` either absent, empty, or already matches prior migrate marker | Abort on unexpected overlap |
| **G4 Disk / permissions** | Can create backup + write Library + write Target parents | Abort |
| **G5 Binary/tool** | `agent-sync` itself runnable; Target dirs resolvable | Abort |

### Mid / post gates

| Gate | When | Rule |
|---|---|---|
| **G6 Backup readable** | After P2 | Backup manifest checksum / file count recorded |
| **G7 Library shape** | After P3 | Every MOVE/VENDOR row exists under `library/`; private rows exist under local/gitignore paths |
| **G8 Fan-out** | After P5 | `verify`-equivalent: expected Target installs present (copy/symlink rules); unsupported kinds = skip reports, not hard fail |
| **G9 State file** | After P5 | Sync state file written so future `verify` / `sync` know ownership |

### Options — post-Fan-out failure policy

| ID | Option | Summary |
|---|---|---|
| **B1** | **Hard fail migrate** if any required Fan-out target fails | Stop; enter rollback path |
| **B2** | Soft-fail per Target; migrate “succeeds” with warnings | Dangerous — dual trees may already be retired |
| **B3** | Split command: `migrate --library-only` then `sync`; Fan-out failure does not auto-rollback Library | More control, easier footgun |

### Recommendation: **B1 for v1 default**

One-shot means Library materialize + first Fan-out are one transactional *operator* story. Soft-fail after retiring dual trees leaves machines half-migrated. Offer **`--library-only`** later (Round 2) only if grilling insists on decoupling — not as silent default.

`verify` skips for unsupported kinds stay **warnings** inside G8, consistent with wayfinder.

---

## Decision 3 — Rollback

### What rollback restores

| Layer | Roll back? | How |
|---|---|---|
| Repo dual trees + new `library/` | **Yes** | Restore from P2 backup (preferred over `git checkout` alone if migrate also moved gitignored/private files) |
| Target home Fan-outs | **Best-effort** | Remove installs recorded in this migrate’s state diff **or** restore Target backup if taken |
| `~/dotfiles-local` private moves | **Yes if backup included them** | Same backup tree |
| Remote git / pushed commits | **Out of scope** | Migrate should refuse `--write` if it would require push; keep migrate local |

### Options — backup medium

| ID | Option | Summary |
|---|---|---|
| **C1** | **Timestamped directory** under `~/dotfiles/.agent-sync/backups/migrate-<ts>/` (gitignored) | Simple; includes gitignored files |
| **C2** | Git branch + stash only | Misses gitignored private paths |
| **C3** | Tarball of dual trees + Target snapshot | Portable; heavier |
| **C4** | C1 + optional Target snapshot behind `--backup-targets` | Balanced |

### Recommendation: **C4 — Repo/local backup always; Target backup opt-in**

- Always backup everything migrate will delete/move in the clone + private paths it relocates (C1).
- Target homes are large and machine-specific; default rollback for Targets = **delete Fan-outs created in this run** via state file, not full home restore.
- `--backup-targets` for operators who want a full safety net before P5.

### Rollback trigger UX

| Trigger | Behavior |
|---|---|
| Ctrl-C / SIGTERM mid P3–P5 | Stop; print `agent-sync migrate --rollback <backup-id>` |
| Gate fail after mutate started | Auto-offer rollback; **do not** auto-run without `--rollback` confirm flag |
| Explicit | `migrate --rollback <id>` restores backup; then `verify` |

**Do not** claim perfect atomicity across multiple Target directories. Claim: **repo/Library restore is reliable; Target restore is best-effort from this migrate’s install record.**

---

## Decision 4 — Idempotency (Round 2 draft)

Recommend:

- Re-running `--dry-run` always safe.
- Re-running `--write` after **successful** migrate: no-op or “already migrated” using marker file under `library/.agent-sync-migrated` (or state file) — exit 0 with message.
- Re-running `--write` after **failed** migrate: require `--rollback` first **or** `--resume` from last successful phase (implement one; recommendation = **rollback-then-retry** for v1 simplicity).

---

## Round 1 questions (for `/grilling`)

```
❓ **Q1** - **Dry-run default**: Refuse with no flags (A2), default dry-run (A1), or interactive write (A3)?

➡️ A2 — require `--dry-run` or `--write`; dry-run prints the disposition table and still exits non-zero on UNKNOWN/preflight fail.
```

```
❓ **Q2** - **Phases + gates**: Accept P0–P6 pipeline and gates G1–G9 (inventory-complete, dirty-tree policy, post-Fan-out hard fail)?

➡️ Accept; UNKNOWN blocks write; unsupported Fan-out kinds warn via verify-skip; Fan-out required-target failure aborts migrate (B1).
```

```
❓ **Q3** - **Rollback**: Timestamped gitignored backup of repo/private paths always; Target full snapshot opt-in; explicit `--rollback <id>` (no silent auto-rollback)?

➡️ C4 — always backup what migrate moves/deletes; Target backup via `--backup-targets`; restore is explicit; Target undo is best-effort from install record.
```

### Round 2 (after Round 1)

- Exact flag names (`--write` vs `--apply`).
- Whether `--library-only` ships in v1.
- Marker / state file location.
- Resume vs rollback-then-retry.
- How inventory artifact from Task #1 is passed in (`--inventory path` vs auto-discover).

---

## UX checklist (implement when locked)

Use as Task #7 acceptance criteria:

- [ ] `migrate` without flags errors with hint (or dry-runs — per Q1 lock)
- [ ] `--dry-run` prints disposition table; no mutations
- [ ] Dry-run / write both fail closed on UNKNOWN inventory rows
- [ ] `--write` runs preflight gates before backup
- [ ] Backup id printed and reusable with `--rollback`
- [ ] Post-Fan-out `verify` equivalent; required failures abort
- [ ] Unsupported kinds reported as skips, not greenwashed
- [ ] Docs: one-shot migrate + rollback paragraph in README / tool `--help`
- [ ] Inventory plug-in point documented (Task #1 artifact)

---

## Downstream updates when grilling closes

Do **not** mark Task #7 done from this brief alone. After HITL lock:

1. Append gist to wayfinder **Decisions so far**; remove “migrate dry-run / rollback story beyond one-shot” from **Not yet specified**.
2. Link this brief from Task #7 when resolved.
3. Keep Task #1 in progress until inventory artifact exists; migrate **implementation** may stub UNKNOWN detection against a live scan even before the artifact is complete.
4. Align naming with Task #6 local-wins if private relocate destinations are involved.

---

## One-line recommended lock

**Require `--dry-run` or `--write`; plan table + hard preflight; backup then materialize Library then Fan-out; fail closed on unknowns and required Fan-out errors; explicit `--rollback` from a timestamped backup (Targets best-effort).**
