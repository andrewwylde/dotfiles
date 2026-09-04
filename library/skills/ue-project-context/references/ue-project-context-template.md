# Unreal Engine Project Context Template

```markdown
# UE Project Context: <ProjectName>

## Engine & Platform
- **Engine Version**: UE 5.4+ / UE 5.8+
- **Source Build vs Launcher**: Launcher / Custom Engine GitHub build
- **Target Platforms**: Windows / Linux / macOS / Dedicated Server / Mobile
- **RHI / Graphics API**: DirectX 12 / Vulkan / SM6
- **Ray Tracing / Lighting**: Lumen / Hardware Ray Tracing / Virtual Shadow Maps / Nanite

## Module Architecture & Plugins
- **Primary Runtime Modules**: `<MainGameModule>`
- **Editor Modules**: `<GameEditorModule>`
- **Enabled Plugins**:
  - `EnhancedInput` (Input management)
  - `Niagara` (VFX)
  - `GameplayAbilities` (GAS)
  - `ModelContextProtocol` / `NiagaraMCPBridge` / `unreal-blueprint-mcp` (Agentic automation)
  - `PCG` (Procedural Content Generation)

## Coding Conventions
- **Macro Style**: Modern `UPROPERTY()`, `UFUNCTION()`, `UCLASS(Blueprintable)`
- **Pointers**: `TObjectPtr<T>` for member variables, `TWeakObjectPtr<T>` for caching, `TSharedPtr<T>` for non-UObject Slate/C++ objects.
- **Includes**: IWYU strict, `.generated.h` always last.
- **Logging**: Dedicated `DECLARE_LOG_CATEGORY_EXTERN(LogGame, Log, All)`.

## Agent Governance & Action Tiering
- **Initiative Level**: Level 4 Autonomous for Tier 1 (audits/reads) and Tier 2 (sandboxed parameter tweaks).
- **Dual-Control Gate**: Required for all Tier 3 operations (asset deletion, binary `.uasset` overrides, config ini modifications, shipping builds).
- **RAG Verification**: Strict pre-flight verification against local engine headers before emitting C++ reflection macros or CVars.
```
