# Status and edge model

Use these labels on the canvas. Do not invent a second vocabulary.

## Node status

| Status | When | Dot |
|--------|------|-----|
| `done` | Required artifacts are on `origin/<default>` | `theme.category.green` |
| `review` | Open PR owns the remaining artifacts | `theme.category.cyan` |
| `start` | Code-unblocked, no open PR, ready to dispatch | `theme.category.blue` |
| `blocked` | Hard dependency is not on main | `theme.category.yellow` |
| `coordinate` | No hard dep, but file ownership must be confirmed | `theme.category.orange` |
| `external` | Outside the epic, or Linear-only / live-acceptance gate | `theme.category.gray` |

Linear status is a hint, not the node status.

- Linear Done + missing on main → `blocked` or `external`, never `done`
- Linear In Progress + open PR for the remaining slice → `review`
- Linear In Progress + no PR and a real upstream missing → `blocked` or `external`
- Linear Backlog + all hard deps on main → `start`

## Edge kind

**Hard** (solid): the downstream ticket cannot compile, type-check, or implement against main without the upstream artifact.

Examples: generated contracts → gRPC handler; adapter → runtime; host language → editor extra-libs.

**Soft** (dashed): the downstream ticket can ship a tested slice with a named fallback.

Examples:

- Preferred ordinal with a documented total-order fallback
- Live `outputSchema` writer when fixture Plots exist
- `resultUri` writer when the read path returns a structured not-ready error
- A Linear blocker whose work is Done
- A Linear blocker that the current slice does not consume (predicate bindings vs schema-only C1)

Never draw a hard edge for a Linear relation alone.

## Three graphs, one picture

Each node may carry facts from all three. Status follows **code truth**, then PR state, then Linear.

1. **Linear** — parent/child, `blocks` / `blockedBy`, assignee
2. **GitHub** — open / merged PRs, review decision, last update
3. **Stacks** — planning group (T1/T2/T3) or `gh stack` base chain

A planning stack in review is one node (`3 PRs open`) unless the user asked to explode layers.

## Stale Linear

A `blockedBy` row is stale when the blocker is Done or the current slice does not need that artifact.

Show stale relations in a compact table. Do not paint the dependent node `blocked` for a stale row.

Typical pairs:

| Listed blocker | Clear when |
|----------------|------------|
| Foundation ticket | Its PR is on `origin/<default>` |
| Fetch / transport ticket | Runtime only needed the merged client |
| Historical schema split | That split already merged |
| Projection / ledger ticket | The writer already landed |

## Columns

Left to right by shipment, not by Linear parentage:

1. Foundations and live gates
2. Contracts
3. Execution
4. API and runtime
5. Editor / product surface

Drop empty columns. Add a column only when a node would otherwise sit on the wrong stage.

Live gates that do not block the next SDK slice stay in column 1 as `external`.

## Node fields

Required: `id`, `label`, `shortLabel` (ticket id), `status`, `statusLabel`, `x`, `y`, `owner`, `purpose`, `gate`, `url`.

Optional: `promptPath` for a paste-ready subagent brief.

`gate` is the one sentence a dispatcher needs ("PR #5841 open since DATE, REVIEW_REQUIRED"), not the ticket description.

## Critical path

The sequential hard-edge chain to user-visible value. State it as ticket IDs:

`2699-C1 → 2701/2708 → 2702 → 2709 → 2710`

Parallel tracks (TSX host, live R8) sit beside it, not on it, unless they are the next merge.

## Unblocked next

A ticket is unblocked when:

1. Every hard upstream is `done` or the remaining work is already in its own `review` PR
2. Soft upstreams have a named fallback
3. No missing generated type is required to compile the first test

Finish in-flight `review` work before dispatching a new `start` node on the same path.
