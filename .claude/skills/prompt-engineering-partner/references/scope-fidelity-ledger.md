# Scope Fidelity Ledger

The ledger is a trailing block you emit after every prompt. It exists so the user's Review Gate (Step 3 of their workflow) is a one-glance check instead of a manual diff against the intent spec.

## Why this exists

Before this skill, the user had to mentally diff your prompt against their intent spec — noticing dropped items, silent rescoping, or constraints that didn't make it in. That's tedious and easy to miss. The ledger makes every scope decision you made visible in one place.

If the ledger is complete and accurate, the user's Review Gate becomes: "does every spec item have a row, and does each treatment match my expectation?" — a ~30 second check instead of a multi-minute diff.

## Required structure

```markdown
## Scope Fidelity Ledger

| Intent spec item | Prompt section | Treatment |
|---|---|---|
| ... | ... | ... |

## Scope Opinions
- {only if you have scoping opinions — otherwise omit this section}

## Assumptions
- {only if you made assumptions worth flagging — otherwise omit this section}
```

## What to include in the ledger table

Every distinct item from the intent spec gets one row. Sources of items:

- Explicit "Done looks like" bullets
- Explicit constraints
- Context details the executing agent will need (branch names, file paths, PR numbers, etc.)
- Out-of-scope items (yes, these too — treatment: `marked out-of-scope`)

## Treatment values

| Value | When to use |
|---|---|
| `verbatim` | The prompt uses the same wording as the spec |
| `rephrased` | Same meaning, different wording (e.g., spec says "make it fast", prompt says "optimize for <500ms P99") |
| `summarized` | Multiple spec items condensed into one prompt section |
| `expanded` | You added sub-steps or detail the spec didn't specify |
| `split` | One spec item mapped to multiple prompt sections |
| `marked out-of-scope` | Spec listed it as out of scope and the prompt's "Out of scope" section reflects it |
| `dropped` | You did not include it — requires an entry under Scope Opinions explaining why |

## Worked example

**Intent spec from user:**
> Intent: Rebase 5 stacked draft PRs (#1095, #1096, #1097, #1101, #1102) onto current main. Done looks like: all 5 rebased cleanly, de-stacked so each targets main, reopened. Constraints: preserve original intent per EDR-0011, don't merge anything. Out of scope: resolving conflicts that require business logic changes — flag those in a PR comment.

**Ledger for the resulting prompt:**

```markdown
## Scope Fidelity Ledger

| Intent spec item | Prompt section | Treatment |
|---|---|---|
| PR #1095 (AppError.WithCode) | What to read first #3 + What to produce #1 | verbatim |
| PR #1096 (SDK code propagation) | What to read first #3 + What to produce #1 | verbatim |
| PR #1097 (error-codes schema dep) | What to read first #3 + What to produce #1 | verbatim |
| PR #1101 (frontend toast codes) | What to read first #3 + What to produce #1 | verbatim |
| PR #1102 (RFC 7807 wire format) | What to read first #3 + What to produce #1 | verbatim |
| rebase cleanly onto main | Definition of done #1 | verbatim |
| de-stack (base = main) | Definition of done #2 | rephrased as "each PR's base is `main`, verify with gh pr view" |
| reopen each PR | Definition of done #3 | verbatim |
| preserve original intent per EDR-0011 | Constraints #1 + What to read first #1 | split |
| don't merge anything | Constraints #3 | verbatim |
| business-logic conflicts → PR comment | Constraints #2 | rephrased as "if conflict resolution requires non-trivial judgment, leave a PR comment explaining the choice" |
```

No Scope Opinions or Assumptions sections needed here because nothing was dropped or inferred.

## When to write Scope Opinions

Only when you have a specific view on how the spec should change. Formats:

**Proposing a split:**
```markdown
## Scope Opinions

- I'd recommend splitting PR #1102 (RFC 7807 wire format) into its own prompt. It touches different layers (middleware, SDK, frontend) and the rebase conflicts will be larger in scope. The current prompt still includes it per your spec — you decide.
```

**Flagging a dropped item (rare):**
```markdown
## Scope Opinions

- **Dropped**: "reopen each PR". I omitted this from the prompt because 2 of the 5 PRs appear to already be open based on the `gh` state I'd expect. Listed as `dropped` in the ledger — add it back if you want explicit reopen commands for all 5.
```

**Scope concerns:**
```markdown
## Scope Opinions

- The intent spec implies the agent should resolve EDR-0011 ↔ EDR-0002 conflicts based on "which intent wins" judgment. This is high-ambiguity — consider pre-reviewing one PR's conflicts manually before handing all 5 to a fresh agent.
```

## When to write Assumptions

Use this section when you had to fill in a gap rather than ask a clarifying question (because the gap was minor). Examples:

```markdown
## Assumptions

- I assumed `main` is the target base (not `master` or `develop`). Adjust the prompt if that's wrong.
- I assumed the agent has `gh` CLI access. If not, the PR state verification commands won't work — use `git` + manual PR checks instead.
```

Avoid this section for major guesses — ask instead. Use it only for small defaults that would slow the user down if you'd stopped to ask.

## Anti-patterns

### Skipping the ledger on "simple" prompts
Even trivial prompts get a ledger. Brevity is fine — a 2-row ledger is still a Review Gate accelerator.

### Fake treatments
Don't mark `verbatim` if you rephrased. The user will diff, catch it, and lose trust in the ledger.

### Ledger as commentary
The ledger maps spec → prompt. It's not the place for your opinions on the spec — those go under Scope Opinions.

### Ledger instead of doing the work
A perfect ledger doesn't rescue a bad prompt. Spend the effort on the prompt first; the ledger should be the last 60 seconds.
