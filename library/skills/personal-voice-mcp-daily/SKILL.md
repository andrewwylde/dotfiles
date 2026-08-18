---
name: personal-voice-mcp-daily
description: >-
  Daily personal-voice-model tick via Slack MCP harvest + local Ollama refine.
  Use when the user runs /loop 1d with MCP harvest, asks to harvest via Slack
  MCP for the voice model, or cannot use SLACK_USER_TOKEN search:read.
disable-model-invocation: true
---

# Personal voice — MCP daily tick

Keeps `~/.agent/personal-voice-model/voice-model.md` current when the shell
`run_daily.sh` path is unavailable (missing `search:read` on the user token).

Policy / apply / hard rules: see [personal-voice-model](../personal-voice-model/SKILL.md).
Ollama setup: [ollama-guide.md](../personal-voice-model/ollama-guide.md).

## Loop

```text
/personal-voice-mcp-daily
```

Or scheduled:

```text
/loop 1d /personal-voice-mcp-daily
```

Follow the **loop** skill for scheduling. This skill is the **tick body**.
Slash command: [personal-voice-mcp-daily.md](../../commands/personal-voice-mcp-daily.md).
## Tick (run once per day)

Fail closed without `config.json` → `slack_user_id` (expected: `U09TKBVFG3T`).

### 1. Harvest via Slack MCP

1. `GetMcpTools` for `plugin-slack-slack` / `slack_search_public_and_private`.
2. Search Andrew’s messages for the last **7 days**:

   ```text
   query: from:<@U09TKBVFG3T> after:YYYY-MM-DD
   content_types: messages
   include_context: false
   limit: 20
   sort: timestamp
   sort_dir: desc
   response_format: detailed
   ```

3. Paginate with `cursor` up to **5 pages** (≤100 msgs) unless empty sooner.
4. Save each page’s `results` markdown under `/tmp/pvm-mcp-raw/daily-PAGE.md`.
5. Parse + merge:

   ```bash
   SKILL=~/.cursor/skills/personal-voice-model/scripts
   mkdir -p /tmp/pvm-mcp-raw
   # parse each page → msgs JSON, then concat arrays into /tmp/pvm-mcp-raw/daily.msgs.json
   python3 "$SKILL/parse_slack_mcp_markdown.py" /tmp/pvm-mcp-raw/daily-1.md > /tmp/pvm-mcp-raw/p1.json
   # …merge pages…
   python3 "$SKILL/write_daily_harvest.py" --messages-json /tmp/pvm-mcp-raw/daily.msgs.json --days 7
   ```

6. Work-safe filter is in the writers (emoji-only drop, secret/email redaction).
   Skip HR/health/legal/comp/1:1 drama — do not put those texts in harvest.

### 2. Refine via Ollama

```bash
curl -sf http://127.0.0.1:11434/api/tags >/dev/null \
  || { echo "start ollama"; exit 1; }
python3 -u ~/.cursor/skills/personal-voice-model/scripts/refine_ollama.py \
  --root ~/.agent/personal-voice-model
```

- Decay **on** (default) for daily.
- Never edit **Hard rules**.

### 3. Report (brief)

- Messages kept, `last_refined_at`, patterns strengthened/decayed, snippets rotated.
- Do **not** dump raw Slack.

## Prefer shell when possible

If `SLACK_USER_TOKEN` (`xoxp-`) has `search:read`:

```bash
~/.cursor/skills/personal-voice-model/scripts/run_daily.sh
```

Use this MCP skill only when that path fails.

## Paths

| Path | Role |
|------|------|
| `~/.agent/personal-voice-model/config.json` | `slack_user_id`, ollama knobs |
| `~/.agent/personal-voice-model/harvest.json` | Daily harvest (MCP or API) |
| `~/.agent/personal-voice-model/voice-model.md` | Living model |
| `~/.agent/personal-voice-model/state.json` | Last refine metadata |
| `~/.cursor/skills/personal-voice-model/scripts/` | parse / write / refine helpers |
