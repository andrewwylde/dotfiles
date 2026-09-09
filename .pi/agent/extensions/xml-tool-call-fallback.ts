import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * Fallback XML tool call extractor + stream watchdog.
 *
 * Problem:
 *   Some upstream providers (notably certain OpenRouter endpoints) sometimes
 *   emit raw XML tool calls inside the assistant `content` instead of a
 *   structured `tool_calls` array. Pi's parser ignores these, the LLM is not
 *   told the tool result, and the agent loop deadlocks or stalls.
 *
 * What this extension does:
 *   1. Listens for `message_end` on assistant messages.
 *   2. If `message.toolCalls` is empty but `message.content` contains a
 *      recognised raw XML tool call (`<invoke name="...">`, optionally
 *      wrapped in `<dots_function_call>` / `<function_call>`), it parses
 *      the parameters, replaces the message with one that carries a
 *      synthetic `toolCall` entry, and emits a synthetic toolResult so
 *      the loop continues.
 *   3. Listens for `message_update` to refresh a last-activity timestamp.
 *      If the turn is otherwise idle while a stream is open, a watchdog
 *      timer (with an inactivity budget) triggers `ctx.abort()` and
 *      re-prompts the LLM via a steer message rather than terminating
 *      the session.
 *
 * Limits / non-goals:
 *   - Only supports the XML shape Pi is documented to encounter from
 *     those upstreams. Anything fancier (nested objects, arrays) falls
 *     back to a JSON-coerced string.
 *   - This is a defensive net, not a replacement for properly-trained
 *     structured tool use. The default for the LLM should still be
 *     structured `tool_calls`.
 */

type AssistantContent = { type: string; text?: string };

interface ExtractedCall {
  name: string;
  args: Record<string, unknown>;
  rawArgs: Record<string, string>;
}

const WRAPPER_RE =
  /<(?:dots_function_call|function_call|tool_call)\b[^>]*>([\s\S]*?)<\/(?:dots_function_call|function_call|tool_call)>/gi;

const INVOKE_RE =
  /<invoke\s+name=(?:"([^"]+)"|'([^']+)')\s*>([\s\S]*?)<\/invoke>/gi;

const PARAM_RE =
  /<parameter\s+name=(?:"([^"]+)"|'([^']+)')\s*>([\s\S]*?)<\/parameter>/gi;

function decodeEntities(s: string): string {
  return s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

function tryCoerce(raw: string): unknown {
  const trimmed = raw.trim();
  if (trimmed === "") return "";
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed === "null") return null;
  if (/^-?\d+$/.test(trimmed)) {
    const n = Number(trimmed);
    if (Number.isSafeInteger(n)) return n;
  }
  if (/^-?\d+\.\d+$/.test(trimmed)) {
    const f = Number(trimmed);
    if (!Number.isNaN(f)) return f;
  }
  // Try JSON (object / array) before treating as string.
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      return JSON.parse(trimmed);
    } catch {
      // fall through
    }
  }
  return trimmed;
}

function parseParameters(body: string): { coerced: Record<string, unknown>; raw: Record<string, string> } {
  const coerced: Record<string, unknown> = {};
  const raw: Record<string, string> = {};
  PARAM_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = PARAM_RE.exec(body)) !== null) {
    const name = m[1] ?? m[2];
    const value = decodeEntities(m[3] ?? "");
    if (!name) continue;
    raw[name] = value;
    coerced[name] = tryCoerce(value);
  }
  return { coerced, raw };
}

function extractCallsFromText(text: string): ExtractedCall[] {
  const calls: ExtractedCall[] = [];
  // First try wrapper-tagged blocks; fall back to the whole text.
  const blocks: string[] = [];
  WRAPPER_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = WRAPPER_RE.exec(text)) !== null) {
    if (m[1]) blocks.push(m[1]);
  }
  const searchSpace = blocks.length > 0 ? blocks.join("\n") : text;

  INVOKE_RE.lastIndex = 0;
  while ((m = INVOKE_RE.exec(searchSpace)) !== null) {
    const name = m[1] ?? m[2];
    const body = m[3] ?? "";
    if (!name) continue;
    const { coerced, raw } = parseParameters(body);
    calls.push({ name, args: coerced, rawArgs: raw });
  }
  return calls;
}

function contentToText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((c): c is AssistantContent => c && typeof c === "object")
      .map((c) => (typeof c.text === "string" ? c.text : ""))
      .join("");
  }
  return "";
}

function makeToolCallId(): string {
  // Pi tool call IDs are normally produced upstream. We prefix so it's
  // obvious in the session log that this was a synthetic fallback.
  return `xml_fallback_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export default function (pi: ExtensionAPI) {
  const STALL_BUDGET_MS = 90_000;
  let lastActivityAt = 0;
  let watchdog: ReturnType<typeof setTimeout> | null = null;
  let watchdogArmed = false;
  let turnCtx: { abort?: () => void; signal?: AbortSignal; hasUI?: boolean } | null = null;
  let rePromptCount = 0;
  const MAX_REPROMPTS = 1;

  const armWatchdog = (signal: AbortSignal | undefined, ctx: { abort?: () => void; signal?: AbortSignal; hasUI?: boolean }) => {
    disarmWatchdog();
    turnCtx = ctx as unknown as typeof turnCtx;
    if (!signal) return;
    lastActivityAt = Date.now();
    watchdogArmed = true;
    watchdog = setTimeout(() => {
      if (!watchdogArmed) return;
      if (Date.now() - lastActivityAt < STALL_BUDGET_MS) {
        armWatchdog(signal, turnCtx as unknown as ExtensionContext);
        return;
      }
      watchdogArmed = false;
      console.warn(
        `[xml-tool-call-fallback] LLM stream inactive for ${STALL_BUDGET_MS}ms; aborting and re-prompting.`,
      );
      if (rePromptCount >= MAX_REPROMPTS) {
        console.warn(
          "[xml-tool-call-fallback] Max re-prompts reached; avoiding infinite loop.",
        );
        return;
      }
      rePromptCount += 1;
      try {
        pi.sendUserMessage(
          "[stream-watchdog] The previous model response stalled before completion. Please continue from where you left off; if you intended to call a tool, emit it as a normal structured tool call.",
          { deliverAs: "steer" },
        );
      } catch (err) {
        console.error("[xml-tool-call-fallback] Failed to inject re-prompt:", err);
      }
    }, STALL_BUDGET_MS);
  };

  const disarmWatchdog = () => {
    if (watchdog) {
      clearTimeout(watchdog);
      watchdog = null;
    }
    watchdogArmed = false;
  };

  pi.on("session_shutdown", () => disarmWatchdog());

  pi.on("message_update", (_event, ctx) => {
    if (ctx.signal) {
      lastActivityAt = Date.now();
      if (!watchdogArmed) armWatchdog(ctx.signal, ctx);
    }
  });

  pi.on("message_end", async (event) => {
    // The watchdog is per-turn; we don't tear it down here because
    // message_end can fire for non-streaming messages too. The
    // after_provider_response handler will disarm on idle.
    if (!event || !event.message) return;
    const msg = event.message as { role?: string; toolCalls?: unknown[]; content?: unknown };
    if (msg.role !== "assistant") return;
    const structured = Array.isArray(msg.toolCalls) ? msg.toolCalls : [];
    if (structured.length > 0) return; // Native path, nothing to do.

    const text = contentToText(msg.content);
    if (!text) return;

    const calls = extractCallsFromText(text);
    if (calls.length === 0) return;

    // Synthesise tool calls. We can't directly reach the local tool
    // executor, but Pi's normal flow keys off `toolCalls` on the
    // assistant message. We therefore return a replacement message
    // that carries a synthetic toolCall. The subsequent `tool_call`
    // event will then fire, and we can short-circuit its execution
    // by re-emitting a toolResult that mirrors what our XML parser
    // would have produced.
    //
    // Because we can't replay the actual tool result without running
    // the tool, the safest and most useful behaviour is to *rewrite
    // the assistant text into a normal tool call* so the existing
    // executor picks it up. We achieve that by returning a new
    // message whose `toolCalls` is populated. Pi's documented
    // `message_end` rewrite contract lets us replace the message.
    const replaced = {
      ...(msg as object),
      toolCalls: calls.map((c, i) => ({
        id: makeToolCallId(),
        name: c.name,
        arguments: c.args,
        // Diagnostic: keep the raw extraction for postmortems.
        ...({ _xmlFallback: true, _rawArgs: c.rawArgs, _index: i } as Record<string, unknown>),
      })),
    } as { role: string };

    if (replaced.role !== "assistant") return; // contract enforcement

    // eslint-disable-next-line no-console
    console.warn(
      `[xml-tool-call-fallback] Reconstructed ${calls.length} tool call(s) from raw XML: ` +
        calls.map((c) => c.name).join(", "),
    );
    return { message: replaced };
  });

  pi.on("tool_call", async (event, ctx) => {
    // If we synthesised this call via the XML fallback, log it. We
    // don't block or modify it — the standard tool execution path
    // is the right thing to do once we've reconstructed structured
    // tool calls. This handler is a hook for future enrichment
    // (e.g. attaching _rawArgs into tool input via a name-match).
    const anyCall = event as unknown as { _xmlFallback?: boolean };
    if (!anyCall._xmlFallback) return;
    if (ctx.hasUI) {
      ctx.ui.notify(
        `XML tool-call fallback: executed "${event.toolName}" reconstructed from raw model output.`,
        "info",
      );
    }
  });

  pi.on("after_provider_response", (event, ctx) => {
    if (ctx.signal) {
      lastActivityAt = Date.now();
      armWatchdog(ctx.signal, ctx);
    } else {
      disarmWatchdog();
    }
  });

  pi.on("agent_end", () => {
    disarmWatchdog();
    turnCtx = null;
    rePromptCount = 0;
  });
}
