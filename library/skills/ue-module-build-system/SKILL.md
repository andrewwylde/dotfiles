---
name: ue-module-build-system
description: "Use when working with Build.cs, Target.cs, module creation, plugin setup, or build errors in Unreal Engine — including unresolved external symbol, cannot open include file, IWYU violations, missing API macros, or dependency configuration. See also ue-cpp-foundations for UObject macro patterns."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: build
  difficulty: advanced
---

# UE Module & Build System

You are an expert in Unreal Engine's module and build system. You understand Unreal Build Tool (UBT), ModuleRules, TargetRules, the .uproject manifest, plugin architecture, and the IWYU include discipline enforced by UE5.

## Module Rules

### Build.cs Configuration

```cpp
// Example Build.cs - Core Module
public class MyProjectModule : ModuleRules
{
    public MyProjectModule(ReadOnlyTargetRules Target)
        : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
        PrivateDependencyModuleNames.AddRange(new string[] { "Engine" });

        // Add third-party dependencies
        // ThirdPartyPrivateModuleNames.Add("SomeLibrary");

        // Plugin dependencies
        // Plugins.Add("MyPlugin");
    }
}
```

### Target Rules

```cpp
// Example Target.cs - Server target
public class MyProjectServerTarget : TargetRules
{
    public MyProjectServerTarget(TargetInfo Target)
        : base(Target)
    {
        Type = TargetType.Server;
        // UE 5.5+ requires shared build configuration
        bUsesSharedBuildConfiguration = true;
    }
}
```

## IWYU (Include What You Use) Discipline

### Proper IWYU Usage

```cpp
// Use .Build.cs settings rather than adding includes manually
// Let UBT generate IWYU includes

// When needed, use these patterns:
#include "MyModule/Public/MyComponent.h"     // Public header
#include "MyModule/Private/MyComponent.h"   // Private header
#include "MyComponent.generated.h"            // Generated header (UE specific)

// Avoid:
#include "MyComponent.h"  // This may break IWYU
```

### Common IWYU Violations & Fixes

| Issue | Resolution |
|-------|------------|
| `'ClassA' : cannot open source file` | Add `PublicIncludePaths.Add(...)` to Build.cs |
| `C4430: missing type specifier` | Ensure UCLASS/UPROPERTY macros are present |
| `C2027: missing unsigned` | Check UHT-generated files |

### Plugin Setup for Features

```cpp
// Plugin dependency configuration in Build.cs
public DependencyModuleNames.AddRange(new string[] { "AdvancedSessions", "OnlineSubsystem" });

// Plugin enabling in .uproject
// "Plugins": [ {"Name": "AdvancedSessions", "Enabled": true} ]
```

## Dependency Management Patterns

### Public vs Private Dependencies

| Dependency Type | When to Use | Effect |
|----------------|-------------|--------|
| `PublicDependencyModuleNames` | Headers needed by other modules | Exported to dependent modules |
| `PrivateDependencyModuleNames` | Implementation only | Not exported, reduces compile times |
| `ThirdPartyPrivateModuleNames` | External libraries | Links only during build |

### Per-Module IWYU Configuration

```cpp
// In Build.cs (per-module)
PrivateIncludePaths.Add("MyModule/Private");
PublicIncludePaths.Add("MyModule/Public");
```

## Common Build Errors

| Error Type | Cause | Fix |
|------------|-------|-----|
| `LNK2019: unresolved external symbol` | Missing module dependency in Build.cs | Add missing module to Public/PrivateDependencyModuleNames |
| `C1083: Cannot open include file` | Improper IWYU include path | Fix include paths; let UBT handle it |
| `UHT error: unexpected token` | Missing UCLASS/UPROPERTY macros | Add required macros; ensure correct order |
| `Error building module: build failed` | Conflicting Target.cs settings | Harmonize Target.cs with Build.cs |

## Files

- Create: `module-dependency-diagram.md`
- References: `references/module-rules-reference.md`