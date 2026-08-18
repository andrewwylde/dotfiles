#!/usr/bin/env python3
"""Merge a Slack harvest into voice-model.md via local Ollama (no cloud tokens)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".agent" / "personal-voice-model"

HARD_RULES_RE = re.compile(
    r"(## Hard rules\n)(.*?)(\n## )",
    re.DOTALL | re.IGNORECASE,
)

SYSTEM_PROMPT = """You refine a personal writing/speech voice model from Slack messages the author sent.

Fixed policy:
- Hybrid: sticky hard rules (DO NOT OUTPUT OR CHANGE THEM) + descriptive dossier
- Soft dials only (more terse / more warm / more formal) — not separate full profiles
- Dimensions: prosody, stance, structure; lexicon only if a phrase appears >= sticky_min times in THIS harvest
- Evidence: at most max_snippets short anonymized snippets (1-2 sentences). Redact coworker names to role/initials. No secrets.
- Work-safe: ignore HR/performance, health, legal, compensation, private 1:1 drama
- Merge with prior dossier; strengthen repeated patterns
- If decay is true: demote/remove unsupported patterns. If false: only strengthen/add
- Do NOT invent catchphrases from one-offs

Return ONLY valid JSON with this shape:
{
  "core_voice": {
    "prosody": "markdown",
    "stance": "markdown",
    "structure": "markdown",
    "lexicon": "markdown"
  },
  "soft_dials": {
    "more_terse": "...",
    "more_warm": "...",
    "more_formal": "..."
  },
  "evidence_snippets": [
    {"dial": "default", "text": "...", "why": "..."}
  ],
  "pattern_ledger": [
    {"id": "snake_case", "dimension": "prosody", "summary": "...", "strength": "strong", "last_seen": "YYYY-MM-DD"}
  ],
  "stats": {"patterns_strengthened": 0, "patterns_decayed": 0, "snippets_rotated": 0}
}
"""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def extract_hard_rules(voice_md: str) -> str:
    m = HARD_RULES_RE.search(voice_md)
    if not m:
        return (
            "## Hard rules\n\n"
            "Hand-edited only. Refine mode must not change this section.\n\n"
            "- Lead with the point; put context after.\n"
        )
    return m.group(1) + m.group(2).rstrip() + "\n"


def ollama_chat(host: str, model: str, system: str, user: str) -> str:
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                payload = json.loads(resp.read().decode())
            last_err = None
            break
        except TimeoutError as e:
            last_err = e
            print(f"ollama timeout (attempt {attempt}/3), retrying…", file=sys.stderr)
        except urllib.error.URLError as e:
            sys.exit(
                f"Cannot reach Ollama at {host}: {e}\n"
                "Start it with: ollama serve   (or brew services start ollama)"
            )
    if last_err is not None:
        sys.exit(f"Ollama chat timed out after 3 attempts ({last_err})")
    content = (payload.get("message") or {}).get("content") or ""
    if not content.strip():
        sys.exit(f"empty Ollama response: {payload!r}")
    return content


def parse_model_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def assemble_voice_md(
    hard_rules: str,
    patch: dict,
    lookback_days: int,
    decay_weeks: int,
    max_snippets: int,
) -> str:
    cv = patch.get("core_voice") or {}
    dials = patch.get("soft_dials") or {}
    snippets = (patch.get("evidence_snippets") or [])[:max_snippets]
    ledger = patch.get("pattern_ledger") or []
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    snip_lines: list[str] = []
    if not snippets:
        snip_lines.append(f"_None yet. Cap: {max_snippets}._")
    else:
        for i, s in enumerate(snippets, 1):
            dial = s.get("dial") or "default"
            text = (s.get("text") or "").strip()
            why = (s.get("why") or "").strip()
            snip_lines.append(f"{i}. **[{dial}]** {text}")
            if why:
                snip_lines.append(f"   - _{why}_")

    ledger_rows = [
        "| id | dimension | summary | strength | last_seen |",
        "|----|-----------|---------|----------|-----------|",
    ]
    if not ledger:
        ledger_rows.append("| — | — | — | — | — |")
    else:
        for row in ledger:
            ledger_rows.append(
                "| {id} | {dimension} | {summary} | {strength} | {last_seen} |".format(
                    id=(row.get("id") or "—").replace("|", "/"),
                    dimension=(row.get("dimension") or "—").replace("|", "/"),
                    summary=(row.get("summary") or "—").replace("|", "/"),
                    strength=(row.get("strength") or "—").replace("|", "/"),
                    last_seen=(row.get("last_seen") or "—").replace("|", "/"),
                )
            )

    return "\n".join(
        [
            "# Personal voice model",
            "",
            f"- Last refined: {now}",
            f"- Lookback days: {lookback_days}",
            f"- Decay weeks: {decay_weeks}",
            "",
            hard_rules.rstrip(),
            "",
            "## Core voice",
            "",
            "### Prosody",
            "",
            (cv.get("prosody") or "_No observations yet._").rstrip(),
            "",
            "### Stance",
            "",
            (cv.get("stance") or "_No observations yet._").rstrip(),
            "",
            "### Structure",
            "",
            (cv.get("structure") or "_No observations yet._").rstrip(),
            "",
            "### Lexicon",
            "",
            (cv.get("lexicon") or "_None sticky yet._").rstrip(),
            "",
            "## Soft dials",
            "",
            f"- **More terse** — {(dials.get('more_terse') or '_TBD_').rstrip()}",
            f"- **More warm** — {(dials.get('more_warm') or '_TBD_').rstrip()}",
            f"- **More formal** — {(dials.get('more_formal') or '_TBD_').rstrip()}",
            "",
            "## Evidence snippets",
            "",
            *snip_lines,
            "",
            "## Pattern ledger",
            "",
            *ledger_rows,
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--harvest", type=Path, default=None)
    parser.add_argument("--no-decay", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--host", default=None)
    args = parser.parse_args()

    root = args.root.expanduser()
    cfg = load_json(root / "config.json")
    voice_path = root / "voice-model.md"
    if not voice_path.exists():
        sys.exit(f"missing {voice_path}")

    harvest_path = args.harvest or (root / "harvest.json")
    if not harvest_path.exists():
        sys.exit(f"missing harvest file: {harvest_path}")

    harvest = load_json(harvest_path)
    messages = list(harvest.get("messages") or [])
    max_msgs = int(cfg.get("ollama_max_messages") or 120)
    if len(messages) > max_msgs:
        step = max(1, len(messages) // max_msgs)
        messages = messages[::step][:max_msgs]

    host = args.host or cfg.get("ollama_host") or "http://127.0.0.1:11434"
    model = args.model or cfg.get("ollama_model") or "qwen2.5:14b"
    max_snippets = int(cfg.get("max_snippets") or 6)
    sticky_min = int(cfg.get("sticky_lexicon_min_count") or 3)
    lookback = int(harvest.get("lookback_days") or cfg.get("lookback_days") or 7)
    decay_weeks = int(cfg.get("decay_weeks") or 4)
    decay = not args.no_decay

    voice_md = voice_path.read_text()
    hard_rules = extract_hard_rules(voice_md)
    prior_for_model = HARD_RULES_RE.sub(
        r"\1[HAND-EDITED — OMIT FROM OUTPUT]\n\3",
        voice_md,
    )

    sample_lines = []
    for m in messages:
        ts = m.get("ts") or ""
        ch = m.get("channel_name") or m.get("channel") or "?"
        text = (m.get("text") or "").replace("\n", " ").strip()
        if len(text) > 400:
            text = text[:400] + "…"
        sample_lines.append(f"- [{ts}] #{ch}: {text}")

    user_prompt = (
        f"decay={str(decay).lower()}\n"
        f"sticky_min={sticky_min}\n"
        f"max_snippets={max_snippets}\n"
        f"harvest_window={harvest.get('after')} .. {harvest.get('before')}\n"
        f"message_count_in_prompt={len(messages)}\n\n"
        f"CURRENT_VOICE_MODEL:\n{prior_for_model}\n\n"
        f"NEW_MESSAGES:\n" + "\n".join(sample_lines)
    )

    print(f"ollama refine model={model} messages={len(messages)} decay={decay}")
    raw = ollama_chat(host, model, SYSTEM_PROMPT, user_prompt)
    try:
        patch = parse_model_json(raw)
    except json.JSONDecodeError as e:
        debug = root / "logs" / "last-ollama-raw.txt"
        debug.parent.mkdir(parents=True, exist_ok=True)
        debug.write_text(raw)
        sys.exit(f"Ollama returned non-JSON ({e}); raw saved to {debug}")

    voice_path.write_text(
        assemble_voice_md(
            hard_rules=hard_rules,
            patch=patch,
            lookback_days=lookback,
            decay_weeks=decay_weeks,
            max_snippets=max_snippets,
        )
    )

    stats = patch.get("stats") or {}
    state_path = root / "state.json"
    state = load_json(state_path) if state_path.exists() else {}
    state.update(
        {
            "last_refined_at": datetime.now(timezone.utc)
            .astimezone()
            .isoformat(timespec="seconds"),
            "lookback_days": lookback,
            "messages_kept": len(harvest.get("messages") or []),
            "messages_in_prompt": len(messages),
            "patterns_strengthened": stats.get("patterns_strengthened", 0),
            "patterns_decayed": stats.get("patterns_decayed", 0),
            "snippets_rotated": stats.get("snippets_rotated", 0),
            "backend": "ollama",
            "ollama_model": model,
            "decay": decay,
            "last_attempt_status": "ok",
            "last_attempt_error": None,
            "harvest_path": str(harvest_path),
        }
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(f"updated {voice_path}")
    print(
        f"stats: strengthened={state['patterns_strengthened']} "
        f"decayed={state['patterns_decayed']} "
        f"snippets={state['snippets_rotated']}"
    )


if __name__ == "__main__":
    main()
