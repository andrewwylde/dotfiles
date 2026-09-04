---
name: swarm-review
description: Conduct multi-agent PR reviews using parallel subagent swarms, structured around the PR's intent and validated against internal EDRs and specs. Produces a saved review artifact that separates tactical fixes (with effort estimates) from systemic follow-ups. Use when reviewing a pull request, analyzing PR changes, when the user asks for a code review, or when they mention swarm review, subagent review, or multi-agent review. Also trigger when the user pastes a GitHub PR URL and asks for review, even without mentioning subagents explicitly.
---

# Swarm Review

Multi-agent PR review that evaluates changes against the PR's stated intent and internal engineering standards (EDRs/specs), then separates findings into scoped tactical fixes and systemic follow-ups.

## Quick Mode

For small PRs (**<200 lines of diff, single domain, AND <3 files changed**), skip the subagent swarm entirely. Instead:
1. Gather context (Phase 1 + 2, using lazy EDR extraction)
3. Do a direct review yourself using the relevant domain lens from Phase 3
4. Produce the artifact (Phase 5)

Mention that you're using quick mode: "This is a small, single-domain PR — I'll review directly instead of launching a subagent swarm."

Even in quick mode, a PR that touches multiple layers (e.g., a handler + migration + frontend component) should get the full swarm regardless of line count.

## Phase 1: Gather Context

Fetch the PR metadata and diff before anything else.

1. `gh pr view <number> --json title,body,labels,files` — description and file list
2. `gh pr diff <number>` — full diff
3. If the PR body references a Linear issue, fetch that too (use the `linear-fetch` skill or `gh` to pull context)

Scan the changed files to understand the PR's **domain footprint** — which layers it touches (backend Go, frontend Svelte/TS, infra, DB, CI, schema, Python). This determines subagent selection and EDR relevance.

## Phase 2: Intent & Standards Discovery

### Establish intent

**If the user provided intent** (e.g., "focusing on the fact that direct DB updates bypassed validation"), use it directly. Confirm briefly: "I'll frame the review around **X** — anything else to focus on?"

**If no intent was given**, infer from the PR description and confirm: "Based on the PR description, the main motivation appears to be **X**. Is that right, or should I focus on something else?"

Note secondary objectives the user raises (e.g., "also flag systemic issues"). These shape how you categorize findings later.

### Check EDRs (lazy extraction — never load full files)

Based on the PR's intent and domain footprint, dynamically discover relevant EDRs. **Do not read entire `.mdx` files into context** — use the extraction script:

```bash
# From repo root (auto-finds docs/internal/edr)
python3 ~/.claude/skills/swarm-review/scripts/extract-edr-sections.py \
  --domain connector --keywords status,lifecycle

# Cheap header map before committing to extraction
python3 ~/.claude/skills/swarm-review/scripts/extract-edr-sections.py \
  --domain api --headers-only

# List all EDRs with titles
python3 ~/.claude/skills/swarm-review/scripts/extract-edr-sections.py --list

# Explicit file + keywords
python3 ~/.claude/skills/swarm-review/scripts/extract-edr-sections.py \
  --file 0004-connector-lifecycle.mdx --keywords status
```

**Script behavior** (`scripts/extract-edr-sections.py`):

1. Shortlists EDRs by keyword hits in filename, front matter, and section headers/bodies
2. Maps `##` / `###` section boundaries (respects nesting)
3. Emits a **constraints digest** — matched sections only, not full `.mdx` files
4. Enforces budget: `--max-edrs 3` (default), `--max-lines-per-edr 30` (default)

Use `--domain` presets from the table below (`api`, `connector`, `service`, `infra`, `pipeline`, `query`) or pass raw `--keywords`.

Paste the digest into subagent prompts under **Codebase Conventions**. Do not re-read the source `.mdx` files unless the digest is insufficient.

This dynamic approach ensures you always check what actually exists rather than relying on a static list. EDRs get added and updated — discover them fresh each time.

**Domain-to-keyword mapping** (use these to guide your grep):

| PR domain | Search keywords |
|---|---|
| API design, endpoints, handlers | api, endpoint, handler, error code, response |
| Connector logic, status, config | connector, lifecycle, behavior, schema, status |
| Service structure, packages | package, service, structure, module |
| Infrastructure, IaC | pulumi, stack, gke, otel, infrastructure |
| Data pipelines, ingestion | prefect, pipeline, ingestion, gold layer |
| Query layer | datafusion, query, sql |

If no EDRs are relevant, note that and move on.

## Phase 2.5: Blast Radius Analysis

Specialist subagents (golang-pro, security-engineer, etc.) have restricted tool access -- they can only review code embedded in their prompts. They **cannot discover issues in files outside the diff**. This phase identifies affected-but-unchanged code so it can be included in subagent prompts.

### Identify behavioral changes

Scan the diff for:
- **Removed functions/methods** (e.g., `mergePermissions` deleted)
- **Changed data sources** (e.g., permissions now read from role table instead of user column)
- **Removed fallback paths** (e.g., union of legacy + new data replaced with new-only)
- **Changed function signatures** (callers outside the diff may need updating)

### Trace the blast radius

For each behavioral change, grep for code that **still depends on the old behavior**:

```bash
# If a function was removed, find callers that might still need its behavior
grep -r "removedFunctionName" --include="*.go"

# If a data source changed, find code that still writes to the old source
grep -r "legacyField" --include="*.go"

# If a shared helper changed signature, find all callers
grep -r "changedHelper(" --include="*.go"
```

Focus on files **NOT in the diff** -- those are the ones the PR author may have missed.

### Include affected files in subagent prompts

Any file identified in the blast radius that is relevant to a subagent's domain should be embedded in that agent's prompt using the **excerpt rules from Phase 3** (diff hunk + padding — not full files). Mark it clearly:

```
## Blast Radius: Unchanged files that may be affected
[Relevant excerpt with ±50 lines around the dependent call site, plus a note explaining why it's included]
```

Full-file embed is allowed only when the blast-radius file is **<120 lines** or the dependent logic is spread across most of the file.

### Example

PR removes `mergePermissions()` which unioned legacy permissions with role-derived permissions. Blast radius analysis:
1. `grep mergePermissions` -- confirms it's only called from the changed file (safe)
2. `grep "invite.Permissions"` -- finds `AutoClaimPendingInvites` in an unchanged file still writing to the legacy column
3. Since the PR removed the only code that READ the legacy column, the unchanged file's writes are now dead -- but worse, the data it writes is no longer surfaced to users

This analysis takes 2-5 minutes and catches the class of bugs that specialist agents structurally cannot find.

## Phase 3: Subagent Swarm

### Selecting agents

**If the user specified agents** (e.g., `/platform-engineer /golang-pro /api-designer`), honor their choices but still apply the agent budget unless they explicitly ask for more. Trim to the cap and confirm: "You named 4 specialists — I'll run X and Y plus code-reviewer per the 2+1 budget unless you want the full set."

**If the user didn't specify**, select based on domain footprint. Discover available agents from both sources:
- **Personal agents**: `~/.claude/agents/` — each `.md` file is a launchable `subagent_type`
- **Project skills**: `.claude/skills/` — project-specific skills (e.g., `test-fix`, `skeptic`, `edr-discover`)

Then select the best fit:

| PR domain | Suggested agents | Each agent's lens |
|---|---|---|
| Backend Go | `golang-pro`, `api-designer`, `platform-engineer` | Code quality + idioms; API surface + error consistency; architecture alignment |
| Frontend Svelte/TS | `frontend-developer`, `typescript-pro`, `ui-designer` | Reactivity + state mgmt; type safety + patterns; accessibility + UX |
| Infrastructure/IaC | `cloud-architect`, `terraform-engineer`, `security-engineer` | Cloud architecture; IaC patterns + drift; security posture |
| Database/migrations | `database-administrator`, `sql-pro`, `security-auditor` | Schema design + perf; query optimization; data exposure + migration safety |
| CI/CD workflows | `devops-engineer`, `deployment-engineer`, `security-engineer` | Workflow reliability + triggers; deploy patterns; supply chain + secrets |
| Python services | `python-pro`, `platform-engineer`, `data-engineer` | Code quality + async; architecture; pipeline design |
| Schema/codegen | `api-designer`, `platform-engineer`, `typescript-pro` | Schema design; generated vs hand-written boundaries; type generation |

The table covers common cases, but the full agent roster includes many more specialists (e.g., `kubernetes-specialist`, `docker-expert`, `graphql-architect`, `postgres-pro`). If the PR's domain has a more specific match, prefer it.

### Agent budget (strict caps)

**Always include `code-reviewer`** — it has full tool access and explores beyond the diff. It does **not** count against the domain-specialist cap.

Classify the PR, then cap agents:

| PR size | Criteria | Launch |
|---|---|---|
| **Small-medium** (default) | <500 lines diff **and** ≤2 domains **and** ≤8 files | **2** domain specialists + `code-reviewer` (**3 total**) |
| **Large / mixed** | ≥500 lines, **or** ≥3 domains, **or** >8 files, **or** blast radius spans 3+ packages | **3** domain specialists + `code-reviewer` (**4 total**) |

**Hard ceiling: 4 agents total** (including `code-reviewer`). More agents have diminishing returns and multiply token cost.

For mixed-domain PRs at the large tier, pick the 3 specialists covering the **highest-risk** areas (e.g., migration + auth beats lint + docs). Do not add a fourth domain specialist — that's what `code-reviewer` is for.

Present: "For this PR I'd launch **X**, **Y**, and **code-reviewer** (2+1 budget). Want to adjust?"

### Preparing subagent prompts

Each subagent gets a **tailored prompt** — not the raw diff. The quality of the review depends on prompt quality. See [references/prompt-example.md](references/prompt-example.md) for a complete example. Use this structure:

```
## Context
[What the PR does, the confirmed intent, 2-3 sentences]

## Codebase Conventions
[Key rules from relevant EDRs that apply to this agent's domain.
E.g., for a golang-pro reviewing API handlers: "EDR-0002 requires X,
EDR-0011 mandates error codes follow Y pattern."]

## Code to Review
[Relevant excerpts — only files/hunks for this agent's domain. Use diff hunks
with ±50 lines of padding per changed region; merge overlapping windows.]

## Focus Areas
[3-5 domain-specific questions using the lens from the agent selection
table above. Frame as questions, not instructions.]

## Severity Framework
Flag each issue as:
- **Blocker**: Must fix before merge (data loss, security, correctness bugs)
- **Improvement**: Should fix, low effort (code quality, consistency, missing guards)
- **Follow-up**: Systemic issue for a separate PR (architecture, tech debt, missing tests)
```

**Code excerpt sizing (default: hunk + padding, not full files)**:

Specialist agents cannot read files — they need enough context in-prompt, but **full-file dumps are a token furnace**. Default to:

1. **Diff hunks** for every changed file in the agent's domain
2. **±50 lines of padding** above and below each hunk (merge overlapping windows into one block)
3. **Type/signature context** when padding isn't enough — add the enclosing function/type definition even if outside the padding window

**When full file is allowed** (rare):

| Condition | Action |
|---|---|
| File <120 lines | Full file OK |
| Blast-radius file where the change invalidates file-wide assumptions | Full file for that file only |
| `platform-engineer` / cross-cutting architecture review | Prefer struct/interface definitions + changed functions, not every line of a 2k-line file |

**When full file is forbidden**: A PR changes 5 lines in a 2,000-line file — send the hunk + padding, not the whole file. If the agent needs more, it should say so in findings; do not preemptively dump the file.

For PRs >500 lines, also add a **one-line summary per omitted section** ("lines 400-900: unchanged CRUD helpers").

**`code-reviewer` prompt is lightweight** — intent, EDR digest, file list, blast-radius notes, and focus questions. It has Read/Grep; do **not** embed large code blocks for it.

**Include EDR constraints** in each specialist's prompt (from the Phase 2 digest only). Only rules relevant to that agent's domain.

### Launching subagents

Use the **Agent tool** to spawn each reviewer as an actual parallel subagent — do NOT simulate multiple perspectives yourself or apply "lenses" inline. The entire point of the swarm is that independent agents review in isolation without influencing each other, then you synthesize their findings.

Concretely: call the Agent tool once per reviewer, all in the same message so they run in parallel. Use the specialist `subagent_type` values (e.g., `golang-pro`, `api-designer`) to get their domain expertise.

**Critical: specialist agents have restricted tool access** — most can't use Bash or Read. Before launching the swarm, read relevant files yourself and build **targeted excerpts** per the sizing rules above (hunk + ±50 line padding by default).

Each specialist prompt must include the **complete enclosing function** for every changed hunk (extend padding if the function is larger than 50 lines). That is not the same as embedding the whole file.

### Runtime-verification rule (specialists)

Specialists must **not** invent compile/runtime/migration blockers from static reading alone. Every prompt MUST include:

```
## Evidence rules
- Mark claims as OBSERVED (from provided excerpts) vs INFERRED.
- Do NOT file BLOCKER/Required findings that depend on runtime, migration
  apply order, SvelteKit/TanStack cache behavior, or DB concurrency unless
  the prompt includes runtime evidence (test output, logs, applied migration
  transcript). Otherwise mark as Needs runtime verification.
- Example code in this prompt is illustrative unless labeled OBSERVED.
- Tool access: you may only use what this prompt embeds. If Bash/Read would
  be required to prove a claim, say so — do not speculate.
```

When a finding **does** need runtime proof, assign it to `code-reviewer` (full tools) or run the check yourself in Phase 4 synthesis before accepting a specialist BLOCKER.

```
Agent(subagent_type="golang-pro", prompt="<tailored prompt with hunk+padded excerpts>")
Agent(subagent_type="api-designer", prompt="<tailored prompt with hunk+padded excerpts>")
Agent(subagent_type="code-reviewer", prompt="<lightweight prompt — no large code dumps>")
```

Launch all agents in one message (parallel). Respect the agent budget table — do not launch 4 domain specialists.

Wait for all agents to complete before moving to Phase 4 synthesis.

## Phase 4: Synthesis

After subagents return, synthesize a unified review. Individual agents review in isolation, but you see the full picture.

### Merge findings

1. **Deduplicate** — agents often flag the same issue from different angles. Merge into a single finding with the strongest rationale.
2. **Categorize** — split into tactical (fix in this PR) vs systemic (follow-up).
3. **Estimate effort** — for tactical fixes, include a rough estimate (e.g., "1-line change, 2 minutes" or "new test file, ~15 minutes").
4. **Rank** — within each category, order by severity, then by effort (low-effort blockers first). For ties, rank by likelihood of user impact.

### Cross-cutting review

After merging subagent findings, do your own pass looking for issues that span agent boundaries:
- **Blast radius gaps** — revisit Phase 2.5 findings. Did any subagent flag issues in the blast radius files? If not, verify those files are truly unaffected. This is the highest-value cross-cut because it catches the class of bugs that specialist agents structurally miss.
- **Contract consistency** — when the PR calls a shared interface (e.g., a Prefect client, an HTTP client, a shared utility), grep for how *other callers* of that same interface pass parameters. Flag divergences in parameter names, types, or semantics. Example: if existing callers pass a UUID as `tenant_id` but the new code passes a slug, that's a contract break even though the code compiles and tests pass.
- **Test semantics** — for any new or modified test files in the PR, spot-check that each test name matches what the test body actually exercises. A test named `Returns400ForInvalidInput` should construct invalid input and assert a 400. A test named `NonLatinFallback` should use non-Latin characters. Tests that compile and pass but don't test their claimed scenario are worse than no test -- they give false confidence.
- **Inconsistent patterns** across layers (e.g., admin API uses one DB access pattern, customer API uses another)
- **Scope creep** — changes unrelated to the PR's stated intent (suggest separating or reverting)
- **EDR violations** — check findings against the EDR constraints gathered in Phase 2. Flag any that conflict with established standards.
- **Missing connections** — e.g., a new API endpoint with no corresponding frontend integration, or a schema change with no migration

### Severity calibration

To keep ratings consistent:
- **Blocker**: The PR should not merge without addressing this. Examples: data loss risk, security vulnerability, non-deterministic behavior visible to users, correctness bug that produces wrong results.
- **Improvement**: Worth fixing and low effort, but the PR is mergeable without it. Examples: missing test for a new code path, inconsistent error message format, minor code quality issue.
- **Follow-up**: Real issue but wrong scope for this PR. Examples: pre-existing tech debt exposed by the changes, architectural concern that requires its own design, missing feature that's adjacent to the PR's intent.

### Present and wait

Structure findings as:

```
### Tactical (fix in this PR)
1. [Blocker] {finding} — {effort estimate}
2. [Improvement] {finding} — {effort estimate}

### Systemic (follow-up work)
1. [Follow-up] {finding} — {suggested scope}

### EDR Observations
- {any violations or alignment notes from EDR checking}
```

Present findings and **wait for user feedback**. The user may:
- Confirm scope ("yes, fix the tacticals")
- Reclassify items ("move X to follow-up")
- Correct recommendations ("the migration should just fail, not silently delete")

Capture all corrections — they go into the artifact.

### Handoff suggestions

Based on findings, suggest logical next steps (only when warranted — skip if findings are minor):
- If the PR modifies **handler logic or business rules**: "Want me to have a **qa-expert** identify testing gaps?"
- If there are **systemic follow-ups**: "Want me to create Linear issues for the follow-up items?" (If yes, use the Linear MCP tools to create issues with appropriate labels and link them back to the PR.)
- If tactical fixes are **small**: "Want me to implement the tactical fixes now?"

## Phase 5: Artifact

Save the review to `docs/internal/analysis/`. The user can override the path.

**Path**: `docs/internal/analysis/pr-{number}-review.md`

### Template

```markdown
# PR #{number} Review: {title}

**Intent**: {confirmed motivation}
**Reviewed by**: {subagent list}
**EDRs checked**: {list of relevant EDRs, or "None applicable"}
**Date**: {date}

## Summary
{1-3 sentence overview of the PR and its alignment with stated intent}

## Tactical Fixes (this PR)

### Blockers
- {finding with rationale} — {effort estimate}

### Improvements
- {finding with rationale} — {effort estimate}

## Systemic Follow-ups (separate PRs)
- {finding with rationale and suggested scope}

## EDR Observations
- {violations, alignment notes, or "No violations found"}

## Corrections & Decisions
- {user corrections captured during the review}
```
