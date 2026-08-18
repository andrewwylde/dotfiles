#!/usr/bin/env python3
"""Write daily harvest.json from a messages JSON array (MCP harvest helper)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".agent" / "personal-voice-model"
SECRETISH = re.compile(
    r"(?i)(xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9]+|sk-[A-Za-z0-9_-]{20,}"
    r"|Bearer\s+[A-Za-z0-9._\-]+|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"\+?\d[\d\-\s().]{8,}\d)"
)
EMOJI_ONLY = re.compile(
    r"^(\s*|:[a-z0-9_+-]+:|\s|[\U0001F300-\U0001FAFF\u2600-\u27BF])+$",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    return SECRETISH.sub("[redacted]", text or "")


def keep(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and not EMOJI_ONLY.match(t)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p.add_argument("--messages-json", type=Path, required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--after", default=None)
    p.add_argument("--before", default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    root = args.root.expanduser()
    raw = json.loads(args.messages_json.read_text())
    if not isinstance(raw, list):
        sys.exit("messages-json must be a JSON array")

    end = date.fromisoformat(args.before) if args.before else date.today() + timedelta(days=1)
    start = date.fromisoformat(args.after) if args.after else end - timedelta(days=args.days)

    msgs = []
    seen: set[str] = set()
    for m in raw:
        text = redact((m.get("text") or "").strip())
        if not keep(text):
            continue
        ts = str(m.get("ts") or "")
        if ts and ts in seen:
            continue
        if ts:
            seen.add(ts)
        msgs.append(
            {
                "ts": ts,
                "channel": m.get("channel") or m.get("channel_id"),
                "channel_name": m.get("channel_name"),
                "text": text,
                "permalink": m.get("permalink"),
                "username": m.get("username"),
            }
        )

    out = args.out or (root / "harvest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "after": start.isoformat(),
        "before": end.isoformat(),
        "lookback_days": args.days,
        "message_count": len(msgs),
        "messages": msgs,
        "source": "slack_mcp",
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(msgs)} messages → {out}")


if __name__ == "__main__":
    main()
