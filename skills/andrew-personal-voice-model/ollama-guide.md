# Personal voice model — local Ollama guide

Zero Cursor/cloud tokens for the **refine** loop. Harvest Slack with the Web API, merge the dossier with a local OSS model via Ollama. Artifacts stay under `~/.agent/personal-voice-model/`.

Cursor `/personal-voice-model apply` is still optional when you want help drafting *as you*.

## Architecture

```text
SLACK_USER_TOKEN  →  harvest_slack.py  →  harvest.json / harvest/backfill/*.json
                                              ↓
voice-model.md  →  refine_ollama.py  →  Ollama (qwen2.5:14b)  →  voice-model.md
                                              ↓
                                         state.json
```

- **Daily:** last 7 days, one harvest + one refine (decay on).
- **Backfill (6 months):** 26 weekly shards, refine oldest→newest with `--no-decay`, final pass with decay.

## Prerequisites

1. **Ollama** (you already have the binary at `/opt/homebrew/bin/ollama`):

   ```bash
   brew services start ollama   # or: ollama serve
   ollama pull qwen2.5:14b
   ```

2. **Slack user token** (`xoxp-…`), not a bot token. Bot tokens cannot search *your* DMs.

   Create/open a Slack app → **OAuth & Permissions** → **User Token Scopes**:

   | Scope | Why |
   |-------|-----|
   | `search:read` | `search.messages` harvest |
   | `channels:history` | public channels you can see |
   | `groups:history` | private channels |
   | `im:history` | DMs you sent |
   | `mpim:history` | multi-person DMs |
   | `channels:read` / `groups:read` | channel metadata |
   | `users:read` | identity checks |

   Reinstall to workspace, copy the **User OAuth Token**.

3. **Config** — `~/.agent/personal-voice-model/config.json` already has `slack_user_id: U09TKBVFG3T`. Add:

   ```json
   {
     "ollama_model": "qwen2.5:14b",
     "ollama_host": "http://127.0.0.1:11434",
     "backfill_days": 180,
     "ollama_max_messages": 120
   }
   ```

4. **Token env** — never commit this. Either export in your shell or create `~/.agent/personal-voice-model/.env`:

   ```bash
   SLACK_USER_TOKEN=xoxp-...
   ```

## Install scripts (once)

Scripts live next to this skill (dotfiles-linked):

```text
~/.cursor/skills/personal-voice-model/scripts/
  harvest_slack.py
  refine_ollama.py
  run_daily.sh
  run_backfill.sh
```

Scripts are already on disk under `scripts/`. Ensure dirs exist:

```bash
mkdir -p ~/.agent/personal-voice-model/{logs,harvest/backfill}
```

## Bootstrap: 6-month backfill

Slack search will not return “everything in 180 days” in one query. Backfill **slices weeks**, then refines chronologically.

```bash
export SLACK_USER_TOKEN=xoxp-...   # if not in .env; needs search:read
~/.cursor/skills/personal-voice-model/scripts/run_backfill.sh --days 180
```

### No user token / missing `search:read`?

Use Cursor Slack MCP (`slack_search_public_and_private` as you) to fill weekly shards under `~/.agent/personal-voice-model/harvest/backfill/`, then refine only:

```bash
~/.cursor/skills/personal-voice-model/scripts/run_backfill.sh --days 180 --refine-only
```

MCP harvest is page-capped (~20 msgs/week unless you paginate); enough for voice signal, not a full export. Shard helpers: `parse_slack_mcp_markdown.py`, `write_mcp_shard.py`.

What happens:

1. `harvest_slack.py --days 180 --chunk weeks`  
   - Query: `from:<@U09TKBVFG3T> after:YYYY-MM-DD before:YYYY-MM-DD`  
   - Writes `~/.agent/personal-voice-model/harvest/backfill/YYYY-Www.json`  
   - Updates `harvest/backfill/manifest.json`
2. For each shard **oldest → newest**: `refine_ollama.py --harvest <shard> --no-decay`  
   - Hard rules section is **never** rewritten  
   - Snippet bank stays ≤ 6  
3. Final pass: refine last shard again **with decay on** (4-week policy)
4. Resume: re-run the same command; already-refined shards are skipped

Logs: `~/.agent/personal-voice-model/logs/backfill-YYYYMMDD.log`

**Wipe and redo** (keeps Hard rules if you restore them by hand):

```bash
rm -rf ~/.agent/personal-voice-model/harvest/backfill
# optionally reset Core voice / Soft dials / Evidence / Pattern ledger in voice-model.md
~/.cursor/skills/personal-voice-model/scripts/run_backfill.sh --days 180
```

## Daily refine (after backfill)

```bash
~/.cursor/skills/personal-voice-model/scripts/run_daily.sh
```

Equivalent:

```bash
python3 ~/.cursor/skills/personal-voice-model/scripts/harvest_slack.py --days 7
python3 ~/.cursor/skills/personal-voice-model/scripts/refine_ollama.py
```

### launchd (09:00 local daily)

Save as `~/Library/LaunchAgents/com.andrewwylde.personal-voice-model.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.andrewwylde.personal-voice-model</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>source "$HOME/.zshrc" 2>/dev/null; exec "$HOME/.cursor/skills/personal-voice-model/scripts/run_daily.sh"</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/REPLACE/Library/Logs/personal-voice-model.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/REPLACE/Library/Logs/personal-voice-model.err.log</string>
</dict>
</plist>
```

```bash
# fix REPLACE → your home user, then:
launchctl unload ~/Library/LaunchAgents/com.andrewwylde.personal-voice-model.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.andrewwylde.personal-voice-model.plist
```

Ensure `SLACK_USER_TOKEN` is available to non-interactive shells (`.env` under `~/.agent/personal-voice-model/` is loaded by the Python harvest script).

## Policy reminder (same as Cursor skill)

- Hard rules: **hand-edit only**
- Soft dials + dossier: automated
- Prosody / stance / structure; lexicon only if sticky (≥3× in window)
- ≤6 anonymized snippets
- Work-safe exclusions (HR/health/legal/comp/1:1 drama)
- Merge + ~4-week decay on daily / final backfill pass

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `could not connect to ollama` | `brew services start ollama` or `ollama serve` |
| `missing_scope` / `not_allowed_token_type` | Use **user** token with `search:read` (+ history scopes); reinstall app |
| Bot token warning | Set `SLACK_USER_TOKEN` (`xoxp-`), not `SLACK_BOT_TOKEN` |
| Non-JSON from Ollama | See `~/.agent/personal-voice-model/logs/last-ollama-raw.txt`; retry or try `llama3.1:8b` |
| Empty harvest | Confirm you’re in the workspace, token is for Parable, and you posted in the window |
| Rate limits | Scripts sleep on `ratelimited`; backfill can take a while — leave it running |

## Manual one-off (no shell wrappers)

```bash
# harvest one week for debugging
python3 ~/.cursor/skills/personal-voice-model/scripts/harvest_slack.py --days 7

# refine without decay (inspect merge)
python3 ~/.cursor/skills/personal-voice-model/scripts/refine_ollama.py --no-decay

# refine with decay (normal daily)
python3 ~/.cursor/skills/personal-voice-model/scripts/refine_ollama.py
```

## Related

- Skill policy: [SKILL.md](SKILL.md)
- Schemas / redaction: [reference.md](reference.md)
- Living model: `~/.agent/personal-voice-model/voice-model.md`
