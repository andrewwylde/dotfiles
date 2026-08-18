---
description: "Auto-routing command: describe what you need and this routes to the right skill chain. Reads intent and picks the path — ship a feature, debug a problem, review code, or investigate an issue. Usage: /do 'description of what you need'"
alwaysApply: false
---

# Do

Describe what you need. This command reads your intent and routes to the right
skill chain. You don't need to know which skill to invoke.

## Routing

Parse `$ARGUMENTS` and classify the intent:

| If the description sounds like... | Route to | Example |
|---|---|---|
| Building something new, implementing a feature, a Linear ticket ID | `/ship` | "add retry logic to connector sync", "SYSTEM-1354" |
| Something is broken, a bug, unexpected behavior | `superpowers:systematic-debugging` | "null account_ids in Slack Silver tables" |
| Review code, check a PR, audit changes | `/review-fix-loop` | "review PR #482", "check the auth refactor" |
| Understand the codebase, find something, explore | `codenavi` or Explore agent | "how does the permission system work" |
| Plan or design something (not implement yet) | `/deep-plan` | "design the admin config API" |
| Challenge a decision or stress-test an idea | `the-fool` | "should we use microservices for this" |
| Improve the harness itself | `/improve-skill` or `effectiveness-map` | "what should I improve in my workflow" |

## Classification Rules

1. **Linear ticket IDs** (pattern: `TEAM-NNNN`) always route to `/ship`
2. **PR numbers or GitHub URLs** always route to `/review-fix-loop`
3. **Questions** ("how", "why", "what", "where") route to exploration
4. **Problem statements** ("X is broken", "X isn't working", "error in X") route to debugging
5. **Everything else** routes to `/ship` (building is the default)

## Execution

After classifying:

1. Announce the routing: "This sounds like [classification] — routing to [skill/command]."
2. If ambiguous, ask: "I could treat this as [A] or [B]. Which fits better?"
3. Hand off to the target skill/command with the full description as context

Do NOT re-parse arguments or lose context during handoff. The target command
receives the original description verbatim.
