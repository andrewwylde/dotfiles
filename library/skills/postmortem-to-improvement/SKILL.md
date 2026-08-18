---
name: postmortem-to-improvement
description: Run a session postmortem AND immediately propose the top improvement it suggests, as a single chained flow. Use this whenever the user wants to close out a significant session with both reflection AND an actionable next step — e.g. "/postmortem-to-improvement", "wrap this session and tell me what to fix", "postmortem then improve", "what should I change based on how this went", "run postmortem and act on it". Prefer this over standalone `session-postmortem` when the session produced clear friction worth acting on; prefer standalone `session-postmortem` only when the user explicitly says they just want to capture, not act.
---

# Postmortem → Improvement

A two-stage chained flow that fuses `session-postmortem` and `/improve-skill`. Data from 7 days of usage showed these two fire together 4+ times in the same session — the user almost always wants to *do something* with the postmortem, not just file it. This skill removes the round-trip.

## Why this exists, not just the two skills independently

- `session-postmortem` writes findings to disk but leaves the actionable next step dangling ("Want me to open a skill improvement session?").
- `/improve-skill` needs evidence, and the freshest evidence is the postmortem that was just written — but running them sequentially costs a context switch.
- Fusing them preserves the reasoning from stage 1 into stage 2 without re-reading files.

## Stage 1: Postmortem (delegate)

Follow `~/.claude/skills/session-postmortem/SKILL.md` end-to-end. That produces:
- A JSON postmortem at `~/.agent/postmortems/YYYY-MM-DD-<topic>.json`
- A user-facing summary in the conversation

Do *not* prompt the user to follow up at Step 5 of that skill — this skill handles the follow-up.

## Stage 2: Identify the top improvement candidate

Using **only** the postmortem you just wrote (plus `~/.agent/effectiveness-map.json` if it exists) pick the single highest-leverage change. Candidates in priority order:

1. **Skill misfire** — an existing skill gave wrong guidance in this session. Fix the skill.
2. **Workflow friction** — a repeated manual step. Propose a hook.
3. **Skill gap** — work that needs a new skill. Sketch the skill (name, description, steps).
4. **Knowledge gap** — info that was hard to find. Propose where to index it.

Pick one. Not three. If the session had no actionable findings ("what worked" dominated), say so honestly and stop — don't invent a change.

## Stage 3: Draft the concrete change

Follow `~/.claude/commands/improve-skill.md` Steps 2–3 scoped to the candidate:

- For a **skill edit**: read the target SKILL.md, draft minimal surgical edits with before/after.
- For a **new skill**: sketch the frontmatter (name, description) + a 3–5 step process. Don't write the whole skill yet.
- For a **hook**: write the matcher + command + block message. Pipe-test it if you can.
- For an **index**: propose where and what to add.

## Stage 4: Gate — present and await confirmation

Show the user:

```
## Postmortem → Improvement

**Session outcome:** [from postmortem]

**Top finding:** [one sentence]

**Proposed change:**
- Type: [skill edit | new skill | hook | index]
- Target: [file path or skill name]
- Change: [concrete diff or sketch]
- Expected benefit: [what this kills or enables, from postmortem evidence]

Apply this change? (yes / revise / skip)
```

**Stop here.** Do not apply the change until the user says yes. If they say "revise", adjust and re-present. If "skip", log the postmortem as-is and stop.

## Stage 5: Apply (only on confirmation)

On yes:
- Skill edit → use Edit to apply.
- New skill → invoke `skill-creator:skill-creator` to scaffold it properly.
- Hook → invoke `update-config` to wire it into settings.json (don't hand-edit settings.json; the file_safety hook blocks direct writes).
- Index → write to the proposed location.

Then append to `~/.agent/improvement-log.jsonl` as `/improve-skill` Step 5 specifies.

## Scope discipline

- One change per invocation. If the postmortem surfaced three equally-important findings, present all three as a ranked list but only propose the top one concretely. The user can re-run for the others.
- Don't touch code outside the stated change. A postmortem is not a license to refactor.
- If Stage 1 produces a postmortem with no `skill_misfires`/`workflow_friction`/`skill_gaps`/`knowledge_gaps` entries (purely "what worked"), skip Stages 2–5 and just report that the session was clean.
