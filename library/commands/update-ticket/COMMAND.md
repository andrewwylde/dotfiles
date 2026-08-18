# Update Ticket

Review and update a Linear ticket with changes to title, description, status, assignee, labels, and other fields. This command provides a comprehensive review of the current ticket state and guides you through making updates.

**IMPORTANT FOR AI AGENTS:** Always use this command (`/update-ticket`) instead of directly calling Linear MCP update functions. This command ensures proper validation, clear presentation of changes, and confirmation before making updates.

## Prerequisites

- Git repository initialized (optional, for branch-based ticket detection)
- Linear MCP server configured (for ticket operations)
- Access to the Linear workspace

---

## AI Execution Steps

When this command is invoked, automatically perform these steps:

### 1. Determine the ticket ID

**Priority order for ticket ID extraction:**

1. **User input**: If provided (e.g., `/update-ticket ENG-123`)

2. **Current git branch**: Extract from branch name
   - Expected format: `<TEAM>-<NUMBER>-<description>`
   - Extract: `<TEAM>-<NUMBER>`
   ```bash
   git rev-parse --abbrev-ref HEAD
   ```

3. **Recent commit messages**: Scan commits for `Refs: <TICKET_ID>` pattern
   ```bash
   git log origin/main..HEAD --format=%B | grep -oE '[A-Z]+-[0-9]+' | head -1
   ```

4. **STOP if ticket ID cannot be determined**:

   ```
   ❌ ERROR: Could not determine Linear ticket ID.
   
   Please provide a ticket ID:
     /update-ticket ENG-123
   
   Or ensure your branch follows the format:
     <TEAM>-<NUMBER>-description (e.g., ENG-123-add-feature)
   
   Current branch: <branch-name>
   ```
   
   **STOP execution immediately.**

### 2. Verify Linear MCP connectivity

Attempt a simple query to verify the Linear MCP server is accessible:

```
mcp_linear_list_teams(limit=1)
```

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

- **STOP execution immediately.**

### 3. Fetch current ticket details

Use the Linear MCP server to fetch comprehensive ticket information:

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

- **STOP execution immediately.**

**Extract and store:**
- Title
- Description
- Status (state)
- Priority
- Assignee
- Labels
- Project
- Cycle
- Milestone
- Due date
- Estimate
- Parent issue (if any)
- Related issues (if any)
- Blocking/blocked-by relations
- Created date
- Updated date
- URL

### 4. Fetch ticket comments

Retrieve all comments for context:

```
mcp_linear_list_comments(issueId="<TICKET_ID>")
```

**Store comments with:**
- Author
- Body (content)
- Created date
- Any replies (threaded)

### 5. Display current ticket state

Present a comprehensive view of the ticket:

```
## Current Ticket State: <TICKET_ID>

**Title:** <title>
**Status:** <status>
**Priority:** <priority>
**Assignee:** <assignee>
**Labels:** <comma-separated labels>
**Project:** <project>
**Cycle:** <cycle>
**Milestone:** <milestone>
**Due Date:** <due-date>
**Estimate:** <estimate>

---

## Description

<description>

---

## Relationships

**Parent:** <parent-issue-id> (if any)
**Related:** <related-issue-ids> (if any)
**Blocking:** <blocking-issue-ids> (if any)
**Blocked By:** <blocked-by-issue-ids> (if any)

---

## Recent Comments

<Display last 5 comments with author and date>

---

## Metadata

**Created:** <created-date>
**Updated:** <updated-date>
**URL:** <linear-url>
```

### 6. Determine what to update

Ask the user what they'd like to update:

```
What would you like to update?

1. 📝 Title
2. 📄 Description
3. 📊 Status
4. 👤 Assignee
5. 🏷️ Labels
6. 📁 Project
7. 🔄 Cycle
8. 🎯 Milestone
9. 📅 Due Date
10. ⏱️ Estimate
11. 🔗 Relationships (parent, related, blocking)
12. ✏️ Add a comment
13. 📋 Review all fields (show current values)
14. ❌ Cancel

You can select multiple items (e.g., "1, 3, 5" or "title, status, labels")
```

### 7. Get available options for fields

For fields that require specific values, fetch available options:

**For Status:**
```
mcp_linear_list_issue_statuses(team="<TEAM>")
```

**For Teams:**
```
mcp_linear_list_teams()
```

**For Labels:**
```
mcp_linear_list_issue_labels(team="<TEAM>")
```

**For Projects:**
```
mcp_linear_list_projects(team="<TEAM>")
```

**For Cycles:**
```
mcp_linear_list_cycles(teamId="<TEAM_ID>")
```

**For Users:**
```
mcp_linear_list_users(team="<TEAM>")
```

### 8. Collect update values

For each field the user wants to update, collect the new value:

**Title:**
- Ask: "What should the new title be?"
- Validate: Non-empty, reasonable length

**Description:**
- Ask: "What should the new description be? (Markdown supported)"
- Show current description for reference
- Allow user to provide full replacement or edits

**Status:**
- Show available statuses from step 7
- Ask: "Which status should this ticket have?"
- Validate: Status exists and is valid for the team

**Assignee:**
- Show available users from step 7
- Ask: "Who should be assigned? (user ID, name, email, or 'me')"
- Allow "unassign" or empty to remove assignee

**Labels:**
- Show current labels
- Show available labels from step 7
- Ask: "Which labels should be set? (comma-separated names or IDs, or 'none' to remove all)"
- Validate: All labels exist

**Project:**
- Show available projects from step 7
- Ask: "Which project should this belong to? (name or ID, or 'none' to remove)"
- Validate: Project exists

**Cycle:**
- Show available cycles from step 7
- Ask: "Which cycle should this belong to? (name, number, or ID, or 'none' to remove)"
- Validate: Cycle exists

**Milestone:**
- Show available milestones (if accessible)
- Ask: "Which milestone should this belong to? (name or ID, or 'none' to remove)"
- Validate: Milestone exists

**Due Date:**
- Ask: "What should the due date be? (ISO format: YYYY-MM-DD, or 'none' to remove)"
- Validate: Valid date format

**Estimate:**
- Ask: "What should the estimate be? (number, or 'none' to remove)"
- Validate: Positive number

**Relationships:**
- Ask for each relationship type:
  - Parent: "What should the parent issue be? (issue ID, or 'none' to remove)"
  - Related: "Which issues should be related? (comma-separated issue IDs, or 'none' to remove all)"
  - Blocking: "Which issues does this block? (comma-separated issue IDs, or 'none' to remove all)"
  - Blocked By: "Which issues block this? (comma-separated issue IDs, or 'none' to remove all)"
- Validate: Issue IDs exist

**Comment:**
- Ask: "What comment would you like to add? (Markdown supported)"
- Validate: Non-empty

### 9. Show proposed changes

Display a summary of all changes:

```
## Proposed Changes for <TICKET_ID>

### Fields to Update

| Field | Current Value | New Value |
|-------|--------------|-----------|
| Title | <current> | <new> |
| Status | <current> | <new> |
| Assignee | <current> | <new> |
| ... | ... | ... |

### Comments to Add

- <comment-preview>

---

**⚠️ This will update the ticket in Linear.**

Would you like to:
1. ✅ Apply these changes
2. ✏️ Modify any values
3. ❌ Cancel
```

### 10. Apply updates (if approved)

If the user confirms, apply the updates:

**For issue updates:**
```
mcp_linear_update_issue(
    id="<TICKET_ID>",
    title="<new-title>" (if changed),
    description="<new-description>" (if changed),
    state="<new-status>" (if changed),
    assignee="<new-assignee>" (if changed),
    labels=["<label1>", "<label2>"] (if changed),
    project="<new-project>" (if changed),
    cycle="<new-cycle>" (if changed),
    milestone="<new-milestone>" (if changed),
    dueDate="<new-due-date>" (if changed),
    estimate=<new-estimate> (if changed),
    parentId="<new-parent>" (if changed),
    relatedTo=["<issue1>", "<issue2>"] (if changed),
    blocks=["<issue1>", "<issue2>"] (if changed),
    blockedBy=["<issue1>", "<issue2>"] (if changed)
)
```

**For comments:**
```
mcp_linear_create_comment(
    issueId="<TICKET_ID>",
    body="<comment-text>"
)
```

**Important notes:**
- Only include fields that are being updated
- For arrays (labels, relatedTo, blocks, blockedBy), provide the complete new array (not additions)
- Use appropriate value formats (IDs, names, or special values like "me")

### 11. Verify updates

After applying updates, fetch the ticket again to verify:

```
mcp_linear_get_issue(id="<TICKET_ID>")
```

Compare key fields to ensure changes were applied correctly.

### 12. Confirm and provide summary

Display confirmation:

```
✅ Ticket <TICKET_ID> updated successfully!

## Summary of Changes

- Title: <old> → <new> (if changed)
- Status: <old> → <new> (if changed)
- Assignee: <old> → <new> (if changed)
- Labels: <old> → <new> (if changed)
- ... (list all changes)

---

## Updated Ticket

**URL:** <linear-url>

**Quick actions:**
- View ticket: <linear-url>
- Add another comment: /update-ticket <TICKET_ID> (select option 12)
- Update again: /update-ticket <TICKET_ID>
```

---

## Field Update Examples

### Updating Status

```
Current status: In Progress
Available statuses:
  - Backlog
  - Todo
  - In Progress
  - In Review
  - Done
  - Cancelled

Which status should this ticket have? In Review
```

### Updating Labels

```
Current labels: bug, high-priority
Available labels:
  - bug
  - feature
  - documentation
  - high-priority
  - low-priority

Which labels should be set? bug, high-priority, documentation
```

### Updating Assignee

```
Current assignee: John Doe
Available users:
  - me (Your Name)
  - jane@example.com (Jane Smith)
  - john@example.com (John Doe)

Who should be assigned? me
```

### Adding a Comment

```
What comment would you like to add?

PR #42 has been merged. This ticket is ready for testing.
```

---

## Error Handling

This command will STOP and display an error if:

1. Ticket ID cannot be determined
2. Linear MCP server not accessible
3. Ticket not found or inaccessible
4. Invalid field values provided (e.g., status doesn't exist, invalid date format)
5. Update operation fails

**For update failures:**
```
❌ ERROR: Failed to update ticket <TICKET_ID>.

Error: <error-message>

Please verify:
1. You have permission to update this ticket
2. All field values are valid
3. The Linear MCP server is properly configured

You can try again or contact support if the issue persists.
```

---

## Integration

This command works well with:

- **validate-ticket**: Run first to verify ticket exists and get context
- **prepare-commit**: Update ticket status after committing
- **prepare-pr**: Update ticket status when PR is created
- **incorporate-feedback**: Update ticket status after addressing feedback
- **generate-review-doc**: Review ticket before updating

---

## Common Workflows

### Workflow 1: Update Status After PR Creation

```
1. /prepare-pr ENG-123
2. PR created successfully
3. /update-ticket ENG-123
4. Select: Status → "In Review"
5. Add comment: "PR #42 created and ready for review"
```

### Workflow 2: Update Ticket After Feedback Addressed

```
1. /incorporate-feedback 42
2. Feedback addressed, changes pushed
3. /update-ticket ENG-123
4. Select: Status → "In Review"
5. Add comment: "Addressed all review feedback. Ready for re-review."
```

### Workflow 3: Update Multiple Fields

```
1. /update-ticket ENG-123
2. Select: Status, Assignee, Labels, Due Date
3. Update each field
4. Review proposed changes
5. Apply updates
```

### Workflow 4: Add Progress Comment

```
1. /update-ticket ENG-123
2. Select: Add a comment
3. Enter comment with progress update
4. Apply update
```

---

## Best Practices

1. **Review before updating**: Always review the current ticket state before making changes
2. **Use descriptive comments**: When updating status, add a comment explaining why
3. **Validate relationships**: Ensure related/blocking issues exist before setting relationships
4. **Batch updates**: Update multiple fields in one operation when possible
5. **Document changes**: Add comments for significant status changes or important updates
6. **Verify after update**: Always verify the changes were applied correctly

---

## Field-Specific Guidelines

### Status Updates
- Add a comment explaining the status change
- Use appropriate statuses for the workflow stage
- Consider team conventions for status transitions

### Description Updates
- Preserve important context from the original description
- Use Markdown formatting for clarity
- Include acceptance criteria if updating a feature ticket

### Label Updates
- Follow team labeling conventions
- Use labels consistently across similar tickets
- Don't over-label (3-5 labels is usually sufficient)

### Relationship Updates
- Set parent issues for sub-tasks
- Use "blocks" and "blockedBy" for dependencies
- Use "relatedTo" for loosely connected work

### Comment Guidelines
- Be clear and concise
- Reference PRs, commits, or other tickets when relevant
- Use Markdown for formatting (code blocks, links, etc.)

---

## Limitations

- **Array fields**: When updating labels, relatedTo, blocks, or blockedBy, you must provide the complete new array. The API replaces the entire array, not individual items.
- **Permissions**: You can only update tickets you have permission to modify
- **Status transitions**: Some status transitions may be restricted by Linear workflow rules
- **Rate limits**: Be mindful of Linear API rate limits when making multiple updates

---

## Troubleshooting

**Issue: "Status not found"**
- Verify the team name is correct
- Check available statuses using the list function
- Ensure the status name matches exactly (case-sensitive)

**Issue: "Label not found"**
- Verify labels exist for the team
- Check if labels are workspace-level vs team-level
- Ensure label names match exactly

**Issue: "Cannot update ticket"**
- Verify you have edit permissions
- Check if the ticket is in a state that allows updates
- Ensure all required fields are provided

**Issue: "Relationship update failed"**
- Verify issue IDs exist and are accessible
- Check if relationships would create circular dependencies
- Ensure parent issues are valid

---

## Configuration

The command uses Linear MCP server configuration from:
- `~/.cursor/mcp.json` (user-level)
- `.cursor/mcp.json` (project-level)

Ensure `LINEAR_API_KEY` is set in your environment or MCP configuration.
