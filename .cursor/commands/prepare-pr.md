# prepare-pr

Prepare a pull request with a well-formatted title, description, and proper Linear ticket integration.

**IMPORTANT FOR AI AGENTS:** Always use this command (`/prepare-pr`) instead of directly calling `gh pr create`. This command ensures proper PR formatting, Linear ticket integration, and narrative-driven descriptions that align with Parable's writing philosophy.

## Prerequisites

- Git repository initialized
- GitHub CLI (`gh`) installed and authenticated
- Commits pushed to a remote branch
- Linear MCP server configured (for ticket details)
- GitHub MCP server configured (for PR operations)

---

## AI Execution Steps

When this command is invoked, automatically perform these steps:

### 1. Verify prerequisites

Run and verify:

```bash
command -v gh
git rev-parse --git-dir
```

If either fails, inform the user and stop.

### 2. Check branch status

Run:

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
git log origin/main..HEAD --oneline 2>/dev/null || git log origin/master..HEAD --oneline
```

**Verify:**

- Not on `main` or `master` branch
- Has commits ahead of the base branch
- No uncommitted changes (warn if present)

**If on main/master:**

```
❌ ERROR: Cannot create PR from main/master branch.

Create a feature branch first:
  git checkout -b <TICKET_ID>-description
```

**If no commits ahead:**

```
❌ ERROR: No commits to include in PR.

Make some commits first, then run /prepare-pr again.
```

**If uncommitted changes exist:**

```
⚠️ Warning: You have uncommitted changes.

Consider committing them first:
  /prepare-commit
```

### 3. Determine the ticket ID

**Priority order for ticket ID extraction:**

1. **User input**: If provided (e.g., `/prepare-pr ENG-123`)

2. **Current git branch**: Extract from branch name
   - Expected format: `<TEAM>-<NUMBER>-<description>`
   - Extract: `<TEAM>-<NUMBER>`

3. **Recent commit messages**: Scan commits for `Refs: <TICKET_ID>` pattern

   ```bash
   git log origin/main..HEAD --format=%B | grep -oE '[A-Z]+-[0-9]+' | head -1
   ```

4. **STOP if ticket ID cannot be determined**:

   ```
   ❌ ERROR: Could not determine Linear ticket ID for PR.
   
   Please provide a ticket ID:
     /prepare-pr ENG-123
   
   Or ensure your branch follows the format:
     <TEAM>-<NUMBER>-description (e.g., ENG-123-add-feature)
   
   Current branch: <branch-name>
   ```

   **STOP execution immediately.**

### 4. Fetch ticket details from Linear

Use the Linear MCP server:

```
mcp_linear_get_issue(id="<TICKET_ID>", includeRelations=true)
```

Extract:

- Title
- Description
- Status
- Labels
- Parent issue (if any)
- Related issues (if any)

**If ticket not found:**

```
⚠️ Warning: Could not fetch ticket <TICKET_ID> from Linear.
Proceeding with available information...
```

### 5. Analyze commits for PR content

Run:

```bash
git log origin/main..HEAD --format="- %s" 2>/dev/null || git log origin/master..HEAD --format="- %s"
```

Analyze:

- Number of commits
- Types of changes (feat, fix, refactor, etc.)
- Scope of changes

Get the diff summary:

```bash
git diff origin/main..HEAD --stat 2>/dev/null || git diff origin/master..HEAD --stat
```

### 6. Check for existing PR

Use GitHub MCP or CLI to check if a PR already exists for this branch:

```bash
gh pr list --head $(git rev-parse --abbrev-ref HEAD) --json number,title,url
```

**If PR exists:**

```$$
ℹ️ A PR already exists for this branch:

PR #<number>: <title>
URL: <url>

Would you like to:
1. Update the existing PR description
2. View the PR
3. Cancel
```

### 7. Determine base branch

Check which base branch to use:

```bash
git remote show origin | grep "HEAD branch" | cut -d: -f2 | tr -d ' '
```

Default to `main`, fallback to `master` if `main` doesn't exist.

### 8. Generate PR title

Format: `<type>(<scope>): <description> [<TICKET_ID>]`

**Rules:**

- Use the primary commit type (feat, fix, refactor, etc.)
- Scope from the ticket or primary module changed
- Description from ticket title or commit summary
- Always include ticket ID in brackets

**Examples:**

- `feat(auth): add password reset flow [ENG-123]`
- `fix(api): handle null responses from external service [DATA-456]`

### 9. Generate PR description

Use this narrative-driven template. Write in clear, plain English prose. Avoid bullet points and checkboxes. Structure the narrative to tell the story of what changed and why, making it a referenceable artifact for future understanding.

```markdown
## Summary

<Write a clear narrative paragraph describing what this PR accomplishes. Begin with the problem or opportunity, explain the approach taken, and conclude with the outcome. This should be derived from the ticket description and commit analysis, written as flowing prose rather than a list of points.>

This work addresses **[<TICKET_ID>](<linear-url>)**: <ticket-title>. <If the ticket description provides context, weave it into the narrative here, explaining the motivation and requirements that led to this implementation.>

## What Changed

<Write a narrative description of the changes made. Instead of listing commits as bullet points, weave them into a coherent story. Explain the sequence of work: what was built first, what dependencies were established, and how the pieces fit together. Describe the technical approach taken and the reasoning behind key decisions. If there were multiple commits, explain how they relate to each other and why they were structured that way.>

The implementation involved <describe scope and scale of changes>. <For each significant change, explain what was modified and why, in narrative form.> This work builds upon <describe any dependencies or related work> and establishes <describe what foundations or patterns were created>.

## Type of Change

<Write a sentence or two describing the nature of this change. State clearly whether this is a bug fix, new feature, breaking change, refactor, documentation update, or test update. If it's a combination, explain how the different aspects relate to each other.>

## Testing

<Write a narrative description of the testing approach. Explain what tests were added or updated, why those tests were chosen, and how they validate the changes. Describe any manual testing performed, integration testing, or other validation methods used. If testing is still needed, explain what remains to be done and why.>

<If applicable, describe the test coverage:> The changes are covered by <describe test types and coverage>. <Explain any edge cases or scenarios that were specifically tested.> <If manual testing was performed, describe what was tested and what the results were.>

## Additional Context

<If there are screenshots, UI changes, or other visual artifacts, describe them here in narrative form. Explain what the screenshots show and why they're relevant. If there are design decisions, architectural choices, or trade-offs that should be documented for posterity, explain them here.>

---

Refs: <TICKET_ID>
```

**Populate the template:**

- Write the Summary as a flowing narrative paragraph that explains the what, why, and how
- Convert commit summaries into a narrative story of the changes
- Describe the type of change in prose rather than checkboxes
- Write testing as a narrative explanation of what was tested and why
- Include any screenshots or visual context in narrative form
- Ensure the entire description reads as a coherent document that will be understandable months from now

### 10. Present PR for approval

Display the generated PR:

```
## Proposed Pull Request

**Title:** <generated title>

**Base:** <base-branch> ← **Head:** <current-branch>

---

<generated description>

---

**Commits:** <count>
**Files changed:** <count>
**Ticket:** <TICKET_ID>

---

Would you like me to:
1. ✅ Create this PR
2. ✏️ Modify the title or description
3. 📋 Create as draft PR
4. ❌ Cancel
```

### 11. Create the PR (if approved)

Use GitHub MCP or CLI:

**For regular PR:**

```
mcp_github_create_pull_request(
    owner="<org>",
    repo="<repo>",
    title="<title>",
    body="<description>",
    head="<current-branch>",
    base="<base-branch>"
)
```

Or via CLI:

```bash
gh pr create --title "<title>" --body "<description>" --base <base-branch>
```

**For draft PR:**

```bash
gh pr create --title "<title>" --body "<description>" --base <base-branch> --draft
```

### 12. Confirm and provide next steps

```
✅ Pull Request created successfully!

**PR #<number>:** <title>
**URL:** <pr-url>

---

Next steps:
1. Review the PR diff: gh pr diff <number>
2. Request reviewers: gh pr edit <number> --add-reviewer <username>
3. Link to Linear: The ticket <TICKET_ID> should auto-link via the Refs footer
4. Monitor CI: Check GitHub Actions for build status

---

**Quick commands:**
- View PR: gh pr view <number> --web
- Check status: gh pr checks <number>
- Merge when ready: gh pr merge <number>
```

---

## PR Title Examples

```
feat(auth): add OAuth2 integration [ENG-123]
fix(ingestion): prevent duplicate records [DATA-456]
refactor(api): extract validation to middleware [PLATFORM-789]
docs(readme): update setup instructions [ENG-100]
test(flows): add integration tests for ETL pipeline [DATA-200]
chore(deps): update to Python 3.12 [INFRA-50]
```

---

## Error Handling

This command will STOP and display an error if:

1. Not in a git repository
2. On main/master branch
3. No commits to include in PR
4. Ticket ID cannot be determined
5. GitHub CLI not installed/authenticated
6. PR creation fails

---

## Integration

This command works well with:

- **validate-ticket**: Run first to verify ticket exists and get context
- **prepare-commit**: Run before to ensure proper commit messages
- **pr-review**: Run after PR is created to self-review before requesting others

---

## Configuration

The PR template can be customized by:

1. Adding a `.github/PULL_REQUEST_TEMPLATE.md` to your repository
2. The command will detect and use this template if present

---

## Linear Integration

This command leverages Linear MCP to:

- Validate ticket exists
- Fetch ticket title and description for PR context
- Include proper ticket references for automatic linking

When the PR is merged, Linear should automatically:

- Update ticket status (if configured)
- Link the PR to the ticket

## Auto-Running Before gh pr create

To automatically intercept direct `gh pr create` calls and prompt users to use `/prepare-pr` instead, you can install a shell wrapper:

```bash
./utils/setup-gh-pr-wrapper.sh
```

This creates a shell function that:

- Detects when `gh pr create` is called in a repository that defines a `/prepare-pr` command
- Prompts the user to use `/prepare-pr` in Cursor instead
- Allows bypassing with confirmation if needed

**Note:** This wrapper only works in interactive shells. AI agents should use `/prepare-pr` directly rather than calling `gh pr create`.

This command will be available in chat with /prepare-pr
