---
name: ue-gameplay-abilities
description: "Use this skill when working with GAS, Gameplay Ability System, GameplayAbility, GameplayEffect, AttributeSet, GameplayTags, ability system, buffs, debuffs, cooldowns, or attribute modification. See references/ for detailed setup patterns, effect configuration, and ability task usage."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: gameplay
  difficulty: advanced
---

# Gameplay Ability System (GAS)

You are an expert in Unreal Engine's Gameplay Ability System (GAS). This is the industry-standard framework for character abilities, attributes, and gameplay effects in UE5.

## Prerequisites

Before providing GAS guidance, read `.agents/ue-project-context.md` to determine:
- Whether the `GameplayAbilities` plugin is enabled
- Which actors own the `AbilitySystemComponent` (PlayerState vs Character)
- The replication mode in use (Minimal, Mixed, Full)
- Any existing `AttributeSets` or ability base classes

## Core Components

### 1. AbilitySystemComponent (ASC)
Owned by actors that have abilities. Manages:
- **Owned Gameplay Tags** — current state tags (`Status.Dead`, `Character.AtJumpApex`)
- **Gameplay Cues** — visual/audio feedback tied to gameplay events
- **Prediction Keys** — client-side prediction reconciliation

### 2. GameplayAbilities
Subclass `UGameplayAbility` for active abilities:
- **Montage Tasks** — `WaitTargetData`, `MontageEvent`, `Delay`
- **Ability Scope** — defines what gameplay context the ability runs in
- **Cost/Commit** — define resource costs before activation

### 3. GameplayEffects
Blueprint/asset-based modifications to attributes:
- **Instant** — immediate effect (healing, damage)
- **Duration** — timed effect (buffs/debuffs)
- **Infinite** — permanent until removed (passive abilities)
- **Periodic** — ticks over duration (DoT/HoT)
- **Execution Definition** — custom logic for complex calculations

### 4. AttributeSet
Defines attributes (Health, Mana, AttackPower) with accessor/modifier functions:
- **Replicated Using** — mark attributes for replication callbacks
- **Pre-Attribute Change** — intercept changes for validation
- **Post-Attribute Change** — trigger reactions when attributes change

## Key Patterns

### Server-Authoritative Ability Activation
```cpp
// In ASC subclass
void UMyAbilitySystemComponent::AbilityActivated(UMyGameplayAbility* Ability)
{
    if (Ability->CheckCost(ActorInfo, SpecHandle))
    {
        Ability->CommitAbility(SpecHandle, ActorInfo, ActivationInfo);
        Ability->ActivateAbility(SpecHandle, ActorInfo, ActivationInfo);
    }
}
```

### Gameplay Cue Routing
```cpp
// Trigger visual effects
FGameplayCueParameters CueParams;
CueParams.EffectCauser = Instigator;
UAbilitySystemBlueprintLibrary::SendGameplayCueToActor(TargetActor, 
    FGameplayTag::RequestGameplayTag("GameplayCue.Impact"), CueParams);
```

### Attribute Set Implementation
```cpp
UCLASS()
class UMyAttributeSet : public UAttributeSet
{
    GENERATED_BODY()

public:
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutProperty) const override;
    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;

    UPROPERTY(BlueprintReadOnly, Category="Attributes")
    FGameplayAttributeData Health;
    GAMEPLAYATTRIBUTE_PROPERTY_GETTER(UMyAttributeSet, Health)
};

void UMyAttributeSet::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutProps) const
{
    Super::GetLifetimeReplicatedProps(OutProps);
    DOREPLIFETIME_CONDITION(UMyAttributeSet, Health, COND_InitialOrOwner);
}
```

## Common Pitfalls

1. **Authority Confusion** — GAS server-authoritative means clients can't directly modify attributes
2. **Prediction Key Bugs** — must pair with correct AbilitySystemComponent contexts
3. **Replication Mode Mismatch** — mixing Minimal replication with Mixed replication data

## Integration Points

- **Montage Integration**: GAS montages use `Montage_SetEndDelegate()` for ability completion detection
- **Animation Blueprint Integration**: Use `SetDRC` to blend animations based on GAS states
- **UI Integration**: Bind HUD elements to `OnGameplayAttributeValueChangedDelegate`

## Files

- Create: `gas-setup-checklist.md`
- References: `references/gas-setup-guide.md`, `references/gameplay-effect-calculation.md`