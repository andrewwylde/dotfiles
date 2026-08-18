# Hook Config Merge — Claude Code & Cursor

> Research for Task Master task #3 (`agent-sync` tag).
> Answers: what file formats and merge strategies let agent-sync install Hook packs
> into Claude Code and Cursor safely — tagged keys, round-trip idempotency, uninstall
> — without clobbering hand edits.

---

## 1. File Locations and Formats

### 1.1 Cursor — `~/.cursor/hooks.json`

Single file. `version: 1` is required at the root; Cursor ignores files with a
missing or wrong version. The `hooks` object maps event name (camelCase) to a
**flat array of entry objects**.

```jsonc
// ~/.cursor/hooks.json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./hooks/block-worktree-remove.sh",
        "matcher": "worktree\\s+(remove|rm)\\b",
        "failClosed": true,
        "timeout": 10
      }
    ],
    "sessionStart": [
      {
        "command": "/Users/andrewwylde/.superconductor/hooks/cursor-notify.sh"
      }
    ]
  }
}
```

Each entry object fields (all optional except `command`):

| Field | Type | Notes |
|---|---|---|
| `command` | string | Shell command; user hooks run from `~/.cursor/`, project from repo root |
| `matcher` | string | JS-style regex; omit to run on every event |
| `failClosed` | bool | Block on crash/timeout when `true`; default fail-open |
| `timeout` | int | Seconds; Cursor default is 30 |
| `type` | string | `"command"` or `"prompt"`; defaults to `"command"` |
| `loop_limit` | int | For `stop`/`subagentStop` follow-up loops |

**Important:** Cursor evaluates `matcher` as `new RegExp(matcher).test(input)` —
JavaScript regex syntax, not POSIX. Use `\s`, `\b`, not `[[:space:]]`.

### 1.2 Claude Code — `~/.claude/settings.json` (hooks section)

Hooks live inside the larger `settings.json`. The `hooks` object maps event name
(PascalCase) to an **array of event-group objects**. Each event group wraps one or
more hook definitions in a nested `hooks` array.

```jsonc
// ~/.claude/settings.json — hooks section only
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/worktree-awareness-session-start.sh",
            "timeout": 5,
            "statusMessage": "Checking for worktree..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/worktree-read-redirect.sh",
            "timeout": 5,
            "statusMessage": "Checking worktree path..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/dangerous_command_safety.py",
            "timeout": 5,
            "statusMessage": "Checking command safety..."
          }
        ]
      }
    ]
  }
}
```

**Two-level nesting:**

| Level | Object shape | Purpose |
|---|---|---|
| Outer (event group) | `{ matcher?, hooks: [...] }` | One matcher → one or more hook commands |
| Inner (hook def) | `{ type, command, timeout?, statusMessage? }` | Actual invocation |

Multiple event groups under one event name all fire; Claude evaluates them in
array order. A group fires only when its `matcher` matches (or always when
`matcher` is absent).

**Event name case differences:**

| Cursor event | Claude Code event |
|---|---|
| `beforeShellExecution` | `PreToolUse` (matcher: `"Bash"`) |
| `sessionStart` | `SessionStart` |
| `preToolUse` | `PreToolUse` |
| `postToolUse` | `PostToolUse` |
| `stop` | `Stop` |

Claude Code does not have a direct equivalent of Cursor's
`beforeShellExecution`; the closest is `PreToolUse` with `matcher: "Bash"`.

---

## 2. The Tag Field: `_as`

JSON doesn't support comments, but both Claude Code and Cursor pass unknown
fields through without error (confirmed from live `~/.cursor/hooks.json` and
`~/.claude/settings.json` in this repo). agent-sync uses a single marker field
`_as` on the **installable unit** of each target:

- **Cursor**: tag on the flat entry object (the whole entry is the unit)
- **Claude Code**: tag on the outer event-group object (the whole group is the unit)

### Tag format

```
"_as": "agent-sync:<pack-name>:<semver>:<event>:<ordinal>"
```

Examples:
```
"_as": "agent-sync:skill-gates:1.0.0:beforeShellExecution:0"
"_as": "agent-sync:skill-gates:1.0.0:PreToolUse:0"
"_as": "agent-sync:skill-gates:1.0.0:PreToolUse:1"
```

Components:
- `agent-sync` — fixed namespace; identifies agent-sync ownership
- `pack-name` — Hook pack name (e.g. `skill-gates`, `worktree-guard`)
- `semver` — pack version; allows upgrade detection
- `event` — the exact event key for this target
- `ordinal` — 0-based position within this pack × event pair; handles packs that
  register multiple entries for the same event

**Uninstall key:** strip ordinal; any `_as` value starting with
`"agent-sync:<pack-name>:"` belongs to this pack across all events and versions.

---

## 3. Merge Algorithm

### 3.1 Pseudocode (target-agnostic)

```python
def install(config_path, hook_pack, target):
    """
    Idempotently install a Hook pack into a target's hook config.
    Preserves all entries that do NOT carry an _as tag for this pack.
    """
    config = read_json(config_path)  # {} if file absent
    hooks_map = config.setdefault("hooks", {})

    for event, new_entries in hook_pack.entries_for(target).items():
        existing = hooks_map.setdefault(event, [])

        # 1. Strip any previously installed entries for this pack (any version)
        prefix = f"agent-sync:{hook_pack.name}:"
        kept = [e for e in existing if not managed_by_pack(e, prefix, target)]

        # 2. Tag new entries
        tagged = [tag(e, hook_pack, event, i, target) for i, e in enumerate(new_entries)]

        # 3. Append after hand-edits (preserves user ordering)
        hooks_map[event] = kept + tagged

    # Preserve other top-level fields (permissions, model, sandbox, etc.)
    config["hooks"] = hooks_map
    if target == "cursor":
        config.setdefault("version", 1)

    write_json_atomic(config_path, config)


def uninstall(config_path, pack_name, target):
    config = read_json(config_path)
    if "hooks" not in config:
        return
    prefix = f"agent-sync:{pack_name}:"
    for event in list(config["hooks"].keys()):
        config["hooks"][event] = [
            e for e in config["hooks"][event]
            if not managed_by_pack(e, prefix, target)
        ]
        # Remove empty event lists to keep the file tidy (optional)
        if not config["hooks"][event]:
            del config["hooks"][event]
    write_json_atomic(config_path, config)


def managed_by_pack(entry, prefix, target):
    """Return True if the entry was installed by the pack identified by prefix."""
    if target == "claude":
        # Tag lives on the outer event-group object
        return entry.get("_as", "").startswith(prefix)
    else:
        # Cursor: tag lives on the flat entry
        return entry.get("_as", "").startswith(prefix)


def tag(entry, hook_pack, event, ordinal, target):
    tagged = dict(entry)  # shallow copy
    tagged["_as"] = f"agent-sync:{hook_pack.name}:{hook_pack.version}:{event}:{ordinal}"
    return tagged
```

### 3.2 Atomic write

Always write via a temp file + rename to avoid a torn state if the process
is killed mid-write. Both targets load the file lazily, so a rename swap is
safe on macOS (POSIX rename is atomic).

```python
import json, os, tempfile

def write_json_atomic(path, data):
    dir_ = os.path.dirname(path) or "."
    os.makedirs(dir_, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise
```

---

## 4. Before / After Examples

### 4.1 Cursor — install `skill-gates` pack v1.0.0

**Hook pack definition (library/hooks/skill-gates/hook-pack.json):**
```json
{
  "name": "skill-gates",
  "version": "1.0.0",
  "targets": {
    "cursor": {
      "preToolUse": [
        {
          "command": "~/.cursor/skills/_shared/hooks/enforce-gate.sh",
          "matcher": "StrReplace|Write|EditNotebook",
          "failClosed": true,
          "timeout": 10
        }
      ]
    }
  }
}
```

**Before (existing `~/.cursor/hooks.json`):**
```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./hooks/block-worktree-remove.sh",
        "matcher": "worktree\\s+(remove|rm)\\b"
      }
    ],
    "preToolUse": [
      {
        "command": "/Users/andrewwylde/.superconductor/hooks/cursor-notify.sh"
      }
    ]
  }
}
```

**After (agent-sync installs skill-gates v1.0.0):**
```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./hooks/block-worktree-remove.sh",
        "matcher": "worktree\\s+(remove|rm)\\b"
      }
    ],
    "preToolUse": [
      {
        "command": "/Users/andrewwylde/.superconductor/hooks/cursor-notify.sh"
      },
      {
        "command": "~/.cursor/skills/_shared/hooks/enforce-gate.sh",
        "matcher": "StrReplace|Write|EditNotebook",
        "failClosed": true,
        "timeout": 10,
        "_as": "agent-sync:skill-gates:1.0.0:preToolUse:0"
      }
    ]
  }
}
```

**What changed:** one new entry appended to `preToolUse`; the hand-edited
`beforeShellExecution` entry and the `cursor-notify` entry are untouched.

**Re-running install (idempotent):** the old `"_as": "agent-sync:skill-gates:..."` entry is
stripped first, then the same entry is re-appended. Net result: identical file.

**Upgrading to v1.1.0:** old entry (tagged `:1.0.0:`) is stripped; new entry
(tagged `:1.1.0:`) is appended. Position may shift to end, but that's safe for
Cursor (hooks run in array order; ordering relative to hand-edits is preserved).

**Uninstalling:** any entry where `_as` starts with `"agent-sync:skill-gates:"`
is removed; the `cursor-notify` entry remains.

---

### 4.2 Claude Code — install `skill-gates` pack v1.0.0

**Hook pack definition for Claude (library/hooks/skill-gates/hook-pack.json):**
```json
{
  "name": "skill-gates",
  "version": "1.0.0",
  "targets": {
    "claude": {
      "PreToolUse": [
        {
          "matcher": "Write|Edit",
          "hooks": [
            {
              "type": "command",
              "command": "python3 ~/.claude/hooks/file_safety.py",
              "timeout": 5,
              "statusMessage": "Checking file safety..."
            }
          ]
        }
      ]
    }
  }
}
```

**Before (excerpt from `~/.claude/settings.json`):**
```json
{
  "model": "sonnet",
  "permissions": { "allow": [], "deny": [], "defaultMode": "auto" },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/worktree-awareness-session-start.sh",
            "timeout": 5,
            "statusMessage": "Checking for worktree..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/dangerous_command_safety.py",
            "timeout": 5,
            "statusMessage": "Checking command safety..."
          }
        ]
      }
    ]
  }
}
```

**After (agent-sync installs skill-gates v1.0.0):**
```json
{
  "model": "sonnet",
  "permissions": { "allow": [], "deny": [], "defaultMode": "auto" },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/worktree-awareness-session-start.sh",
            "timeout": 5,
            "statusMessage": "Checking for worktree..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/dangerous_command_safety.py",
            "timeout": 5,
            "statusMessage": "Checking command safety..."
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "_as": "agent-sync:skill-gates:1.0.0:PreToolUse:0",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/file_safety.py",
            "timeout": 5,
            "statusMessage": "Checking file safety..."
          }
        ]
      }
    ]
  }
}
```

**What changed:** one new event-group appended to `PreToolUse`; `_as` is on the
outer event-group object (not inside the inner `hooks` array). The `SessionStart`
entry and the hand-edited `Bash` entry are untouched. All non-hook root keys
(`model`, `permissions`) survive.

**Re-running / upgrading / uninstalling:** same logic as Cursor — prefix-strip
on outer `_as`, re-append. Because `settings.json` contains many other top-level
keys, the merge must only touch `hooks.*` and leave everything else intact.

---

## 5. Edge Cases and Rules

### 5.1 File absent

If `~/.cursor/hooks.json` does not exist, create it with `{ "version": 1, "hooks": {} }`
and proceed. If `~/.claude/settings.json` does not exist, create it with `{ "hooks": {} }`.
Never write a bare `{}` as the hooks object.

### 5.2 Event key absent

If the target event key (`preToolUse`, `PreToolUse`) is absent in the file,
create it as an empty array then append. Never assume it exists.

### 5.3 `version` field (Cursor only)

Cursor ignores `hooks.json` when `version` is missing or not `1`. Always
preserve or insert `"version": 1`. Do not touch this field if it already exists
at a higher value (future-proof).

### 5.4 Non-hook keys in `settings.json` (Claude only)

`settings.json` is the whole Claude settings object. The merge reads the
full file, merges `hooks` in-place, and writes back. All other keys
(`permissions`, `model`, `sandbox`, `statusLine`, `enabledPlugins`, etc.) must
round-trip exactly. Use a shallow read-modify-write; never reconstruct from
scratch.

### 5.5 Ordering

Managed entries are appended **after** all unmanaged entries in the event array.
This ensures hand-edits (which run first) have highest priority. For deny/block
hooks this is important: a hand-edited blocking hook fires before any
agent-sync-installed hook. If a pack needs to run *first* (e.g. an early-exit
gate), document this in the pack Manifest and instruct users to move the entry
manually — agent-sync does not reorder hand edits.

### 5.6 Detecting hand-edits during uninstall

An entry is hand-edited if and only if it has no `_as` field, or `_as` does not
start with `"agent-sync:"`. agent-sync never touches those entries. This is the
full definition — no other heuristics needed.

### 5.7 Pack with multiple entries for the same event

The ordinal (`:0`, `:1`) distinguishes them. On uninstall, all ordinals for
the pack are removed because the prefix match `"agent-sync:<pack-name>:"` is
ordinal-agnostic.

### 5.8 Pack removed from Library

If a pack's event key was removed in an upgrade (e.g. v2.0.0 drops
`beforeShellExecution`), the old tagged entries remain until an explicit
uninstall or an upgrade pass that strips by prefix. `verify` should warn about
stale tagged entries that no longer appear in the current pack definition.

---

## 6. Hook Pack Library Layout

```
library/hooks/
  skill-gates/
    hook-pack.json       # pack name, version, per-target entries
    hooks/
      enforce-gate.sh    # scripts referenced in entries (relative to this dir)
  worktree-guard/
    hook-pack.json
    hooks/
      block-worktree-remove.sh
```

**`hook-pack.json` schema (draft):**
```json
{
  "name": "skill-gates",
  "version": "1.0.0",
  "description": "Gate skill-phase writes via skill_gate.py",
  "targets": {
    "cursor": {
      "<cursorEventName>": [ /* flat entry objects */ ]
    },
    "claude": {
      "<ClaudeEventName>": [ /* event-group objects (with nested hooks[]) */ ]
    }
  }
}
```

Fan-out copies scripts to the target hooks dir and rewrites command paths.
The pack's `hooks/` scripts are copied (or symlinked) to
`~/.cursor/hooks/` / `~/.claude/hooks/` with a namespace prefix
(`as-<pack-name>-<script>.sh`) to avoid collisions with hand-placed scripts.

---

## 7. Summary

| Concern | Cursor (`~/.cursor/hooks.json`) | Claude Code (`~/.claude/settings.json` `.hooks`) |
|---|---|---|
| **Unit installed** | Flat entry `{ command, matcher?, ... }` | Event group `{ matcher?, hooks: [...] }` |
| **Tag placement** | On the flat entry object | On the outer event-group object |
| **Tag field** | `"_as": "agent-sync:<pack>:<ver>:<event>:<n>"` | Same |
| **Event name case** | camelCase (`preToolUse`) | PascalCase (`PreToolUse`) |
| **File** | Dedicated `hooks.json`; `version: 1` required | Shared `settings.json`; non-hook keys must survive |
| **Create-if-missing** | `{ "version": 1, "hooks": {} }` | `{ "hooks": {} }` (rest left to user) |
| **Uninstall** | Remove entries where `_as` starts with pack prefix | Same |
| **Idempotency** | Strip-then-append | Strip-then-append |
| **Hand-edit protection** | Any entry without matching `_as` is untouched | Any event-group without matching `_as` is untouched |
