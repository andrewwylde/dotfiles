---
description: "Daily personal-voice tick via Slack MCP harvest + Ollama refine"
---

# Personal voice — MCP daily

Run the `personal-voice-mcp-daily` skill once (this turn).

Follow the skill exactly:

1. Harvest last 7 days of Andrew’s Slack via Slack MCP search
2. Write `~/.agent/personal-voice-model/harvest.json` using the skill scripts
3. Run `refine_ollama.py` (decay on; never edit Hard rules)
4. Brief status only — no raw Slack dump

For a daily schedule in Cursor:

```text
/loop 1d /personal-voice-mcp-daily
```
