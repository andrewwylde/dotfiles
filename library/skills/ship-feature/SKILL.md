---
name: andrew-ship-feature
description: >
  Andrew's user-scoped overlay for shipping. Extends project /ship-feature with
  optional campaign profiles (Parables 609/613 visual proof + two human pauses),
  and gate scripts under ~/.cursor/skills/andrew-ship-feature/scripts/. Does not
  replace the project skill — always load and follow
  .claude/skills/ship-feature/SKILL.md first. Use for Parables campaign children
  or when you want overlay campaign/visual gates; otherwise use project
  /ship-feature.
---

# Andrew Ship Feature — User Overlay

Personal composition layer over the repo `/ship-feature` pipeline. Lives at
`~/.cursor/skills/andrew-ship-feature/SKILL.md`.

## Composition contract (required first)

1. **Read and execute** the workspace project skill:
   `.claude/skills/ship-feature/SKILL.md` (or the same skill under
   `.cursor/skills/ship-feature/` if that is what the workspace vendors).
2. Run project Stages 0–6 (and project gate scripts) as that skill defines.
3. This overlay **only adds** campaign detection, visual/reference gates, and
   human pauses. It does not redefine the base pipeline.

## When to use

| Invoke | When |
|--------|------|
| `/ship-feature` | Default shipping — project skill only |
| `/andrew-ship-feature` | Parables campaign children, or when you want this overlay's campaign/visual gates |

## Campaign profiles (optional)

Activated when the ticket resolves to a known campaign child. Profiles:
[`references/campaigns/`](references/campaigns/).

| Campaign | Children (examples) | Git base | Visual harness |
|----------|---------------------|----------|----------------|
| **PARABLE-609** | 641, 644, 631, 636, 640, 616, … | `origin/main` | `persistent_external` `/dev/ponder` |
| **PARABLE-613** | 1045, … | `origin/feature/parable-editor` | `app_route` `/admin/ponder` on PR worktree |

### Fixed decisions (campaign mode)

1. **Git base** comes from the campaign manifest (`git_base` / `stack_host`).
2. **ponder-admin** at `https://local.parable.work:5300/admin/ponder` remains a
   behavioral/visual **reference** for 609 chrome work (never the merge base).
3. **613+ visual proof** drives the **regular admin app** (`/admin/ponder`) on
   the PR worktree — no `/dev/ponder` region mounts, no separate editor slot.
4. **Two human gates** (campaign-only; must pause):
   - **Stage 3.9** — implementation approval (no source edits until approved)
   - **Stage 4.9** — visual QA approval (no `gh pr create` until approved)

### Activation

```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/activate_session.py --from-branch --task-desc "..."
```

When the ticket resolves to a campaign child:

- Writes `~/.cursor/ship-feature-state/<campaign>/<ticket>/campaign-snapshot.json`
- Writes `<workspace>/.context/campaign-gate.json`
- Prints `<CAMPAIGN> CAMPAIGN MODE` and may set `resume_stage: 39` (3.9)

### Campaign stages

```
… → 3.5b → 3.85 reference audit → 3.9 HUMAN impl approval
  → 4 implement → 4.8 visual after → 4.9 HUMAN visual approval → 5 ship …
```

- **609:** Stage 4.75 mounts into persistent `/dev/ponder`, then 4.8.
- **613 app_route:** skip region mounts; Stage 4.8 Playwright against `/admin/ponder`.

Full procedure: [`references/parables-campaign-stage-details.md`](references/parables-campaign-stage-details.md)

### Fail-closed enforcement

| Gate | Script |
|------|--------|
| Stage 4 + campaign | `stage_compliance_check.py --gate stage4` |
| Stage 5 PR | `stage_compliance_check.py --gate stage5-pr` |
| skill_gate | `~/.cursor/skills/_shared/skill_gate.py` blocks source edits / `gh_pr_create` |

Artifacts live under `~/.cursor/ship-feature-state/<campaign>/` — **not** in the repo.

### Autonomous rule carve-out

Between automated stages, continue without asking. **Must pause** at 3.9 and 4.9
in campaign mode. Do not forge approval artifacts; quote the user's verbatim
approval sentence into `approval_gate.py --approve`.

### Context pack requirements

Include campaign snapshot paths, parent AC/OOS, and `Reference Fidelity` +
`Visual Proof Matrix` plan sections when delegating plan-create / plan-review.
For app_route tickets, the matrix is Playwright scenarios against `/admin/ponder`.
