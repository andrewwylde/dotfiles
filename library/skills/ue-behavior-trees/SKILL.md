---
name: ue-behavior-trees
description: "Build NPC AI in Unreal Engine 5 with Behavior Trees and Blackboards: composites (Selector/Sequence), tasks, decorators, services, and running the tree from an AIController. Use for creating enemy/NPC AI, BT_/BB_ assets, custom BTTask or BTService nodes, or when the user mentions Behavior Tree, Blackboard, AIController, BTTask, decorator, or service. Requires AIModule."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: ai
  difficulty: advanced
---

# UE Behavior Trees

Author NPC decision-making in UE5 with Behavior Trees driven by a Blackboard. Structure trees with composites, gate branches with decorators, keep state current with services, and run the tree from an AIController. Targets **UE 5.4+**.

## When to Use
Use this skill when creating enemy/NPC AI, BT_/BB_ assets, custom BTTask or BTService nodes, or when the user mentions Behavior Tree, Blackboard, AIController, BTTask, decorator, or service.

## When NOT to Use
For general game AI without UE5 integration, or for gameplay logic that doesn't need hierarchical decision-making. Use simpler state machines for basic behavior patterns.

## Prerequisites
- UE 5.4+ project with `AIModule` plugin enabled
- Navigation mesh (NavMesh) built in editor
- AIController class set up (`AAIController::SetAIContext`)
- Blackboard asset with keys defined

## Core Architecture

Behavior Trees are driven by a **Blackboard** - a key/value store used by all components. Keys include:

| Key Type | Description | Typical Use |
|----------|-------------|-------------|
| `Bool` | Binary flags | HasLOS, IsDead |
| `Object` | Generic UObject reference | TargetActor |
| `Vector` | 3D position data | PatrolPoint |
| `Class` | UObject subclass | EnemyClass |
| `Enum` | Enumeration state | EPatrolBehavior |
| `Float` | Scalar values | HealthFraction |

## Composite Nodes

The root and logic controllers of every tree:

### Selector
Evaluates children left-to-right, succeeds on the first child that **succeeds**, fails if **all** children fail.
Use for fallback behaviors: "Find cover → If none, flee → If can't flee, attack"

### Sequence
Evaluates children left-to-right, succeeds only if **all** children succeed, fails on the first failure.
Use for ordered behaviors: "Move to point → Wait → Execute animation"

## Task Nodes

Execute atomic actions that return a result:

| Task | Returns | When Complete |
|------|---------|---------------|
| `BTTask_MoveTo` | Success/Fail | Reached destination or failed path |
| `BTTask_PlayMontage` | Success/Fail | Montage finished playing |
| `BTTask_Wait` | Success | After specified delay |

For custom logic, subclass `UBTTask_BlackboardBase` or `UBTTaskNode`.

## Decorators

Filter execution paths conditionally:

| Decorator | Purpose | Common Keys |
|----------|---------|-------------|
| `Cooldown` | Prevents repeated execution | CooldownRemaining |
| `TagCooldown` | Uses gameplay tags | TagCooldown |
| `Service` | Runs periodically during execution | ServiceTick |

## Related Skills
- `ue-cpp-foundations`: Subclassing `UBTTaskNode` requires reflection macros
- `ue-actor-component-architecture`: Integrating AI with Actor lifecycle

## Files
- Create: `references/behavior-tree-nodes.md`