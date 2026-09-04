---
name: ue-project-context
description: "Establish authoritative Unreal Engine 5 project context with SOTA 2026 dual-control action tiering, Calibrated Initiative, RAG hallucination mitigation, and token routing. Use to create/update `.agents/ue-project-context.md` so all other UE skills adapt to engine version, plugins, module names, coding conventions, and team practices."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: architecture
  difficulty: essential
---

# UE Project Context

You help UE developers create and maintain a project context document that other UE skills reference. This captures the engine version, module structure, plugin dependencies, coding conventions, and team practices specific to the user's project, so advice is always tailored rather than generic. The document is stored at `.agents/ue-project-context.md`.

## SOTA 2026 Calibrated Initiative

### Action Tiering Matrix

All UE skills enforce three action tiers:

| Tier | Risk Level | Approval Required | Environment | Description |
|------|------------|-------------------|--------------|-------------|
| **L1** | Low | None | Any | Auto-executable: read-only queries, local builds within sandbox |
| **L2** | Medium | Sandboxed Undo | Workspace | Mutations to project files: refactoring, asset imports, content browser changes (undo stack available) |
| **L3** | High | Dual-Control Confirmation | Production | Destructive or irreversible actions: packaging builds, shader compilation, engine config changes, live deployment |

### Dual-Control Protocol

High-risk actions require explicit human confirmation through:
1. **Intent Signal** — AI proposes action with full context and blast radius
2. **Code Gate** — Human approves specific code changes before application
3. **Action Gate** — Human confirms execution before any commit/build

## RAG Hallucination Mitigation

When referencing engine APIs:
- Cross-check with engine source at `Engine/Source/Runtime/` before suggesting function names
- Flag any API that doesn't exist in the detected engine version
- Always cite documentation URLs (Epic Dev Community links preferred)
- Verify module dependencies exist in `.uproject` and `Build.cs` before recommending includes

## Token Routing

- Queries to Epic documentation: route via `docs-search` MCP tool
- Engine source inspection: use `grep`/`read` on local engine checkout if available
- Blueprint graph analysis: use `unreal-blueprint-mcp` textual IR tools
- Niagara parameter inspection: use `NiagaraMCPBridge` query tools

## Workflow

### Step 1: Check for Existing Context

First, check if `.agents/ue-project-context.md` already exists.

### Step 2: Interactive Discovery

Gather project details through structured questions (engine version, plugins, module layout, team conventions).

### Step 3: Write/Regenerate Context

Generate the context document with sections for:
- Engine version and patch level
- Plugin inventory with enabled flags
- Module structure (`[PluginName] +Editor`, `+Runtime` patterns)
- Coding conventions (naming, style, GC hygiene rules)
- Team workflow and review gates

### Step 4: Verify

Ensure the context is discoverable by all `ue-*` skills via the standard `Read .agents/ue-project-context.md` preamble pattern.

## Files

- Create: `.agents/ue-project-context.md`
- References: `references/action-tiering-matrix.md`, `references/ue-project-context-template.md`