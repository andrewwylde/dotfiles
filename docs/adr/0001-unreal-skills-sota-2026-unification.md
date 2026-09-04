# Architecture Decision Record: Unified Unreal Engine 2026 SOTA Skill Suite

## Context

Our development team is transitioning to a first-party, unified Unreal Engine skill suite aligned with SOTA 2026 innovations. This ADR formalizes the consolidation of Unreal Engine skills under `ue-*` in `dotfiles/library/skills/`, with enhanced capabilities for MCP automation, action tiering, and engine integration.

## Decision

- **Unified Scope**: All 20 Unreal Engine skills will reside in `dotfiles/library/skills/ue-*` and fan out via `agent-sync` with the first-party prefix `andrew-ue-*`.
- **SOTA 2026 Integration**: MCP in-engine tool calls (e.g., `NiagaraMCPBridge`, `unreal-blueprint-mcp`), dual-control action tiering, and PCG supervision are codified in `ue-project-context`.
- **Action Tiering**: Three-tier architecture (Low-risk auto-exec, Medium-risk sandbox, High-risk dual-control confirmation) enforced across skills.
- **First-Party Ownership**: Maintains `ue-cpp-foundations`, `ue-actor-component-architecture`, and `ue-gameplay-abilities` as core pillars.

## Rationale

1. **Simplified Maintenance**: Consolidating legacy `unreal-*` skills into a single suite reduces duplication and improves discoverability.
2. **SOTA Alignment**: Leverage 2026 MCP capabilities for richer in-engine automation (e.g., procedural generation via PCG supervision, Niagara parameter streaming).
3. **Future-Proofing**: Action tiering prevents accidental high-risk changes in shared environments.
4. **Consistent Tooling**: Unified Macedon workflows across all skills enable faster agent integration.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Overenforcement of tiering | Provide opt-out mechanisms in `ue-project-context` |
| Performance overhead from MCP | Profile affected skills during benchmarks |
| Complexity of unified references | Implement type validation in validation tools |

## Next Steps

1. Generate `SKILL.md` for all 20 `ue-*` skills with validated frontmatter.
2. Migrate legacy `unreal-*` skills to new structure.
3. Implement dual-control UI in editor for high-risk actions.
4. Verify integration with `agent-sync` and `andrew-ue-*` fan-out.