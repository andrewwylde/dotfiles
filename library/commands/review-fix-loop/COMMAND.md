# review-fix-loop

Automated review-fix cycle: run `/swarm-review` on the current branch's PR, implement tactical fixes, re-review — repeating until the review passes or hitting a max iteration cap. Architectural and systemic feedback is collected but never acted on.

## Arguments

Optional arguments after the command:
- `max=N` — max cycles (default: 3)
- A **review target** (see below) — what code to review
- Anything else is treated as a scope hint for the review (e.g., "focus on the handler layer")

### Review Targets

The skill accepts many ways to specify what code to review. If multiple are given, the first recognized target wins.

| Input | Example | What gets reviewed |
|---|---|---|
| PR number | `pr=482`, `#482`, `482` (bare number) | `gh pr diff 482` |
| PR URL | `https://github.com/org/repo/pull/482` | Extracts PR number, uses `gh pr diff` |
| Branch name | `branch=feature/auth-refactor`, `feature/auth-refactor` | Diff from merge-base with default branch to tip of that branch |
| Commit hash | `abc123f`, `abc123f..def456a` | `git diff <hash>` or `git diff <hash1>..<hash2>` |
| Commit range | `HEAD~3`, `HEAD~3..HEAD` | `git diff` on the range |
| File/dir path | `src/api/handlers/`, `src/lib/auth.ts` | Diff of those paths against the base branch |
| GitHub permalink | `https://github.com/org/repo/blob/abc123/src/file.ts#L10-L50` | Extracts file, ref, and line range — reviews that file in context of full branch diff |
| _(nothing)_ | `/review-fix-loop` | Falls back to diff of current branch vs its base (merge-base with default branch) |

Examples:
```
/review-fix-loop
/review-fix-loop max=2
/review-fix-loop pr=482 focus on connector status validation
/review-fix-loop #482
/review-fix-loop https://github.com/your-org/your-repo/pull/123
/review-fix-loop feature/auth-refactor
/review-fix-loop abc123f..def456a
/review-fix-loop HEAD~5
/review-fix-loop src/api/handlers/ focus on error handling
/review-fix-loop max=5 abc123f
```

## Why This Exists

Code review feedback often includes a mix of quick tactical fixes (typos, missing error checks, lint issues) and deeper architectural observations. Humans are good at the architectural judgment calls but spend a lot of time on the mechanical fixes. This skill automates the mechanical part: run review, fix the easy stuff, re-review, repeat — so by the time a human looks at the PR, only the interesting feedback remains.

The hard cap on iterations (default 3) prevents runaway loops. The strict separation between tactical and systemic findings prevents the skill from attempting changes that need human judgment.

## Prerequisites

- `gh` CLI authenticated (for PR-based targets; branch/hash targets work without it)
- The `/swarm-review` skill available and working
- The project should be a git repository

## Sandbox Note

File edits use Claude's built-in Edit/Write tools, which bypass the bash sandbox entirely. Only test/lint commands run through bash. If you have sandbox enabled and tests need to write outside the project directory (e.g., coverage output, temp files), add those paths to your `settings.json`:

```json
{
  "sandbox": {
    "filesystem": {
      "allowWrite": ["/tmp", "~/.cache"]
    }
  }
}
```

This is optional — most projects work fine with default sandbox settings.

---

## Execution Steps

Follow these steps exactly. Do not skip the parsing logic or attempt systemic fixes.

### Step 0: Parse Arguments and Resolve Review Target

1. Parse arguments from `$ARGUMENTS`:
   - Extract `max=N` if present (default: 3, hard cap: 5)
   - Identify the review target (see resolution order below)
   - Everything that isn't a target or `max=N` becomes the `SCOPE_HINT`

2. **Resolve the review target** by checking these patterns in order. Stop at the first match:

   **a) GitHub PR URL** — matches `github.com/.*/pull/(\d+)`
   ```bash
   # Extract PR number from URL
   PR_NUMBER=<extracted digits>
   TARGET_MODE="pr"
   ```

   **b) Explicit PR** — matches `pr=(\d+)` or `#(\d+)`
   ```bash
   PR_NUMBER=<extracted digits>
   TARGET_MODE="pr"
   ```

   **c) GitHub permalink** — matches `github.com/.*/blob/([a-f0-9]+)/(.+?)(?:#L(\d+)(?:-L(\d+))?)?`
   ```bash
   # Extract commit ref, file path, and optional line range
   PERMALINK_REF=<extracted ref>
   PERMALINK_FILE=<extracted path>
   PERMALINK_LINES=<extracted range or empty>
   TARGET_MODE="permalink"
   # The file serves as a focus hint; the actual diff is the full branch diff
   # containing that ref. Append the file to SCOPE_HINT.
   ```

   **d) Commit hash or range** — matches `[a-f0-9]{7,40}` (single hash), `<hash>..<hash>`, or `HEAD~\d+` patterns
   ```bash
   # Validate the hash exists
   git rev-parse --verify <hash> 2>/dev/null
   DIFF_SPEC="<the hash or range as given>"
   TARGET_MODE="diff"
   ```

   **e) Explicit branch** — matches `branch=(.+)` or an arg that matches an existing branch name
   ```bash
   # Verify branch exists (use --verify to confirm it's a ref, not a file path)
   git rev-parse --verify <branch> 2>/dev/null
   # If the arg also matches a file/directory, prefer branch only if branch= prefix was used.
   # Unprefixed args that match both a branch and a path: prefer the path (more common intent).
   DIFF_BRANCH="<branch name>"
   TARGET_MODE="branch"
   ```

   **f) File/directory path** — an arg that matches an existing file or directory in the repo
   ```bash
   # Verify path exists
   test -e <path>
   PATH_FILTER="<path>"
   TARGET_MODE="path"
   ```

   **g) Bare number** — matches `^\d+$` (could be a PR number)
   ```bash
   # Try as PR first
   gh pr view <number> --json number 2>/dev/null
   # If that works:
   PR_NUMBER=<number>
   TARGET_MODE="pr"
   # If not, skip — it'll fall through to the default
   ```

   **h) Default fallback** — no target recognized
   ```bash
   # Try to find a PR for the current branch
   PR_NUMBER=$(gh pr view --json number --jq '.number' 2>/dev/null)
   if [ -n "$PR_NUMBER" ]; then
     TARGET_MODE="pr"
   else
     # No PR — diff current branch against its base
     TARGET_MODE="branch-diff"
   fi
   ```

3. **Generate the diff** based on `TARGET_MODE`:

   | TARGET_MODE | How to get the diff |
   |---|---|
   | `pr` | `gh pr diff $PR_NUMBER` |
   | `branch` | `git diff $(git merge-base $DIFF_BRANCH $(git symbolic-ref refs/remotes/origin/HEAD \| sed 's@refs/remotes/origin/@@'))..$DIFF_BRANCH` |
   | `diff` | `git diff $DIFF_SPEC` |
   | `path` | `git diff $(git merge-base HEAD $(git symbolic-ref refs/remotes/origin/HEAD \| sed 's@refs/remotes/origin/@@'))..HEAD -- $PATH_FILTER` |
   | `permalink` | Same as `branch-diff` but append `PERMALINK_FILE` to `SCOPE_HINT` for focused review |
   | `branch-diff` | `git diff $(git merge-base HEAD $(git symbolic-ref refs/remotes/origin/HEAD \| sed 's@refs/remotes/origin/@@'))..HEAD` |

   If the diff is empty, tell the user: "No changes found for the given target. Nothing to review." and stop.

4. **Determine artifact naming**:
   - PR mode: `~/.agent/reviews/pr-${PR_NUMBER}-review.md`
   - All other modes: `~/.agent/reviews/review-${TARGET_MODE}-$(date +%Y%m%d-%H%M%S).md`

5. Store:
   - `TARGET_MODE`, `PR_NUMBER` (if applicable), `DIFF_SPEC` / `DIFF_BRANCH` / `PATH_FILTER` (as applicable)
   - `MAX_CYCLES` (from arg or default 3)
   - `SCOPE_HINT` (from remaining args or empty)
   - `CYCLE` = 1
   - `ALL_FIXES_APPLIED` = [] (accumulator across cycles)
   - `DEFERRED_FEEDBACK` = [] (systemic items, accumulated)
   - `CAN_PUSH` = true only if `TARGET_MODE` is `pr` or `branch` and the branch has an upstream. Otherwise false — fixes get committed locally but not pushed.
   - `STATIC_DIFF` = true if `TARGET_MODE` is `diff` with a fixed hash range (e.g., `abc123..def456`). A static diff can't reflect fixes, so override `MAX_CYCLES` to 1 — review once, fix, done. `HEAD~N` ranges are NOT static (they shift as you commit).

### Loop Discipline

- **Every cycle MUST run the full swarm review (Step 1).** You cannot declare
  PASS based on your own assessment of the fixes.
- **The review artifact file MUST exist and be recent** before parsing (Step 2).
  Run `find ~/.agent/reviews/ -name "*.md" -mmin -5 | head -1` to verify.
- **After implementing fixes (Step 4), you MUST go back to Step 1 and re-run
  the swarm.** Do not skip the re-review because "the fixes are mechanical."

### Step 1: Run Swarm Review

Run the `/swarm-review` workflow using the diff generated in Step 0. Adapt based on `TARGET_MODE`:

**If `TARGET_MODE` is `pr`**:
Follow the standard swarm-review flow — it already knows how to handle PRs:
1. `gh pr view $PR_NUMBER --json title,body,labels,files`
2. `gh pr diff $PR_NUMBER`
3. Follow swarm-review's Phase 1-5 workflow

**If `TARGET_MODE` is anything else** (branch, diff, path, permalink, branch-diff):
You already have the diff from Step 0. Adapt swarm-review's workflow:
1. Use the diff you generated — no need for `gh pr diff`
2. For Phase 1 (Gather Context): use `git log --oneline` on the relevant range to understand intent, plus any scope hint the user provided
3. For Phase 2 (Intent): if user gave a `SCOPE_HINT`, use it. Otherwise infer from the diff and commit messages
4. For Phase 3-5: proceed normally — subagent swarm, synthesis, artifact

Ensure the artifact directory exists (`mkdir -p ~/.agent/reviews/`) before saving. Save the artifact using the naming convention from Step 0.

**Subagent tool access**: Specialist agent types (`golang-pro`, `code-reviewer`, etc.) have restricted tool access — most can't use Bash and some can't use Read. To use them safely, **include all code they need to review directly in the prompt**. Before launching the swarm, read the relevant files yourself and embed the full file contents (or diff hunks with surrounding context) in each agent's prompt. This way the specialist agent can review from context alone without needing filesystem access. The prompt should contain everything the agent needs — don't rely on agents being able to `cat` or `grep` files.

If a specialist agent needs to run commands (e.g., check types, run lint), use `general-purpose` for that agent instead and encode the specialist lens in the prompt.

**Important**: During swarm-review's Phase 4, when it says "Present and wait for user feedback" — do NOT wait. The review-fix-loop automates this step. Proceed directly to parsing.

### Step 2: Parse the Review Artifact

Read the saved artifact file. Extract findings into two categories:

**Tactical fixes** — items under `## Tactical Fixes (this PR)`:
- `### Blockers` items — each has a description and effort estimate
- `### Improvements` items — each has a description and effort estimate

**Systemic items** — items under `## Systemic Follow-ups (separate PRs)`:
- Append these to `DEFERRED_FEEDBACK`. Do not attempt to fix them.

**Determining the verdict**:
- If there are **zero** Blockers AND **zero** Improvements → verdict is **PASS**
- If there are any Blockers or Improvements → verdict is **NEEDS WORK**

If the artifact file doesn't exist or can't be parsed, report the error and abort. Do not retry the review.

### Step 3: Check Verdict

**If PASS and `ALL_FIXES_APPLIED` is empty**: Skip commit — nothing to commit. Go directly to the report (Step 5 output format, verdict = "PASS, no fixes needed").

**If PASS and `ALL_FIXES_APPLIED` is non-empty**: Go to Step 5 (commit and report).

**If NEEDS WORK and CYCLE < MAX_CYCLES**: Go to Step 4 (implement fixes).

**If NEEDS WORK and CYCLE >= MAX_CYCLES**: Go to Step 6 (report without committing).

### Step 4: Implement Tactical Fixes

For each tactical fix (Blockers first, then Improvements), in order:

1. **Read the finding** and understand what file(s) and code need to change.

2. **Classify the fix type**:
   - **Safe to auto-fix**: Edits to existing files, adding test cases to existing test files, creating new test files, fixing lint/type errors, adding missing error handling, fixing string/format issues.
   - **NOT safe to auto-fix**: Deleting files, removing dependencies, changing public API signatures, modifying CI/CD config, anything that changes behavior in a way that requires human judgment.

3. **If safe**: Implement the fix using Edit/Write tools. Use Read first to understand the surrounding code. Make the minimal change needed.

4. **If not safe**: Skip it and add to the "remaining tactical issues" list with a note explaining why it was skipped.

5. After each fix, add a short description to `ALL_FIXES_APPLIED`.

After all fixes are implemented:

6. **Run tests** if the project has an obvious test command (look for `Makefile`, `package.json` scripts, or `go test`). This is a sanity check — if tests fail on something you just changed, investigate and fix before proceeding.

7. **Stage the changes**: `git add` the specific files you modified. Do NOT use `git add -A`.

8. Do NOT commit yet. Increment `CYCLE` and go back to Step 1.

### Step 5: Commit and Report (PASS)

The review passed. Commit all accumulated fixes:

```bash
git commit -m "fix: address review findings from swarm-review

Automated fixes applied across $CYCLE cycle(s):
$(for fix in ALL_FIXES_APPLIED; echo "- $fix"; done)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

If `CAN_PUSH` is true: `git push`
If `CAN_PUSH` is false: tell the user the commit is local-only (e.g., reviewing a hash range or detached HEAD).

Then produce the final report (see Output Format below).

### Step 6: Report Without Committing (INCOMPLETE)

Max cycles reached without a PASS verdict. Do NOT commit. Do NOT push.

Leave all changes staged so the user can inspect them with `git diff --cached`.

Produce the final report (see Output Format below).

---

## Output Format

After completion, present this report:

```
## Review-Fix Loop Complete

**Verdict**: PASS ✓ (committed and pushed) | PASS ✓ (committed locally) | INCOMPLETE (not committed)
**Cycles**: {CYCLE} of {MAX_CYCLES}
**Target**: {describe what was reviewed — e.g., "PR #482", "branch feature/auth vs main", "abc123f..def456a", "current branch vs main"}
**Artifact**: {path to saved review artifact}

### Tactical Fixes Applied
{numbered list of ALL_FIXES_APPLIED with brief descriptions}

### Remaining Tactical Issues
{items that couldn't be auto-fixed, with reasons}
{or "None — all tactical fixes were resolved."}

### Deferred Architectural Feedback
{DEFERRED_FEEDBACK items — systemic issues the user should review}
{Include the original severity and suggested scope from the review}
{or "None identified."}
```

---

## Edge Cases

**swarm-review errors out**: Abort immediately. Report the error. Do not retry.

**No tactical fixes found but verdict is NEEDS WORK**: This shouldn't happen given the verdict logic, but if it does, treat as PASS.

**Same finding appears across cycles**: If a fix was applied in cycle N but the same finding appears in cycle N+1, it means the fix didn't resolve it. Skip it on the second occurrence and add it to "remaining tactical issues" with a note: "Fix attempted in cycle N but finding persists."

**Merge conflicts**: If `git push` fails due to conflicts, report the failure and leave the commit local. Do not force-push.

**Large PRs**: swarm-review handles large PRs with its own heuristics (subagent selection, diff sizing). This skill doesn't add additional constraints.

---

## Coupling Warning

This skill depends on the `/swarm-review` skill's output format — specifically:
- The artifact path convention: `~/.agent/reviews/pr-{number}-review.md`
- The markdown structure: `## Tactical Fixes (this PR)` → `### Blockers` / `### Improvements`
- The `## Systemic Follow-ups (separate PRs)` section
- Effort estimates in parentheses or em-dashes after each finding

If swarm-review's artifact format changes, this skill's parsing in Step 2 will break. When that happens, read the updated swarm-review SKILL.md and adjust the parsing logic.
