---
name: session-postmortem
description: Use after completing significant work sessions to capture what succeeded, what failed, which skills helped or hurt, and what workflow friction to address. Feeds the self-improvement loop (effectiveness-map -> /improve-skill). Triggers on "postmortem", "session review", "retrospective", "what should we improve".
---

# Session Postmortem

Structured end-of-session learning capture. Extracts patterns from how the session went and writes findings to a persistent file that the effectiveness-map skill aggregates.

## When to Use

- After completing significant work (feature implementation, debugging session, review cycle)
- When the user asks "what should we improve" or "what went well"
- When a session felt particularly smooth or rough and the patterns should be captured

## Process

### Step 1: Gather Evidence

Review the current conversation for:
1. **What was attempted** -- the goals, tasks, and scope
2. **What succeeded** -- tasks completed, problems solved
3. **What failed or was abandoned** -- and why
4. **What was repeated** -- similar instructions given multiple times, rework
5. **What took surprisingly long** -- unexpected complexity or dead ends
6. **Which skills were invoked** -- and whether they helped
7. **Which skills should have been invoked but weren't** -- missed opportunities

### Step 2: Classify Findings

Sort findings into four categories:

| Category | Definition | Example |
|----------|-----------|---------|
| **Skill gaps** | Work that would have gone better with a skill that doesn't exist | "Spent 20 min manually formatting release notes -- a skill could automate this" |
| **Skill misfires** | Skills that triggered but didn't help or gave wrong guidance | "arch-review flagged non-issues in a simple handler change" |
| **Workflow friction** | Manual steps that could be automated with hooks, commands, or config | "Had to manually run psgen after every schema edit" |
| **Knowledge gaps** | Information the agent had to rediscover or couldn't find efficiently | "Couldn't find which EDR covers permission declarations" |

Also note **what worked well** -- skills that helped, patterns that were efficient.

### Step 3: Write Postmortem

Write to `~/.agent/postmortems/YYYY-MM-DD-<topic>.json`:

```json
{
  "date": "2026-04-14",
  "topic": "connector-status-page-implementation",
  "duration_estimate": "long|medium|short",
  "outcome": "completed|partial|abandoned",
  "summary": "One sentence describing the session.",
  "what_worked": [
    {"description": "...", "skill_or_pattern": "swarm-review"}
  ],
  "skill_gaps": [
    {"description": "...", "recommendation": "Create a skill for X"}
  ],
  "skill_misfires": [
    {"description": "...", "skill": "arch-review", "recommendation": "Adjust trigger conditions"}
  ],
  "workflow_friction": [
    {"description": "...", "recommendation": "Add a hook for X"}
  ],
  "knowledge_gaps": [
    {"description": "...", "recommendation": "Index EDRs in doc-index"}
  ]
}
```

### Step 4: Present Summary

Show the user a brief summary:

```
## Session Postmortem: [topic]

**Outcome:** [completed/partial/abandoned]

**What worked well:**
- [items]

**Improvement opportunities:**
- [top 2-3 actionable items across all categories]

**Next step:** Run `effectiveness-map` to see aggregated priorities, or `/improve-skill [name]` to act on a specific finding.
```

### Step 5: Offer Follow-Up

If any finding has a clear actionable recommendation (e.g., "the arch-review skill should be less aggressive on simple changes"), ask:

> "Want me to open a skill improvement session for [skill-name]?"

## Constraints

- Keep postmortems factual, not speculative. Only note things that actually happened in the session.
- Don't log every trivial observation -- focus on patterns that would matter if they recurred.
- One postmortem per session. If a session covers multiple topics, pick the dominant one for the filename and mention the others in the summary.
- The JSON file is the source of truth; the user-facing summary is a convenience view.
