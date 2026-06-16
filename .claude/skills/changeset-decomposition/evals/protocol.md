# Eval protocol — copy-paste for harness or humans

## Baseline system prefix (prepend to system or first user block)

```text
You are helping split a large git changeset into multiple PRs.
Do not use any external skill documents. Answer from general software engineering practice only.
Be concise but complete.
```

## Treatment system prefix

```text
You MUST follow the changeset-decomposition skill before producing your final answer.

Steps:
1. Read and follow: ~/.claude/skills/changeset-decomposition/SKILL.md
2. In order, read and execute each reference:
   - references/pattern-01-inventory.md
   - references/pattern-02-dependency-mapping.md
   - references/pattern-03-risk-assessment.md
   - references/pattern-04-pr-boundaries.md
   - references/pattern-05-sequencing.md
   (paths relative to the skill directory above)

Produce the full pipeline outputs (inventory through split-to-prs hand-off) using ONLY the files listed in the user scenario. If information is missing, state assumptions explicitly.
```

## User message wrapper

After the prefix, paste the contents of `cases/<id>/scenario.md` unchanged.

## Grader instructions

1. Open `RUBRIC.md` and the case's `grading-notes.md`.
2. Check critical violations first.
3. Score structure, then quality.
4. Log wall time and token count if your platform exposes them.

## Optional: pair with split-to-prs eval

Treatment output should end with a **split-to-prs hand-off** block. A second eval can feed that block to an agent with `split-to-prs` and check it does not run git until user approval (per that skill's rules).
