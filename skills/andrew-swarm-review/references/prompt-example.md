# Subagent Prompt Example

A complete, realistic prompt for a `golang-pro` agent reviewing a PR that adds a new connector status endpoint.

**Excerpt policy**: This example shows focused hunks (new handler, changed service method, route line) — not full source files. In production, wrap each hunk with ±50 lines of padding and merge overlapping windows. EDR text is a digest of extracted sections, not full `.mdx` files.

---

## Context

PR #347 adds a `GET /api/v1/connectors/{id}/status` endpoint that returns the current connector status and last sync timestamp. The intent is to give the dashboard a lightweight polling endpoint instead of fetching the full connector object. The PR touches the handler, a new service method, and a SQL query.

## Codebase Conventions

From EDR-0002 (API Design Standards):
- All API handlers must return structured error responses using `apierror.New()`
- Handler functions live in `internal/api/handlers/` grouped by domain
- Request validation uses the `validate` package, not manual checks

From EDR-0011 (Error Codes):
- Every error response must include a machine-readable `code` field from the error code registry
- New error codes must be registered in `internal/apierror/codes.go`

From EDR-0004 (Connector Lifecycle):
- Connector status is derived from the state machine in `internal/connector/status.go`
- Direct DB reads of status columns are discouraged — use `StatusResolver.Current()` which accounts for in-flight syncs

## Code to Review

### Handler — `internal/api/handlers/connector_status.go` (new file)

```go
package handlers

func (h *ConnectorHandler) GetStatus(w http.ResponseWriter, r *http.Request) {
    connectorID := chi.URLParam(r, "id")
    if connectorID == "" {
        http.Error(w, "missing connector id", http.StatusBadRequest)
        return
    }

    status, err := h.service.GetConnectorStatus(r.Context(), connectorID)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    render.JSON(w, r, status)
}
```

### Service — `internal/connector/service.go` (added method)

```go
func (s *Service) GetConnectorStatus(ctx context.Context, id string) (*StatusResponse, error) {
    var resp StatusResponse
    err := s.db.QueryRowContext(ctx,
        "SELECT status, last_sync_at FROM connectors WHERE id = $1", id,
    ).Scan(&resp.Status, &resp.LastSyncAt)
    if err != nil {
        return nil, err
    }
    return &resp, nil
}
```

### Route registration — `internal/api/router.go` (added line)

```go
r.Get("/connectors/{id}/status", h.GetStatus)
```

## Focus Areas

1. Does the error handling in the handler follow project conventions (structured errors via `apierror.New()`)?
2. Is the direct SQL query for status appropriate, or should it use `StatusResolver.Current()` per EDR-0004?
3. Is the `connectorID` parameter validated beyond emptiness (UUID format, length)?
4. Are there missing edge cases — e.g., connector not found vs. DB error?
5. Does the response shape match existing API patterns in the codebase?

## Evidence rules

- Mark claims as OBSERVED (from provided excerpts) vs INFERRED.
- Do NOT file BLOCKER/Required findings that depend on runtime, migration apply
  order, or framework cache semantics unless this prompt includes runtime
  evidence. Otherwise mark as Needs runtime verification.
- Example code here is illustrative unless labeled OBSERVED.

## Severity Framework

Flag each issue as:
- **Blocker**: Must fix before merge (data loss, security, correctness bugs)
- **Improvement**: Should fix, low effort (code quality, consistency, missing guards)
- **Follow-up**: Systemic issue for a separate PR (architecture, tech debt, missing tests)
