---
name: plan-adversary-review
description: Use when a plan, spec, or proposal needs automated adversary review before execution. Non-interactive -- runs three lenses (assumptions, pre-mortem, blast radius) without prompting for mode selection. Designed for pipeline use in /deep-plan or any automated planning chain.
---

# Plan Adversary Review

Automated three-lens adversary review for plans and specs. Unlike the-fool (interactive, user-selects mode), this skill runs all three lenses without stopping and produces a single structured output section.

## When to Use

- Before executing any implementation plan touching 3+ files or crossing service boundaries
- As a step in `/deep-plan` or other automated planning chains
- When you need structured adversary output without interactive mode selection
- When the-fool's interactive workflow would break an automated chain

When NOT to use: for interactive, deep-dive adversary sessions (use the-fool instead).

## Input

Read the plan or spec from: the current plan file, a file path the user provides, or inline content from the conversation.

## Process

Run all three lenses sequentially against the plan. For each lens, read the corresponding reference from the-fool:

### Lens 1: Assumption Inventory

Read `skills/the-fool/references/socratic-questioning.md` for methodology.

1. Extract every stated and unstated assumption in the plan
2. Rate each: High / Medium / Low confidence
3. For each Low or Medium assumption, write one probing question
4. Identify the single riskiest assumption

### Lens 2: Pre-Mortem (3 Failure Narratives)

Read `skills/the-fool/references/pre-mortem-analysis.md` for methodology.

1. Set the scene: "It's 3 months from now. This plan has failed."
2. Write exactly 3 failure narratives, each passing the specificity checklist:
   - Names a specific trigger
   - Includes a number or threshold
   - Describes the chain of events
   - Identifies who/what is affected
   - Could actually happen
3. For each narrative, trace a 2-level consequence chain
4. Identify one early warning sign per narrative

### Lens 3: Blast Radius

What the plan does NOT account for:

1. List adjacent systems, teams, or workflows that could be affected but aren't mentioned
2. Identify missing rollback or recovery strategy (if any)
3. Flag any implicit dependencies on external teams, services, or timelines
4. Note what happens if the plan succeeds but takes 2x longer than expected

## Output

Append this structured section to the plan (or output it for the caller to integrate):

```markdown
## Adversary Review

**Confidence:** HIGH / MEDIUM / LOW
**Riskiest assumption:** [one sentence]

### Assumptions

| # | Assumption | Confidence | Question |
|---|-----------|------------|----------|
| 1 | ... | High/Med/Low | ... |

### Pre-Mortem

#### Failure 1: [Title] -- Likelihood: X | Impact: Y
[Narrative]
- 1st order: ...
- 2nd order: ...
- Warning sign: ...

#### Failure 2: [Title] -- Likelihood: X | Impact: Y
[Narrative]
- 1st order: ...
- 2nd order: ...
- Warning sign: ...

#### Failure 3: [Title] -- Likelihood: X | Impact: Y
[Narrative]
- 1st order: ...
- 2nd order: ...
- Warning sign: ...

### Blast Radius

- **Adjacent systems affected:** ...
- **Missing rollback plan:** ...
- **Implicit dependencies:** ...
- **2x timeline scenario:** ...

### Recommended Mitigations

| Risk | Mitigation | Effort |
|------|-----------|--------|
| [From above] | [Specific action] | Low/Med/High |
```

## Constraints

- Never skip a lens. All three run every time.
- Keep failure narratives specific and grounded -- no vague "what ifs."
- If the plan references code or architecture, read the relevant files before reviewing.
- Do not ask the user to select modes or respond to challenges -- this is non-interactive.
- Do not synthesize a "strengthened position" -- that's the caller's job (or the-fool's job in interactive mode).
- Limit assumptions table to the 5-8 most significant, not an exhaustive audit.
