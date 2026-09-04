# Plan Task

## Variables

### prompt

{{prompt}}

### previous_envelope

{{previous_envelope}}

### context_handoff_dir

{{context_handoff_dir}}

### adw_id

{{adw_id}}

## Task

Plan the work described in `prompt`.

1. Write the full plan to `{{context_handoff_dir}}/plan.md` — this is the copy the builder reads. Use that exact path.
2. If the task changes Unreal editor state, write the falsifiable assertion spec required by your system instructions to `{{context_handoff_dir}}/verify.yaml`.
3. Copy the plan into the repo under `specs/`:
   - **List `specs/` before you pick the name.** A session that plans more than once reuses its `{{adw_id}}`, so the obvious name may already be taken.
   - Base name: `specs/{{adw_id}}_<slug>.md`, where `<slug>` is two to four kebab-case words naming the work.
   - If a file with that name already exists, use `specs/{{adw_id}}_<slug>_v2.md`, then `_v3`, and so on until the name is free. **Never overwrite an existing spec** — the earlier plan is the record of what was asked for then.
   - **Copy it, do not retype it.** One bash call does the whole step:
     `mkdir -p specs && cp "{{context_handoff_dir}}/plan.md" "specs/{{adw_id}}_<slug>.md"`
     Writing the plan a second time through `write` re-emits every line you already wrote, which costs the whole document again in output tokens and lets the two copies drift.
4. Emit your `Report` JSON. Declare both plan paths in `artifacts`, plus `{{context_handoff_dir}}/verify.yaml` when you generated it.

## Report

Respond with ONLY raw valid JSON matching `PlanOutput` — no markdown wrappers, no prose, no commentary before or after:

```json
{
  "status": "success",
  "summary": "<one sentence describing the plan>",
  "artifacts": ["{{context_handoff_dir}}/plan.md", "{{context_handoff_dir}}/verify.yaml", "specs/{{adw_id}}_<slug>.md"],
  "commit_message": "<imperative one-line git subject for committing THIS PLAN DOCUMENT>",
  "notes_for_next_agent": "<what the builder must know>"
}
```

NOTE: The "status" field MUST be exactly the literal string "success" or "fail" (never "failed", "error", or "completed").