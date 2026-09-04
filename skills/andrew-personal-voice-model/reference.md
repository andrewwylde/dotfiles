# Personal Voice Model — Reference

## Directory layout

```
~/.agent/personal-voice-model/
├── config.json          # Required for refine
├── voice-model.md       # Living model
├── state.json           # Last refine metadata
└── templates/           # Scaffolds (copied by skill on first setup)
    ├── config.json
    └── voice-model.md
```

Skill source: `~/.cursor/skills/personal-voice-model/` (dotfiles-linked).

## config.json

```json
{
  "slack_user_id": "U0123456789",
  "lookback_days": 7,
  "decay_weeks": 4,
  "max_snippets": 6,
  "sticky_lexicon_min_count": 3
}
```

| Field | Meaning |
|-------|---------|
| `slack_user_id` | Your Slack member ID. Required. Fail closed if empty. |
| `lookback_days` | Harvest window (default 7). |
| `decay_weeks` | Demote/remove dossier patterns not seen this long (default 4). |
| `max_snippets` | Cap on evidence snippets (default 6). |
| `sticky_lexicon_min_count` | Min occurrences in-window to record a phrase (default 3). |
| `channel_ids` | Optional allowlist of channel IDs when `slack_list_channels` is unavailable. |
| `ollama_model` | Local model for zero-token refine (default `qwen2.5:14b`). |
| `ollama_host` | Ollama HTTP host (default `http://127.0.0.1:11434`). |
| `backfill_days` | Default window for `run_backfill.sh` (default `180`). |
| `ollama_max_messages` | Cap messages sent to Ollama per refine call (default `120`). |

## voice-model.md schema

Keep this structure stable so merges stay mechanical:

```markdown
# Personal voice model

- Last refined: ISO-8601
- Lookback days: 7
- Decay weeks: 4

## Hard rules

Hand-edited only. Refine mode must not add, edit, or delete bullets here.

- …

## Core voice

### Prosody
Length, pacing, punctuation, emoji density, hedges.

### Stance
Directness, warmth, humor, how you disagree / say no / decide / defer.

### Structure
Lead-with-point vs build-up; bullets vs prose; openings/closings.

### Lexicon
Only sticky phrases (≥ sticky_lexicon_min_count in a week). Prefer “use / avoid” over long lists.

## Soft dials

Short notes, not separate profiles. Examples:
- **More terse** — …
- **More warm** — …
- **More formal** — …

## Evidence snippets

Max `max_snippets`. Each entry:
- Dial tag (optional): terse | warm | formal | default
- Anonymized 1–2 sentence excerpt
- Why it calibrates (one line)

## Pattern ledger

Machine-friendly decay tracking (markdown table is fine):

| id | dimension | summary | strength | last_seen |
|----|-----------|---------|----------|-----------|
| … | prosody | … | strong\|medium\|weak | YYYY-MM-DD |
```

### Strength rules

- **strong** — clear, repeated in current window
- **medium** — present but inconsistent
- **weak** — fading; candidate for removal at next decay pass

On refine: bump strength / refresh `last_seen` when observed; after `decay_weeks` without observation, step down one tier or delete.

## state.json

```json
{
  "last_refined_at": "2026-07-30T18:00:00-06:00",
  "lookback_days": 7,
  "channels_scanned": 0,
  "messages_kept": 0,
  "patterns_strengthened": 0,
  "patterns_decayed": 0,
  "snippets_rotated": 0
}
```

## Slack harvest notes

Available MCP tools (approximate): `slack_list_channels`, `slack_get_channel_history`, `slack_get_thread_replies`, `slack_get_users`, `slack_get_user_profile`.

### Required bot scopes (fail closed)

Refine needs history. If MCP returns `missing_scope`, stop and report — do not invent voice from memory or old transcripts.

| Scope | Why |
|-------|-----|
| `users:read` | Resolve / confirm `slack_user_id` |
| `channels:read` | List public channels |
| `groups:read` | List private channels the bot is in |
| `channels:history` | Read public channel messages |
| `groups:history` | Read private channel messages |
| `im:history` | Read DMs you sent (required for DM harvest) |
| `mpim:history` | Read multi-person DMs |

Optional: `users.profile:read` for profile confirmation during setup.

If `slack_list_channels` fails but history works, fall back to `config.json` → `channel_ids` allowlist (optional array of channel IDs) and scan those only. Prefer fixing scopes so listing works.

**No server-side time filter** on channel history in current MCP — pull with a sufficient `limit`, then filter client-side:

- Keep `user === config.slack_user_id`
- Keep `ts` ≥ (now − lookback_days)
- Drop subtypes that are not user text (bots, joins, etc.) when present

**DMs:** Include IM/DM channels returned by list APIs the bot can access. Still keep only messages you sent.

**Threads:** Use replies sparingly for *your* stance in context. Never store coworkers’ verbatim text in `voice-model.md`.

**Pagination:** Follow cursors on channel list until exhausted or a sane safety cap (document in `state.json` if capped).

## Redaction & exclusions

### Always redact before writing snippets or notes

- Tokens, passwords, API keys, cookies
- Emails, phone numbers, street addresses
- Customer/account identifiers, raw URLs with secrets
- Full names of coworkers → role or initials (e.g. “PM”, “J.”)

### Skip entirely (do not analyze or quote)

- Personnel / performance / hiring
- Health
- Legal risk / privilege-adjacent
- Compensation
- Private 1:1 drama or emotionally sensitive conflict dumps
- Content that is only emoji/reactions with no prose

When in doubt, skip the message. Voice signal is not worth the leak.

## Apply blend rule

When a project skill or style guide applies alongside this model:

| Layer | Source |
|-------|--------|
| Sections, checklists, required headings, CI/PR templates | Project |
| Diction, stance, pacing, hedges, how you disagree | Voice model |

Safety and factual accuracy always override voice.

## Anti-patterns

- Rewriting **Hard rules** during refine
- Storing > `max_snippets` quotes
- Building a lexicon from one-off jokes
- Dumping raw Slack into the chat response
- Guessing `slack_user_id` from a similar display name
- Quiet-week **replace** of the whole dossier (use merge+decay)
