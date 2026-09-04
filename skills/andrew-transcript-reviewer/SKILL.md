---
name: transcript-reviewer
description: Use when the user shares a conversation log, agent run, Claude Code session, or subagent transcript and wants to know what went wrong, why the agent behaved unexpectedly, how to improve the prompting, or whether a workflow is well-structured. Also use when the user asks "what's wrong with this prompt", "why did it do X instead of Y", "how do I get better results from this agent", or pastes a conversation and asks for feedback. Do NOT use for code review, PR review, or reviewing written documents — this is specifically for reviewing agent/LLM interaction transcripts.
---

# Transcript Reviewer

Read a conversation transcript and produce a precise, actionable diagnosis — not a generic "be more specific" critique, but specific findings about what each side of the conversation did and didn't do well, and concrete changes that would produce a better outcome if the conversation were run again.

## Two Sides to Review

**The prompting side** — how requests were framed:
- Was the objective stated clearly enough to uniquely determine the desired output?
- Was necessary context provided, or did the model have to assume it?
- Was the output format, scope, or quality bar communicated?
- If this is a subagent prompt: was the task decomposed at the right granularity?

**The response side** — what the agent did with those prompts:
- Did it follow the actual instruction or its interpretation of it?
- Where did it make unwarranted assumptions without disclosing them?
- Where did it add unrequested content — summaries, hedges, caveats, restatements?
- Did it use the right tools in the right order, or waste round trips?
- Did it ask clarifying questions when it should have? Proceed when it should have paused?
- Did it verify its own output before claiming completion?

## Finding Format

For each issue:

**Finding:** One sentence describing the specific problem.
**Location:** Which turn or exchange (quote the relevant line if short).
**Root cause:** Prompt issue (missing context, ambiguous instruction) or response issue (model error, drift, slop).
**Impact:** What went wrong as a result — wrong output, wasted tokens, missed objective.
**Fix:** The specific change to the prompt, system prompt, or task structure that prevents this.

"Be more specific" is not a finding. "The prompt said 'review the code' without specifying whether to check for correctness, security, or style — the model defaulted to style and missed the SQL injection on line 47" is a finding.

## Categories

Group findings under whichever of these apply. Skip categories with nothing worth reporting.

### Prompt Weaknesses
- **Vague objective** — desired output isn't uniquely determined by the instruction
- **Missing context** — model needed information that wasn't provided
- **No output spec** — format, length, or quality bar wasn't stated
- **Over-specification** — constraints prevented a better approach
- **Bad delegation** — task split at wrong abstraction level (too broad or too narrow for a subagent)
- **Missing examples** — a single few-shot example would have resolved ambiguity that words couldn't

### Response Weaknesses
- **Assumption without disclosure** — proceeded on an assumption it didn't flag
- **Instruction drift** — addressed a plausible interpretation rather than the actual request
- **Slop** — unnecessary summaries, hedges, filler, or restating the question before answering
- **Missed tool** — a faster or more reliable approach was available and not taken
- **Wrong tool sequence** — tools used in an order that created unnecessary re-work
- **Premature completion** — claimed done before verifying the output
- **Overclaiming** — stated an inference as a fact

### Structural Issues
- **Wrong granularity** — should have been one task vs. many, or vice versa
- **Missing checkpoint** — model proceeded past a point where a human review would have caught a mismatch
- **Scope creep** — model (or prompt) expanded beyond what was asked
- **Context loss** — relevant earlier context wasn't referenced when it should have been

## Output Structure

**Executive summary** (2–4 sentences): what kind of interaction was this, overall quality, and the single most important thing to change.

**Findings** grouped by category, ordered by impact within each.

**Top 3 Actionable Changes**: the three specific edits — to a prompt, system prompt, or task structure — that would most improve this interaction if run again. Make these copy-pasteable where possible.

## Calibration

If the transcript shows a well-structured prompt producing a high-quality response, say so briefly and move on. The goal is not to find problems — it is to surface findings that would actually change behavior if acted on.

When the same pattern appears repeatedly (e.g., the model over-explains in every response), flag it once with the root cause rather than listing each instance.

If the transcript is very long, focus on: the first prompt (sets the whole trajectory), any turn where output quality dropped noticeably, and the final response.
