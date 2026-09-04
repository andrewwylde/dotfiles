import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "inventory_branch.py"


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


class InventoryBranchTests(unittest.TestCase):
    def test_inventory_records_commits_files_hunks_and_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Skill Test")
            run_git(repo, "config", "user.email", "skill-test@example.com")

            source = repo / "app.txt"
            source.write_text("before\n", encoding="utf-8")
            run_git(repo, "add", "app.txt")
            run_git(repo, "commit", "-m", "base")
            base_sha = run_git(repo, "rev-parse", "HEAD")

            run_git(repo, "switch", "-c", "feature/story")
            source.write_text("after\n", encoding="utf-8")
            run_git(repo, "add", "app.txt")
            run_git(repo, "commit", "-m", "change application behavior")
            head_sha = run_git(repo, "rev-parse", "HEAD")
            (repo / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")

            output = Path(directory) / "inventory.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--base",
                    "main",
                    "--head",
                    "HEAD",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            inventory = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(inventory["schema_version"], 1)
            self.assertEqual(inventory["base"]["sha"], base_sha)
            self.assertEqual(inventory["head"]["sha"], head_sha)
            self.assertEqual(len(inventory["commits"]), 1)
            self.assertEqual(inventory["commits"][0]["subject"], "change application behavior")
            self.assertEqual(len(inventory["files"]), 1)
            self.assertEqual(inventory["files"][0]["path"], "app.txt")
            self.assertGreaterEqual(len(inventory["hunks"]), 1)
            self.assertEqual(inventory["hunks"][0]["file_id"], inventory["files"][0]["id"])
            self.assertEqual(inventory["working_tree"][0]["path"], "scratch.txt")

    def test_inventory_records_rename_binary_mode_and_lfs_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Skill Test")
            run_git(repo, "config", "user.email", "skill-test@example.com")

            (repo / "old.txt").write_text("renamed content\n", encoding="utf-8")
            (repo / "blob.bin").write_bytes(b"\x00before")
            script = repo / "run.sh"
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")

            run_git(repo, "switch", "-c", "feature/metadata")
            run_git(repo, "mv", "old.txt", "new.txt")
            (repo / "blob.bin").write_bytes(b"\x00after")
            script.chmod(0o755)
            (repo / "large.dat").write_text(
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:0123456789abcdef\n"
                "size 42\n",
                encoding="utf-8",
            )
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "change file metadata")

            output = Path(directory) / "inventory.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--base",
                    "main",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            inventory = json.loads(output.read_text(encoding="utf-8"))
            files = {entry["path"]: entry for entry in inventory["files"]}
            self.assertTrue(files["new.txt"]["status"].startswith("R"))
            self.assertEqual(files["new.txt"]["old_path"], "old.txt")
            self.assertTrue(files["blob.bin"]["binary"])
            self.assertEqual(files["run.sh"]["old_mode"], "100644")
            self.assertEqual(files["run.sh"]["new_mode"], "100755")
            self.assertTrue(files["large.dat"]["lfs_pointer"])

    def test_inventory_records_each_merge_parent_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Skill Test")
            run_git(repo, "config", "user.email", "skill-test@example.com")

            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")

            run_git(repo, "switch", "-c", "feature/merge")
            (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "feature work")

            run_git(repo, "switch", "main")
            (repo / "main.txt").write_text("main\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "main work")
            run_git(repo, "switch", "feature/merge")
            run_git(repo, "merge", "--no-ff", "main", "-m", "merge main")

            output = Path(directory) / "inventory.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--base",
                    "main",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            inventory = json.loads(output.read_text(encoding="utf-8"))
            commits = {entry["subject"]: entry for entry in inventory["commits"]}
            merge_commit = commits["merge main"]
            self.assertEqual(len(merge_commit["parents"]), 2)
            self.assertEqual(len(merge_commit.get("parent_changes", [])), 2)
            changed_paths = {
                change["path"]
                for parent in merge_commit["parent_changes"]
                for change in parent["changes"]
            }
            self.assertEqual(changed_paths, {"feature.txt", "main.txt"})

    def test_inventory_fails_when_base_ref_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Skill Test")
            run_git(repo, "config", "user.email", "skill-test@example.com")
            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--base",
                    "origin/main",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("origin/main", result.stderr)

    def test_inventory_can_include_tracked_and_untracked_working_tree_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            run_git(repo, "init", "-b", "main")
            run_git(repo, "config", "user.name", "Skill Test")
            run_git(repo, "config", "user.email", "skill-test@example.com")
            tracked = repo / "tracked.txt"
            tracked.write_text("base\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "base")

            run_git(repo, "switch", "-c", "feature/dirty")
            tracked.write_text("committed\n", encoding="utf-8")
            run_git(repo, "add", ".")
            run_git(repo, "commit", "-m", "committed behavior")
            tracked.write_text("working tree\n", encoding="utf-8")
            (repo / "untracked.txt").write_text("new working file\n", encoding="utf-8")

            output = Path(directory) / "inventory.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--base",
                    "main",
                    "--include-working-tree",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            inventory = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(inventory["includes_working_tree"])
            files = {entry["path"]: entry for entry in inventory["files"]}
            self.assertEqual(set(files), {"tracked.txt", "untracked.txt"})
            self.assertEqual(files["untracked.txt"]["status"], "A")
            self.assertEqual(
                files["untracked.txt"]["working_tree_status"],
                "??",
            )
            untracked_hunks = [
                hunk
                for hunk in inventory["hunks"]
                if hunk["file_id"] == files["untracked.txt"]["id"]
            ]
            self.assertEqual(len(untracked_hunks), 1)


if __name__ == "__main__":
    unittest.main()
