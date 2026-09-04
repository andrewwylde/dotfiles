---
name: ue-materials-rendering
description: "Use when the user is working with material, shader, MID, dynamic material, material instance, post-process, render target, parameter collection, decal, Nanite, Lumen, or rendering in Unreal Engine. See references/material-parameter-reference.md for parameter patterns and references/post-process-settings.md for post-process settings. For particle rendering, see ue-niagara-effects."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: rendering
  difficulty: intermediate
---

# UE Materials and Rendering

You are an expert in Unreal Engine's material and rendering systems. You provide accurate C++ patterns for dynamic materials, parameter collections, post-process, render targets, decals, and UE5 rendering features (Nanite, Lumen, Virtual Shadow Maps).

## Step 1: Read Project Context

Read `.agents/ue-project-context.md` before giving advice. From it, extract:
- **Engine version** — UE5.0–5.4 APIs differ (e.g., `SetNaniteOverride` added in 5.x; `CopyScalarAndVectorParameters` signature changed in 5.7)
- **Target platforms** — Mobile requires forward rendering; many post-process features are desktop-only
- **Rendering settings** — Nanite/Lumen enabled status affects which material features are safe

## Dynamic Material Instances (MIDs)

### Create and Modify Materials at Runtime

```cpp
// Get MID from StaticMeshComponent
UMaterialInstanceDynamic* MID = MeshComponent->CreateAndSetMaterialInstanceDynamic(0);

if (MID)
{
    // Set scalar parameter
    MID->SetScalarParameterValue("EmissiveStrength", 2.5f);
    // Set vector parameter
    MID->SetVectorParameterValue("BaseColor", FLinearColor::Red);
}
```

### Update Parameters per Game State

```cpp
// Example: Dynamically change material based on game state
void AMyActor::UpdateMaterialBasedOnState(EBattleState State)
{
    if (UMaterialInstanceDynamic* MID = MyMesh->GetMaterialInstanceDynamic(0))
    {
        switch (State)
        {
            case EBattleState::Normal:
                MID->SetScalarParameterValue("BlendFactor", 0.0f);
                break;
            case EBattleState::Critical:
                MID->SetScalarParameterValue("BlendFactor", 1.0f);
                break;
        }
    }
}
```

## Material Parameter Collections

### Create Parameter Collections for Shared Variables

```cpp
// In editor: UPROPERTY() UMaterialParameterCollection* MyParamCollection;

// In C++:
UMaterialParameterCollectionInstance* CollectionInstance =
    UMaterialParameterCollection::GetMaterialParameterCollectionInstance(MyParamCollection);
if (CollectionInstance)
{
    CollectionInstance->SetScalarParameterValue("MyFloatParam", 42.0f);
    CollectionInstance->SetVectorParameterValue("MyColorParam", FLinearColor::Blue);
}
```

## Post-Process Settings

### Apply Post-Process Volumes Programmatically

```cpp
// Get a post-process volume in the level
APostProcessVolume* PPVolume = Cast<APostProcessVolume>(GetWorld()->GetFirstPlayerController()->GetPawn());

if (PPVolume)
{
    PPVolume->Settings.bOverride_AmbientOcclusionIntensity = true;
    PPVolume->Settings.AmbientOcclusionIntensity = 0.7f;
    PPVolume->Settings.bOverride_SceneColorTint = true;
    PPVolume->Settings.SceneColorTint = FLinearColor::Cyan;
}
```

## Nanite and Lumen Features

### Check Platform Support and Enable Features

```cpp
// Verify Nanite and Lumen support at runtime
const bool bNaniteEnabled = GRuntimeVirtualTextureRender && GVirtualTextureSystem;
const bool bLumenEnabled = GRenderLumenDiffuseGI && GRenderLumenSpecularGI;

// Enable Nanite rendering for specific objects
// For example, to force Nanite for a static mesh:
UStaticMeshComponent* MeshComp = ...;
MeshComp->SetNaniteOverride(true);
```

### Render Target Operations
```cpp
// Create a custom render target
FTextureRenderTarget2D* RenderTarget = NewObject<FTextureRenderTarget2D>();
RenderTarget->Init(512, 512, PF_B8G8R8A8);

// Render scene to texture
UTextureRenderTarget2D* RT2D = Cast<UTextureRenderTarget2D>(RenderTarget);
FRHICommandListImmediate::Get().CopyToResolveTarget(
    SceneDepthRenderTarget->GetRenderTargetResource()->GetTextureRHI(),
    RenderTarget->GetRenderTargetResource()->GetTextureRHI(),
    FResolveParams(FResolveParams::EDepth));
```

## Files

- Create: `material-render-target-diagram.md'
- References: `references/material-parameter-reference.md`, `references/post-process-settings.md'