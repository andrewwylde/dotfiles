#!/usr/bin/env python3
"""Harvest Andrew's Slack messages via search.messages (no LLM)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
DEFAULT_ROOT = HOME / ".agent" / "personal-voice-model"
EMOJI_ONLY = re.compile(
    r"^(\s*|:[a-z0-9_+-]+:|\s|[\U0001F300-\U0001FAFF\u2600-\u27BF])+$",
    re.IGNORECASE,
)
SECRETISH = re.compile(
    r"(?i)(xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9]+|sk-[A-Za-z0-9_-]{20,}"
    r"|Bearer\s+[A-Za-z0-9._\-]+|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"\+?\d[\d\-\s().]{8,}\d)"
)


def load_config(root: Path) -> dict:
    path = root / "config.json"
    if not path.exists():
        sys.exit(f"missing config: {path}")
    return json.loads(path.read_text())


def load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'").strip('"')
        os.environ.setdefault(k, v)


def slack_api(token: str, method: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    while True:
        try:
            with urllib.request.urlopen(req) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            raise
        if payload.get("error") == "ratelimited":
            time.sleep(5)
            continue
        return payload


def redact(text: str) -> str:
    return SECRETISH.sub("[redacted]", text or "")


def keep_message(text: str) -> bool:
    t = (text or "").strip()
    if not t or EMOJI_ONLY.match(t):
        return False
    return True


def week_windows(days: int, end: date | None = None) -> list[tuple[date, date]]:
    end = end or date.today()
    start = end - timedelta(days=days)
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(days=7), end)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows


def iso_week_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def search_window(
    token: str,
    user_id: str,
    after: date,
    before: date,
    max_pages: int = 20,
) -> list[dict]:
    query = f"from:<@{user_id}> after:{after.isoformat()} before:{before.isoformat()}"
    messages: list[dict] = []
    page = 1
    while page <= max_pages:
        payload = slack_api(
            token,
            "search.messages",
            {
                "query": query,
                "sort": "timestamp",
                "sort_dir": "asc",
                "count": 100,
                "page": page,
            },
        )
        if not payload.get("ok"):
            err = payload.get("error", "unknown")
            if err in ("missing_scope", "invalid_auth", "not_allowed_token_type"):
                sys.exit(
                    f"slack search.messages failed: {err}\n"
                    "Need a user token (xoxp-) with search:read."
                )
            if err == "ratelimited":
                time.sleep(10)
                continue
            sys.exit(f"slack search.messages failed: {err}")

        matches = (payload.get("messages") or {}).get("matches") or []
        paging = (payload.get("messages") or {}).get("paging") or {}
        for m in matches:
            text = redact(m.get("text") or "")
            if not keep_message(text):
                continue
            messages.append(
                {
                    "ts": m.get("ts"),
                    "channel": (m.get("channel") or {}).get("id")
                    or (m.get("channel") or {}).get("name"),
                    "channel_name": (m.get("channel") or {}).get("name"),
                    "text": text,
                    "permalink": m.get("permalink"),
                    "username": m.get("username"),
                }
            )
        total_pages = int(paging.get("pages") or 1)
        if page >= total_pages or not matches:
            break
        page += 1
        time.sleep(1.2)
    return messages


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--chunk", choices=("weeks", "none"), default="none")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root: Path = args.root.expanduser()
    load_dotenv(root)
    cfg = load_config(root)
    user_id = (cfg.get("slack_user_id") or "").strip()
    if not user_id:
        sys.exit("config.slack_user_id is empty — run setup first")

    token = os.environ.get("SLACK_USER_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit(
            f"Set SLACK_USER_TOKEN (xoxp-…) in the environment or {root / '.env'}"
        )
    if token.startswith("xoxb-"):
        print(
            "warning: bot token cannot search your personal DMs; "
            "prefer SLACK_USER_TOKEN (xoxp-)",
            file=sys.stderr,
        )

    days = args.days if args.days is not None else int(cfg.get("lookback_days") or 7)
    now = datetime.now(timezone.utc).isoformat()

    if args.chunk == "weeks":
        backfill_dir = root / "harvest" / "backfill"
        backfill_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = backfill_dir / "manifest.json"
        manifest = (
            json.loads(manifest_path.read_text())
            if manifest_path.exists()
            else {"days": days, "windows": [], "created_at": now}
        )
        by_label = {w["label"]: w for w in manifest.get("windows", []) if "label" in w}

        total = 0
        for after, before in week_windows(days):
            label = iso_week_label(after)
            shard_path = backfill_dir / f"{label}.json"
            existing = by_label.get(label)
            if existing and existing.get("harvested") and shard_path.exists():
                print(f"skip harvest {label} (already harvested)")
                continue
            msgs = search_window(token, user_id, after, before)
            write_json(
                shard_path,
                {
                    "label": label,
                    "after": after.isoformat(),
                    "before": before.isoformat(),
                    "harvested_at": now,
                    "message_count": len(msgs),
                    "messages": msgs,
                },
            )
            by_label[label] = {
                "label": label,
                "after": after.isoformat(),
                "before": before.isoformat(),
                "path": str(shard_path),
                "message_count": len(msgs),
                "harvested": True,
                "refined": bool(existing.get("refined")) if existing else False,
            }
            total += len(msgs)
            print(f"harvested {label}: {len(msgs)} messages → {shard_path}")

        manifest["days"] = days
        manifest["updated_at"] = now
        manifest["windows"] = [by_label[k] for k in sorted(by_label.keys())]
        write_json(manifest_path, manifest)
        print(f"backfill harvest complete: {total} messages across {len(by_label)} windows")
        return

    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=days)
    msgs = search_window(token, user_id, start, end)
    out = args.out or (root / "harvest.json")
    write_json(
        out,
        {
            "harvested_at": now,
            "after": start.isoformat(),
            "before": end.isoformat(),
            "lookback_days": days,
            "message_count": len(msgs),
            "messages": msgs,
        },
    )
    print(f"wrote {len(msgs)} messages → {out}")


if __name__ == "__main__":
    main()
