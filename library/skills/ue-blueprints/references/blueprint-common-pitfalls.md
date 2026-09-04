# Blueprint Common Pitfalls & Anti-Patterns

## 1. Hard Reference Memory Bloat (The "Cast-To Everything" Anti-Pattern)
- **Symptom**: Loading one small UI widget or pickup actor loads 500MB of meshes, sounds, and textures into RAM.
- **Root Cause**: Direct `Cast To SpecificActor` creates a hard compile-time reference. When the Blueprint is loaded, all referenced assets load synchronously.
- **Fix**: Use **Blueprint Interfaces** (`BPI_`) or `TSoftObjectPtr` / Soft Class references loaded via Async Load Asset.

## 2. Event Tick Overload
- **Symptom**: Frame rate degradation when multiple AI or decorative actors exist in the level.
- **Fix**: Replace `Event Tick` with event-driven architecture (Timers, OnComponentBeginOverlap, Gameplay Tag changes, or Delegate broadcasts).

## 3. Hidden Pass-by-Reference Side Effects
- **Symptom**: Variables passed into Blueprint function calls change unexpectedly outside the function.
- **Fix**: Check function input parameter details; avoid "Pass by Reference" for structs unless mutation is explicitly intended.

## 4. Delay Nodes in Loops
- **Symptom**: `Delay` inside a `For Each Loop` executes asynchronously and does not pause the iteration, causing simultaneous trigger chaos.
- **Fix**: Use recursive timer callbacks or state machines instead of `Delay` inside loops.
