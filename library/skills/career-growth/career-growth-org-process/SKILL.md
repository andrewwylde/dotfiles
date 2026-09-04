---
name: career-growth-org-process
description: >
  Loads Parable review calendar, required document sections, deadlines, and
  calibration norms from Notion links in the career-growth README. Use before
  drafting self-reviews, manager reviews, promotion packets, or when the user
  asks about EOY, mid-year, review deadlines, or required sections.
disable-model-invocation: true
---

# Career growth org process

Resolve Parable-specific review requirements so drafts match the current cycle.

## Modes

Both self-review and manager review use the same org process facts.

## Inputs

| Input | Required | Notes |
|-------|----------|-------|
| `cycle` | optional | `eoy`, `mid-year`, or `current` (default: ask user if unclear) |
| `notion_export` | optional | Paste or file if Notion MCP unavailable |

## Outputs

`org_process_brief` markdown:

- Cycle name and key dates (submission, manager draft, calibration, delivery)
- Required sections for the employee self-review
- Required sections for the manager review
- Links to templates (promotion worksheet, accomplishments doc)
- Calibration reminders (human-owned; list norms only if documented in Notion)

## Human judgment

This skill reports process requirements. It does not assign ratings or run calibration.

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | none |
| Downstream | `career-growth-self-review`, `career-growth-manager-review`, `career-growth-promotion-packet`, `career-growth-orchestrator` |

## Organizational sources (canonical links)

Configured via user prompt, Notion URL, or local export (see [../README.md](../README.md)):

- Engineering Competency Matrix (user-provided Notion URL or document export)
- Values Competency Matrix (user-provided Notion URL or document export)
- EOY + mid-year reviews guidelines (user-provided Notion URL or document export)

Self-review templates: promotion leveling worksheet, accomplishments doc (user-provided paths or Notion).

Manager review: promotion leveling worksheet.

## Workflow

### Phase 1: Fetch process doc

1. If `user-Notion` MCP is available, fetch the EOY + mid-year page by URL.
2. Else if the user pasted an export, parse it.
3. Else ask the user for the current cycle deadlines and required sections. **Do not invent deadlines.**

### Phase 2: Extract checklist

Produce two checklists:

**Employee self-review**

- Required sections (from Notion)
- Suggested artifacts (accomplishments doc, evidence ledger)
- Due date

**Manager direct-report review**

- Required sections
- Feedback sources expected (peers, self, etc.)
- Calibration constraints documented in Notion
- Due date

### Phase 3: Handoff note

Tell the user which drafting skill to run next and which inputs are still missing.

## Failure modes

| Condition | Action |
|-----------|--------|
| Notion unreachable | Ask for paste/export; list README links |
| Cycle ambiguous | Ask: EOY or mid-year? |
| Process doc silent on a section | Mark "not specified in source"; do not guess |
