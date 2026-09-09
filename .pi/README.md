# Pi Coding Agent Extensions

This directory tracks custom extensions for the [Pi coding agent](https://github.com/badlogic/pi) (`@earendil-works/pi-coding-agent`).

## Extensions

### `xml-tool-call-fallback.ts`
* **Path:** `.pi/agent/extensions/xml-tool-call-fallback.ts`
* **Target:** `~/.pi/agent/extensions/xml-tool-call-fallback.ts`

#### Problem
Certain upstream models (e.g. via OpenRouter) occasionally emit raw XML tool calls inside the assistant message content (e.g. `<invoke name="...">...<parameter name="...">...</parameter></invoke>`) rather than standard structured `tool_calls`. Pi's parser ignores these raw strings, resulting in missing tool invocations, missing tool results, and deadlocked or stalled agent loops.

#### Capabilities
1. **Fallback Tool Call Reconstitution (`message_end`)**:
   - Inspects assistant messages lacking structured `toolCalls`.
   - Extracts raw `<invoke name="...">`, `<dots_function_call>`, `<function_call>`, and `<tool_call>` blocks.
   - Decodes XML entities (`&lt;`, `&gt;`, `&quot;`, `&#39;`, `&amp;`) and coerces arguments (JSON, numbers, booleans, null, strings).
   - Replaces the assistant message with a rewritten message containing synthetic structured `toolCalls` (`_xmlFallback: true`).
   - Pi's execution engine seamlessly executes the tool call and returns the result to the model.

2. **Stream Watchdog & Auto-Steer (`message_update`, `after_provider_response`)**:
   - Monitors streaming activity with an inactivity timeout (`STALL_BUDGET_MS = 90_000`).
   - If the stream stalls mid-generation, aborts the hanging turn and injects a steer message (`deliverAs: "steer"`) requesting the model to resume and use structured tool calling.
   - Bounded by `MAX_REPROMPTS = 1` to prevent infinite recovery loops.

3. **Lifecycle Management (`tool_call`, `agent_end`, `session_shutdown`)**:
   - Emits UI notifications when a tool call is executed via XML fallback.
   - Disarms the watchdog and clears turn state upon agent turn or session termination.
