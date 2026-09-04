---
name: ue-gameplay-framework
description: "Use this skill when working with Unreal Engine's gameplay framework classes: GameMode, GameState, PlayerController, PlayerState, Pawn, Character, or GameInstance. Also use when the user mentions 'gameplay framework', 'game rules', 'player management', 'match flow', or 'player spawning'. See references/framework-class-map.md for the full authority/presence matrix."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: framework
  difficulty: intermediate
---

# UE Gameplay Framework

You are an expert in Unreal Engine's gameplay framework architecture. This covers `GameMode`, `GameState`, `PlayerController`, `PlayerState`, `Pawn`, `Character`, and `GameInstance` with proper authority/replication mapping for single-player and multiplayer games.

## Context

Read `.agents/ue-project-context.md` to determine:
- Whether this is single player, co-op, competitive multiplayer, dedicated vs listen server?
- What game type (TPS, RTS, RPG, etc.)?
- Which game types (single-player, co-op, competitive multiplayer, dedicated vs listen server) determine which classes to subclass and which replication patterns apply.

## Class Responsibility Map

Each class exists on specific machines for specific reasons. Getting this wrong is the primary source of multiplayer bugs.

| Class | Default Authority (WHO EXISTS?) | Default Replication (WHO SEES?)" | Typical Use |
|-------|--------------------------------|-----------------------------------|-------------|
| **GameMode** | Server | Server | Game rules, match flow, game state policies |
| **GameState** | Server | Client + Server | Game state info (score, match status), HUD data |
| **PlayerController** | Server | Client | Client input, camera, local game view |
| **PlayerState** | Server | Client | Player stats, UI score, match results |
| **Pawn** | Server | Server + Client (own pawn) | Physical entity, collisions, mesh, input handling |
| **Character** | Server | Server + Client (own character) | Movement, ability system, targeting |
| **GameInstance** | Server | Server | Persistent game-wide data, menus, loading |

## Core Patterns

### 1. Single-Player GameMode
```cpp
UCLASS()
class AMyGameMode : public AGameMode
{
    GENERATED_BODY()

public:
    virtual void BeginPlay() override;
    virtual APawn* SpawnDefaultPawnFor(AController* NewPlayer) override;
};

void AMyGameMode::BeginPlay()
{
    Super::BeginPlay();
    // Initialize game state, load levels, create persistent objects
}
```

### 2. Multiplayer PlayerController with Authority
```cpp
UCLASS()
class AMyPlayerController : public APlayerController
{
    GENERATED_BODY()

protected:
    virtual void BeginPlay() override;
    virtual void OnPossess(APawn* InPawn) override;
    virtual void OnUnpossess(APawn* UnpossessedPawn) override;
};

void AMyPlayerController::BeginPlay()
{
    Super::BeginPlay();
    // Initialize input, camera, UI components
}
```

### 3. PlayerState Replication
```cpp
UCLASS()
class AMyPlayerState : public APlayerState
{
    GENERATED_BODY()

public:
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(ReplicatedUsing, ReplicatedStats)
    int32 Kills;
};

void AMyPlayerState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutProps) const
{
    Super::GetLifetimeReplicatedProps(OutProps);
    DOREPLIFETIME_CONDITION(AMyPlayerState, Kills, COND_InitialOrOwner);
}
```

## Dedicated Server vs Listen Server Patterns

### Listen Server
- Server + Clients on same machine
- All classes exist on all machines
- Use `Listen` in `AddEngineMessages()` or `Launch()

### Dedicated Server
- Server only, clients run separate process
- GameMode, GameState, Pawn on server; PlayerController on clients
- Use `Dedicated` configuration in `.uproject`

### Server Migration (Loading/Bootstrap)
```cpp
// Server side
UCLASS()
class AServerGameMode : public AGameMode
{
    GENERATED_BODY()

public:
    virtual void PostLogin(AController* NewPlayer) override;
    virtual void Logout(AController* ExitingPlayer) override;
};
```

## Common Pitfalls

1. **Pawn vs Character** — Pawn is generic physical entity, Character adds movement & ability system
2. **PlayerState vs PlayerController** — PlayerState is persistent; PlayerController is transient
3. **GameMode Authority** — GameMode lives on Server in dedicated, both in Listen
4. **Pawn Replication** — Pawns are replicated as sub-objects, automatically assigned to owning controller

## Files

- Create: `framework-class-dependencies.md'
- References: `references/framework-class-map.md`