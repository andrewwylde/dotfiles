# PARABLE-613 — Authoring and Lifecycle (campaign parent)

Parent: [PARABLE-613](https://linear.app/parable-work/issue/PARABLE-613/parables-authoring-and-lifecycle)

## Campaign mode

- **Git host:** stack PRs on `origin/feature/parable-editor` (not `main` until the editor branch lands).
- **Harness:** `app_route` — drive the regular admin app at `/admin/ponder` on the PR worktree. Do **not** add `/dev/ponder` region mounts for 613 children.
- **Human gates:** Stage 3.9 implementation approval; Stage 4.9 visual QA approval (same as 609).

## Active children

| Ticket | Focus |
|--------|--------|
| PARABLE-1045 | Interactive Plot Run → real Flight SQL results in BottomPane |

## Deferred (related, not this campaign's ship slice)

- PARABLE-337 / PARABLE-783 — durable runs, History population, scheduling
- PARABLE-336 — query sampling

## Visual proof

Matrix rows are Playwright scenarios against `/admin/ponder` (select Plot, edit SQL, Run, assert Results). Artifacts under `~/.cursor/ship-feature-state/parable-613/<ticket>/visual-proof/`.
