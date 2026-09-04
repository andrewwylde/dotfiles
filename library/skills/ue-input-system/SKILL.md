---
name: ue-input-system
description: "Use this skill when implementing player input with Unreal Engine's Enhanced Input system. Also use when the user mentions 'Enhanced Input', 'input', 'input action', 'InputAction', 'mapping context', 'InputMappingContext', 'input binding', 'key binding', 'input trigger', 'input modifier', 'gamepad', or 'keyboard'. Covers ETriggerEvent, built-in triggers (Hold, Tap, Pulse, ChordAction, Combo), built-in modifiers (DeadZone, Scalar, Negate, SwizzleAxis), and custom trigger/modifier authoring. See references/input-action-reference.md for the full catalogue. For UI input modes, see ue-ui-umg-slate."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: input
  difficulty: intermediate
---

# UE Enhanced Input System

You are an expert in implementing player input with Unreal Engine's Enhanced Input system. This covers data-driven Input Actions, Input Mapping Contexts, built-in and custom triggers/modifiers, and automated controller/camera transitions over MCP.

## Context

Before providing input guidance, confirm:
- `EnhancedInput` plugin is listed as enabled
- Target platforms (affects which modifiers are needed per platform)
- Whether CommonUI is in use (it manages input mode switching automatically)
- Whether the project still uses legacy input (migration may be needed)

## Core Components

### Input Action (IA_)
Defines what an action is, not how it's triggered. One Input Action can have multiple bindings and triggers.

```cpp
UCLASS()
class UMyInputAction : public UInputAction
{
    GENERATED_BODY()
};
```

### Input Mapping Context (IMC_)
Groups bindings together. Multiple IMCs can be active simultaneously with priority.

```cpp
// In PlayerController
UEnhancedInputComponent* EIComponent = Cast<UEnhancedInputComponent>(InputComponent);
UInputMappingContext* IMC = LoadObject<UInputMappingContext>(nullptr, TEXT("/Game/Input/IMC_Gameplay"));
EIComponent->AddMappingContext(IMC);
```

### Triggers
| Trigger | Description | Use Case |
|---------|-------------|----------|
| **Hold** | Continuous while key held | Charge attacks, sprinting |
| **Tap** | One-shot on key press | Jump, shoot, interact |
| **Pulse** | Repeats while held | Movement axis (smooth) |
| **ChordAction** | Two keys simultaneously | Vehicle exit + interact |
| **Combo** | Sequence of taps | Combo attacks |

### Modifiers
| Modifier | Description | Use Case |
|----------|-------------|----------|
| **DeadZone** | Ignore small inputs | Gamepad stick dead zones |
| **Scalar** | Multiply input by factor | Sensitivity adjustments |
| **Negate** | Invert axis | Flip camera Y axis |
| **SwizzleAxis** | Swap X/Y | Left/right stick swap |

## Binding Patterns

### C++ Binding
```cpp
void AMyPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    UEnhancedInputComponent* EIComponent = Cast<UEnhancedInputComponent>(InputComponent);
    
    if (EIComponent)
    {
        EIComponent->BindAction(JumpAction, ETriggerEvent::Started, this, &AMyPlayerController::OnJumpStarted);
        EIComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyPlayerController::OnMove);
    }
}

void AMyPlayerController::OnMove(const FInputActionValue& Value)
{
    const float InputValue = Value.Get<float>();
    APawn* Pawn = GetPawn();
    if (Pawn)
    {
        Pawn->AddMovementInput(GetActorForwardVector(), InputValue);
    }
}
```

### Blueprint Binding
```cpp
// Blueprint node: Enhanced Input Bind Action
// Action: IA_Jump
// Event: ETriggerEvent::Started
// Target: PlayerController
```

## In-Engine MCP Integration

Use `unreal-input-mcp` for automated input setup:
- `create_input_action` — creates IA_ assets programmatically
- `add_mapping_context` — injects IMC_ into PlayerController
- `validate_bindings` — checks for conflicting bindings
- `set_input_mode` — switches between Game and UI modes

## Common Pitfalls

1. **Using legacy input** — check Project Settings for axis/action mappings
2. **Missing IMC priority** — multiple IMCs with same action cause unpredictable behavior
3. **Hardcoded trigger events** — use ETriggerEvent enums consistently
4. **Not clearing bindings** — stale bindings persist across level transitions

## Files

- Create: `input-action-catalog.md`
- References: `references/input-action-reference.md`