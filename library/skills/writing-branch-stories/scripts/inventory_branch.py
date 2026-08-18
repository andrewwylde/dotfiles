#!/usr/bin/env python3
"""Create a deterministic Git branch inventory for story coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HUNK_HEADER = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<context>.*)$"
)
RAW_DIFF_HEADER = re.compile(
    r"^:(?P<old_mode>\d{6}) (?P<new_mode>\d{6}) "
    r"[0-9a-f]+ [0-9a-f]+ (?P<status>[A-Z]\d*)$"
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def stable_id(prefix: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8", errors="surrogateescape")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:16]}"


def resolve_commit(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def diff_range(base_sha: str, target_sha: str | None) -> list[str]:
    if target_sha is None:
        return [base_sha]
    return [base_sha, target_sha]


def parse_name_status_output(raw: str) -> list[dict[str, Any]]:
    fields = raw.split("\0")
    files: list[dict[str, Any]] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        old_path: str | None = None
        if status.startswith(("R", "C")):
            old_path = fields[index]
            path = fields[index + 1]
            index += 2
        else:
            path = fields[index]
            index += 1
        files.append(
            {
                "id": stable_id("file", status, old_path or "", path),
                "status": status,
                "old_path": old_path,
                "path": path,
                "binary": False,
                "old_mode": None,
                "new_mode": None,
                "submodule": False,
                "lfs_pointer": False,
            }
        )
    return files


def parse_name_status(
    repo: Path,
    base_sha: str,
    target_sha: str | None,
    working_tree: list[dict[str, str]],
) -> list[dict[str, Any]]:
    target_args = diff_range(base_sha, target_sha)
    raw = git(
        repo,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        *target_args,
    )
    files = parse_name_status_output(raw)
    metadata = parse_raw_metadata(repo, base_sha, target_sha)
    working_status = {entry["path"]: entry["status"] for entry in working_tree}
    for file_entry in files:
        entry_metadata = metadata.get(file_entry["path"], {})
        file_entry.update(entry_metadata)
        stats = git(
            repo,
            "diff",
            "--numstat",
            "--no-renames",
            *target_args,
            "--",
            file_entry["path"],
        )
        file_entry["binary"] = any(
            line.startswith("-\t-") for line in stats.splitlines()
        )
        if file_entry["status"][0] != "D":
            if target_sha is None:
                try:
                    blob = (repo / file_entry["path"]).read_bytes()
                except OSError:
                    blob = b""
                file_entry["working_tree_status"] = working_status.get(
                    file_entry["path"]
                )
            else:
                try:
                    blob = git_bytes(repo, "show", f"{target_sha}:{file_entry['path']}")
                except RuntimeError:
                    blob = b""
            file_entry["lfs_pointer"] = blob.startswith(
                b"version https://git-lfs.github.com/spec/v1\n"
            )
    if target_sha is None:
        existing_paths = {entry["path"] for entry in files}
        for working_entry in working_tree:
            if working_entry["status"] != "??":
                continue
            path = working_entry["path"]
            if path in existing_paths:
                continue
            try:
                blob = (repo / path).read_bytes()
                mode = "100755" if (repo / path).stat().st_mode & 0o111 else "100644"
            except OSError:
                blob = b""
                mode = "100644"
            files.append(
                {
                    "id": stable_id("file", "A", "", path),
                    "status": "A",
                    "old_path": None,
                    "path": path,
                    "binary": b"\0" in blob,
                    "old_mode": "000000",
                    "new_mode": mode,
                    "submodule": False,
                    "lfs_pointer": blob.startswith(
                        b"version https://git-lfs.github.com/spec/v1\n"
                    ),
                    "working_tree_status": "??",
                }
            )
    return files


def parse_raw_metadata(
    repo: Path,
    base_sha: str,
    target_sha: str | None,
) -> dict[str, dict[str, Any]]:
    target_args = diff_range(base_sha, target_sha)
    raw = git(
        repo,
        "diff",
        "--raw",
        "-z",
        "--find-renames",
        "--find-copies",
        *target_args,
    )
    fields = raw.split("\0")
    metadata: dict[str, dict[str, Any]] = {}
    index = 0
    while index < len(fields) and fields[index]:
        match = RAW_DIFF_HEADER.match(fields[index])
        if match is None:
            raise RuntimeError(f"unexpected raw diff entry: {fields[index]!r}")
        index += 1
        old_path = fields[index]
        index += 1
        status = match.group("status")
        path = old_path
        if status.startswith(("R", "C")):
            path = fields[index]
            index += 1
        old_mode = match.group("old_mode")
        new_mode = match.group("new_mode")
        metadata[path] = {
            "old_mode": old_mode,
            "new_mode": new_mode,
            "submodule": old_mode == "160000" or new_mode == "160000",
        }
    return metadata


def parse_hunks(
    repo: Path,
    base_sha: str,
    target_sha: str | None,
    file_entry: dict[str, Any],
) -> list[dict[str, Any]]:
    if file_entry.get("working_tree_status") == "??":
        if file_entry["binary"]:
            return []
        try:
            content = (repo / file_entry["path"]).read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            content = ""
        line_count = len(content.splitlines())
        header = f"@@ -0,0 +1,{line_count} @@ untracked"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return [
            {
                "id": stable_id("hunk", file_entry["id"], header, content_hash),
                "file_id": file_entry["id"],
                "old_start": 0,
                "old_count": 0,
                "new_start": 1,
                "new_count": line_count,
                "context": "untracked",
                "content_hash": content_hash,
            }
        ]
    target_args = diff_range(base_sha, target_sha)
    patch = git(
        repo,
        "diff",
        "--unified=0",
        "--no-color",
        "--no-ext-diff",
        *target_args,
        "--",
        file_entry["path"],
    )
    lines = patch.splitlines()
    hunks: list[dict[str, Any]] = []
    current_header: re.Match[str] | None = None
    body: list[str] = []

    def append_hunk() -> None:
        if current_header is None:
            return
        header = current_header.group(0)
        content_hash = hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()
        hunks.append(
            {
                "id": stable_id("hunk", file_entry["id"], header, content_hash),
                "file_id": file_entry["id"],
                "old_start": int(current_header.group("old_start")),
                "old_count": int(current_header.group("old_count") or "1"),
                "new_start": int(current_header.group("new_start")),
                "new_count": int(current_header.group("new_count") or "1"),
                "context": current_header.group("context").strip(),
                "content_hash": content_hash,
            }
        )

    for line in lines:
        match = HUNK_HEADER.match(line)
        if match:
            append_hunk()
            current_header = match
            body = []
        elif current_header is not None:
            body.append(line)
    append_hunk()
    return hunks


def inventory_commits(repo: Path, merge_base: str, head_sha: str) -> list[dict[str, Any]]:
    shas = git(
        repo,
        "rev-list",
        "--reverse",
        "--topo-order",
        f"{merge_base}..{head_sha}",
    ).splitlines()
    commits: list[dict[str, Any]] = []
    for sha in shas:
        fields = git(
            repo,
            "show",
            "-s",
            "--format=%H%x00%P%x00%an%x00%aI%x00%s%x00%b",
            sha,
        ).split("\0", 5)
        parents = fields[1].split() if fields[1] else []
        parent_changes = []
        for parent in parents:
            raw_changes = git(
                repo,
                "diff",
                "--name-status",
                "-z",
                "--find-renames",
                "--find-copies",
                parent,
                sha,
            )
            changes = [
                {
                    "status": entry["status"],
                    "old_path": entry["old_path"],
                    "path": entry["path"],
                }
                for entry in parse_name_status_output(raw_changes)
            ]
            parent_changes.append({"parent": parent, "changes": changes})
        commits.append(
            {
                "id": f"commit:{sha}",
                "sha": sha,
                "parents": parents,
                "author": fields[2],
                "authored_at": fields[3],
                "subject": fields[4],
                "body": fields[5].strip(),
                "parent_changes": parent_changes,
            }
        )
    return commits


def working_tree_entries(repo: Path) -> list[dict[str, str]]:
    fields = git(
        repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "-z",
    ).split("\0")
    entries: list[dict[str, str]] = []
    index = 0
    while index < len(fields) and fields[index]:
        entry = fields[index]
        index += 1
        status = entry[:2]
        path = entry[3:]
        item = {"status": status, "path": path}
        if status[0] in {"R", "C"} and index < len(fields) and fields[index]:
            item["old_path"] = fields[index]
            index += 1
        entries.append(item)
    return entries


def build_inventory(
    repo: Path,
    base_ref: str,
    head_ref: str,
    include_working_tree: bool,
) -> dict[str, Any]:
    repo = Path(git(repo, "rev-parse", "--show-toplevel").strip())
    base_sha = resolve_commit(repo, base_ref)
    head_sha = resolve_commit(repo, head_ref)
    merge_base = git(repo, "merge-base", base_sha, head_sha).strip()
    branch = git(repo, "branch", "--show-current").strip() or head_sha
    working_tree = working_tree_entries(repo)
    target_sha = None if include_working_tree else head_sha
    files = parse_name_status(repo, merge_base, target_sha, working_tree)
    hunks = [
        hunk
        for file_entry in files
        for hunk in parse_hunks(repo, merge_base, target_sha, file_entry)
    ]
    commits = inventory_commits(repo, merge_base, head_sha)
    snapshot_payload = json.dumps(
        {
            "files": files,
            "hunks": hunks,
            "working_tree": working_tree if include_working_tree else [],
        },
        sort_keys=True,
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "repository": str(repo),
        "branch": branch,
        "base": {"ref": base_ref, "sha": base_sha},
        "merge_base": merge_base,
        "head": {"ref": head_ref, "sha": head_sha},
        "includes_working_tree": include_working_tree,
        "snapshot_sha256": hashlib.sha256(snapshot_payload).hexdigest(),
        "commits": commits,
        "files": files,
        "hunks": hunks,
        "working_tree": working_tree,
        "totals": {
            "commits": len(commits),
            "files": len(files),
            "hunks": len(hunks),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--include-working-tree", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inventory = build_inventory(
            args.repo,
            args.base,
            args.head,
            args.include_working_tree,
        )
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    payload = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
