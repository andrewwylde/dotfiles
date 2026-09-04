---
name: ue-data-assets-tables
description: "Use when working with DataAsset, DataTable, soft reference, hard reference, TSoftObjectPtr, async loading, Asset Manager, StreamableManager, or game data structures in Unreal Engine. See references/asset-loading-patterns.md for async loading and StreamableManager patterns. See references/data-driven-design.md for data-driven gameplay architecture. For serialization, see ue-serialization-savegames. For C++ foundations, see ue-cpp-foundations."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: data
  difficulty: intermediate
---

# UE Data Assets and Tables

You are an expert in Unreal Engine's data management and asset loading systems. Data-driven design is essential for scalable game development.

## Core Types

### UPrimaryDataAsset
- **Inherits**: `UObject`
- **Purpose**: Structured game data with versioning and filtering
- **Usage**: Item definitions, ability data, level configurations
- **Tags**: `GameplayTag` support for categorization

```cpp
USTRUCT(BlueprintType)
struct FWeaponData : public FTableRowBase
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FGameplayTagContainer Tags;
    UPROPERTY(EditAnywhere) float Damage;
    UPROPERTY(EditAnywhere) TSoftObjectPtr<UStaticMesh> Mesh;
};

UCLASS()
class UWeaponDataAsset : public UPrimaryDataAsset
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FWeaponData WeaponData;
};
```

### UDataTable
- **Inherits**: `UObject`
- **Purpose**: Tabular data from CSV/JSON import
- **Usage**: Lookup tables (XP curves, drop tables, localization)
- **Rows**: Must inherit `FTableRowBase`

```cpp
USTRUCT(BlueprintType)
struct FXPCurveRow : public FTableRowBase
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) int32 Level;
    UPROPERTY(EditAnywhere) int32 XPRequired;
};

// Runtime access
UDataTable* XPTable = LoadObject<UDataTable>(nullptr, TEXT("/Game/Data/DT_XPCurve"));
FXPCurveRow* Row = XPTable->FindRow<FXPCurveRow>(FName("Level5"), TEXT("XP Lookup"));
```

## Reference Patterns

| Pattern | When to Use | Pros | Cons |
|---------|-------------|------|------|
| **Hard Ref** | Immediate dependencies | Simple, auto-loads | Loads with parent |
| **Soft Ref (`TSoftObjectPtr`)** | Deferred loading, modular content | On-demand, memory efficient | Requires async load |
| **Soft Class (`TSoftClassPtr`)** | Blueprint classes, plugins | Cross-module safe | One extra load step |

## Async Loading with StreamableManager

```cpp
// Async load with callback
FStreamableManager& Streamable = UAssetManager::GetStreamableManager();
TSoftObjectPtr<UDataAsset> AssetRef(TEXT("/Game/Data/DA_Weapons"));

Streamable.RequestAsyncLoad(AssetRef.ToSoftObjectPath(),
    [this](TSoftObjectPtr<UDataAsset> LoadedAsset)
    {
        if (LoadedAsset.IsValid())
        {
            ApplyWeaponData(LoadedAsset.Get());
        }
    });
```

## Data-Driven Architecture Guidelines

1. **Schema Versioning** — Use `FTableRowBase::TableVersion` for migration
2. **Validation** — Implement `FDataTableRowHandle` with `ValidateDataTable()`
3. **Modularity** — Separate data assets per game system (weapons, abilities, economy)
4. **Tagging** — Use `GameplayTag` containers for filtering and queries

## Related Skills
- `ue-cpp-foundations`: `TSoftObjectPtr` patterns require smart-pointer hygiene
- `ue-gameplay-abilities`: GAS data typically lives in DataAssets

## Files

- Create: `data-asset-workflow.md`
- References: `references/asset-loading-patterns.md`, `references/data-driven-design.md`