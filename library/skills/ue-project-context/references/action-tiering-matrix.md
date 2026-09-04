# Unreal Engine SOTA 2026 Action Tiering & Dual-Control Matrix

Modern agentic development in Unreal Engine 5.8+ requires calibrated initiative and operational risk boundaries to prevent asset corruption, performance regressions, and broken serialization.

## Operational Risk Tiers

| Tier | Risk Profile | Execution Boundary | Agent Protocol | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Low Risk** | Read-only & Auditing | **Autonomous Execution** | Execute immediately; cache state in local context. | • Inspecting level geometry / scene graphs<br>• Reading dynamic reflection metadata & UPROPERTY tags<br>• Auditing Niagara particle count & pooling<br>• Querying CVar schemas & header definitions<br>• Inspecting Blueprint node connections via MCP IR |
| **Tier 2: Medium Risk** | Reversible In-Editor Mutation | **Sandboxed Execution** | Execute with local undo/redo transaction buffer. | • Modifying Material Instance parameters (scalar/vector)<br>• Reordering or adding modules to Niagara emitter stacks<br>• Adjusting actor transform coordinates in level blockouts<br>• Generating procedural PCG curve distributions<br>• Setting non-destructive component default values |
| **Tier 3: High Risk** | Destructive / Binary / Global Mutation | **Dual-Control Required** | **STOP & REQUIRE HUMAN CONFIRMATION** before applying changes to disk. | • Bulk deletion of assets or level actors<br>• Overwriting binary `.uasset` or `.umap` files directly<br>• Modifying `DefaultEngine.ini`, `Build.cs`, or global project settings<br>• Executing cooking or shipping packaging (`RunUAT BuildCookRun`)<br>• Committing directly to version control branches |

---

## Calibrated Initiative Hierarchy

```
[Level 1: Silent Monitoring]
    │  Agent passively tracks editor selection, active map, and context stack.
    ▼
[Level 2: Contextual Hints]
    │  Agent flags missing particle pooling, uncompressed textures, or broken soft references.
    ▼
[Level 3: Prefill Assistance]
    │  Agent drafts HLSL shader code, PCG rules, or C++ boilerplate for manual user trigger.
    ▼
[Level 4: Autonomous Execution]
       Agent executes validated Tier 1 and Tier 2 operations directly.
```

---

## Dual-Control Verification Flow for High-Risk Actions

When an agent needs to execute a **Tier 3 (High-Risk)** action:
1. **State Intent & Blast Radius**: Clearly describe what will change, which files/assets are affected, and why.
2. **Present Diff / Intermediate Representation**: Provide a structured preview (e.g. textual IR diff, JSON-RPC mutation preview, or C++ file diff).
3. **Obtain Explicit Human Sign-Off**: Wait for user approval before mutating disk state or binary assets.
4. **Post-Mutation Diagnostic Audit**: Immediately run diagnostic validation (compilation check, asset audit tool) to confirm engine stability.
