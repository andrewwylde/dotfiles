# Flesh Out Ticket

Expand and enrich a Linear ticket with detailed description, acceptance criteria, technical considerations, and implementation context. This command helps transform sparse or minimal tickets into comprehensive, actionable work items.

**IMPORTANT FOR AI AGENTS:** Always use this command (`/flesh-out-ticket`) when a ticket needs more detail before work can begin. This command ensures proper structure, completeness, and clarity for implementation.

## Prerequisites

- Git repository initialized (optional, for branch-based ticket detection)
- Linear MCP server configured (for ticket operations)
- Access to the Linear workspace

---

## AI Execution Steps

When this command is invoked, automatically perform these steps:

### 1. Determine the ticket ID

**Priority order for ticket ID extraction:**

1. **User input**: If provided (e.g., `/flesh-out-ticket ENG-123`)

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
     /flesh-out-ticket ENG-123
   
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
- Description (current)
- Status
- Priority
- Assignee
- Labels
- Project
- Cycle
- Parent issue (if any)
- Related issues (if any)
- Blocking/blocked-by relations

### 4. Fetch related context

**Fetch parent ticket (if applicable):**
```
mcp_linear_get_issue(id="<PARENT_ID>")
```

**Fetch related tickets:**
For each related/blocking issue:
```
mcp_linear_get_issue(id="<RELATED_ID>")
```

**Fetch comments:**
```
mcp_linear_list_comments(issueId="<TICKET_ID>")
```

**Store context:**
- Parent ticket title and description
- Related ticket titles and statuses
- Discussion history from comments
- Any technical details mentioned in comments

### 5. Analyze current ticket completeness

Assess what's missing or sparse:

**Check for:**
- [ ] Detailed description (beyond title)
- [ ] Acceptance criteria
- [ ] Technical context
- [ ] Implementation approach
- [ ] Dependencies
- [ ] Testing requirements
- [ ] Edge cases
- [ ] Related documentation links

**Display analysis:**

```
## Current Ticket Analysis: <TICKET_ID>

**Title:** <title>
**Status:** <status>
**Current Description Length:** <word-count> words

### Completeness Assessment

- Description: <Present/Partial/Missing>
- Acceptance Criteria: <Present/Partial/Missing>
- Technical Details: <Present/Partial/Missing>
- Context: <Present/Partial/Missing>

### What's Missing

<Based on analysis, list what needs to be added>
```

### 6. Generate enhanced description structure

Create a structured description template with sections:

```markdown
## Overview

<Expand the title into a clear, comprehensive description. Explain what needs to be built, fixed, or changed. Include the problem statement, user need, or business requirement.>

## Context & Background

<Explain why this work is needed. Include:
- Business context or user impact
- Related work or dependencies
- Historical context if relevant
- Parent ticket context (if applicable)
- Related ticket context (if applicable)>

## Acceptance Criteria

<Define clear, testable criteria for completion. Use bullet points or numbered list. Each criterion should be:
- Specific and measurable
- Testable (can be verified)
- Complete (covers the full requirement)

Examples:
- User can successfully authenticate with OAuth2
- Error messages display correctly for invalid inputs
- API returns 200 status code for valid requests>

## Technical Approach

<Describe the technical implementation approach:
- Architecture or design decisions
- Key components or modules involved
- Data structures or schemas
- API contracts or interfaces
- Performance considerations
- Security considerations>

## Implementation Details

<Provide specific implementation guidance:
- Files or modules to modify
- Functions or classes to create/modify
- Configuration changes needed
- Database migrations (if applicable)
- External dependencies or integrations>

## Testing Requirements

<Specify testing needs:
- Unit tests required
- Integration tests needed
- Manual testing scenarios
- Edge cases to cover
- Performance testing (if applicable)>

## Dependencies & Prerequisites

<List any dependencies:
- Other tickets that must be completed first
- External services or APIs
- Infrastructure requirements
- Documentation or design specs needed>

## Edge Cases & Considerations

<Document edge cases and special considerations:
- Error handling scenarios
- Boundary conditions
- Race conditions or concurrency issues
- Backward compatibility requirements
- Migration or rollout considerations>

## Related Resources

<Include links to:
- Design documents
- API documentation
- Related tickets
- External references
- Code examples or patterns>
```

### 7. Generate content for each section

**For each section, use AI to generate content based on:**

1. **Current ticket title and description** - Extract and expand existing information
2. **Parent ticket context** - Incorporate parent ticket details if applicable
3. **Related tickets** - Reference related work
4. **Comments** - Extract technical details from discussion
5. **Labels** - Infer technical domain from labels (e.g., "api", "frontend", "database")
6. **Project context** - Use project name to infer domain
7. **Team conventions** - Apply team-specific patterns and standards

**Content generation guidelines:**

- **Overview**: Expand the title into 2-3 paragraphs explaining what, why, and who benefits
- **Context**: Synthesize parent ticket, related tickets, and comments into coherent background
- **Acceptance Criteria**: Generate 3-7 specific, testable criteria based on the description
- **Technical Approach**: Infer from labels, project, and description what technical stack/patterns to use
- **Implementation Details**: Be specific about files/modules if context allows, otherwise keep high-level
- **Testing Requirements**: Suggest appropriate test types based on the work type
- **Dependencies**: List any blocking or related tickets already identified
- **Edge Cases**: Think through common edge cases for the type of work
- **Related Resources**: Include links to parent/related tickets, and suggest documentation if applicable

### 8. Present enhanced description

Display the complete enhanced description:

```
## Enhanced Ticket Description for <TICKET_ID>

<Show the complete structured description with all sections populated>

---

**Word Count:** <count> words (was <original-count>)
**Sections Added:** <list of new sections>
**Improvements:** <summary of enhancements>

---

Would you like me to:
1. ✅ Update the ticket with this enhanced description
2. ✏️ Edit specific sections
3. 📝 Add more detail to a section
4. 🔄 Regenerate a section
5. ❌ Cancel
```

### 9. Allow section-by-section editing

If user wants to edit:

**For each section:**
- Show current content
- Allow user to provide edits or additions
- Regenerate if requested
- Confirm before proceeding

**Example interaction:**

```
Which section would you like to edit?

1. Overview
2. Context & Background
3. Acceptance Criteria
4. Technical Approach
5. Implementation Details
6. Testing Requirements
7. Dependencies & Prerequisites
8. Edge Cases & Considerations
9. Related Resources
10. ✅ Done editing - proceed to update

Current section: Overview

<Show current content>

Would you like to:
- Edit this section
- Add more detail
- Regenerate with different focus
- Skip to next section
```

### 10. Update the ticket (if approved)

If the user confirms, update the ticket description:

```
mcp_linear_update_issue(
    id="<TICKET_ID>",
    description="<enhanced-description-markdown>"
)
```

**Important:**
- Preserve any existing valuable content from the original description
- Use Markdown formatting
- Ensure all sections are properly formatted
- Keep the enhanced description readable and well-structured

### 11. Optionally update other fields

After updating the description, suggest updating related fields:

```
✅ Description updated successfully!

Would you like to also update:

1. 🏷️ Labels - Add relevant labels (e.g., "needs-design", "backend", "api")
2. 📊 Priority - Set priority if not already set
3. 👤 Assignee - Assign to team member
4. 📁 Project - Add to relevant project
5. ⏱️ Estimate - Add time estimate
6. ✅ Done - Ticket is now complete
```

**For each selected field:**

- **Labels**: Suggest labels based on content (e.g., "api", "frontend", "database", "security")
- **Priority**: Suggest based on urgency indicators in description
- **Assignee**: List team members, suggest based on labels/project
- **Project**: List available projects, suggest based on ticket content
- **Estimate**: Suggest estimate based on scope and complexity

### 12. Verify and confirm

After all updates:

```
✅ Ticket <TICKET_ID> has been fleshed out!

## Summary of Enhancements

- **Description**: Expanded from <original-word-count> to <new-word-count> words
- **Sections Added**: <list>
- **Fields Updated**: <list>
- **Labels Added**: <list> (if applicable)

---

## Updated Ticket

**URL:** <linear-url>

**Quick actions:**
- View ticket: <linear-url>
- Start work: Create branch `<TICKET_ID>-<kebab-case-title>`
- Generate review doc: /generate-review-doc <TICKET_ID>
```

---

## Description Template Structure

The enhanced description follows this structure:

```markdown
## Overview

[2-3 paragraphs explaining what, why, and who benefits]

## Context & Background

[Background information, parent ticket context, related work]

## Acceptance Criteria

- [Specific, testable criterion 1]
- [Specific, testable criterion 2]
- [Specific, testable criterion 3]

## Technical Approach

[High-level technical approach, architecture decisions, key components]

## Implementation Details

[Specific files, modules, functions, configuration changes]

## Testing Requirements

[Unit tests, integration tests, manual testing scenarios, edge cases]

## Dependencies & Prerequisites

- [Dependency 1]
- [Dependency 2]

## Edge Cases & Considerations

[Error handling, boundary conditions, race conditions, compatibility]

## Related Resources

- [Link to parent ticket]
- [Link to related ticket]
- [Link to documentation]
```

---

## Content Generation Guidelines

### Overview Section
- Start with a clear problem statement or user need
- Explain the solution or approach
- Describe the expected outcome or benefit
- 2-3 paragraphs, 100-200 words

### Acceptance Criteria
- Use action-oriented language ("User can...", "System should...")
- Make each criterion specific and measurable
- Include both positive and negative test cases
- 3-7 criteria typically sufficient

### Technical Approach
- Describe high-level architecture or design
- Mention key technologies or patterns
- Explain major design decisions
- Keep it at the right level of detail (not too low-level, not too vague)

### Implementation Details
- List specific files/modules if known
- Describe key functions or classes
- Mention configuration or schema changes
- Be specific enough to guide implementation

### Testing Requirements
- Specify test types (unit, integration, e2e)
- List key scenarios to test
- Mention edge cases
- Include performance testing if relevant

---

## Examples

### Example 1: Sparse Ticket → Enhanced

**Before:**
```
Title: Add user authentication
Description: Need to add login functionality
```

**After:**
```markdown
## Overview

This ticket implements user authentication for the application, allowing users to securely log in and access protected resources. Currently, the application has no authentication mechanism, which prevents user-specific features and data access controls. This work will establish the foundation for user management and authorization.

The implementation will support email/password authentication initially, with plans to extend to OAuth2 providers in future work. Users will be able to register new accounts, log in, reset passwords, and manage their sessions.

## Acceptance Criteria

- User can register a new account with email and password
- User can log in with valid credentials
- User receives error message for invalid credentials
- User can reset password via email link
- User session persists across page refreshes
- User can log out and session is terminated
- Password meets security requirements (min 8 chars, complexity rules)

## Technical Approach

Implement authentication using JWT tokens stored in HTTP-only cookies for security. Use bcrypt for password hashing. Create user model with email, hashed password, and timestamps. Implement middleware for protecting routes that require authentication.

## Implementation Details

- Create `models/user.py` with User model
- Create `routes/auth.py` with login, register, logout endpoints
- Create `middleware/auth.py` for route protection
- Add password hashing utilities in `utils/security.py`
- Update database schema with users table

## Testing Requirements

- Unit tests for password hashing and validation
- Integration tests for login/register/logout flows
- Test invalid credentials, duplicate emails, weak passwords
- Test session persistence and expiration
```

### Example 2: Feature Ticket Enhancement

**Before:**
```
Title: Add export to CSV feature
Description: Users want to export data to CSV
Labels: feature, frontend
```

**After:**
```markdown
## Overview

Add the ability for users to export table data to CSV format. This addresses user feedback requesting data portability and offline analysis capabilities. The feature will be accessible from data table views throughout the application.

## Acceptance Criteria

- Export button visible in all data table views
- Clicking export downloads CSV file with current table data
- CSV includes all visible columns
- CSV respects current filters and sorting
- File name includes table name and timestamp
- Large datasets (>10k rows) show progress indicator
- CSV encoding handles special characters correctly

## Technical Approach

Implement client-side CSV generation using a library (e.g., Papa Parse). Fetch current table data (respecting filters), transform to CSV format, and trigger browser download. For large datasets, implement pagination or streaming approach.

## Implementation Details

- Add `ExportButton` component to `components/DataTable.tsx`
- Create `utils/csvExport.ts` for CSV generation
- Update `hooks/useTableData.ts` to support export
- Add loading state for large exports
- Test with various data types and special characters

## Testing Requirements

- Unit tests for CSV generation with various data types
- Test export with filters and sorting applied
- Test large dataset export performance
- Test special character handling (quotes, commas, newlines)
- Manual testing across different browsers
```

---

## Error Handling

This command will STOP and display an error if:

1. Ticket ID cannot be determined
2. Linear MCP server not accessible
3. Ticket not found or inaccessible
4. Update operation fails

**For update failures:**
```
❌ ERROR: Failed to update ticket <TICKET_ID>.

Error: <error-message>

Please verify:
1. You have permission to update this ticket
2. The description is valid Markdown
3. The Linear MCP server is properly configured

You can try again or contact support if the issue persists.
```

---

## Integration

This command works well with:

- **validate-ticket**: Run first to verify ticket exists
- **generate-review-doc**: Generate review doc after fleshing out
- **update-ticket**: Update other fields after description is enhanced
- **prepare-pr**: Use enhanced description when creating PR

---

## Common Workflows

### Workflow 1: Flesh Out Before Starting Work

```
1. /validate-ticket ENG-123
2. Ticket is sparse, needs more detail
3. /flesh-out-ticket ENG-123
4. Review and edit enhanced description
5. Update ticket
6. Start implementation work
```

### Workflow 2: Flesh Out After Initial Discussion

```
1. Ticket created with minimal description
2. Discussion in comments adds context
3. /flesh-out-ticket ENG-123
4. Command incorporates comments into description
5. Update ticket with comprehensive description
```

### Workflow 3: Enhance Existing Ticket

```
1. Ticket has basic description but missing acceptance criteria
2. /flesh-out-ticket ENG-123
3. Command adds missing sections
4. Review and edit
5. Update ticket
```

---

## Best Practices

1. **Preserve existing content**: Don't remove valuable information from the original description
2. **Be specific**: Generate concrete, actionable acceptance criteria
3. **Consider context**: Use parent tickets, related tickets, and comments to inform content
4. **Review before updating**: Always present the enhanced description for review before updating
5. **Iterate on sections**: Allow editing individual sections for refinement
6. **Update related fields**: Suggest updating labels, priority, estimate after enhancing description

---

## Content Quality Guidelines

### Good Acceptance Criteria
- ✅ "User can log in with valid email and password"
- ✅ "API returns 400 error for invalid request body"
- ✅ "Export includes all visible columns in current sort order"

### Poor Acceptance Criteria
- ❌ "Login works" (too vague)
- ❌ "Handle errors" (not specific)
- ❌ "Export data" (not testable)

### Good Technical Approach
- ✅ "Use JWT tokens in HTTP-only cookies for session management"
- ✅ "Implement rate limiting using Redis with 100 requests/minute limit"
- ✅ "Create RESTful API endpoints following OpenAPI 3.0 specification"

### Poor Technical Approach
- ❌ "Add authentication" (too vague)
- ❌ "Use best practices" (not specific)
- ❌ "Make it secure" (no details)

---

## Troubleshooting

**Issue: "Generated content is too generic"**
- Provide more context in the original ticket
- Reference parent ticket or related tickets
- Add comments with technical details before running command

**Issue: "Missing important details"**
- Edit specific sections to add details
- Use the section-by-section editing feature
- Manually add sections if needed

**Issue: "Content doesn't match team conventions"**
- Review and edit generated content
- Adjust template structure if needed
- Provide feedback to improve generation

---

## Configuration

The command uses Linear MCP server configuration from:
- `~/.cursor/mcp.json` (user-level)
- `.cursor/mcp.json` (project-level)

Ensure `LINEAR_API_KEY` is set in your environment or MCP configuration.
