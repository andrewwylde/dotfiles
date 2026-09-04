# Build Task — Unreal Engine Editor

## Variables

### prompt

{{prompt}}

### previous_envelope

{{previous_envelope}}

### context_handoff_dir

{{context_handoff_dir}}

## Task

Implement the work described in `prompt`, guided by `previous_envelope` if present.

If `previous_envelope` contains a plan (`PlanOutput`), read `{{context_handoff_dir}}/plan.md` — it is your spec. If it also contains a verification spec, read `{{context_handoff_dir}}/verify.yaml` — it defines what must be true after your work.

After implementing, run the verification spec:
```
bash: python scripts/adw_editor_verify.py --spec {{context_handoff_dir}}/verify.yaml
```
Fix any failures before emitting your Report.

## Report

Respond with ONLY valid JSON matching `BuildOutput` — no prose before or after:

```json
{
  "status": "success",
  "summary": "<one sentence describing what you built>",
  "changed_files": ["Content/Characters/BP_MyCharacter.uasset"],
  "artifacts": [],
  "commit_message": "<imperative one-line git subject for the code you changed — this is what the commit of your work will say>",
  "notes_for_next_agent": "<how to verify this work, or paste verification failure output verbatim>"
}
```