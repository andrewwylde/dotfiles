# pr-review

Review a pull request at a staff engineer level using a streamlined diff-based workflow.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Git repository initialized and connected to GitHub

---

## AI Execution Steps

**IMPORTANT: Steps 1-3 are setup/preparation only. Do NOT perform any analysis or review work until step 4.**

When this command is invoked, automatically perform these steps:

### 1. Get the PR number

- Extract from user input (e.g., `/pr-review 11` or `/pr-review #11`).
- This command only activates when invoked with the `/pr-review` slash command.
- If no number is provided, ask:  
  `Which PR number should I review?`

### 2. Verify prerequisites

Run and verify:

```bash
command -v gh
git rev-parse --git-dir
```

If either fails, inform the user and stop.

### 3. Fetch PR data

Run these commands (no checkout needed—`gh pr diff` works from any branch):

```bash
# Get the diff
gh pr diff <PR_NUMBER> > .context/prs/diffs/pr<PR_NUMBER>.diff

# Get PR metadata
gh pr view <PR_NUMBER> --json title,body,author --jq '"## \(.title)\n\nAuthor: \(.author.login)\n\n\(.body)"'
```

- If the diff file is empty, inform the user and stop.
- Store the PR metadata as the **PR Summary** for review context.

### 4. Conduct the review

- Use the `read_file` tool to read `pr<PR_NUMBER>.diff`.
- Follow the **Review Prompt** below.
- If you need more context, list specific file paths and why so the user can attach them.

### 5. Write the review output

- Use `write_file` to create:

  ```text
  PR_REVIEW_#<PR_NUMBER>.md
  ```

- The file content must exactly follow the **Output structure** described below.

---

## Review Prompt

You are reviewing a pull request at a staff engineer level.

### Context

- This diff is PR #<PR_NUMBER> (use the actual PR number from step 1).
- You have the **PR Summary** (title, description, author) from the submitter to understand intent.
- You also see the diff and any files I attach as context.
- If you need more context, list specific file paths and why, and I will provide them.
- Assume a layered data architecture with clear boundaries (e.g., Bronze / Silver / Gold, ingestion vs transform vs serving).
- Immutability in raw layers and idempotency in transformed layers are required.
- Clean code, small focused functions, and clear data contracts are expected.

### Priorities

1. Correctness and data contracts
2. Performance and memory characteristics
3. Long term maintainability
4. Style and minor consistency

### Review Convention

Use these prefixes to clarify intent and priority in your review comments:

- **`!!`** - Blocking issues that must be fixed before merge. Use for security vulnerabilities, logic bugs, correctness errors, or anything that would break production. Signals "I cannot approve this PR until this is addressed."

- **No prefix** - Standard feedback expected to be addressed. Use for suggestions, design concerns, or improvements you believe should change but aren't blocking on. This is the default for most feedback.

- **Rhetorical questions** (no prefix) - Questions that imply concern and expect a response or fix. Examples: "Why aren't we validating this input?" or "Shouldn't this be async?" These function similarly to no-prefix feedback.

- **`?`** - Genuine curiosity without implied criticism. Use when you want to understand the reasoning behind an implementation choice. Example: `? Why did we choose Redis over Memcached?` This creates space for learning without suggesting the choice is wrong.

- **`nit`** - Minor style or consistency tweaks that don't affect functionality. These should never block a PR. Use for small improvements that could be fixed if already editing nearby code, but aren't required.

- **`->`** or **`>>`** - Good ideas that are out of scope. Use for refactoring opportunities, performance optimizations, or improvements better suited to a separate PR. Acknowledges the idea without derailing current work.

- **`+`** - Positive feedback. Use when something is clever, well-tested, cleanly implemented, or demonstrates good patterns. Balances critical feedback and shows thorough review.

### Tasks

1. Read the diff and any related files needed for context.
2. Produce a PR review in the exact structure below.
3. Use appropriate prefixes to signal priority and intent in all comments.
4. Be direct and specific. Avoid generic advice.

### Output structure

#### 1. Summary of changes

- Brief, high-level description of what this PR does.
- Mention any new modules, major refactors, or contract-impacting changes.
- List concrete changes with file paths and line numbers where appropriate.

#### 2. Architectural risks

- **`!!` Blocking architectural issues**:
  - Items that could cause correctness errors, brittle coupling, unclear ownership, bad layering, or long-term maintenance pain.
  - For each issue, include:
    - **What**: Specific description with file paths and line numbers
    - **Impact**: Concrete explanation of the risk or maintenance burden
    - **Recommendation**: Actionable fix
- **Standard feedback** (no prefix or rhetorical questions):
  - Improvements that address architectural concerns but aren't blocking.
  - Suggestions that improve clarity, consistency, or future extensibility.
- **`nit`** - Minor clarity or consistency improvements that don't affect architecture.
- **`+`** - Well-architected patterns worth highlighting and potentially replicating.
- Explicitly call out:
  - Any violation of layering (e.g., business logic in ingestion, dedupe in Bronze, cross-layer coupling).
  - Any new patterns that deviate from existing architectural conventions in the repo.
  - **Duplication**: If logic/patterns are duplicated, list ALL locations with specific file paths and line numbers.

#### 3. Data contract violations

- **`!!` Blocking contract violations**:
  - Changes to schemas, field names, types, nullability, or semantics that might break downstream consumers without a migration path.
  - Silent behavior changes that might alter meaning of existing fields.
  - For each issue, include:
    - **What changed**: Specific field/schema with file path and line number
    - **Impact**: Which downstream parts are affected
    - **Recommendation**: Concrete action (e.g., add migration, bump version, add explicit docs, or revert)
- **Standard feedback** (no prefix):
  - Contract changes that need documentation, versioning, or migration planning but have a path forward.
- **`?` Questions** - Clarification about contract decisions or design choices.
- **`nit`** - Suggestions to document contract changes better or name fields more clearly.

#### 4. Performance hazards

- **`!!` Blocking performance issues**:
  - Patterns that are likely to cause memory blowups, unnecessary scans, full table operations, or N+1 style behavior.
  - Examples: early JSON decode before dedupe, premature explode, repeated scans, unnecessary collects, non-pushdownable filters.
  - For each issue, include:
    - **What**: Specific code pattern with file path and line number
    - **Impact**: Why it's a problem (memory spike, slow execution, resource exhaustion)
    - **Recommendation**: How to fix it (e.g., move dedupe after extraction, avoid explode before filter, restructure lazy pipeline)
- **Standard feedback** (no prefix):
  - Suboptimal patterns worth fixing but not causing immediate resource exhaustion.
- **`->`** or **`>>`** - Optimization opportunities better suited for a separate PR.
- **`nit`** - Micro-optimizations or readability changes that would improve performance but are not critical.

#### 5. Testing and validation gaps

- **`!!` Blocking test gaps**:
  - Missing tests for new logic, changed contracts, failure paths, or critical edge cases.
  - Inadequate coverage for data shape changes (e.g., new JSON structure, new types, new branching).
  - For each issue, include:
    - **What's missing**: Specific test scenarios or coverage gaps
    - **Impact**: Risk of regressions or undetected failures
    - **Recommendation**: Concrete tests to add or validation approach
- **Standard feedback** (no prefix):
  - Additional test coverage recommended but not critical for merge.
- **`nit`** - Suggestions for improving test clarity, parametrization, fixtures, or documentation.
- **`+`** - Particularly thorough test coverage or well-structured test patterns.
- Call out:
  - Specific scenarios that should be tested but are not (with file paths and specific functions).
  - Any gaps between documented behavior and what tests assert.

#### 6. Git hygiene issues

- **`!!` Blocking hygiene problems**:
  - Commits that mix unrelated concerns, hard-to-revert changes, or introduce noisy history that obscures intent.
  - **Formatting mixed with functional changes**: Whitespace/style changes bundled with logic changes (list specific files).
  - **Multiple unrelated features**: Changes that should be separate PRs combined into one.
  - For each issue, include:
    - **What**: Specific files or commits that violate hygiene
    - **Impact**: Why it makes review/revert harder
    - **Recommendation**: How to split or reorganize (e.g., "split formatting in X and Y into separate commit")
- **Standard feedback** (no prefix):
  - Commit organization recommendations that improve clarity but aren't blocking.
- **`nit`** - Minor commit message improvements or suggestions for squashing, renaming, or grouping commits for a cleaner story.
- If needed, propose:
  - A concrete squash/cleanup plan (for example: "squash commits 3–9 into a single 'Refactor X to Y' commit and keep commit N as the behavior change").

#### 7. Specific inline comments to paste into GitHub

- Provide a list of ready-to-paste comments using the prefix convention:
  - `file_path:line_number – <prefix> <one to three sentence comment>`
- **Use appropriate prefixes**:
  - `!!` for blocking issues that must be fixed
  - No prefix for standard feedback expected to be addressed
  - `?` for genuine questions seeking understanding
  - `nit` for minor style/consistency tweaks
  - `->` or `>>` for out-of-scope improvements
  - `+` for positive feedback on good patterns
- **Keep comments concise**: Each comment should be 1-3 sentences, directly paste-able into GitHub without editing.
- **Be specific**: Include exact line numbers, variable names, function names.
- **If patterns are duplicated**: List ALL locations in relevant comments (e.g., "This regex is duplicated in X:123, Y:456, Z:789").
- Focus on:
  - Violations of layering or contracts
  - Non-obvious logic
  - Places where future maintainers are likely to get confused
  - All instances of duplicated code/logic/patterns
- Example formats:
  - `src/flows/github_commits_by_branch.py:142 – !! This decodes JSON before dedupe and explode, which can cause a large memory spike on wide payloads. Consider deduping on a stable key first, then decoding only the surviving rows.`
  - `src/utils/validation.py:67 – Missing input sanitization here. Should validate before processing.`
  - `src/handlers/auth.py:23 – ? Why JWT over sessions for this use case?`
  - `src/models/user.py:89 – nit Variable \`x\` could be \`userId\` for clarity`
  - `src/transforms/aggregate.py:156 – -> This aggregation could be optimized with window functions (separate PR)`
  - `tests/test_integration.py:234 – + Excellent edge case coverage here`

### Constraints

- **Be thorough**: Don't skip sections. If there are no issues, explicitly state "None" rather than omitting the section.
- **Use appropriate prefixes**: Signal priority and intent clearly using the prefix convention. Reserve `!!` for truly blocking issues that prevent approval.
- **Distinguish question types**: Use `?` for genuine curiosity without implied criticism. Rhetorical questions (no prefix) function as standard feedback expecting a response or fix.
- **Include positive feedback**: Use `+` to highlight good patterns, thorough testing, or clean implementations. This balances critical feedback.
- **Be specific**: Always include file paths, line numbers, function names, variable names where applicable.
- **List ALL instances**: If you find duplication or a pattern repeated multiple times, list every occurrence with line numbers.
- **Check git hygiene carefully**: Look for formatting-only changes mixed with functional changes (whitespace, quote style, indentation changes bundled with logic).
- **Be concrete and opinionated**: Prefer fewer, higher quality comments over a sea of vague suggestions.
- **Write paste-able inline comments**: Keep inline comments concise (1-3 sentences) and ready to paste into GitHub without editing. Use prefixes consistently.
- **Assume the author is a capable engineer**: Provide direct, actionable feedback without handholding.

## Output

Generate your analysis as a markdown document named `.context/prs/reviews/PR_REVIEW_#<PR_NUMBER>.md` in the repository root. Replace `<PR_NUMBER>` with the actual PR number from step 1.
****
