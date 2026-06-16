# super-review

Run this from the current workspace root (the repo you want reviewed). Use a file in the workspace for the diff (e.g. .pr-review.diff):

PR_REVIEW_DIFF_FILE=".pr-review.diff" /Users/andrewwylde/code/engineering-onboarding/pr-review-agent/scripts/prepare_pr_review.sh

(Use the absolute path to the script if needed.) The script writes the diff to .pr-review.diff and prints:
- Line 1: PROJECT_ROOT=<path>
- Line 2: TICKET_ID=<id>
- Line 3: CODE_CHANGES_PATH=<absolute path to the diff file>

Call the pr_review MCP tool with:
- code_changes_path: the value of CODE_CHANGES_PATH from line 3 (absolute path; do not pass code_changes)
- ticket_id: the TICKET_ID value from line 2
- project_root: the PROJECT_ROOT value from line 1
- domain_context: leave empty unless the user gave a pre-resolved bundle.

Return the tool result (manifest, reports, resolution) to the user.