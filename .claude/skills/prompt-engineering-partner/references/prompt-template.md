# Canonical Prompt Template

Every prompt you produce follows this structure. The examples below come from real shipped prompts — they demonstrate what "good" looks like for each section.

## Full skeleton

```markdown
# {Specific action-oriented title}

## Context

{One paragraph. What the agent is working on and why it matters.
Include the concrete state of the world — what branches exist, what's broken,
what's been tried, what's about to happen next. Never more than ~6 sentences.}

## What to read first

1. `{specific file path}` — {why this file}
2. `{specific command}` — {what this tells the agent}
3. `{specific directory}` — {what the agent will find here}

## What to produce

1. **{Deliverable 1 name}**: {concrete description with file paths and outputs}
2. **{Deliverable 2 name}**: {concrete description}

## Constraints

- {Specific rule with file reference when possible}
- {Specific rule}
- {Specific rule}

## Definition of done

- [ ] {Checkable outcome 1}
- [ ] {Checkable outcome 2}
- [ ] {Checkable outcome 3}
```

## Why these sections, in this order

**Context** comes first so the agent has a mental model before it starts reading.

**What to read first** is second because modern agents are tempted to start writing immediately. Front-loading required reading forces grounding.

**What to produce** comes before **Constraints** because "what" is load-bearing and "how" modifies it. Agents skim the middle of long prompts; put the work description before the rules.

**Definition of done** comes last so the agent finishes the prompt holding a checklist in working memory.

---

## Example 1: Git Branch Surgery

A real prompt for restacking a UI branch onto an API branch. Demonstrates concrete state description, ordered diagnostic commands, and a verifiable checklist.

```markdown
# Git Branch Surgery: Restack UI Branch onto API Branch

## Context

You have three existing branches in a stacked PR workflow that needs restructuring:

- `feat/PARABLE-495` — API-only changes (1 commit). Has an open PR targeting `main`.
- `feat/parable-495-merged` — UI+API changes combined. This is the source of truth for UI code.
- `feat/UI-188` — UI-only branch. Currently in a broken state (wrong base, doesn't compile, out of date). Has an open PR that currently targets the wrong base.

The goal is to reconstruct `feat/UI-188` so it contains exactly two commits:
1. The single API commit from `feat/PARABLE-495`
2. A single commit with only the frontend/UI changes from `feat/parable-495-merged`

After this, the PR for `feat/UI-188` should target `feat/PARABLE-495` (stacked PR). The API PR merges to `main` first, then the UI PR auto-retargets to `main`.

## What to read first

1. `git log --oneline feat/PARABLE-495` — confirm there is exactly 1 commit ahead of main
2. `git log --oneline feat/parable-495-merged` — understand the full commit history
3. `git log --oneline feat/UI-188` — understand current (broken) state
4. `git diff main...feat/PARABLE-495 --stat` — see what files the API commit touches
5. `git diff main...feat/parable-495-merged --stat` — see full scope of merged branch

## What to produce

1. Reconstruct `feat/UI-188` with exactly 2 commits:
   - Commit 1: identical to the API commit from `feat/PARABLE-495`
   - Commit 2: frontend-only code (files under `apps/`) from `feat/parable-495-merged`
2. Force-push the reconstructed branch
3. Update the PR for `feat/UI-188` to target `feat/PARABLE-495`

## Constraints

- When code conflicts between `feat/parable-495-merged` and `feat/PARABLE-495` on shared files, prefer the version from `feat/parable-495-merged`
- Do not modify `feat/PARABLE-495` itself
- Do not create new branches — work in place on `feat/UI-188`

## Definition of done

- [ ] `git log --oneline feat/UI-188` shows exactly 2 commits
- [ ] `git diff feat/PARABLE-495..feat/UI-188 --stat` shows only frontend files
- [ ] The PR for `feat/UI-188` is open and targets `feat/PARABLE-495`
- [ ] `feat/UI-188` compiles (run the project's build command)
```

**What this demonstrates:**
- Specific branch names, not placeholders
- "Read first" section has diagnostic commands, not just file paths
- Definition of done items are verifiable by running a command
- Constraints handle the conflict-resolution rule explicitly

---

## Example 2: Cross-PR Rebase with Changed Upstream

A real prompt for rebasing 5 stacked draft PRs after their upstream EDR landed. Demonstrates handling multiple related work items and explicit de-stacking.

```markdown
# Rebase and Update EDR-0011 Error Code PRs Post-EDR-0002 Migration

## Context

EDR-0011 introduced error codes across the platform. This work was split across 5 stacked draft PRs that went stale waiting for EDR-0002 to land on main. EDR-0002 has now landed and changed significant portions of the generated code: route handler definitions, response enveloping, query param serialization, and SDK shapes. You need to rebase each branch onto current main, resolve conflicts informed by both EDRs, de-stack the PRs so each targets main independently, and reopen them.

## What to read first

1. `docs/internal/edrs/edr-0011.md` — source of truth for what these PRs are trying to accomplish
2. `docs/internal/edrs/edr-0002.md` — understand what changed on main so you can resolve conflicts correctly
3. For each PR, run `gh pr view <number> --json headRefName,baseRefName,title,body`:
   - #1095 — add ErrorCode field and WithCode() method to AppError
   - #1096 — update SDK code propagation and detail fallback
   - #1097 — add error-codes dependency to API schemas
   - #1101 — display error codes in frontend toasts
   - #1102 — switch to RFC 7807 Problem Details wire format

## What to produce

1. For each branch, rebase onto current `main`, resolve conflicts using EDR-0011 as intent and EDR-0002 as the new baseline
2. De-stack: each PR's base should become `main`, not another PR's branch
3. Reopen each PR (they're currently closed/stale)
4. Update PR descriptions where EDR-0002 changed the approach (e.g., enveloping format)

## Constraints

- Preserve the original intent of each PR per EDR-0011 — don't silently change what the PR does
- If conflict resolution requires non-trivial judgment, leave a comment on the PR explaining the choice
- Do not merge any PRs — only rebase and reopen

## Definition of done

- [ ] All 5 branches rebase cleanly onto `main`
- [ ] Each PR's base is `main` (run `gh pr view <n> --json baseRefName` to verify)
- [ ] Each PR is in `OPEN` state, not closed or draft
- [ ] Where EDR-0002 changed the wire format, the PR description reflects the new format
```

**What this demonstrates:**
- "What to read first" uses EDRs as intent grounding, not just code
- The PR list is embedded in the reading instructions, not in a separate context blob
- "Definition of done" items each have a verification command

---

## Anti-patterns to avoid

### Vague reading instructions
- Bad: "Read the relevant files"
- Good: "Read `services/web-api/internal/route-impl/add_connector.go` to understand the route-impl pattern"

### Baked-in scope opinions
- Bad (inside the prompt): "Skip the frontend piece — it's out of scope" (when the user listed it in "Done looks like")
- Good (under Scope Opinions *after* the code block): "I suggest splitting the frontend piece into a second prompt because X. The current prompt still includes it per your spec — you decide."

### Generic padding
- Bad: "Be thorough and make sure to test your changes carefully"
- Good: "Run `make test-web-api` and ensure all tests pass"

### Missing state description
- Bad: "Update the connector status logic"
- Good: "The current connector status logic lives in `services/pkg/connectorstatus/status.go`. It currently returns raw status from the DB. Update `ResolveStatus()` to apply the priority order documented in EDR-0010 §3."
