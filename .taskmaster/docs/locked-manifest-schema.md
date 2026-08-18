# Locked decisions: Manifest schema (agent-sync task 5)

Auto-approved 2026-08-17 (user: approve recommended locks; no further review).

## Schema

- **Filename:** `manifest.toml` at item root (opt-in; missing = all valid Targets, no overlay).
- **Layout:** directory per item for all kinds:
  - `library/skills/<name>/SKILL.md` + optional `manifest.toml`
  - `library/commands/<name>/COMMAND.md` + optional `manifest.toml`
  - `library/agents/<name>/AGENT.md` + optional `manifest.toml`
  - `library/hooks/<pack>/manifest.toml` + scripts (+ nested `[pack]` / per-Target hook tables)
- **Target ids:** `claude` | `cursor` | `agents` | `opencode` | `pi` (reserve `agents`; v1 Fan-out may omit — see task 11).
- **Exclude-only Targets:** optional `exclude = ["pi", ...]` — no include list required.
- **Overlays (markdown kinds):**

```toml
exclude = ["pi"]

[overlays.cursor.frontmatter]
disable-model-invocation = true

body_append = """
<!-- cursor-only note -->
"""
```

- **Merge:** deep-merge frontmatter maps; overlay wins on conflict; body unchanged except optional `body_append`.
- **Hooks:** `kind` inferred as `hooks` from path; Manifest holds pack metadata + per-Target entrypoint payloads (absorbs hook-pack draft); config install still strip `_as` then append.
- **Cursor commands:** adapter maps Library `command` → Cursor skills path automatically.
- **Unsupported Target×kind:** skip + `verify` info (never hard-fail Fan-out for capability gaps).

## Worked examples

### Skill with Cursor-only overlay

```toml
# library/skills/personal-voice-model/manifest.toml
[overlays.cursor.frontmatter]
disable-model-invocation = true
```

### Hook pack excluding OpenCode

```toml
# library/hooks/skill-gates/manifest.toml
exclude = ["opencode", "pi"]
version = "1.0.0"
# per-Target entrypoint tables per research-hook-config-merge.md
```
