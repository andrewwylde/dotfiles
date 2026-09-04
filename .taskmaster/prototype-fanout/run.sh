#!/usr/bin/env bash
# PROTOTYPE — throwaway one-skill Fan-out. Not production agent-sync.
# Reads library/skills/demo-echo and writes Wrappers into the sandbox only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

exec python3 - "$ROOT" <<'PY'
from __future__ import annotations

import os
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
LIBRARY = ROOT / "library" / "skills" / "demo-echo"
SKILL = LIBRARY / "SKILL.md"
MANIFEST = LIBRARY / "manifest.toml"
PROTO = ROOT / ".taskmaster" / "prototype-fanout"
WRAPPERS = PROTO / "wrappers"
SANDBOX = PROTO / "sandbox"
FANOUT_NAME = "andrew-demo-echo"
OWNER_PREFIX = "andrew"
TARGETS = ("claude", "cursor")  # prototype: two Targets only

HOME_CLAUDE = Path.home() / ".claude"
HOME_CURSOR = Path.home() / ".cursor"


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_skill(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        die("SKILL.md: expected closing --- on frontmatter")
    fm: dict = {}
    for line in parts[1].strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, raw = stripped.partition(":")
        val = raw.strip()
        if val in ("true", "false"):
            fm[key.strip()] = val == "true"
        elif (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            fm[key.strip()] = val[1:-1]
        else:
            fm[key.strip()] = val
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    return fm, body


def dump_skill(fm: dict, body: str) -> str:
    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    out = "\n".join(lines) + "\n"
    if body and not body.startswith("\n"):
        out += "\n"
    return out + body


def deep_merge(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def overlay_for(manifest: dict, target: str) -> dict:
    overlays = manifest.get("overlays") or {}
    return overlays.get(target) or {}


def generate_wrapper(base_fm: dict, body: str, overlay: dict, target: str) -> str:
    fm_overlay = overlay.get("frontmatter") or {}
    if not isinstance(fm_overlay, dict):
        die(f"overlays.{target}.frontmatter must be a table")
    fm = deep_merge(base_fm, fm_overlay)
    extra = overlay.get("body_append") or ""
    return dump_skill(fm, body + extra)


def assert_sandbox_only(path: Path) -> None:
    resolved = path.resolve()
    if not str(resolved).startswith(str(SANDBOX.resolve())):
        die(f"refusing to write outside sandbox: {resolved}")
    for home in (HOME_CLAUDE, HOME_CURSOR):
        try:
            resolved.relative_to(home.resolve())
        except ValueError:
            continue
        die(f"refusing to write into real Target home {home}")


def install_mode(target: str) -> str:
    # Locked: Cursor ALWAYS copy (symlink discovery bug). Claude: symlink OK.
    if target == "cursor":
        return "copy"
    return "symlink"


def install(target: str, wrapper_dir: Path) -> Path:
    skills_parent = SANDBOX / f".{target}" / "skills"
    dest = skills_parent / FANOUT_NAME
    assert_sandbox_only(dest)
    skills_parent.mkdir(parents=True, exist_ok=True)
    mode = install_mode(target)
    if dest.exists() or dest.is_symlink():
        dest.unlink() if dest.is_symlink() or dest.is_file() else shutil.rmtree(dest)
    if mode == "copy" or skills_parent.is_symlink():
        # Coerce copy if the parent skills dir itself is a symlink (npx pattern).
        shutil.copytree(wrapper_dir, dest, symlinks=False)
        mode = "copy"
    else:
        dest.symlink_to(os.path.relpath(wrapper_dir, dest.parent))
    return dest


def describe(path: Path) -> str:
    if path.is_symlink():
        return f"symlink -> {os.readlink(path)}"
    if path.is_dir():
        return "directory (copy)"
    return "file"


def main() -> None:
    if not SKILL.is_file():
        die(f"missing {SKILL}")
    if not MANIFEST.is_file():
        die(f"missing {MANIFEST}")

    base_fm, body = parse_skill(SKILL.read_text())
    manifest = tomllib.loads(MANIFEST.read_text())
    excluded = set(manifest.get("exclude") or [])
    library_name = LIBRARY.name
    if FANOUT_NAME != f"{OWNER_PREFIX}-{library_name}":
        die(f"fan-out name {FANOUT_NAME} != {OWNER_PREFIX}-{library_name}")

    shutil.rmtree(WRAPPERS, ignore_errors=True)
    shutil.rmtree(SANDBOX, ignore_errors=True)
    WRAPPERS.mkdir(parents=True)
    SANDBOX.mkdir(parents=True)

    report: list[str] = [
        "PROTOTYPE LAST RUN — wipe/re-run via .taskmaster/prototype-fanout/run.sh",
        f"library: {LIBRARY.relative_to(ROOT)}",
        f"fan-out basename: {FANOUT_NAME}",
        f"sandbox: {SANDBOX.relative_to(ROOT)}  (NOT ~/.claude or ~/.cursor)",
        "",
    ]

    for target in TARGETS:
        if target in excluded:
            report.append(f"{target}: skipped (exclude)")
            continue
        overlay = overlay_for(manifest, target)
        wrapper_text = generate_wrapper(base_fm, body, overlay, target)
        wrapper_dir = WRAPPERS / target / FANOUT_NAME
        wrapper_dir.mkdir(parents=True)
        (wrapper_dir / "SKILL.md").write_text(wrapper_text)
        dest = install(target, wrapper_dir)
        overlay_keys = list((overlay.get("frontmatter") or {}).keys())
        appended = "yes" if overlay.get("body_append") else "no"
        report.append(
            f"{target}: install={describe(dest)}  overlay_fm={overlay_keys or 'none'}  body_append={appended}"
        )
        report.append(f"  wrapper: {wrapper_dir.relative_to(ROOT)}/SKILL.md")
        report.append(f"  target:  {dest.relative_to(ROOT)}")

    report.extend(
        [
            "",
            "Inspect: diff Library SKILL.md vs wrappers/cursor/.../SKILL.md",
            "Inspect: ls -la sandbox/.claude/skills  (symlink) vs sandbox/.cursor/skills  (copy)",
        ]
    )
    text = "\n".join(report) + "\n"
    (PROTO / "LAST_RUN.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
PY
