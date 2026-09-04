---
name: ue-cpp-foundations
description: "Write correct UE5 C++ code involving UCLASS/UPROPERTY/UFUNCTION reflection macros, TArray/TMap/smart pointers, garbage collection, and subsystem patterns. Use for UCLASS/UPROPERTY macros, container choice, reflection hygiene, GC-aware coding, and smart-pointer ownership. Targets UE 5.4–5.8+; C++17+ toolchain."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: cpp
  difficulty: advanced
---

# UE C++ Foundations

You are an expert in Unreal Engine's C++ extensions and property system. Code you provide must compile with UE 5.4–5.8+ toolchains and follow Epic's reflection and memory-management conventions.

## Engine Version Matters

- **UE 5.0–5.3**: Raw `UObject*` patterns, `GENERATED_USTRUCT_BODY()` in structs
- **UE 5.4+**: `TObjectPtr<>`, `GENERATED_BODY()` replaces `GENERATED_USTRUCT_BODY()` in structs

## Core Principles

### 1. Macro Discipline

- **`UCLASS(BlueprintType, Blueprintable)`** — when exposing to Blueprints
- **`UPROPERTY(VisibleAnywhere, BlueprintReadOnly)`** — for read-only editor/BP access
- **`UFUNCTION(BlueprintCallable, Category="MyCategory")`** — for BP-callable C++

### 2. Container Choice Guide

| Container | Use Case | Notes |
|-----------|----------|-------|
| `TArray` | Dynamic arrays, Blueprint-exposed | Supports `Add()`, `RemoveAt()`, iteration |
| `TMap` | Key-value lookup | Key must implement `operator<` or provide `GetTypeHash()` |
| `TSet` | Unique-element collection | Requires `GetTypeHash()` for elements |
| `TObjectPtr<>` | UObject/USubobject ownership | **Prefer over raw `UObject*`**; ensures GC tracking |

### 3. Smart-Pointer Hygiene

| Pointer Type | When to Use | Ownership Model |
|--------------|-------------|-----------------|
| `TObjectPtr<>` | UObject derived classes | Non-null, GC-tracked; disallows dangling |
| `TWeakObjectPtr<>` | Non-owning reference to UObject | Avoids circular references; auto-nulls on destroy |
| `TUniquePtr<>` | Exclusive ownership of non-UObject | RAII; moves only |
| `TSharedPtr<>` | Shared ownership of non-UObject | Reference counted; use for interop |

### 4. Reflection & Dynamic Casting

```cpp
// Safe dynamic cast via reflection
UClass* MyClass = AActor::StaticClass();
if (UObject* Obj = SomeComponent->GetOwner())
{
    if (MyClass->IsChildOf(Obj->GetClass()))
    {
        // Safe cast
        AMyActor* Casted = Cast<AMyActor>(Obj);
    }
}
```

### 5. Lifetime Management

- **`TObjectPtr<>`** — always prefer for UObjects; handles GC tracking automatically
- **`TWeakObjectPtr<>`** — for non-owning references; set to `nullptr` when object destroyed
- **Never store raw `UObject*`** — risk of dangling pointer if GC collects object

## Pitfalls to Avoid

1. **Mixing raw `UObject*` with `TObjectPtr<>`** in the same class — pick one and stay consistent
2. **Forgetting `GENERATED_BODY()`** in UCLASS/UPROPERTY structs under UE 5.4+
3. **Using `TArray<UObject*>`** instead of `TArray<TObjectPtr<UObject>>`** — invites GC crashes
4. **Calling `Remove()` on `TMap` with UObject keys** without proper `GetTypeHash` implementation
5. **`TSubclassOf<>` deprecation** — use `TSoftClassPtr<>` for lazy loading in UE 5.5+

## Files

- Create: `UE5_CPP_Foundations.md` (local copy in your project)
- References: `references/property-specifiers.md`, `references/container-choice-guide.md`