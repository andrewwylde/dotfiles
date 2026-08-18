# Generate Review Document

Generate a comprehensive manual review document from a Linear ticket. This command fetches all relevant ticket details, comments, relationships, and context to produce a structured document suitable for code review, design review, or implementation verification.

## Prerequisites

- Linear MCP server configured and connected
- A ticket ID provided via input OR a branch name following the pattern `<TEAM>-<NUMBER>-*` (e.g., `ENG-123-add-feature`)

**Linear MCP Configuration:**

The Linear MCP server should be configured in your Cursor MCP settings. If using environment variables:

```json
{
  "linear": {$$
    "url": "https://mcp.linear.app/sse",
    "headers": {
      "Authorization": "Bearer ${LINEAR_API_KEY}"
    }
  }
}
```

Alternatively, ensure `LINEAR_API_KEY` is set in your environment.

---

## AI Execution Steps

**CRITICAL: This command MUST error and stop if a ticket ID cannot be determined or if the Linear MCP server is not accessible. Do not proceed with assumptions or placeholder values.**

When this command is invoked, automatically perform these steps:

### 1. Verify Linear MCP connectivity

Attempt a simple query to verify the Linear MCP server is accessible:

```
mcp_linear_list_teams(limit=1)
```$$

**If the query fails or returns an error:**

- Display error:
  ```
  ❌ ERROR: Unable to connect to Linear MCP server.
  
  Please verify:
  1. Linear MCP server is configured in Cursor settings
  2. LINEAR_API_KEY environment variable is set and valid
  3. You have access to the Linear workspace
  
  MCP Configuration location: ~/.cursor/mcp.json or project .cursor/mcp.json
  ```

- **STOP execution immediately. Do not continue.**

### 2. Determine the ticket ID

**Priority order for ticket ID extraction:**

1. **User input**: If the user provides a ticket ID (e.g., `/generate-review-doc ENG-123`), use that directly.

2. **Current git branch**: If no ticket ID is provided, extract from the current branch name.

   Run:
   ```bash
   git rev-parse --abbrev-ref HEAD
   ```

   Parse the branch name using this pattern:
   - Expected format: `<TEAM>-<NUMBER>` or `<TEAM>-<NUMBER>-<description>`
   - Examples: `ENG-123`, `ENG-123-add-feature`, `DATA-456-fix-bug`
   - Extract the ticket ID as `<TEAM>-<NUMBER>` (e.g., `ENG-123`)

3. **STOP if ticket ID cannot be determined**:

   If neither user input nor branch name yields a valid ticket ID:
   
   - Display error:
     ```
     ❌ ERROR: Could not determine Linear ticket ID.
     
     Please provide a ticket ID in one of these ways:
     1. Include it in your command: /generate-review-doc ENG-123
     2. Use a branch name with format: <TEAM>-<NUMBER>-description (e.g., ENG-123-add-feature)
     
     Current branch: <branch-name>
     ```
   
   - **STOP execution immediately. Do not continue.**

### 3. Fetch primary ticket details

Use the Linear MCP server to fetch the ticket with relations:

```
mcp_linear_get_issue(id="<TICKET_ID>", includeRelations=true)
```

**If the ticket is not found or an error occurs:**

- Display error:
  ```
  ❌ ERROR: Linear ticket <TICKET_ID> not found or inaccessible.
  
  Please verify:
  1. The ticket ID is correct
  2. You have access to this ticket in Linear
  3. The Linear MCP server is properly configured
  ```

- **STOP execution immediately. Do not continue.**

**Store the following from the response:**
- Title
- Description
- Status
- Priority
- Assignee
- Labels
- Project
- Cycle
- Due date
- Estimate
- Created date
- Updated date
- URL
- Git branch name (if provided)
- Parent issue ID (if any)
- Blocking/blocked-by relations
- Related issues

### 4. Fetch ticket comments

Retrieve all comments for context and discussion history:

```
mcp_linear_list_comments(issueId="<TICKET_ID>")
```

**Store comments with:**
- Author
- Body (content)
- Created date
- Any replies (threaded)

### 5. Fetch parent ticket (if applicable)

If the ticket has a parent issue ID:

```
mcp_linear_get_issue(id="<PARENT_ID>")
```

**Store parent ticket context:**
- Title
- Description (summarized)
- Status
- URL

### 6. Fetch related and blocking issues (if applicable)

For each blocking, blocked-by, or related issue ID found in step 3:

```
mcp_linear_get_issue(id="<RELATED_ID>")
```

**Store for each:**
- Ticket ID
- Title
- Status
- Relationship type (blocks, blocked by, related to)

### 7. Fetch sub-issues (if applicable)

Check if this ticket has child issues:

```
mcp_linear_list_issues(parentId="<TICKET_ID>")
```

**Store sub-issues with:**
- Ticket ID
- Title
- Status
- Assignee

### 8. Generate the review document

Create a markdown file in the repository root:

```
REVIEW_<TICKET_ID>.md
```

Use the **Document Template** below to structure the content.

---

## Document Template

```markdown
# Review Document: <TICKET_ID>

> Generated on <DATE> for manual review

## Quick Reference

| Field | Value |
|-------|-------|
| **Ticket** | [<TICKET_ID>](<LINEAR_URL>) |
| **Title** | <TITLE> |
| **Status** | <STATUS> |
| **Priority** | <PRIORITY or "None"> |
| **Assignee** | <ASSIGNEE or "Unassigned"> |
| **Project** | <PROJECT or "None"> |
| **Cycle** | <CYCLE or "None"> |
| **Due Date** | <DUE_DATE or "None"> |
| **Estimate** | <ESTIMATE or "None"> |
| **Labels** | <LABELS or "None"> |
| **Created** | <CREATED_DATE> |
| **Updated** | <UPDATED_DATE> |

---

## Description

<FULL_DESCRIPTION or "No description provided">

---

## Acceptance Criteria

<EXTRACT_FROM_DESCRIPTION_IF_PRESENT or "No explicit acceptance criteria found. Review the description for implicit requirements.">

---

## Context & Background

### Parent Ticket

<IF_PARENT_EXISTS>
- **[<PARENT_ID>](<PARENT_URL>)**: <PARENT_TITLE>
  - Status: <PARENT_STATUS>
  - Summary: <PARENT_DESCRIPTION_SUMMARY>
</IF_PARENT_EXISTS>

<IF_NO_PARENT>
*This is a top-level ticket with no parent.*
</IF_NO_PARENT>

### Related Issues

<IF_RELATED_EXIST>
| Relationship | Ticket | Title | Status |
|-------------|--------|-------|--------|
| <RELATIONSHIP_TYPE> | [<RELATED_ID>](<RELATED_URL>) | <RELATED_TITLE> | <RELATED_STATUS> |
...
</IF_RELATED_EXIST>

<IF_NO_RELATED>
*No related issues found.*
</IF_NO_RELATED>

### Sub-Issues

<IF_SUB_ISSUES_EXIST>
| Ticket | Title | Status | Assignee |
|--------|-------|--------|----------|
| [<SUB_ID>](<SUB_URL>) | <SUB_TITLE> | <SUB_STATUS> | <SUB_ASSIGNEE> |
...

**Progress:** <COMPLETED_COUNT>/<TOTAL_COUNT> completed
</IF_SUB_ISSUES_EXIST>

<IF_NO_SUB_ISSUES>
*No sub-issues found.*
</IF_NO_SUB_ISSUES>

---

## Discussion History

<IF_COMMENTS_EXIST>
### Comment Thread

<FOR_EACH_COMMENT>
**<AUTHOR>** - <DATE>:
> <COMMENT_BODY>

---
</FOR_EACH_COMMENT>
</IF_COMMENTS_EXIST>

<IF_NO_COMMENTS>
*No comments on this ticket.*
</IF_NO_COMMENTS>

---

## Implementation Notes

### Suggested Git Branch

```
<GIT_BRANCH_NAME or "<TICKET_ID>-<kebab-case-title>">
```

### Key Requirements (Extracted)

<BULLET_LIST_OF_KEY_REQUIREMENTS_FROM_DESCRIPTION>

### Technical Considerations

<INFER_FROM_DESCRIPTION_AND_LABELS>
- <Technical consideration 1>
- <Technical consideration 2>
...

---

## Review Checklist

### Pre-Implementation Review

- [ ] Requirements are clear and complete
- [ ] Acceptance criteria is defined
- [ ] Dependencies/blockers are resolved or accounted for
- [ ] Technical approach is understood
- [ ] Estimate is reasonable for scope

### Code Review Checklist

- [ ] Implementation matches requirements
- [ ] Code follows project conventions
- [ ] Tests cover acceptance criteria
- [ ] Edge cases are handled
- [ ] Documentation is updated (if needed)
- [ ] No unrelated changes included

### Post-Implementation Verification

- [ ] All acceptance criteria met
- [ ] No regressions introduced
- [ ] Performance is acceptable
- [ ] Ready for deployment

---

## Notes for Reviewer

<ADD_ANY_SPECIFIC_NOTES_OR_QUESTIONS>

---

*This document was auto-generated from Linear ticket <TICKET_ID>. Update manually as needed during review.*
```

---

## Output

The command generates a markdown file named `REVIEW_<TICKET_ID>.md` in the repository root containing:

1. **Quick Reference** - At-a-glance ticket metadata
2. **Description** - Full ticket description
3. **Acceptance Criteria** - Extracted or noted as missing
4. **Context & Background** - Parent ticket, related issues, sub-issues
5. **Discussion History** - All comments in chronological order
6. **Implementation Notes** - Git branch, key requirements, technical considerations
7. **Review Checklist** - Pre-implementation, code review, and post-implementation checklists

---

## Error Handling

This command is designed to **fail fast** and **fail clearly**. It will STOP and display an error message if:

1. Linear MCP server is not accessible
2. No ticket ID can be extracted from input or branch name
3. The ticket ID format is invalid
4. The ticket does not exist in Linear
5. Required ticket data cannot be retrieved

**This command should NEVER proceed with assumed or placeholder ticket data.**

---

## Examples

### Valid invocations:

```
/generate-review-doc ENG-123
generate review doc DATA-456
create review document for PLATFORM-789
```

### From branch name (no input):

```
# On branch: ENG-123-add-user-authentication
/generate-review-doc
# Extracts: ENG-123 and generates REVIEW_ENG-123.md
```

### Output file:

```
# On branch: ENG-123-add-feature
/generate-review-doc
# Creates: REVIEW_ENG-123.md in repository root
```

### Error cases:

```
# Linear MCP not configured
/generate-review-doc ENG-123
# ERROR: Unable to connect to Linear MCP server

# On branch: main
/generate-review-doc
# ERROR: Could not determine ticket ID

# Invalid ticket
/generate-review-doc FAKE-999
# ERROR: Linear ticket FAKE-999 not found
```

---

## Integration with Other Commands

This command works well with:

- **validate-ticket**: Validate before generating review doc
- **prepare-pr**: Use review doc context when preparing PR
- **pr-review**: Reference review doc during PR review

### Recommended workflow:

1. `/validate-ticket ENG-123` - Verify ticket exists and understand scope
2. Implement the feature/fix
3. `/generate-review-doc ENG-123` - Generate review document
4. Self-review using the generated checklist
5. `/prepare-pr` - Create pull request with full context

---

## Customization

### Modifying the template

The document template can be customized by editing this command file. Common customizations:

- Add project-specific checklist items
- Include additional metadata fields
- Modify the review checklist sections
- Add team-specific sections

### Output location

By default, the document is created in the repository root. To change:

1. Modify step 8 to use a different path (e.g., `docs/reviews/`)
2. Ensure the directory exists or create it

---

## Troubleshooting

### "Unable to connect to Linear MCP server"

1. Check that Linear MCP is configured in Cursor settings
2. Verify `LINEAR_API_KEY` is set: `echo $LINEAR_API_KEY`
3. Test the API key: Try accessing Linear directly
4. Restart Cursor to reload MCP configuration

### "Ticket not found"

1. Verify the ticket ID is correct (check Linear UI)
2. Ensure you have access to the ticket's team/project
3. Check if the ticket was recently created (may need sync)

### Empty or incomplete document

1. The ticket may have minimal information in Linear
2. Check if comments failed to load (network issue)
3. Re-run the command to retry fetching

