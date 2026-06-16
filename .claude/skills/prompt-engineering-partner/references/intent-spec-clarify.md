# Clarifying Before Drafting

When the intent spec is ambiguous or missing information the fresh agent will need, ask before drafting. Skip this when the spec is clear enough to produce a prompt that survives the Review Gate.

## When to ask vs. when to infer

**Ask** when:
- The spec references specific entities (branches, PRs, files, IDs) but doesn't name them
- The spec implies multiple possible scopes and the right split isn't obvious
- The spec mentions a tool or system the executing agent might not know about
- The "Done looks like" criteria would be unverifiable without more detail
- The spec doesn't say which project/repo, and you can't infer it from context

**Infer and state your assumption** when:
- The spec is clear but you're filling in a minor detail (e.g., the exact command flag)
- A reasonable default exists (e.g., "the tests" probably means `make test` or equivalent)
- You can point at the assumption under an "Assumptions" heading so the user can correct it

Never guess silently. Either ask, or state the assumption in writing.

## Question patterns

### Entity identification
- "What are the exact branch names (I'll inline them into the prompt)?"
- "Which PR numbers? I'll list them explicitly so the agent doesn't have to search."
- "Which file is the source of truth for X? I'll make that the first item in 'What to read first.'"

### Scope boundaries
- "You mentioned X and Y. Should the prompt cover both, or just X with Y as follow-up?"
- "Is the frontend piece in scope for this prompt, or separate?"

### Verification targets
- "How should the agent verify it's done — a test command, a specific file output, a PR state check?"

### Tool/environment
- "Does the executing agent have `gh` CLI access? Slack MCP? The Linear MCP?"
- "Will this run in a worktree or the main checkout?"

### Convention discovery
- "Where do project conventions live — is there a CLAUDE.md, an EDR directory, a specs/ folder?"

## Format

Ask in one numbered list, max 3–6 questions. Keep each tight — a single concrete ask per line. Don't batch rounds; the user paid for a single clarifying exchange, not a back-and-forth.

```
Before I draft, a few clarifications:
1. What are the three branch names exactly?
2. When UI code conflicts between the two source branches, which version wins?
3. Is there an open PR for the UI branch already, or do I include creating one in the prompt?
4. Where should I tell the agent conventions live (CLAUDE.md path)?
```

## After clarification

Once you have the answers, produce the prompt. Do not ask follow-up clarifying questions unless a previous answer exposed a new unknown — and even then, acknowledge the delay ("one more thing before I draft…") rather than sliding into an interview.

## Anti-patterns

- **Asking everything.** Six questions is the ceiling, not the target. If the spec is clear, produce the prompt.
- **Asking what you could infer.** Don't ask "what's the repo's primary language" if the spec mentions Go files.
- **Asking questions the user already answered.** Re-read the spec before listing questions.
- **Multiple clarifying rounds.** If a second round is genuinely needed, say so explicitly; otherwise draft with assumptions and let the user correct.
