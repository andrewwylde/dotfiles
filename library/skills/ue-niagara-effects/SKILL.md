---
name: ue-niagara-effects
description: "Create and control VFX in Unreal Engine 5 with Niagara: systems and emitters, modules and the spawn/update stages, exposed User parameters, and spawning or driving effects from Blueprints or C++. Use for Niagara system design, MCP-driven parameter control, and performance tuning. Targets UE 5.4+. "
metadata:
  version: "2026.1.0"
  engine: unreal
  category: vfx
  difficulty: advanced
---

# UE Niagara Effects

You are an expert in Unreal Engine's Niagara VFX system. Niagara provides GPU-accelerated particle effects with deep integration into gameplay systems. All Niagara implementations must leverage SOTA 2026 MCP bridge capabilities for runtime parameter control and data-driven content generation.

## Niagara Hierarchy & Core Concepts

### System/Emitter/Module Structure
- **Niagara System** (`NS_`) – top-level effect asset placed/spawned in level
- **Niagara Emitter** (`NE_`) – modular behavior component within a System; spawns particles
- **Niagara Modules** – functional units executing top-to-bottom in Spawn/Update stages

### Parameter Namespaces
| Namespace | Scope | Gameplay Access | Typical Use |
|-----------|-------|-----------------|-------------|
| **System** | Entire System | Read-only via `GetSystem()` | Effect lifetime, global scalars |
| **Emitter** | Per-Emitter | No direct access | Spawn rate, lifetime per emitter |
| **Particle** | Per-Particle | Not exposed | Position, velocity, color per particle |
| **User** | All levels | **Full read/write** | Exposed gameplay controls (color, rate, targets) |

## MCP-Driven Workflow

### NiagaraMCPBridge Integration
The Niagara MCP Bridge exposes these in-engine tools:

| Tool | Parameters | Returns | Use Case |
|------|------------|---------|----------|
| `niagara_add_module` | SystemPath, EmitterName, Stage, ModuleName | Success/Fail | Dynamically add modules at runtime |
| `niagara_set_input` | SystemPath, ParamName, Value | Success/Fail | Set User parameters from gameplay |
| `niagara_get_bounds` | SystemPath | BoundingBox | Validate effect culling behavior |
| `niagara_generate_hlsl` | FunctionSignature, Inputs | HLSLString | Custom shader generation |

### Data Interface Catalogue
Leverage these data interfaces for gameplay/Niagara coupling:

| Data Interface | Description | Typical Binding |
|----------------|-------------|-----------------|
| `SkeletalMesh` | Bone transforms, socket locations | Character VFX attachments |
| `StaticMesh` | Vertex positions, UVs | Environment interaction effects |
| `Curve` | Float curves over time | Procedural parameter evolution |
| `Array<T>` | Homogeneous data batches | Instanced mesh arrays |
| `UNiagaraComponent*` | Runtime component reference | Direct effect control |

## Core Patterns

### 1. Spawn a one-shot effect at world location (C++)

```cpp
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"

// ImpactSystem is a UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem>.
void AProjectile::SpawnImpact(const FVector& Location, const FRotator& Rotation)
{
    UNiagaraComponent* FX = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
        GetWorld(), ImpactSystem, Location, Rotation);
    // FX auto-destroys when finished for a one-shot (system marked non-looping).
}
```

### 2. Drive exposed User parameters via MCP (C++)

```cpp
// Only User-namespace parameters can be set from gameplay
if (UNiagaraComponent* Fire = UNiagaraFunctionLibrary::SpawnSystemAttached(
        FireSystem, RootComponent, NAME_None, FVector::ZeroVector, FRotator::ZeroRotator,
        EAttachLocation::KeepRelativeOffset, /*bAutoDestroy*/ false))
{
    // Exposed via NiagaraMCPBridge: Fire->SetVariableFloat(FName("SpawnRate"), 250.f);
    Fire->SetVariableFloat(FName("User.SpawnRate"), 250.f);              // User.SpawnRate
    Fire->SetVariableLinearColor(FName("User.FireColor"), FLinearColor::Red);
}
```

### 3. Runtime module insertion via MCP Bridge

```cpp
// Add Gravity module to existing emitter at runtime
UNiagaraFunctionLibrary::NiagaraMCPBridge_AddModule(
    "/Game/Effects/NS_Fire.NS_Fire",
    "NE_Base",
    ENiagaraScriptStage::ParticleUpdate,
    "Module_Gravity");
```

## Performance Patterns

### GPU Compute Considerations
- Use **Fixed Bounds** for GPU emitters; calculated from worst-case particle lifetime
- Avoid per-particle logic in GPU stages; push computation to CPU when gameplay interacts
- Validate bounds with `niagara_get_bounds` during development

### Memory & Pooling Audits
- Use `NiagaraMCPBridge` to query pool utilization stats
- Monitor `SpawnedParticles` vs `MaxParticles` during stress tests
- Adjust emitter `MaxParticles` based on platform targets

## Files

- Create: `niagara-performance-guide.md`
- References: `references/niagara-data-interfaces.md`, `references/niagara-mcp-tools.md`, `references/niagara-parameter-types.md`