---
name: effectiveness-map
description: Use to aggregate session postmortem data into ranked improvement opportunities for the harness. Shows which skills to improve, which new skills to create, and which workflow automations to add. Triggers on "effectiveness map", "skill effectiveness", "harness health", "what should I improve".
---

# Effectiveness Map

Aggregates postmortem data and skill usage logs into a prioritized improvement roadmap for the harness.

## When to Use

- Periodically (weekly recommended) to review harness health
- Before deciding which skill to improve next
- When the user asks "what should I improve" about the harness itself

## Process

### Step 1: Gather Data

1. Read all postmortem files from `~/.agent/postmortems/*.json`
2. Read skill usage log from `~/.agent/skill-usage-log.jsonl` (if it exists)
3. List all installed skills from `~/.claude/skills/`

### Step 2: Aggregate Findings

From postmortems, count occurrences across all categories:

**Skill gaps** -- recurring requests for skills that don't exist:
- Group by similarity (e.g., "needed a release notes skill" x3 = high priority)
- Rank by frequency and estimated impact

**Skill misfires** -- skills that triggered but didn't help:
- Group by skill name
- Note the specific complaints

**Workflow friction** -- manual steps that could be automated:
- Group by type (hook, command, config)
- Rank by frequency

**Knowledge gaps** -- information that was hard to find:
- Group by topic
- Note whether doc-index would have helped

From skill usage logs (if available):
- Most-used skills (high value, worth polishing)
- Never-used skills (possibly poorly triggered or unnecessary)
- Skills invoked but not in postmortems (working well, no action needed)

### Step 3: Rank Opportunities

Produce three ranked lists:

1. **Top 5 skills to improve** -- existing skills with misfires or that are heavily used but have known issues
2. **Top 3 new skills to create** -- based on recurring skill gaps
3. **Top 3 workflow automations** -- hooks, commands, or config changes to reduce friction

### Step 4: Write Output

Write to `~/.agent/effectiveness-map.md` (human-readable):

```markdown
# Effectiveness Map

Generated: YYYY-MM-DD
Postmortems analyzed: N (date range)

## Skills to Improve

| Rank | Skill | Issue | Mentions | Recommendation |
|------|-------|-------|----------|---------------|
| 1 | ... | ... | N | ... |

## New Skills to Create

| Rank | Need | Mentions | Estimated Value |
|------|------|----------|----------------|
| 1 | ... | N | High/Med/Low |

## Workflow Automations

| Rank | Friction | Type | Mentions | Fix |
|------|----------|------|----------|-----|
| 1 | ... | hook/command/config | N | ... |

## Usage Insights

- Most used: [skill] (N invocations)
- Never used: [skills]
- Working well (no issues): [skills]
```

Write to `~/.agent/effectiveness-map.json` (machine-readable, same data structured for `autoimprove` and `/improve-skill`).

### Step 5: Present Summary

Show the user the top 3 actionable items with a suggestion:

> "Top improvement opportunity: [description]. Run `/improve-skill [name]` to act on it."
