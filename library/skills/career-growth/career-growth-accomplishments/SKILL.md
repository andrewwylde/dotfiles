---
name: career-growth-accomplishments
description: >
  Builds and maintains an accomplishment journal (brag doc) from evidence
  ledger entries and user notes, grouped by theme and impact. Use for "brag
  doc", "accomplishment journal", "what did I achieve this quarter", or to
  prep self-review and promotion packets.
disable-model-invocation: true
---

# Career growth accomplishments

Turn raw evidence into a durable accomplishments document employees update across the review period.

## Modes

Self-review (primary). Manager mode: compile accomplishments **with** the employee's self-assessment; do not replace their voice.

## Inputs

| Input | Required |
|-------|----------|
| `evidence_ledger` | recommended |
| `user_notes` | optional (paste or bullet list) |
| `period_start`, `period_end` | yes |
| `existing_journal` | optional (append mode) |

## Outputs

Markdown accomplishments journal:

```markdown
# Accomplishments: [Name] ([period])

## Executive summary
[3-5 bullets, impact-first]

## By theme
### [Theme / project]
- **[Date]** [Action] -> [Outcome]. Sources: ev-001, ev-002

## By competency (optional)
[Links to competency_mapping if provided]

## Still in progress
[Items started but not finished -- honest status]

## Gaps in record
[Sources that returned no data; user should fill manually]
```

Save path: user-specified or suggest `accomplishments-YYYY-H1.md` in their review folder.

## Human judgment

The employee owns the journal. AI organizes and sharpens wording; it does not add achievements without evidence or user confirmation.

## Composition

| Direction | Skill |
|-----------|-------|
| Upstream | `career-growth-evidence` |
| Downstream | `career-growth-self-review`, `career-growth-promotion-packet` |

## Workflow

### Phase 1: Merge sources

1. Import ledger entries (required fields: date, summary, impact, url).
2. Merge `user_notes`; dedupe against ledger.
3. If append mode, merge with `existing_journal` without losing prior content.

### Phase 2: Write for impact

Each bullet: **verb + scope + measurable or observable outcome**. Avoid vague praise ("great collaborator") unless tied to a specific incident.

### Phase 3: Quality pass

- Remove duplicate events across GitHub/Linear/Slack.
- Flag low-confidence items for user edit.
- List `gaps` from ledger under "Gaps in record".

## Failure modes

| Condition | Action |
|-----------|--------|
| No ledger and no notes | Ask user for bullets or run `career-growth-evidence` first |
| User disputes an entry | Remove or mark draft until confirmed |
