#!/usr/bin/env python3
"""Write/update one backfill shard + manifest entry (MCP harvest helper)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
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
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p.add_argument("--label", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--before", required=True)
    p.add_argument("--messages-json", type=Path, required=True)
    args = p.parse_args()

    root = args.root.expanduser()
    backfill = root / "harvest" / "backfill"
    backfill.mkdir(parents=True, exist_ok=True)
    raw = json.loads(args.messages_json.read_text())
    if not isinstance(raw, list):
        sys.exit("messages-json must be a JSON array")

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

    now = datetime.now(timezone.utc).isoformat()
    shard_path = backfill / f"{args.label}.json"
    shard = {
        "label": args.label,
        "after": args.after,
        "before": args.before,
        "harvested_at": now,
        "message_count": len(msgs),
        "messages": msgs,
        "source": "slack_mcp",
    }
    shard_path.write_text(json.dumps(shard, indent=2, ensure_ascii=False) + "\n")

    manifest_path = backfill / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"days": 180, "windows": [], "created_at": now, "source": "slack_mcp"}

    by_label = {w["label"]: w for w in manifest.get("windows", []) if "label" in w}
    existing = by_label.get(args.label, {})
    by_label[args.label] = {
        "label": args.label,
        "after": args.after,
        "before": args.before,
        "path": str(shard_path),
        "message_count": len(msgs),
        "harvested": True,
        "refined": bool(existing.get("refined")),
        "source": "slack_mcp",
    }
    manifest["windows"] = [by_label[k] for k in sorted(by_label.keys())]
    manifest["updated_at"] = now
    manifest["source"] = "slack_mcp"
    manifest["days"] = manifest.get("days") or 180
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{args.label}: {len(msgs)} messages → {shard_path}")


if __name__ == "__main__":
    main()
