#!/usr/bin/env python3
"""
Export all Claude Code sessions for the current project into a single readable file.

Usage:
    python3 export_sessions.py [output_path] [--project-dir PATH] [--no-tool-results] [--no-system]

Arguments:
    output_path        Where to write the export (default: ~/Downloads/full-export-<date>.txt)
    --project-dir      Override auto-detected project directory
    --no-tool-results  Skip tool result messages (reduces noise)
    --no-system        Skip system-reminder and meta messages
"""

import json
import os
import pathlib
import sys
import datetime
import argparse


def path_to_project_key(path: str) -> str:
    """Convert an absolute filesystem path to its Claude project directory key."""
    return path.replace("/", "-").replace(".", "-")


def find_project_dir(cwd: str) -> pathlib.Path | None:
    """Find the ~/.claude/projects/<hash>/ directory for the given cwd."""
    projects_root = pathlib.Path.home() / ".claude" / "projects"
    if not projects_root.exists():
        return None

    key = path_to_project_key(cwd)
    candidate = projects_root / key
    if candidate.exists():
        return candidate

    # Fallback: walk up the directory tree trying each ancestor
    p = pathlib.Path(cwd)
    while p != p.parent:
        key = path_to_project_key(str(p))
        candidate = projects_root / key
        if candidate.exists():
            return candidate
        p = p.parent

    return None


def extract_text(content) -> str:
    """Extract plain text from a message content field (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "tool_use":
                name = block.get("name", "tool")
                inp = block.get("input", {})
                inp_str = json.dumps(inp, indent=2) if inp else ""
                parts.append(f"[Tool: {name}]\n{inp_str}")
            elif btype == "tool_result":
                result = block.get("content", "")
                if isinstance(result, list):
                    result = " ".join(
                        r.get("text", "") for r in result if isinstance(r, dict)
                    )
                parts.append(f"[Tool Result]\n{result}")
        return "\n".join(p for p in parts if p)
    return ""


def is_meta(entry: dict) -> bool:
    """Return True for internal/meta entries that aren't readable conversation."""
    if entry.get("isMeta"):
        return True
    if entry.get("type") in ("summary", "debug"):
        return True
    return False


def is_tool_result_only(entry: dict) -> bool:
    """Return True if this entry is purely a tool result response."""
    msg = entry.get("message", {})
    content = msg.get("content", [])
    if isinstance(content, list):
        return all(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in content
            if isinstance(b, dict)
        )
    return False


def format_session(jsonl_path: pathlib.Path, no_tool_results: bool, no_system: bool) -> str:
    """Parse a single JSONL session file and return formatted text."""
    lines_out = []
    try:
        raw_lines = jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"[Error reading {jsonl_path.name}: {e}]\n"

    seen_uuids = set()

    for raw in raw_lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if is_meta(entry):
            continue

        msg = entry.get("message", {})
        if not msg:
            continue

        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue

        uuid = entry.get("uuid", "")
        if uuid and uuid in seen_uuids:
            continue
        if uuid:
            seen_uuids.add(uuid)

        if no_tool_results and is_tool_result_only(entry):
            continue

        content = msg.get("content", "")
        text = extract_text(content)

        if no_system:
            # Strip system-reminder and similar injected blocks
            text = strip_system_blocks(text)

        text = text.strip()
        if not text:
            continue

        ts = entry.get("timestamp", "")
        ts_str = f" [{ts[:19]}]" if ts else ""

        lines_out.append(f"[{role.upper()}{ts_str}]\n{text}\n")

    return "\n".join(lines_out)


def strip_system_blocks(text: str) -> str:
    """Remove <system-reminder>...</system-reminder> and similar injected blocks."""
    import re
    # Remove system-reminder blocks
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    # Remove local-command blocks
    text = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", text, flags=re.DOTALL)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.DOTALL)
    return text


def main():
    parser = argparse.ArgumentParser(description="Export all Claude Code sessions for a project")
    parser.add_argument("output", nargs="?", help="Output file path")
    parser.add_argument("--project-dir", help="Override project directory (path to ~/.claude/projects/<hash>/)")
    parser.add_argument("--cwd", default=os.getcwd(), help="Project working directory for auto-detection")
    parser.add_argument("--no-tool-results", action="store_true", help="Skip tool result messages")
    parser.add_argument("--no-system", action="store_true", help="Strip system-reminder blocks")
    args = parser.parse_args()

    # Locate project directory
    if args.project_dir:
        project_dir = pathlib.Path(args.project_dir)
    else:
        project_dir = find_project_dir(args.cwd)

    if not project_dir or not project_dir.exists():
        print(f"ERROR: Could not find project directory for: {args.cwd}", file=sys.stderr)
        print("Try: --project-dir ~/.claude/projects/<hash>/", file=sys.stderr)
        print("\nAvailable projects:", file=sys.stderr)
        projects_root = pathlib.Path.home() / ".claude" / "projects"
        for d in sorted(projects_root.iterdir()):
            if d.is_dir():
                files = list(d.glob("*.jsonl"))
                print(f"  {d.name}  ({len(files)} sessions)", file=sys.stderr)
        sys.exit(1)

    # Find and sort JSONL files by modification time (oldest first)
    jsonl_files = sorted(project_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)

    if not jsonl_files:
        print(f"No session files found in {project_dir}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = pathlib.Path(args.output).expanduser()
    else:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        project_name = project_dir.name[-40:]  # truncate long hashes
        output_path = pathlib.Path.home() / ".agent" / "sessions" / f"full-export-{project_name}-{date_str}.txt"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build output
    sections = []
    sections.append(f"Full Export — {project_dir.name}")
    sections.append(f"Exported: {datetime.datetime.now().isoformat()}")
    sections.append(f"Sessions: {len(jsonl_files)}")
    sections.append("=" * 80)

    for i, jf in enumerate(jsonl_files, 1):
        mtime = datetime.datetime.fromtimestamp(jf.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        sections.append(f"\n{'=' * 80}")
        sections.append(f"SESSION {i}/{len(jsonl_files)}  |  {jf.name}  |  modified {mtime}")
        sections.append("=" * 80 + "\n")
        sections.append(format_session(jf, args.no_tool_results, args.no_system))

    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Exported {len(jsonl_files)} session(s) to: {output_path}")


if __name__ == "__main__":
    main()
