---
name: ue-character-movement
description: "Use this skill when working with character movement, CharacterMovementComponent, CMC, movement modes, walking, falling, swimming, flying, custom movement, network prediction, FSavedMove, root motion, floor detection, step-up, or character physics. Also use for 'PhysWalking', 'PhysCustom', 'LaunchCharacter', 'WalkableFloor', or 'movement replication'. See references/ for CMC extension patterns and movement pipeline details."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: movement
  difficulty: advanced
---

# UE Character Movement

You are an expert in Unreal Engine's `UCharacterMovementComponent` (CMC), the core system that drives character locomotion, floor detection, network prediction, and root motion integration. You understand the full Phys* pipeline, custom movement mode implementation, and the `FSavedMove_Character` prediction architecture.

## Context

Read `.agents/ue-project-context.md` to determine:
- Whether the project uses `ACharacter` or a custom pawn with its own movement
- The UE version (UE 5.4+ adds `GravityDirection` support, UE 5.5 changes `DoJump` signature)
- Whether multiplayer is involved (affects prediction pipeline complexity)
- Any existing CMC subclass or custom movement modes already in use

## Core Systems

### Movement Modes
| Mode | Enum Value | Typical Use Cases |
|------|------------|-------------------|
| **MOVE_None** | 0 | Idle, no movement |
| **MOVE_Walking** | 1 | Ground-based walking/running |
| **MOVE_NavWalking** | 2 | Path-following via NavMesh |
| **MOVE_Falling** | 3 | Airborne via gravity/jump |
| **MOVE_Swimming** | 4 | Water navigation |
| **MOVE_Flying** | 5 | Arbitrary 3D flight |
| **MOVE_Custom** | 254+ | User-defined modes |

### Network Prediction
CMC uses `FSavedMove_Character` for client-side prediction:
- Clients simulate movement locally
- Server sends corrections when positions diverge
- Custom movement modes require overriding `CompressFlagsFromNet` and `SetMoveFor`

### Root Motion Integration
Root motion drives character from animation:
- `bEnablePhysicsRotation` — enable rotation from root motion
- `bOrientRotationToMovement` — face direction of movement
- `RotationRate` — maximum rotation speed

## Key Pipeline Steps

1. **Input Accumulation** — gather player input each frame
2. **Requested vs Actual** — apply acceleration/deceleration limits
3. **Phys* Calculation** — apply gravity, friction, constraints
4. **Movement Mode Update** — transition between Walking/Falling etc.
5. **Replication Preparation** — pack state for network

## Custom Movement Mode Pattern

```cpp
UCLASS()
class UMyCustomMovement : public UCharacterMovementComponent
{
    GENERATED_BODY()

public:
    virtual void PhysCustom(float deltaTime, int32 Iterations) override;
    virtual void OnMovementModeChanged(EMovementMode PreviousMovementMode,
                                      uint8 PreviousCustomMode) override;
};

// CPP Implementation
void UMyCustomMovement::PhysCustom(float deltaTime, int32 Iterations)
{
    // Custom physics calculations here
    FVector NewLocation = UpdatedComponent->GetComponentLocation();
    NewLocation += GetVelocity() * deltaTime;
    UpdatedComponent->SetWorldLocation(NewLocation);
}
```

## Common Patterns

### Floor Detection & Step-Up
- `bIgnoreBaseOnCheck` — ignore standing on dynamic objects
- `StepUpHeight` — maximum step height without falling
- `GetFloor()` — query current surface normal and material

### LaunchCharacter vs AddImpulse
| Method | Use Case | When to Prefer |
|--------|----------|----------------|
| `LaunchCharacter()` | Instant velocity set | Jump initiation, knockback |
| `AddImpulse()` | Gradual force application | Thrusters, continuous push |

## Files

- Create: `cmc-modes-diagram.md`
- References: `references/cmc-extension-patterns.md`, `references/movement-modes.md`