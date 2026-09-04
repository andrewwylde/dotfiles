---
name: dependency-canvas
description: >-
  Renders Linear tickets, GitHub PRs, and stacked-PR dependencies as an
  interactive Cursor canvas. Use when the user asks for an execution map,
  dependency canvas, dependency graph, to visualize Linear/GitHub/stack
  blockers, to re-render a shipment map, or after a gap analysis. Do NOT use
  for Mermaid or Excalidraw diagrams, PR reviews, or implementing tickets.
---

# Dependency Canvas

Turn Linear relations, GitHub PR state, and stacked-PR groups into one
interactive Cursor canvas. Chat stays BLUF. The canvas is the artifact.

Read `~/.cursor/skills-cursor/canvas/SKILL.md` before writing any
`.canvas.tsx`. Import only from `cursor/canvas`. Read
`~/.cursor/skills-cursor/canvas/sdk/index.d.ts` for exports.

## Inputs

One of:

- Linear ticket or epic ID (`PARABLE-2685`)
- Milestone or project name
- Existing gap analysis path (`~/.agent/reviews/<id>/gap-analysis.md`)
- Explicit list of tickets / PRs / stack branches

If scope is ambiguous, ask once. Do not visualize the whole workspace.

## Neighbor skills

| Need | Skill |
|------|--------|
| Fresh layer inventory | `andrew-gap-analysis` first, then this skill |
| PR split / HARD stacks | `andrew-changeset-decomposition` |
| Operate `gh stack` | `andrew-gh-stack` |
| Mermaid file | `andrew-mermaid-studio` (not this) |
| Excalidraw file | `andrew-excalidraw-studio` (not this) |

If a same-day gap analysis exists for the scope, consume it. Re-verify
Linear + GitHub + `origin/main` before drawing. Do not re-run the full
gap-analysis gather unless the user asked for a new analysis or the
doc is stale.

## Workflow

```
SCOPE → GATHER → CLASSIFY → DRAW → VERIFY → PRESENT
```

### 1. Scope

Fetch the root Linear issue with relations (`includeRelations: true`).
List children. Record parent, milestone, assignee, and `blockedBy` /
`blocks`. Write one sentence: what "done" means and which tickets are
in the picture.

### 2. Gather

Collect three graphs. Parallelize.

**Linear**

- Each child and each named gate: status, assignee, attachments, relations
- Stale-blocker check: if `blockedBy` is Done, keep it as Linear-only
- Do not treat a Done Linear blocker as a code gate

**GitHub**

- PR attachments on those tickets
- `gh pr view <n> --json number,title,state,mergedAt,updatedAt,reviewDecision,baseRefName,headRefName,url`
- Open PRs that mention the ticket IDs
- Merged PRs already cited as "on main"

**Stacks** (either or both)

- Planning stack: grouped PRs that land together (docs → schema → host)
- Git stack: `gh stack view --json` when the user named a stack, or
  recover the chain from PR `baseRefName` when branches stack

**Code truth**

- `git fetch origin <default-branch>` and record the SHA
- For each "on main" claim: `git show origin/<default>:<path>`
- For each "missing" claim: grep/glob more than one naming convention
- Linear Done is not evidence. A merged PR is not on main until the
  SHA is an ancestor of `origin/<default>`

Save a short inventory next to other planning artifacts when they
exist (`~/.agent/reviews/<id>/gap-analysis.md` or
`~/.agent/<id>/upstream-status.md`). Do not invent a new docs tree.

### 3. Classify

Read [references/status-model.md](references/status-model.md). Every
node gets one status. Every edge is `hard` or `soft`.

Default-select the current critical-path node (usually the next merge,
not the parent epic).

### 4. Draw

Write exactly one file:

`/Users/<user>/.cursor/projects/<workspace>/canvases/<scope>-execution-map.canvas.tsx`

Use the workspace canvases directory already in the environment. Do
not `mkdir`. Re-render by overwriting the same file when the user
says "re-render the map."

Required layout:

1. Header: title, verified date, SHA
2. Stats: on main / in review / missing (and extra live-gate counts
   only when they changed the picture)
3. One callout: critical path in one sentence
4. Graph: columns by shipment stage, nodes as buttons, SVG edges
5. Detail card for the selected node (owner, gate, Linear link)
6. Optional: stale-Linear table, landed-PR list, prompt buttons

Rules:

- Embed all data inline. No `fetch`.
- Colors from `useHostTheme()` only. Status dots use
  `theme.category.{green,cyan,yellow,orange,gray}`.
- Solid edge = hard. Dashed edge = soft / Linear-only / live-acceptance.
- Link Linear and GitHub from the detail card.
- If prompt files exist, `useCanvasAction` + `{ type: "openFile", path }`.
- No emojis, gradients, box-shadows, or a wall of identical cards.
- If there is no verified data, do not draw an empty canvas.

### 5. Verify

Before presenting, disprove the drawing:

1. Every PR state matches `gh pr view`
2. Every "on main" file exists at the recorded SHA
3. Every "missing" item is absent from main and from open PRs
4. Every Linear status is current
5. Stack edges match `gh stack view --json` or the PR base chain

Fix the canvas and the inventory when verification disagrees.

### 6. Present

Lead with the next unblocked work. Link the canvas with a short label
and its full absolute path. Do not dump the node table into chat.

Example:

> Critical path is still 2699-C1. Open the
> [PARABLE-2685 execution map](/Users/me/.cursor/projects/ws/canvases/parable-2685-execution-map.canvas.tsx)
> beside the chat.

## Re-render

When the user says "check current state and re-render":

1. Re-fetch Linear + GitHub + `origin/<default>`
2. Diff against the last inventory
3. Update statuses, gates, stats, and the callout
4. Add newly relevant gates (only if they change the path)
5. Keep prompt links and node IDs stable so selection still works

## Anti-patterns

- Treating Linear `blockedBy` as a code gate without checking status
- Drawing 2701 as startable while generated types are only in an open PR
- Waiting on a soft gate (ordinal fallback, fixture generator, stub error)
- Mermaid or markdown tables instead of the canvas
- A new canvas file per refresh when one already exists for the scope

## Additional resources

- Status, edges, columns: [references/status-model.md](references/status-model.md)
- Worked prompts: [examples.md](examples.md)
