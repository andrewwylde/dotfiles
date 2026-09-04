# Blueprint Textual Intermediate Representation (IR) via MCP

Because Blueprint graphs are stored as binary `.uasset` files, modern AI integrations use specialized in-engine MCP servers (e.g. `unreal-blueprint-mcp`) to expose graphs as structured textual intermediate representations.

## MCP Intermediate Representation Format

```json
{
  "asset_path": "/Game/Blueprints/BP_PlayerCharacter",
  "graph_type": "UEdGraph_EventGraph",
  "nodes": [
    {
      "id": "K2Node_Event_BeginPlay_0",
      "type": "UK2Node_Event",
      "event_name": "ReceiveBeginPlay",
      "pins": [
        { "name": "OutputDelegate", "direction": "EGPD_Output", "type": "delegate" },
        { "name": "then", "direction": "EGPD_Output", "type": "exec", "linked_to": ["K2Node_CallFunction_InitStats_0.execute"] }
      ]
    },
    {
      "id": "K2Node_CallFunction_InitStats_0",
      "type": "UK2Node_CallFunction",
      "function_name": "InitializePlayerStats",
      "target_class": "UPlayerStatsComponent",
      "pins": [
        { "name": "execute", "direction": "EGPD_Input", "type": "exec", "linked_to": ["K2Node_Event_BeginPlay_0.then"] },
        { "name": "self", "direction": "EGPD_Input", "type": "object", "default_value": "Self" },
        { "name": "StartingHealth", "direction": "EGPD_Input", "type": "real", "default_value": "100.0" },
        { "name": "then", "direction": "EGPD_Output", "type": "exec", "linked_to": [] }
      ]
    }
  ]
}
```

---

## Primary MCP Tool Calls

| MCP Tool | Purpose | Risk Tier |
| :--- | :--- | :--- |
| `inspect_blueprint_graph` | Returns textual IR for specified graph (EventGraph, ConstructionScript, or Function). | Tier 1 (Autonomous) |
| `find_node_pins` | Queries available input/output pins and types on a target node. | Tier 1 (Autonomous) |
| `audit_blueprint_references` | Inspects hard vs soft object dependencies to prevent memory bloat. | Tier 1 (Autonomous) |
| `add_blueprint_node` | Instantiates a node within the graph schema. | Tier 2 (Sandboxed) |
| `connect_blueprint_pins` | Wires an output pin to an input pin, validating type compatibility. | Tier 2 (Sandboxed) |
| `set_node_pin_default` | Sets default scalar/vector/string parameter value on an unconnected input pin. | Tier 2 (Sandboxed) |
| `compile_blueprint` | Triggers editor compilation of the graph and returns diagnostic errors/warnings. | Tier 1 (Autonomous) |
| `delete_blueprint_asset` | Deletes the `.uasset` from the Content browser. | Tier 3 (Dual-Control) |

---

## Diagnostic Flow for Pass-by-Reference Bugs

When auditing functions in Blueprints:
1. Query `inspect_blueprint_graph` for the function graph.
2. Check struct input pins marked with "Pass-by-Reference" (diamond pin).
3. If an input pin is mutated inside the function without an explicit return assignment, flag the unintended side-effect warning.
