# incorporate-feedback

# Incorporate Feedback

Incorporate review feedback from a pull request by fetching comments, organizing them by priority, and systematically addressing each item.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Git repository initialized and connected to GitHub
- Current branch matches the PR branch (or ability to checkout the PR branch)
- Linear MCP server configured (optional, for ticket updates)

---

## AI Execution Steps

When this command is invoked, automatically perform these steps:

### 1. Get the PR number

- Extract from user input (e.g., `/incorporate-feedback 11` or `/incorporate-feedback #11`)
- If no number is provided, try to detect from current branch:
  ```bash
  gh pr list --head $(git rev-parse --abbrev-ref HEAD) --json number,title --jq '.[0].number'
  ```
- If still not found, ask:
  `Which PR number should I incorporate feedback for?`

### 2. Verify prerequisites

Run and verify:

```bash
command -v gh
git rev-parse --git-dir
```

If either fails, inform the user and stop.

### 3. Fetch PR and review data

**IMPORTANT:** `gh pr view --json reviewThreads` does NOT work -- `reviewThreads` is not a supported field.
Use the REST API endpoints below instead.

Run these commands:

```bash
# Get PR metadata
gh pr view <PR_NUMBER> --json number,title,body,headRefName,baseRefName,state,author

# Get review summaries (approved, changes requested, etc.)
gh api repos/:owner/:repo/pulls/<PR_NUMBER>/reviews --jq '.[] | {author: .user.login, state: .state, body: .body}'

# Get line-specific review comments (the primary source of feedback)
gh api repos/:owner/:repo/pulls/<PR_NUMBER>/comments --jq '.[] | {id: .id, author: .user.login, body: .body, path: .path, line: .line, createdAt: .created_at}'

# Get general PR comments (not tied to specific lines)
gh api repos/:owner/:repo/issues/<PR_NUMBER>/comments --jq '.[] | {id: .id, author: .user.login, body: .body, createdAt: .created_at}'
```

**Image-only comments:** Some reviewers post screenshots as their entire comment body (just an `<img>` tag with a `github.com/user-attachments/assets/` URL). These URLs are auth-gated and cannot be fetched programmatically. When you encounter a comment whose body is only an image:
- Note it as: `[Screenshot comment at file:line -- ask user to describe]`
- Ask the user what the screenshot shows before proceeding

**Store this data as:**
- **PR Metadata**: number, title, branch, state
- **Review Comments**: Line-specific comments with file path, line number, and comment ID
- **Review Summaries**: Overall review states and comments
- **General Comments**: Issue-level comments not tied to specific code lines

### 4. Organize feedback by priority

Categorize all feedback using the prefix convention from `pr-review.md`:

**Priority categories:**

1. **Blocking (`!!`)**: Must be fixed before merge
   - Security vulnerabilities
   - Logic bugs
   - Correctness errors
   - Anything that would break production

2. **Standard (no prefix)**: Expected to be addressed
   - Suggestions
   - Design concerns
   - Improvements

3. **Questions (`?`)**: Genuine questions seeking understanding
   - Clarifications needed
   - Design decisions to explain

4. **Minor (`nit`)**: Style/consistency tweaks
   - Non-blocking improvements
   - Can be fixed if already editing nearby code

5. **Out of scope (`->` or `>>`)**: Good ideas for separate PRs
   - Refactoring opportunities
   - Performance optimizations
   - Better suited for future work

6. **Positive (`+`)**: Acknowledgment of good patterns
   - No action needed, but good to note

**Create a structured feedback list:**

```markdown
## Feedback Summary

### Blocking Issues (!!) - Must Fix
- [ ] `file:line` - **Author**: Description
- [ ] `file:line` - **Author**: Description

### Standard Feedback - Expected to Address
- [ ] `file:line` - **Author**: Description
- [ ] `file:line` - **Author**: Description

### Questions (?) - Need Response
- [ ] `file:line` - **Author**: Question
- [ ] `file:line` - **Author**: Question

### Minor (nit) - Optional
- [ ] `file:line` - **Author**: Suggestion
- [ ] `file:line` - **Author**: Suggestion

### Out of Scope (->) - Future Work
- [ ] `file:line` - **Author**: Suggestion (note for future)

### Positive Feedback (+) - Acknowledged
- [x] `file:line` - **Author**: Positive comment (no action needed)
```

### 5. Check current branch state

Verify you're on the correct branch:

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
```

**If not on PR branch:**
```
⚠️ Warning: You're not on the PR branch.

Current branch: <current>
PR branch: <pr-branch>

Would you like me to:
1. Checkout the PR branch
2. Continue on current branch (you'll need to merge later)
3. Cancel
```

**If uncommitted changes exist:**
```
⚠️ Warning: You have uncommitted changes.

Consider committing or stashing them first:
  git stash
  # or
  git commit -m "WIP: addressing feedback"
```

### 6. Create feedback tracking file

Create a file to track feedback incorporation:

```bash
mkdir -p .context/prs/feedback
```

Write to `.context/prs/feedback/PR_<PR_NUMBER>_feedback.md`:

```markdown
# Feedback Incorporation for PR #<PR_NUMBER>

**PR Title:** <title>
**Branch:** <branch>
**Created:** <date>

## Feedback Summary

<Insert organized feedback list from step 4>

## Incorporation Progress

### Blocking Issues
- [ ] Item 1
- [ ] Item 2

### Standard Feedback
- [ ] Item 1
- [ ] Item 2

### Questions
- [ ] Item 1

### Minor
- [ ] Item 1

---

## Notes

<Space for implementation notes>
```

### 7. Present feedback summary

Display the organized feedback:

```
## Review Feedback for PR #<PR_NUMBER>

**Title:** <title>
**Branch:** <branch>
**Reviewers:** <list of reviewers>

---

## Summary

- **Blocking issues:** <count> (must fix)
- **Standard feedback:** <count> (expected to address)
- **Questions:** <count> (need response)
- **Minor suggestions:** <count> (optional)
- **Out of scope:** <count> (future work)
- **Positive feedback:** <count> (acknowledged)

---

<Display organized feedback list>

---

Would you like me to:
1. ✅ Start addressing feedback systematically
2. 📋 Show detailed view of specific feedback items
3. 🔍 Filter by file or reviewer
4. ❌ Cancel
```

### 8. Address feedback systematically

If user chooses to start addressing feedback:

**For each feedback item (prioritize blocking first):**

1. **Display the feedback item:**
   ```
   ## Addressing: <file>:<line>
   
   **Priority:** <!!/standard/?/nit/->/+>
   **Author:** <reviewer>
   **Comment:** <feedback text>
   ```

2. **Read the relevant file section:**
   - Use `read_file` to read the file around the line number
   - Show context (10-20 lines before/after)

3. **Analyze what needs to change:**
   - Understand the feedback
   - Identify the specific code that needs modification
   - Consider impact on other parts of the codebase

4. **Propose changes:**
   - Show the current code
   - Propose the fix
   - Explain the reasoning

5. **Implement the change:**
   - Use `search_replace` or appropriate edit tool
   - Make the change
   - Update the tracking file to mark item as addressed

6. **Verify the change:**
   - Check if the change addresses the feedback
   - Ensure no new issues introduced
   - Run linter if applicable

7. **Mark as addressed in tracking file:**
   ```markdown
   - [x] `file:line` - **Author**: Description ✅ Addressed in commit <hash>
   ```

### 9. Handle questions

For feedback marked with `?` (questions):

- **If the question is about design/implementation:**
  - Provide a clear explanation
  - Consider if code comments or documentation would help
  - Add inline comments if appropriate

- **If the question reveals a misunderstanding:**
  - Clarify the implementation
  - Consider if the code could be clearer
  - Update code or documentation as needed

- **Response format:**
  ```
  ## Response to Question: <file>:<line>
  
  **Question:** <question text>
  **Response:** <explanation>
  
  [Optional: Code changes if clarification needed]
  ```

### 10. Commit changes

After addressing feedback items:

**Option 1: Commit each item separately**
```bash
git add <files>
git commit -m "fix(<scope>): address feedback from <reviewer> [<TICKET_ID>]

- <description of change>
- Addresses: <file>:<line>

Refs: <TICKET_ID>"
```

**Option 2: Group related changes**
```bash
git add <files>
git commit -m "fix(<scope>): address review feedback [<TICKET_ID>]

- <summary of changes>
- Addresses feedback from: <reviewers>

Refs: <TICKET_ID>"
```

**Follow conventional commit format:**
- Use appropriate type (fix, refactor, docs, etc.)
- Include scope if applicable
- Reference ticket ID if available
- List what feedback was addressed

### 11. Reply to review comments

After addressing feedback, post replies to each comment thread using the **direct reply endpoint**.

**IMPORTANT:** Do NOT create a pending review first. GitHub's API enforces "user_id can only have one pending review per pull request," which blocks the replies endpoint. Post replies directly instead.

```bash
# Reply to a specific review comment thread
gh api repos/:owner/:repo/pulls/<PR_NUMBER>/comments/<COMMENT_ID>/replies \
  --raw-field body='<your reply describing what was fixed>'
```

Use the `id` field from Step 3's review comment fetch. Each reply goes to the comment thread, not as a new top-level comment.

**Note:** Only reply when feedback has been fully addressed. If you need clarification, ask the user first.

### 12. Push changes

```bash
git push origin <PR_BRANCH>
```

**If branch tracking not set:**
```bash
git push -u origin <PR_BRANCH>
```

### 13. Update tracking file with final status

Update `.context/prs/feedback/PR_<PR_NUMBER>_feedback.md`:

```markdown
## Final Status

**Last Updated:** <timestamp>
**Items Addressed:** <count>/<total>
**Remaining:** <count>

### Remaining Items
- [ ] Item 1 (if any)

### Addressed Items
- [x] Item 1 ✅
- [x] Item 2 ✅
```

### 14. Provide summary and next steps

```
✅ Feedback incorporation complete!

## Summary

**PR:** #<PR_NUMBER>
**Branch:** <branch>
**Items addressed:** <count>
**Commits created:** <count>
**Changes pushed:** Yes/No

---

## Next Steps

1. **Review your changes:**
   ```bash
   git log origin/<base-branch>..HEAD --oneline
   git diff origin/<base-branch>..HEAD
   ```

2. **Verify all blocking issues are resolved:**
   - Check the tracking file: `.context/prs/feedback/PR_<PR_NUMBER>_feedback.md`
   - Review PR to ensure all threads are resolved

3. **Request re-review (if needed):**
   ```bash
   gh pr comment <PR_NUMBER> --body "Addressed all feedback. Ready for re-review."
   ```

4. **Update Linear ticket (if applicable):**
   - Add comment about feedback addressed
   - Update status if appropriate

---

## Tracking File

Feedback tracking: `.context/prs/feedback/PR_<PR_NUMBER>_feedback.md`
```

---

## Feedback Categories Reference

| Prefix | Priority | Action Required | Example |
|--------|----------|----------------|---------|
| `!!` | Blocking | Must fix before merge | Security vulnerability, logic bug |
| (none) | Standard | Expected to address | Design suggestion, improvement |
| `?` | Question | Respond or clarify | "Why did we choose X?" |
| `nit` | Minor | Optional, fix if nearby | Style tweak, naming suggestion |
| `->` or `>>` | Out of scope | Note for future PR | Refactoring opportunity |
| `+` | Positive | Acknowledge only | "Great test coverage!" |

---

## Error Handling

This command will STOP and display an error if:

1. Not in a git repository
2. GitHub CLI not installed/authenticated
3. PR number cannot be determined
4. PR not found or inaccessible
5. Cannot checkout PR branch (if needed)

---

## Integration

This command works well with:

- **pr-review**: Run first to understand the review context
- **prepare-commit**: Use when committing feedback changes
- **prepare-pr**: Use if creating a new PR after addressing feedback
- **validate-ticket**: Use to get ticket context for commit messages

---

## Best Practices

1. **Address blocking issues first**: Always prioritize `!!` feedback
2. **Group related changes**: Commit related feedback together when possible
3. **Keep commits focused**: Each commit should address a logical unit of feedback
4. **Document decisions**: If you disagree with feedback, explain why in a comment
5. **Test after changes**: Verify fixes don't introduce regressions
6. **Update tracking file**: Keep the feedback tracking file up to date
7. **Communicate clearly**: Add comments to PR threads if clarification is needed

---

## Example Workflow

```bash
# 1. Start incorporating feedback
/incorporate-feedback 42

# 2. Review the organized feedback list
# 3. Start addressing blocking issues first
# 4. Commit changes as you go
# 5. Push when ready
git push origin feature-branch

# 6. Request re-review
gh pr comment 42 --body "Addressed all blocking feedback. Ready for re-review."
```

---

## Handling Disagreements

If you disagree with feedback:

1. **Acknowledge the feedback**: Show you understand the concern
2. **Explain your reasoning**: Provide context for your decision
3. **Propose alternatives**: If applicable, suggest a middle ground
4. **Document in PR**: Add a comment explaining your decision
5. **Escalate if needed**: If it's a blocking issue, discuss with the team

**Example response:**
```markdown
Thanks for the feedback! I considered this approach, but chose the current implementation because:

1. <reason 1>
2. <reason 2>

However, I'm open to revisiting this if you think there's a better approach. What do you think?
```

---

## Tracking File Format

The tracking file (`.context/prs/feedback/PR_<PR_NUMBER>_feedback.md`) serves as:

- **Progress tracker**: See what's been addressed
- **Reference**: Quick lookup of feedback items
- **Documentation**: Record of changes made
- **Communication**: Share status with reviewers

Keep it updated as you work through feedback items.
