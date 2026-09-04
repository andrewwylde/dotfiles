# UE5 MCP Streamable HTTP Protocol

## Port & URL

- Default: `http://127.0.0.1:8000/mcp`
- Override via `UNREAL_MCP_PORT` env var.

## Mandatory Initialize Handshake

POSTing directly to `/mcp` without an `initialize` call returns **HTTP 400**. Always handshake first:

1. POST `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"sssf-cli","version":"1.0"}}}` with header `Accept: application/json, text/event-stream`
2. Read `Mcp-Session-Id` from the response header.
3. Include `Mcp-Session-Id: <value>` on **all** subsequent requests in the same session.

## Capability Token

Read from `Saved/MCP/capability-token` (relative to project root).  
Send as request header: `X-MCP-Capability-Token: <token>`

## Tool Calls

```json
{
  "jsonrpc": "2.0",
  "id": <timestamp_ms>,
  "method": "call_tool",
  "params": {
    "toolset_name": "ActorTools",
    "tool_name": "get_selected_actors",
    "arguments": {}
  }
}
```

The meta-toolset is `ToolsetRegistry` — use `list_toolsets` to discover registered toolsets.

## Security Guard

Always validate console commands before sending via MCP:

```python
BLOCKLIST_REGEX = re.compile(r"(?i)\b(quit|exit|rmdir|remove|git\s+reset|git\s+clean)\b")
```

Raise `ValueError` and refuse to send if matched.

## Tool Search Mode vs. Direct Mode

In UE 5.8, `bEnableToolSearch=true` (default) returns meta-tools (`list_toolsets`, `describe_toolset`, `call_tool`). This is why an LLM only sees `AgentSkills` methods — it is querying the ToolsetRegistry, not a project-specific toolset. Use `list_toolsets` first to discover what toolsets are actually registered.

## UE 5.x Subsystem API (not deprecated)

`unreal.EditorLevelLibrary` is deprecated in UE 5.x. Use subsystems instead:

```python
# Camera
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
# Actors
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
```

## Stale DLL Safety

Live Coding can report "Patch Applied" while failing to load the `.patch_X.dll` into process memory. Always verify `Binaries/Win64/*.patch_X.dll` modification timestamps after a build. Never trust Live Coding log output alone.

## Physics Desync After Spawn/Move

Newly spawned/moved actors have `IsAsyncPhysicsStateCreated() == true`. Raycasting against newly placed geometry fails unless `comp.recreate_physics_state()` is called synchronously on all `PrimitiveComponent`s first.
