# Gap Analysis Output Template

Use this structure for the markdown document produced in Phase 5.

```markdown
# Gap Analysis: [Milestone/Ticket Title]

**Date:** [YYYY-MM-DD]
**Scope:** [Brief description of what this analysis covers]
**Goal:** [From ticket/milestone description -- what "done" looks like]

---

## Settled Decisions

Decisions already resolved by the spec or by prior conversation. Each entry cites its authoritative source.

- [Decision in one line] ([source: file:line, PR #, Linear ticket, or `origin/main:path`])
- [Decision in one line] ([source])

**Rule:** nothing in this section may also appear under "Critical Path", "Things That Don't Exist Anywhere", or "Open Questions". On subsequent runs in the same session, consult this section first -- do not re-open a settled question without new evidence.

(Omit this section entirely if no decisions have been settled yet.)

---

## Pipeline Status

[ASCII diagram showing the layers involved and their status]

---

## Layer-by-Layer Inventory

### [Layer Name] ([Owner])

| Item | Status | On main? | Evidence |
|------|--------|----------|---------|
| [artifact name] | DONE / IN REVIEW / MISSING | Yes/No | [file path, PR number, or "not found"] |

**Gap:** [One sentence: what's blocking or missing in this layer. "None blocking [milestone]" if clear.]

[Repeat for each layer]

---

## Critical Path

The sequential chain of blocking items. Each step blocks the next.

1. **[Step name]** -- [status]. [Who owns it]. [What blocks it].
2. **[Step name]** -- [status]. [Who owns it]. [What blocks it].
...

## Things That Don't Exist Anywhere

Ranked by criticality (critical path items first).

| # | What | Layer | Ticket? | Blocks |
|---|------|-------|---------|--------|
| 1 | [name] | [layer] | No ticket, no owner | [what it blocks downstream] |
| 2 | [name] | [layer] | [ticket if exists] | [what it blocks] |

## Alternative Paths

[If a shortcut exists that bypasses part of the critical path]

**[Shortcut name]:** [What it does, what it skips, what it requires]

---

## Summary

| Category | Done | In Review | Gap |
|----------|------|-----------|-----|
| [Layer] | [items] | [PRs] | [missing items] |

---

Verified [date] against GitHub, Linear, and codebase. [Corrections from verification if any.]
```

## Writing guidelines

- Use "DONE", "IN REVIEW", "MISSING" consistently -- not "complete", "pending", "TBD", "WIP"
- Every claim needs evidence: a file path, PR number, or Linear ticket ID
- For "MISSING" items, confirm they don't exist in any open PR, not just main
- The "Things That Don't Exist Anywhere" section is the most important output -- rank by what blocks the critical path
- Keep the document scannable: a team lead should understand the state in 60 seconds from the summary table and the missing items list
- Frame gaps as facts, not blame: "no ticket, no owner" not "nobody bothered to create a ticket"
