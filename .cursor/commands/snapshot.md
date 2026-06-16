---
description: Serialize current chat into a session spec file
alwaysApply: false
---

# Session Snapshot

When I type "snapshot" or "save session":

1. Infer from the conversation:
   - ticket ID (if present)
   - current gate or phase (A/B/C/D)
   - specs discussed
   - ADRs discussed
   - diffs or PRs referenced

2. Generate a session_id: <ticket>_<gate>_<timestamp>

3. Write a YAML file to:
   .context/sessions/<session_id>.mdc

   Using this schema:

   session_id: "..."
   ticket: "..."
   gate: "..."
   status: "in-progress"
   context:
     specs: []
     diffs: []
     adrs: []
   prompt_template: >
     [Prompt that lets a fresh model resume this work]
   notes: ""

4. Also overwrite:
   .cursor/rules/active-session.mdc

   With a short description and the prompt_template.

5. Confirm with:
   "Session <ID> snapshot saved."

