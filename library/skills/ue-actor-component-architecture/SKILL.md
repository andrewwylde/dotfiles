---
name: ue-actor-component-architecture
description: "Use this skill when working with Actor and component design in Unreal Engine. Triggers on: Actor, component, BeginPlay, Tick, SpawnActor, lifecycle, CreateDefaultSubobject, composition, EndPlay, PostInitializeComponents, UActorComponent, USceneComponent, UINTERFACE, attachment, spawn, interface. See references/actor-lifecycle.md and references/component-types.md for detailed tables."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: architecture
  difficulty: essential
---

# UE Actor-Component Architecture

You are an expert in Unreal Engine's Actor-Component architecture. This skill covers the fundamental patterns for building Actors with composable components, dynamic reflection inspection, and proper lifecycle management.

## Actor Lifecycle Phases

| Phase | Key Event | Typical Actions |
|-------|-----------|-----------------|
| **BeginPlay** | Actor spawns in level | Initialize components, bind delegates, one-time setup |
| **PostInitializeComponents** | All components created | Set initial subobject relations, finalize component properties |
| **Tick** | Per-frame update | Root motion updates, per-frame logic |
| **EndPlay** | Actor removal | Graceful cleanup, delegate unbinding, resource release |

## Component Composition Patterns

### Preferred Composition over Inheritance
- Use **UActorComponent** subclasses for reusable behavior
- Compose Actors via **CreateDefaultSubobject<>** rather than deep class hierarchies
- Keep Actor interface thin; delegate behavior to components

### Component Hierarchy Rules
1. **Root Component** — every Actor must set one component as `RootComponent`
2. **Component Attachment** — use `SetupAttachment(RootComponent)` for child components
3. **SceneComponent** — base for transform-aware components (cameras, collision, skeletal mesh sockets)

### Dynamic Reflection Inspection
```cpp
// Query component types at runtime
for (UActorComponent* C : Actor->GetComponents())
{
    if (USceneComponent* SC = Cast<USceneComponent>(C))
    {
        FTransform LocalToWorld = SC->GetComponentToWorld();
        // Perform transform queries...
    }
}
```

## Interface Design Best Practices

### UActorComponent Subclass Interface
- Expose public API via **virtual functions** with default implementations
- Use **UPROPERTY(VisibleAnywhere)** for debug/configuration
- Provide **pure virtual** methods for required behavior

### Generic Interface Pattern
```cpp
UINTERFACE(MinimalAPI)
class UMyGenericInterface : public UInterface
{
    GENERATED_BODY()
};

class IMyGenericInterface
{
    GENERATED_BODY()
public:
    // Core method all components must implement
    virtual void ExecuteCoreLogic() = 0;
};
```

## Common Patterns & Pitfalls

| Pattern | Recommendation |
|---------|----------------|
| **Component Creation** | Use `CreateDefaultSubobject<UFooComponent>(TEXT("Foo"))` in constructor |
| **Component Lifetime** | Components are owned by Actor; no manual destroy needed |
| **Collision Setup** | Set `SetCollisionEnabled(QueryOnly)` or `PhysicsOnly` based on needs |
| **Input Binding** | Use `UInputComponent` binding in `SetupPlayerInputComponent` |
| **Avoid Circular References** | Use `TWeakObjectPtr<>()` for cross-component references |

## Files

- Create: `actor-hierarchy-diagram.png` (visual guide)
- References: `references/actor-lifecycle.md`, `references/component-types.md`