---
name: ue-animation-system
description: "Use this skill when working with Unreal Engine animation: AnimInstance, montage playback, blend space, state machine, anim notify, IK, AnimGraph, skeletal mesh, or linked anim graphs. See references/anim-notify-reference.md for notify patterns and references/locomotion-setup.md for locomotion setup. For montage integration with GAS, see ue-gameplay-abilities."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: animation
  difficulty: intermediate
---

# UE Animation System

You are an expert in Unreal Engine's animation system. This covers `UAnimInstance` native update logic, Montage playback/state, Blend Spaces, Animation Blueprints, IK, and integration with GAS (Gameplay Ability System) montages.

## Context

Read `.agents/ue-project-context.md` first. Note which plugins are enabled (Control Rig, Motion Matching, Full Body IK), whether GAS is in use, and the skeleton/character hierarchy.

## Key Components

| Component | Role | C++ Access |
|-----------|------|-------------|
| **UAnimInstance** | Per-skeleton animation state | `GetAnimInstance()` |
| **UAnimMontage** | Transient animation sequences | `Montage_Play()` |
| **UBlendSpace** | Directional blending of animations | `SetBlendSpace()` |
| **UAnimCurve** | Float curves for parameter-driven effects | `GetCurveValue()` |

## Core Patterns

### 1. Native AnimInstance Updates
```cpp
// Header
UCLASS()
class UMyAnimInstance : public UAnimInstance
{
    GENERATED_BODY()

private:
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;

    UPROPERTY(BlueprintReadOnly, Category="My Categories")
    float Direction;
};

// CPP
void UMyAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);

    // Safe native access to pawn/orientation
    APawn* Pawn = TryGetPawn(UAnimInstance::GetOwningActor());
    if (Pawn)
    {
        Direction = CalculateDirection(Pawn->GetVelocity(), Pawn->GetActorRotation());
    }
}
```

### 2. Montage Playback from C++
```cpp
// Play attack montage with section jump
UPROPERTY(EditDefaultsOnly)
TObjectPtr<UAnimMontage> AttackMontage;

void ACharacter::PerformAttack()
{
    PlayAnimMontage(AttackMontage, 1.0f, "Start");
}
```

### 3. GAS Montage Integration
```cpp
// In GAS ability
void UGA_CharacterJump::ActivateAbility()
{
    // Play jump montage tied to ability
    Montage_Task = PlayMontageAndWaitForEvent(this, FName("Jump"), JumpMontage);
    Montage_Task->ReadyForActivation();
}
```

## Common Pitfalls

1. **Calling `Montage_Play()` every tick** — results in rapid restarts
2. **Using raw `UAnimMontage*`** instead of `TObjectPtr<>` — invite GC issues
3. **Not validating anim instance** — `GetAnimInstance()` can return `nullptr`
4. **Hard-binding curve names** — use FName constants for performance

## Files

- Create: `ue-locomotion-graph.md`
- References: `references/anim-notify-reference.md`, `references/locomotion-setup.md`