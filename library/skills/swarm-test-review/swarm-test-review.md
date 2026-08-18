# Testing Strategy Reference

Industry-standard testing expectations used by the swarm-test-review skill. Subagent prompts reference specific sections of this document.

## The Testing Pyramid

The testing pyramid defines the ideal distribution of test types. Higher levels exercise more of the system and catch integration issues, but are slower, more expensive to maintain, and more prone to flakiness. Lower levels give higher-fidelity signals about specific behavior.

```
           /   E2E   \          ~5% of tests — full system, real browser/API
          /  Contract  \        ~10% — API boundary, schema compliance
         / Integration  \      ~20% — cross-module, real DB, real services
        /     Unit       \     ~65% — isolated functions, fast, focused
       / Static Analysis  \    Continuous — type-checking, linting, compilation
```

> Percentages are approximate targets by **test case count**, not engineering effort. Integration and E2E tests typically require more effort per test to write and maintain than unit tests.

### Static Analysis (foundation — not counted in percentages)

**What it covers**: Type errors, unreachable code, unused variables, import issues, formatting violations. The cheapest defect prevention layer — catches entire classes of bugs before any test runs.

**Go**: `go vet`, `golangci-lint` (enforced in CI).
**TypeScript**: `tsc --noEmit`, ESLint.
**Python**: `ruff`, `mypy`.

Agents should credit static analysis when evaluating overall defect prevention, but it does not substitute for behavioral tests.

### Unit Tests (~65% of test cases)

**What they cover**: Individual functions, methods, and types in isolation.

**Requirements**:
- Every public function/method should have at least one test (excluding generated code — see note below)
- Every branch in business logic should be exercised (if/else, switch cases)
- Every error return should be tested
- Use mocks/stubs for **slow or non-deterministic** dependencies (network, filesystem, external APIs). Prefer real in-process collaborators when feasible — mock boundaries, not internals.
- Tests should be fast (<100ms each) and deterministic
- Total unit test suite for a package should complete in seconds, not minutes
- Exclude generated code (`platform-schemas/dist/`, files marked `DO NOT EDIT`) from coverage requirements and test obligations. Test the generator, not its output.

**Go specifics**: Table-driven tests, `testify/require` + `testify/assert`, interface-based mocking, `t.Parallel()` where safe.

**TypeScript specifics**: Vitest/Jest, `describe`/`it` blocks, `vi.mock` for module mocking, async/await test patterns.

**Python specifics**: pytest, `@pytest.mark.parametrize`, fixture composition via `conftest.py`, `unittest.mock.patch`.

### Integration Tests (~20% of test cases)

**What they cover**: Interactions between modules, real database operations, service-to-service calls within the same process.

**Requirements**:
- Handler + DB round-trip tests (create → read → verify state)
- Transaction rollback behavior
- Concurrent access patterns (where applicable)
- External service integration (with test doubles or containers)

**Go specifics**: Build tag `//go:build integration`, test database via `TEST_DATABASE_URL` environment variable (set up by docker-compose or CI), `httptest.NewServer`/`httptest.NewRecorder` for handler tests, transaction-scoped test isolation where practical.

**TypeScript specifics**: Vitest with jsdom for server-side logic (`*.server.test.ts`), Playwright for browser-level integration. The SvelteKit BFF proxies to Go APIs — test the proxy layer and data transformations, not HTTP handlers directly.

**Python specifics**: `@pytest.mark.integration`, docker-compose fixtures, `pytest-asyncio` for async.

### Contract Tests (~10% of test cases)

**What they cover**: API boundaries — request/response shapes, validation behavior, error formats.

**Requirements**:
- Input validation rejects malformed requests
- Response shapes match documented API contract
- Error responses follow the project's error format
- Status codes are correct for each scenario

This codebase has two distinct contract testing patterns:

1. **API contracts** (Go services): Request/response shapes, validation behavior, error formats for REST endpoints. Tested via `httptest` with schema assertions.
2. **Data pipeline contracts** (Python transformation-flows): Schema compliance, checkpoint formats, envelope validation, bucket alignment. These verify that data flowing between pipeline stages conforms to agreed schemas. Tested via dedicated contract suites with YAML fixtures.

Both are critical — API contracts protect external consumers; pipeline contracts protect data integrity across asynchronous boundaries.

### E2E Tests (~5% of test cases)

**What they cover**: Full user flows through the system.

**Requirements**:
- Critical happy paths (signup, core feature, payment)
- Auth flows (login, session management, permission boundaries)
- Data integrity across service boundaries

**Tooling**: Playwright for browser E2E (SvelteKit web-app), pytest with docker-compose for backend pipeline E2E (ingestion → transformation flows). E2E tests should use dedicated CI workflows with longer timeouts.

## Advanced Testing Techniques

These complement the pyramid and are especially valuable for high-blast-radius code (auth, billing, data mutations).

### Fuzz Testing

Automatically generates randomized inputs to find crashes, panics, and edge cases that hand-written tests miss. Prioritize for parsers, validators, and serialization code.

**Go**: Native fuzz support via `testing.F`. Write `FuzzXxx` functions in `_test.go` files. Run with `go test -fuzz=FuzzXxx`. Target scalar validation (`ValidateEmail`, `ValidateSlug`, etc.), JSON parsing, and config deserialization.

**Python**: Use `hypothesis` for property-based fuzz-like testing of data transformation logic.

### Property-Based Testing

Define invariants and let the framework generate hundreds of inputs automatically. Use when:
- A function has a clear contract (e.g., "encoding then decoding returns the original value")
- Input space is large and edge cases are hard to enumerate
- Data transformation pipelines must preserve invariants

**Go**: `pgregory.net/rapid` — stateful property testing with automatic shrinking.
**TypeScript**: `fast-check` — integrates with Vitest, supports async properties.
**Python**: `hypothesis` — mature, integrates with pytest, supports complex data strategies.

### Mutation Testing

Measures test *effectiveness* by introducing small code changes (mutants) and checking whether tests detect them. A test suite with high coverage but low mutation score has weak assertions.

**TypeScript**: Stryker Mutator — supports Vitest, incremental mode for CI.
**Go**: Gremlins — supports CI gating, can scope to PR-changed files.
**Python**: mutmut — integrates with pytest.

Use mutation testing selectively on high-blast-radius code rather than across the entire codebase.

## Coverage Requirements by Code Category

Not all code deserves equal test investment. Prioritize by blast radius.

| Category | Min Coverage | Rationale |
|---|---|---|
| **Auth / permissions** | 95%+ | Security-critical; bypass = breach |
| **Financial / billing** | 95%+ | Incorrect calculations = revenue loss |
| **Data mutations** (create, update, delete) | 90%+ | Data loss/corruption risk |
| **Business logic / domain rules** | 85%+ | Core value; bugs = incorrect behavior |
| **API handlers** | 80%+ | Public surface; user-facing errors |
| **Data transformations** | 80%+ | Silent corruption risk |
| **Configuration / startup** | 60%+ | Fails loudly; lower silent-failure risk |
| **Logging / observability** | 40%+ | Low blast radius; test format not content |
| **Generated code** | 0% | Tested by the generator; don't test downstream |

> **Coverage metric caveat**: Line coverage measures which lines were *executed*, not which behaviors were *verified*. A test that executes code without meaningful assertions inflates coverage without adding confidence. Agents should evaluate assertion quality alongside line coverage — consider recommending mutation testing for critical paths where coverage is high but assertion quality is uncertain.

## CI Coverage Enforcement

Coverage thresholds should be enforced in CI, not just documented.

**Go**: `go test -race -coverprofile=coverage.out ./...` — always include `-race` to detect data races. Parse coverage output and fail if any package drops below threshold.

**Python**: `pytest --cov=src --cov-fail-under=80` — pytest-cov natively supports threshold gating.

**TypeScript**: Configure Vitest's `coverage` option with `thresholds: { lines: 80, branches: 80 }` — Vitest fails the run if thresholds are not met.

Apply stricter thresholds to auth/permission packages and business logic, looser thresholds to configuration and observability code.

## What MUST Be Tested

The guiding principle is Google's Beyoncé Rule: **"If you liked it, then you shoulda put a test on it."** If a system behavior matters — correctness, performance, security, failure handling — the only way to be confident it works is an automated test.

These patterns are non-negotiable. Code with these patterns and no tests is a **Critical Gap**.

### Error paths
Every `if err != nil`, `catch`, `except` that changes control flow must have a test that triggers it.

### Permission / authorization checks
Every permission gate must be tested with both authorized and unauthorized callers.

### Data validation
Every validation rule (beyond what the framework handles) needs a test with valid and invalid input.

### State transitions
Every status change, workflow step, or state machine transition needs a test verifying the before/after state.

### External service calls
Every call to an external service needs a test verifying:
- Success behavior
- Failure/timeout behavior
- Retry behavior (if applicable)

### Concurrent operations
Any code using goroutines, channels, locks, async/await, or shared mutable state needs a test exercising the concurrent path.

### Database migrations
Every migration must be validated with `squawk` before commit (per project convention). Migration tests should verify:
- Up migration applies cleanly to the current schema
- Down migration reverses changes without data loss (where applicable)
- Data migrations transform existing rows correctly

## Test Input Selection

When choosing test inputs, apply these techniques systematically rather than picking arbitrary values.

### Boundary Value Analysis
Test at the edges of valid ranges: zero, one, max, max+1, empty string, single character, max-length string. Most bugs cluster at boundaries.

### Equivalence Partitioning
Group inputs into classes that should behave identically. Test one representative from each class. Key partitions: valid inputs, invalid inputs, empty/nil/null, typical values.

### Negative Testing
Verify the system correctly rejects invalid operations: duplicate keys, out-of-range values, unauthorized access attempts, malformed payloads, SQL injection strings, oversized inputs.

### Special Values
Always test: `nil`/`null`/`undefined`, empty string `""`, zero `0`, negative numbers, Unicode (emoji, RTL text, zero-width characters), very long strings, concurrent duplicate submissions.

## Testing Anti-Patterns

Flag these when found in existing tests.

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| **Happy-path-only tests** | Misses the error paths where bugs live | Add error case for every branch |
| **Assert on implementation** | Tests break on refactors without bugs | Assert on behavior and output |
| **Shared mutable state** | Tests fail intermittently, order-dependent | Isolated setup per test |
| **Sleep-based synchronization** | Flaky, slow, hides race conditions | Use channels, waitgroups, polling with timeout |
| **Snapshot overuse** | Large snapshots mask regressions | Targeted assertions on specific fields |
| **Comment `// TODO: add test`** | Tests never get written | Write the test now or file a tracked issue |
| **Catch-all error assertion** | `assert.Error(t, err)` passes for any error | Assert specific error type or message |
| **Mock everything** | Tests verify mock wiring, not behavior | Mock boundaries only; test real logic |
| **Giant test functions** | Hard to diagnose failures, poor isolation | Table-driven subtests with clear names |
| **Testing generated code** | Wastes effort; generator already validates | Skip generated files entirely |
| **Flaky tests left unfixed** | Erodes trust in the entire suite; teams stop investigating failures | Fix immediately, quarantine if non-trivial, track as tech debt |
| **Coverage without assertions** | High coverage with weak assertions gives false confidence | Use mutation testing on critical paths to verify assertion quality |
| **No `-race` flag in Go CI** | Data races cause intermittent production crashes | Always run `go test -race` in CI |
| **No coverage gating** | Coverage ratchet degrades silently over time | Enforce `--cov-fail-under` (Python), coverage thresholds (Go), Vitest `coverage.thresholds` (TS) in CI |

## Flaky Test Management

Flaky tests — tests that pass and fail non-deterministically — erode CI trust and slow delivery. Google's research shows that ~1.5% of test runs are flaky and ~84% of retried failures are flakes.

**Detection**: Run newly added tests at least 10 times before merging to the main CI path. Flag tests that fail even once for review.

**Quarantine**: When a test flakes in CI, move it to a quarantine suite that runs separately. File a tracked issue. Do not delete or skip without resolution.

**Budget**: Target <1% flake rate across all CI runs. Track the flake rate weekly.

**Root causes to investigate**:
- Port/resource conflicts from parallel test execution
- Time-dependent assertions (`time.Now()` in tests — inject clocks instead)
- Uncleared global state between test runs
- Network calls to external services without mocking

## Test Parallelization

Fast CI feedback requires intentional parallelization.

**Go**: Use `t.Parallel()` in unit tests that don't share state. Set `-parallel=N` for per-package concurrency and `-p=M` for cross-package concurrency. Integration tests sharing a database should not use `t.Parallel()` unless they use transaction isolation.

**Python**: Use `pytest-xdist` with `-n auto` for unit tests. Use `--dist loadscope` for integration tests to keep tests in the same module together (shared fixtures). Avoid `-n` for E2E tests that share external state.

**TypeScript**: Vitest runs test files in parallel by default. Use the `concurrent` modifier for individual async tests within a file. Set `maxWorkers` to control resource usage in CI.

## Properties of Good Tests

A well-written test exhibits these properties (adapted from Kent Beck's Test Desiderata):

- **Deterministic**: Same result every run, no flakiness
- **Fast**: Unit tests <100ms, total package suite in seconds
- **Isolated**: No dependency on test execution order or shared state
- **Specific**: When it fails, the cause is obvious from the test name and assertion message
- **Behavioral**: Tests what the code *does*, not how it's structured internally
- **Readable**: A new engineer can understand the test's intent without reading the implementation
