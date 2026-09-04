# Scripts

Executable sources live in [`scripts/`](scripts/):

| File | Role |
|------|------|
| [`harvest_slack.py`](scripts/harvest_slack.py) | Slack `search.messages` → `harvest.json` or weekly shards |
| [`refine_ollama.py`](scripts/refine_ollama.py) | Ollama merge into `voice-model.md` (hard rules preserved) |
| [`run_daily.sh`](scripts/run_daily.sh) | 7-day harvest + refine |
| [`run_backfill.sh`](scripts/run_backfill.sh) | N-day chunked harvest + staged refine (`--refine-only` skips harvest) |
| [`parse_slack_mcp_markdown.py`](scripts/parse_slack_mcp_markdown.py) | Parse Slack MCP search markdown → message JSON |
| [`write_mcp_shard.py`](scripts/write_mcp_shard.py) | Write one backfill shard + manifest entry |
| [`write_daily_harvest.py`](scripts/write_daily_harvest.py) | Write `harvest.json` from MCP message JSON |

See [ollama-guide.md](ollama-guide.md) for setup, token scopes, launchd, and the 6-month backfill runbook.
