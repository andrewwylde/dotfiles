# PARABLE-609 — Parables: Core Components

## Acceptance criteria (inherited by every child)

- All Parable building blocks look and behave consistently wherever they appear.
- People can quickly identify each building block and understand where it belongs.
- People can navigate the Piece tree and open the right work without losing context.
- Editors, property controls, and results work together as one workspace.
- Locked and read-only content stays clear, useful, and easy to navigate.
- Current and historical report context is available so people know which data they are viewing.

## Out of scope (do not implement in 609 children)

- Detailed creation, editing, moving, deletion, and lifecycle rules (PARABLE-613 family).
- Publishing, approvals, conflict resolution, and governance (PARABLE-613).
- Tenant-facing consumption and delivery experiences.
- Child-level component behavior owned by a sibling ticket — cite and defer.

## Branching rules for this campaign

- Feature branches and PRs base on `origin/main`.
- `ponder-admin` is the behavioral and visual reference only (never the git merge base).
- Reference URL: `https://local.parable.work:5300/admin/ponder`.
