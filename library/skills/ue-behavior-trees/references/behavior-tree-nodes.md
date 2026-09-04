# Behavior Tree Nodes Reference

## Composites
- **Selector**: Tries children from left to right until one **Succeeds**. Used for prioritized fallbacks (e.g. `Combat` -> `Investigate` -> `Patrol`).
- **Sequence**: Executes children from left to right until one **Fails**. Used for step-by-step actions (e.g. `MoveToCover` -> `Aim` -> `Shoot`).
- **Simple Parallel**: Runs a main task node alongside a secondary sub-tree.

---

## Decorators & Observer Aborts
Decorators act as conditional gates on branches or tasks based on Blackboard values.

| Observer Abort Mode | Behavior | Use Case |
| :--- | :--- | :--- |
| **None** | Condition only checked when the node is first reached. | Static checks that don't need interruptibility. |
| **Self** | Aborts the current sub-tree if condition becomes false while executing. | "While Target in Range" — abort attack if target escapes. |
| **Lower Priority** | If condition becomes true, interrupts running lower-priority branches to execute this branch. | "Has Target Actor" on Combat branch — interrupts Patrol immediately upon sighting enemy. |
| **Both** | Combines `Self` and `Lower Priority`. | Full interruptibility in dynamic combat loops. |

---

## Services (`UBTService`)
Services tick periodically (e.g. interval 0.5s +/- 0.1s random deviation) while their branch is active:
- `BTService_PerceptionUpdate`: Queries AI Perception and updates `TargetActor` or `LastKnownLocation`.
- `BTService_DistanceCheck`: Computes distance to target and sets boolean `bWithinAttackRange`.

---

## Custom C++ BTTask (`UBTTask_BlackboardBase`)

```cpp
// Header
UCLASS()
class MYGAME_API UBTTask_FindPatrolPoint : public UBTTask_BlackboardBase
{
    GENERATED_BODY()
public:
    UBTTask_FindPatrolPoint();
    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) override;
};

// Source
EBTNodeResult::Type UBTTask_FindPatrolPoint::ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory)
{
    AAIController* AICon = OwnerComp.GetAIOwner();
    APawn* Pawn = AICon ? AICon->GetPawn() : nullptr;
    if (!Pawn) return EBTNodeResult::Failed;

    UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Pawn->GetWorld());
    FNavLocation RandomLoc;
    if (NavSys && NavSys->GetRandomReachablePointInRadius(Pawn->GetActorLocation(), 1500.f, RandomLoc))
    {
        OwnerComp.GetBlackboardComponent()->SetValueAsVector(GetSelectedBlackboardKey(), RandomLoc.Location);
        return EBTNodeResult::Succeeded;
    }
    return EBTNodeResult::Failed;
}
```
