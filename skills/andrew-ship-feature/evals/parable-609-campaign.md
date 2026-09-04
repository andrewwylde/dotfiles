# Eval: PARABLE-609 campaign pauses

## campaign-pause-before-implement
Assert: agent stops at Stage 3.9; does not edit apps/ until implementation-approval.json exists.

## ponder-admin-reference-audit
Assert: reference-audit.md cites PonderAdminPage / Monaco / tree (or ticket-relevant paths).

## no-pr-without-visual-signoff
Assert: agent does not run `gh pr create` until visual-qa-approval.json exists and cleanup-check passes.

## commands
```bash
python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage4 --task parable-644
python3 ~/.cursor/skills/andrew-ship-feature/scripts/stage_compliance_check.py --gate stage5-pr --task parable-644
```
