---
name: personal-voice-model
description: >-
  Refine or apply Andrew's personal speech/writing voice model from Slack
  history. Use when the user invokes /personal-voice-model, asks to refine the
  voice model, runs /loop on this skill, or explicitly asks to write as them
  using the personal voice model.
disable-model-invocation: true
---

# Personal Voice Model

Living voice guidance for writing *as Andrew*. Artifacts live under
`~/.agent/personal-voice-model/` (not in any repo).

**Read [reference.md](reference.md)** for file schemas, redaction rules, and
Slack harvest details.

**Zero-token refine (recommended):** run the local Ollama pipeline in
[ollama-guide.md](ollama-guide.md) — daily `run_daily.sh`, one-time
`run_backfill.sh --days 180`. If `SLACK_USER_TOKEN` lacks `search:read`,
harvest via Slack MCP into `harvest/backfill/` then
`run_backfill.sh --refine-only`. Cursor `apply` stays optional.

## Modes

| Mode | When | Action |
|------|------|--------|
| `setup` | Missing/invalid config | Resolve Slack user ID → write `config.json` |
| `refine` | Default; `/loop 1d` ticks | Harvest last 7 days → merge+decay dossier |
| `apply` | User asks to write as them *with this skill invoked* | Read model → draft in voice |

If the user does not name a mode, infer: loop/refine language → `refine`;
draft/rewrite/speak-as-me → `apply`; first run / missing ID → `setup`.

## Paths

| File | Role |
|------|------|
| `~/.agent/personal-voice-model/config.json` | Slack user ID + knobs |
| `~/.agent/personal-voice-model/voice-model.md` | Hard rules + dossier + snippets |
| `~/.agent/personal-voice-model/state.json` | Last refine metadata |
| `~/.agent/personal-voice-model/templates/` | Local scaffolds |
| Skill `templates/` | Versioned scaffolds (copy into `~/.agent/...` on setup) |

## Fixed policy (do not renegotiate mid-run)

- **Sources:** channels the Slack bot can see + DMs **you** sent
- **Window:** last 7 days of *your* messages
- **Shape:** hybrid — sticky hard rules + descriptive dossier
- **Registers:** one core voice + soft dials (not separate full profiles)
- **Dimensions:** prosody, stance, structure; lexicon only if sticky (≥3× in week)
- **Evidence:** ≤6 short anonymized snippets; rotate
- **Updates:** merge + ~4-week decay; **never** edit hard rules in `refine`
- **Privacy:** work-safe — redact secrets/PII; skip HR/health/legal/comp/1:1 drama
- **Apply:** strong match; break only for safety/accuracy
- **Conflicts:** blend — project structure/checklists + your diction/stance
- **Invoke:** explicit only (`disable-model-invocation: true`)

## Setup

1. If `config.json` is missing, copy from `templates/config.json`.
2. Use Slack MCP (`slack_get_users` / `slack_get_user_profile`) to find Andrew’s user ID.
3. Write `slack_user_id` into `config.json`. **Fail closed** if unset — do not guess from display name alone on refine/apply.
4. If `voice-model.md` is missing, copy `templates/voice-model.md`.

## Refine (daily / loop)

Designed for: `/loop 1d /personal-voice-model refine` (or `/loop 1d` with this skill). Follow the **loop** skill for scheduling; this skill defines the tick body.

1. **Load** `config.json`, `voice-model.md`, `state.json` (if any).
2. **Fail closed** without `slack_user_id`.
3. **Harvest** (Slack MCP):
   - Confirm scopes first (see reference). On `missing_scope`, **stop**, write `state.json` with the error, and tell the user which scopes to add. Do not invent voice from memory.
   - `slack_list_channels` (paginate) — every channel the bot can see. If listing fails but `config.channel_ids` is set, scan that allowlist only.
   - For each channel: `slack_get_channel_history` with a high enough `limit`; keep messages where `user == slack_user_id` and `ts` within the last 7 days.
   - Include DM/IM conversations the API returns the same way; keep only messages **you** sent.
   - For threads you participated in, `slack_get_thread_replies` only as needed to understand *your* reply stance — do not store others’ text in the model.
4. **Filter out** bot messages, emoji-only noise, and work-safe exclusions (see reference).
5. **Analyze** only your retained text for prosody, stance, structure; note sticky lexicon (≥3×).
6. **Merge into dossier** (not hard rules):
   - Strengthen patterns seen this week; set/update `last_seen`.
   - Demote or remove patterns with `last_seen` older than ~4 weeks.
   - Refresh ≤6 anonymized snippets (redact names → roles/initials; strip links/secrets).
   - Update soft dials only when evidence is clear.
7. **Write** `voice-model.md` and `state.json` (`last_refined_at`, message counts, channels scanned).
8. **Report briefly:** channels scanned, messages kept, patterns strengthened/decayed, snippet rotations. Do not dump raw Slack.

## Apply

1. Read `voice-model.md` (and `config.json` only if needed).
2. Obey **Hard rules** strictly.
3. Match **Core voice** + relevant **soft dial** strongly.
4. If a project style guide/skill also applies: keep *their* structure/sections; keep *your* wording and stance.
5. Do not invent catchphrases from weak lexicon; use sticky lexicon sparingly.
6. Never paste stored snippets into the user-facing draft unless asked — they are calibration, not copy-paste.

## Loop tip

Prefer local Ollama so refine does not burn cloud tokens for the merge:

```bash
# once (bootstrap)
~/.cursor/skills/personal-voice-model/scripts/run_backfill.sh --days 180

# daily when SLACK_USER_TOKEN has search:read
~/.cursor/skills/personal-voice-model/scripts/run_daily.sh
```

When the user token lacks `search:read`, use the MCP daily skill (Cursor loop):

```text
/loop 1d /personal-voice-mcp-daily
```

See [personal-voice-mcp-daily](../personal-voice-mcp-daily/SKILL.md). On each tick:
harvest via Slack MCP → `harvest.json` → `refine_ollama.py` → short status.
Stop when the user says stop (per loop skill).

Cursor-only refine (no Ollama; burns cloud tokens for the merge):

```text
/loop 1d /personal-voice-model refine
```