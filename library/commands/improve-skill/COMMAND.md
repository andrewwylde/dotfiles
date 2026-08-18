---
description: "Close the self-improvement loop: read effectiveness-map, gather evidence from postmortems and session logs, draft improvements to a specific skill, then benchmark with skill-creator. Usage: /improve-skill [skill-name]"
alwaysApply: false
---

# Improve Skill

Evidence-driven skill improvement that connects postmortem findings to the skill-creator's benchmarking infrastructure.

## Arguments

`$ARGUMENTS` should contain a skill name. If empty, read `~/.agent/effectiveness-map.json` and pick the top-ranked skill to improve.

## Step 1: Identify Target

If a skill name was given, use it. Otherwise:
1. Read `~/.agent/effectiveness-map.json`
2. Pick the #1 ranked skill from "skills to improve"
3. Confirm with the user: "The top improvement opportunity is [skill]. Proceed?"

## Step 2: Gather Evidence

1. Read the target skill's SKILL.md
2. Read relevant postmortem entries that mention this skill (grep postmortems for the skill name)
3. Use `read-memories` to search session logs for concrete examples of the skill being used -- both good and bad outcomes
4. Summarize: what specifically went wrong, what the skill should do differently

## Step 3: Draft Improvements

Based on the evidence:
1. Identify the specific failure mode (wrong trigger conditions, missing guidance, too verbose, etc.)
2. Draft targeted changes to the SKILL.md -- minimal edits addressing the evidence
3. Do NOT rewrite the entire skill. Surgical improvements only.

Present the draft changes to the user for review before applying.

## Step 4: Benchmark

After the user approves the draft:
1. Apply the changes to the skill
2. Invoke `skill-creator:skill-creator` to run the eval/benchmark loop on the improved skill
3. If the benchmark shows improvement (or the user is satisfied): keep the changes
4. If the benchmark shows regression: revert and try an alternative approach

## Step 5: Log Result

Append to `~/.agent/improvement-log.jsonl`:

```json
{
  "date": "2026-04-14",
  "skill": "arch-review",
  "evidence_source": "postmortem:2026-04-12-connector-work",
  "change_description": "Narrowed trigger conditions to exclude simple handler changes",
  "benchmark_result": "improved|regression|neutral",
  "kept": true
}
```

Report the result to the user.
