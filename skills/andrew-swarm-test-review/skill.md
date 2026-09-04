---
name: swarm-test-review
description: Conduct multi-agent test coverage audits using parallel subagent swarms. Analyzes code changes or modules for testing gaps, enforces industry-standard testing strategy, and produces a structured artifact with prioritized coverage recommendations. Use when reviewing test coverage, auditing test quality, when the user mentions test review, coverage audit, testing gaps, or swarm test. Also trigger when the user asks about insufficient test coverage or wants to ensure code is properly tested before merge.
---

# Swarm Test Review

Multi-agent test coverage audit that evaluates code against an industry-standard testing strategy, identifies gaps across the testing pyramid, and produces a prioritized remediation plan.

## Quick Mode

For small scopes (**<200 lines of production code, single package**), skip the full subagent swarm. Instead:
1. Gather context (Phase 1)
2. Analyze existing tests yourself against the testing strategy in [testing-strategy.md](testing-strategy.md)
3. Produce the artifact (Phase 5)

Mention that you're using quick mode: "This is a small, single-package scope — I'll audit test coverage directly instead of launching a subagent swarm."

## Phase 1: Scope Discovery

Determine what code needs test coverage analysis. The skill supports three modes:

### PR Mode (most common)
Triggered when the user provides a PR number or URL.

1. `gh pr view <number> --json title,body,files` — file list
2. `gh pr diff <number>` — full diff
3. Identify **production code** (non-test files) in the diff — these are the audit targets
4. Identify **test files** in the diff — these are what's been provided so far

### Branch/Directory Mode
Triggered when the user points at a branch, directory, or set of files.

1. Identify all production code in scope
2. Identify corresponding test files (by convention: `_test.go`, `*.test.ts`, `test_*.py`, etc.)
3. Note any production files with no corresponding test file at all

### Post-Implementation Mode
Triggered when the user just finished implementing something and wants coverage validated.

1. Use `git diff --name-only HEAD~N` or `git diff main...HEAD --name-only` to find changed files
2. Separate production code from test code
3. Focus on newly added or significantly changed functions/methods

## Phase 2: Codebase Analysis

Before launching subagents, understand the testing landscape:

1. **Identify the tech stack** — scan changed files to determine languages and frameworks (Go, TypeScript, Python, Svelte)
2. **Find existing test patterns** — read 1-2 existing test files in the same package to understand conventions (test framework, assertion style, fixture patterns, mocking approach)
3. **Map the testing pyramid** for the scope:
   - Which functions/methods have unit tests?
   - Which integration points are tested?
   - Are there contract/API-level tests?
   - Are error paths covered?

4. **Assess structural coverage signals**:
   - Functions/methods with no test at all
   - Test files that exist but only test the happy path
   - Complex branching logic (if/switch) with partial coverage
   - Error handling paths (`if err != nil`, `catch`, `except`) without tests
   - Public API surface without contract tests

## Phase 3: Subagent Swarm

### Selecting agents

**If the user specified agents**, use those directly.

**If the user didn't specify**, select based on the code's domain and language:

| Code domain | Suggested agents | Each agent's testing lens |
|---|---|---|
| Go backend / API handlers | `qa-expert`, `golang-pro`, `test-automator` | Coverage strategy + gap identification; Go testing idioms + table-driven tests; test architecture + framework patterns |
| Go infrastructure / pkg | `qa-expert`, `golang-pro`, `security-engineer` | Coverage completeness; concurrency + error path testing; security-critical path coverage |
| TypeScript / frontend | `qa-expert`, `typescript-pro`, `frontend-developer` | Coverage strategy; type-level testing + mocking patterns; component testing + interaction coverage |
| Python services | `qa-expert`, `python-pro`, `test-automator` | Coverage strategy; pytest idioms + fixture patterns; test automation + parametrization |
| Database / migrations | `qa-expert`, `database-administrator`, `sql-pro` | Migration test coverage; schema validation tests; query correctness tests |
| API surface / schema | `qa-expert`, `api-designer`, `test-automator` | Contract test coverage; endpoint validation; integration test patterns |
| Mixed / cross-cutting | `qa-expert` + 2 domain-specific agents | Always include qa-expert for mixed scopes |

**Always include `qa-expert`** — it provides the strategic testing lens that domain-specific agents lack.

For **mixed-language changes**, pick the top 3-4 agents. More than 4 has diminishing returns.

Present: "For this code I'd launch **qa-expert**, **golang-pro**, and **test-automator**. Want to adjust?"

### Preparing subagent prompts

Each subagent gets a tailored prompt. Use this structure:

```
## Context
[What the code does, which module/package, 2-3 sentences about the feature]

## Testing Strategy Requirements
[Include the relevant sections from testing-strategy.md — the testing
pyramid level expectations, coverage requirements, and anti-patterns
that apply to this agent's domain.]

## Code Under Review
[Production code to analyze — the functions, methods, types that need
test coverage. Include enough context to understand branches, error
paths, and edge cases.]

## Existing Tests
[Any tests that already exist for this code. Include full test code
so the agent can assess what IS covered vs what's missing.]

## Focus Areas
[3-5 domain-specific questions using the lens from the agent selection
table. Frame as questions, not instructions.]

## Gap Classification
Classify each finding as:
- **Critical Gap**: Core business logic, security path, or data integrity
  code with zero test coverage. Must have tests before merge.
- **Missing Coverage**: Important code path without tests — error handling,
  edge cases, boundary conditions. Should have tests.
- **Weak Coverage**: Tests exist but are superficial — only happy path,
  no edge cases, no error scenarios. Improve before or after merge.
- **Enhancement**: Test quality improvements — better assertions, clearer
  test names, fixture reuse, parametrization. Nice to have.

For each gap, specify:
1. What production code is untested
2. What test(s) should be written (brief description, not full implementation)
3. Which testing pyramid level the test belongs to (unit/integration/contract/e2e)
```

Launch all subagents in parallel using the Task tool.

For a complete example prompt, see [prompt-example.md](prompt-example.md).

## Phase 4: Synthesis

After subagents return, synthesize a unified test coverage report.

### Merge findings

1. **Deduplicate** — agents often identify the same untested code from different angles. Merge into one gap with the strongest rationale.
2. **Classify** — apply the gap classification framework consistently.
3. **Estimate effort** — for each gap, estimate test writing effort (e.g., "1 table-driven test, ~10 min" or "integration test with DB setup, ~30 min").
4. **Rank** — within each classification, order by risk (what's the blast radius if this code breaks in production?).

### Cross-cutting analysis

After merging subagent findings, do your own pass:
- **Testing pyramid balance** — is the overall test distribution healthy? Too many unit tests with no integration coverage? All e2e with no unit tests?
- **Structural gaps** — public API functions with no tests at all
- **Error path coverage** — are `if err != nil` / `catch` / `except` blocks tested?
- **Concurrency coverage** — concurrent code without race condition tests
- **State mutation coverage** — database writes, cache updates without verification tests
- **Boundary conditions** — empty inputs, nil/null, max values, Unicode, special characters
- **Negative testing** — do tests verify what the code should NOT do?

### Coverage scoring

Assign an overall coverage health score:

| Score | Meaning | Criteria |
|---|---|---|
| **A** | Production-ready | No critical gaps, ≤2 missing coverage items, good pyramid balance |
| **B** | Acceptable | No critical gaps, some missing coverage, minor pyramid imbalance |
| **C** | Needs work | 1-2 critical gaps OR >5 missing coverage items |
| **D** | Insufficient | 3+ critical gaps, significant untested business logic |
| **F** | No meaningful coverage | Core functionality untested, tests are cosmetic |

### Convert to implementation steps

Transform the classified findings into an ordered implementation plan. Group by:

1. **Test infrastructure** — mock structs, test helpers, fixture factories needed before any tests can be written. Specify which package needs them, which existing file to follow as a pattern, and exactly which repository interfaces to mock.
2. **Pure function tests** — functions with no dependencies (validators, normalizers, mappers). These have the highest ROI per line of test code. Specify exact file to create and table-driven test cases as a list.
3. **State transition / mutation tests** — handlers that change state (create, update, status transitions). Specify the complete status matrix (which initial states are valid, which are rejected).
4. **Read endpoint tests** — handlers that query data (GET, LIST). Lower blast radius but important for tenant isolation and pagination correctness.
5. **Frontend tests** — constants exhaustiveness, query option configuration, component rendering. Separate from backend since they have zero dependencies on each other.

For each step, specify:
- **File to create or modify** (full relative path)
- **Pattern to follow** (path to an existing test file in the same package)
- **Test cases** as a concrete bullet list (test name + what it asserts)
- **Dependencies** on earlier steps (e.g., "requires mock from step 1")

### Present and wait

Present a brief human-readable summary (score + top findings), then say: "The full implementation plan is in the artifact at `{path}`. Want me to implement it now, or send it to a cloud agent?"

**Wait for user feedback.** The user may:
- Accept all recommendations
- Deprioritize items ("skip the enhancements")
- Add context ("that function is being deprecated, skip it")
- Request implementation ("write the critical gap tests for me")

### Handoff suggestions

Based on findings:
- If there are **critical gaps**: "Want me to implement the critical gap tests now?"
- If the score is **C or below**: "Want me to create a test improvement plan as a follow-up Linear issue?"
- If there are **security-related gaps**: "Want me to have a `security-engineer` audit the security test coverage specifically?"

## Phase 5: Artifact

Save the test coverage report to a worktree-based directory at the repo root. The user can override the path.

### PR Mode path
`.worktrees/swarm-review-pr-{number}/test-review.md`

### Branch/Directory Mode path
`.worktrees/swarm-review-{scope-slug}-{date}/test-review.md`

Create the directory if it doesn't exist. This directory is gitignored (`*worktrees*`).

### Template

The artifact has two sections: a human-readable summary and an agent-executable implementation plan. The implementation plan is the primary output — it must be structured so that an agent (or a human) can execute it step-by-step without re-analyzing the codebase.

````markdown
# Test Coverage Audit: {title or scope}

**Score**: {A-F}
**Scope**: {PR number, branch, or directory}
**Audited by**: {subagent list}
**Date**: {date}

## Summary

{2-3 sentence overview of coverage health and key findings}

## Testing Pyramid Assessment

| Level | Existing | Recommended | Gap |
|---|---|---|---|
| Unit | X | Y | Z needed |
| Integration | X | Y | Z needed |
| Contract/API | X | Y | Z needed |
| E2e | X | Y | Z needed |

---

## Implementation Plan

Read this document fully before starting. Execute steps in order —
later steps depend on infrastructure from earlier ones.

### Conventions

- {language}: {test framework, assertion style, patterns}
- {language}: {test framework, assertion style, patterns}
- Pattern references: read the referenced file before writing tests
  in that package to match local conventions.
- Run `{test command}` after each step to verify.

### Step 1: {Package} test infrastructure

> **Creates**: `{relative/path/to/test_helpers_test.go}`
> **Pattern**: `{relative/path/to/existing/test_helpers_test.go}`
> **Depends on**: nothing

{What to build and why, in 2-3 sentences.}

Mock repositories needed:
- `mock{Entity}Repo` — implements `{Interface}` with overridable `GetOneFunc`, `FindManyFunc`, `CreateOneFunc`, `UpdateOneFunc`
- `mock{Entity}DB` — wraps `NoOpDatabase`, overrides `Get{Entity}Repository()` to return the mock

Context helpers needed:
- `test{Package}Context(db)` — returns context with mock DB, test user ID, test tenant ID
- `testImplementation()` — returns `&Implementation{Logger: testLogger}`

### Step 2: {Description — e.g., "Pure function tests"}

> **Creates**: `{relative/path/to/file_test.go}`
> **Pattern**: `{relative/path/to/existing_similar_test.go}`
> **Depends on**: Step 1

**`Test{FunctionName}`** — table-driven, {N} cases:
- `"{case_name}"` — input: `{input}` → expected: `{output}`
- `"{case_name}"` — input: `{input}` → expected: `{output}`
- ...

**`Test{FunctionName2}`** — table-driven, {N} cases:
- `"{case_name}"` — `{EnumValue}` → `{expected_bool}`
- ...

### Step 3: {Description — e.g., "CreateFoo handler tests"}

> **Creates**: `{relative/path/to/file_test.go}` (append to file from Step 2, or new file)
> **Pattern**: `{relative/path/to/existing_handler_test.go}`
> **Depends on**: Step 1

**`Test{HandlerName}_HappyPath`** — valid input → created with correct status, verify fields
**`Test{HandlerName}_EmptyName`** — empty input → `BadRequestError`
**`Test{HandlerName}_DuplicateDetection`** — existing non-terminal match → returns existing, no create
**`Test{HandlerName}_DBError`** — mock returns error → wrapped error propagated
...

{Continue with steps 4, 5, ... for remaining test groups.
Each step follows the same structure: Creates/Pattern/Depends on header,
then concrete test case bullets.}

### Step N: {Frontend tests — if applicable}

> **Creates**: `{relative/path/to/file.test.ts}`
> **Pattern**: `{relative/path/to/existing.test.ts}`
> **Depends on**: nothing (independent of backend steps)

**`describe('{module}')`**:
- `it('{test description}')` — {what it asserts}
- `it('{test description}')` — {what it asserts}
- ...

## Corrections & Decisions

- {any user corrections or deprioritization decisions}
````
