---
name: ue-blueprints
description: "Build Unreal Engine 5 gameplay with Blueprint visual scripting: Blueprint Classes, the Event Graph and Construction Script, variables/functions/macros, and Blueprint communication (Cast, Interfaces, Event Dispatchers). Use for blueprint analysis, visual scripting best practices, and text-based IR generation. Targets UE 5.4+. "
metadata:
  version: "2026.1.0"
  engine: unreal
  category: visual
  difficulty: intermediate
---

# UE Blueprints (Visual Scripting)

You are an expert in Unreal Engine's Blueprint system. Blueprints provide visual scripting capabilities for implementing game logic, component communication, and editor tools. All Blueprints must adhere to SOTA 2026 Blueprint textual intermediate representation (IR) standards.

## Blueprint Analysis Workflow

1. **Convert to IR** using `unreal-blueprint-mcp` tool
2. **Audit pin types** against expected signatures
3. **Detect soft-reference bugs** in Cross-Root references
4. **Validate node inheritance** through parent/child class checks

## Key Patterns & Best Practices

### Blueprint Class Structure
```cpp
UCLASS()
class UMyBlueprintClass : public UObject
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString Greeting;
}```

### Event Graph Best Practices
- Use **Event Dispatchers** for decoupled communication
- Prefer **Custom Events** over native types for replayability
- Use **Default Pins** for required parameters that can't be null

### Variable Types & Flow Control
| Type | Description | Notes |
|-------|-------------|-------|
| `V_String` | Blueprint string
| `V_Int32` | Integer values
| `V_Object` | UObject reference
| `V_Boolean` | True/False flags

### Common Pitfalls
1. **Cross-Root References** – Use `GetOuter()` and `FindOwner()` to resolve root-relative paths
2. **Signal Generator Mismatch** – Ensure pin types match exactly between Send and Receive
3. **Object Ownership** – Ensure referenced objects don't destroy referenced Blueprints

## Textual Intermediate Representation

The Blueprint IR consists of:
- **Nodes** (connected by pins)
- **Namespaces** for group definitions
- **Declaration Blocks** for macros/variables
- **Annotation Elements** for validation markers

```json
// Example Node IR snippet
{}
  "Nodes": [
    {
      "ID": "A1B2C3",
      "ClassID": "BP_Node_Add",
      "Location": { "X": 100, "Y": 50 },
      "Pins": {
        "PINX": {"Connection": "B1C2D3"},
        "PINY": {}, 
        "PINZ": {} 
      }
    }
  ]
```

## Editor Tool Integration

### MCP Bridge Integration
Use `unreal-blueprint-mcp` for:
- Exporting blueprint definitions to JSON
- Validating pin types against expected signatures
- Detecting circular references
- Resolving undefined node IDs

### Action Tiering Guidelines
- **L2 (Medium Risk):** Blueprint modifications that change state - require sandbox undo capabilities
- **L1 (Low Risk):** Blueprint analysis and graph validation - automatic execution allowed
- **L3 (High Risk):** Blueprint-one-to-one replacements - require dual-control confirmation

## Files

- Create: `blueprint-analytics.md`
- References: `references/blueprint-textual-ir.md`, `references/blueprint-common-pitfalls.md}