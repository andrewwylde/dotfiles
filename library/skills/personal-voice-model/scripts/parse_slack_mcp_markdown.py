#!/usr/bin/env python3
"""Parse Slack MCP search markdown dump into message dicts (stdout JSON)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESULT_SPLIT = re.compile(r"\n### Result \d+ of \d+\n")
CHANNEL_RE = re.compile(
    r"Channel:\s+(?:#)?(?P<name>[^\n(]+?)\s*\(ID:\s*(?P<id>[A-Z0-9]+)\)|"
    r"Channel:\s+DM\s*\(ID:\s*(?P<dm_id>[A-Z0-9]+)\)",
    re.I,
)
TS_RE = re.compile(r"Message_ts:\s*(?P<ts>[0-9.]+)")
PERMA_RE = re.compile(r"Permalink:\s*\[.*?\]\((?P<url>[^)]+)\)")
TEXT_RE = re.compile(r"\nText:\s*\n(?P<text>.*?)(?=\n---|\Z)", re.S)


def parse_block(block: str) -> dict | None:
    ch = CHANNEL_RE.search(block)
    ts_m = TS_RE.search(block)
    if not ts_m:
        return None
    text_m = TEXT_RE.search(block)
    text = (text_m.group("text") if text_m else "").strip()
    # unescape common slack markdown leftovers
    text = text.replace("\\n", "\n")
    perma = PERMA_RE.search(block)
    channel_id = None
    channel_name = None
    if ch:
        channel_id = ch.group("id") or ch.group("dm_id")
        channel_name = (ch.group("name") or "dm").strip()
    return {
        "ts": ts_m.group("ts"),
        "channel": channel_id,
        "channel_name": channel_name,
        "text": text,
        "permalink": perma.group("url") if perma else None,
        "username": "Andrew Wylde",
    }


def main() -> None:
    raw = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else sys.stdin.read()
    # drop header before first result
    parts = RESULT_SPLIT.split(raw)
    msgs = []
    for part in parts[1:] if len(parts) > 1 else []:
        m = parse_block(part)
        if m and m.get("text"):
            msgs.append(m)
    # also handle single-result dumps without split
    if not msgs and "Message_ts:" in raw:
        m = parse_block(raw)
        if m and m.get("text"):
            msgs.append(m)
    json.dump(msgs, sys.stdout, ensure_ascii=False)
    print(file=sys.stderr, flush=True)
    print(f"parsed {len(msgs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
