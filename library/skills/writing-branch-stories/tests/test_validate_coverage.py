import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_coverage.py"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def story(title: str, evidence: str) -> str:
    return f"""# {title}

## Problem
- A person cannot complete an important task reliably.

## Requirements
- Confirmed: The person can complete the task and understand the result.

## Implementation
- Current branch implementation: The branch adds the initial behavior. Evidence: `{evidence}`.
- Recommended implementation: Keep the behavior while separating its responsibilities.
- Production readiness:
  - Present in branch, not runtime-verified: Static error handling is present.
"""


class ValidateCoverageTests(unittest.TestCase):
    def test_validator_accepts_hybrid_coverage_and_story_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stories = root / "stories"
            stories.mkdir()
            (stories / "01-primary.md").write_text(
                story("Primary outcome", "commit:c1, file:f1"),
                encoding="utf-8",
            )
            (stories / "02-secondary.md").write_text(
                story("Secondary outcome", "commit:c1, hunk:h3"),
                encoding="utf-8",
            )

            inventory = {
                "schema_version": 1,
                "base": {"sha": "base"},
                "head": {"sha": "head"},
                "snapshot_sha256": "snapshot",
                "commits": [{"id": "commit:c1"}, {"id": "commit:c2"}],
                "files": [{"id": "file:f1"}, {"id": "file:f2"}],
                "hunks": [
                    {"id": "hunk:h1", "file_id": "file:f1"},
                    {"id": "hunk:h2", "file_id": "file:f2"},
                    {"id": "hunk:h3", "file_id": "file:f2"},
                ],
            }
            coverage = {
                "schema_version": 1,
                "base_sha": "base",
                "head_sha": "head",
                "inventory_snapshot_sha256": "snapshot",
                "stories": [
                    {
                        "id": "story-primary",
                        "file": "01-primary.md",
                        "kind": "implementation",
                    },
                    {
                        "id": "story-secondary",
                        "file": "02-secondary.md",
                        "kind": "implementation",
                    },
                ],
                "commits": {
                    "commit:c1": {
                        "disposition": "included",
                        "story_ids": ["story-primary", "story-secondary"],
                    },
                    "commit:c2": {
                        "disposition": "excluded",
                        "story_ids": [],
                        "reason": "Outside the requested scope.",
                    },
                },
                "files": {
                    "file:f1": {
                        "disposition": "included",
                        "story_id": "story-primary",
                        "split_into_hunks": False,
                    },
                    "file:f2": {
                        "disposition": "included",
                        "split_into_hunks": True,
                    },
                },
                "hunks": {
                    "hunk:h2": {
                        "disposition": "included",
                        "story_id": "story-primary",
                    },
                    "hunk:h3": {
                        "disposition": "included",
                        "story_id": "story-secondary",
                    },
                },
            }
            inventory_path = root / "inventory.json"
            coverage_path = root / "coverage.json"
            handoff_path = root / "change-scout.json"
            write_json(inventory_path, inventory)
            write_json(coverage_path, coverage)
            write_json(
                handoff_path,
                {
                    "schema_version": 1,
                    "role": "change-scout",
                    "partition": {
                        "commit_ids": ["commit:c1"],
                        "file_ids": ["file:f1", "file:f2"],
                    },
                    "findings": [
                        {
                            "change_ids": ["file:f1", "hunk:h2", "hunk:h3"],
                            "commit_ids": ["commit:c1"],
                            "paths": ["app.txt"],
                            "observed_behavior": "The branch changes an observable task.",
                            "scope_disposition": "included",
                            "candidate_story": "story-primary",
                            "evidence": ["The changed source and test agree."],
                            "readiness_gaps": [
                                {
                                    "severity": "Required follow-up",
                                    "detail": "Add failure-path coverage.",
                                }
                            ],
                            "confidence": "high",
                        }
                    ],
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inventory",
                    str(inventory_path),
                    "--coverage",
                    str(coverage_path),
                    "--stories-dir",
                    str(stories),
                    "--handoff",
                    str(handoff_path),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["commits"], 2)
            self.assertEqual(summary["change_units"], 3)
            self.assertEqual(summary["stories"], 2)
            self.assertEqual(summary["excluded_commits"], 1)

    def test_validator_rejects_context_story_without_historical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stories = root / "stories"
            stories.mkdir()
            (stories / "01-context.md").write_text(
                story("Attempted outcome", "commit:c1"),
                encoding="utf-8",
            )
            inventory = {
                "schema_version": 1,
                "base": {"sha": "base"},
                "head": {"sha": "head"},
                "snapshot_sha256": "snapshot",
                "commits": [{"id": "commit:c1"}],
                "files": [],
                "hunks": [],
            }
            coverage = {
                "schema_version": 1,
                "base_sha": "base",
                "head_sha": "head",
                "inventory_snapshot_sha256": "snapshot",
                "stories": [
                    {
                        "id": "story-context",
                        "file": "01-context.md",
                        "kind": "context",
                    }
                ],
                "commits": {
                    "commit:c1": {
                        "disposition": "reverted",
                        "story_ids": ["story-context"],
                        "reason": "The attempted implementation was reverted.",
                    }
                },
                "files": {},
                "hunks": {},
            }
            inventory_path = root / "inventory.json"
            coverage_path = root / "coverage.json"
            write_json(inventory_path, inventory)
            write_json(coverage_path, coverage)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inventory",
                    str(inventory_path),
                    "--coverage",
                    str(coverage_path),
                    "--stories-dir",
                    str(stories),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "context story requires evidence_commit_ids",
                result.stderr,
            )
            self.assertIn(
                "context story must state that no implementation survives",
                result.stderr,
            )

    def test_validator_rejects_context_story_with_unknown_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stories = root / "stories"
            stories.mkdir()
            context_story = story("Attempted outcome", "commit:c1").replace(
                "The branch adds the initial behavior.",
                "No surviving implementation remains on the branch.",
            )
            (stories / "01-context.md").write_text(
                context_story,
                encoding="utf-8",
            )
            inventory = {
                "schema_version": 1,
                "base": {"sha": "base"},
                "head": {"sha": "head"},
                "snapshot_sha256": "snapshot",
                "commits": [{"id": "commit:c1"}],
                "files": [],
                "hunks": [],
            }
            coverage = {
                "schema_version": 1,
                "base_sha": "base",
                "head_sha": "head",
                "inventory_snapshot_sha256": "snapshot",
                "stories": [
                    {
                        "id": "story-context",
                        "file": "01-context.md",
                        "kind": "context",
                        "evidence_commit_ids": ["commit:missing"],
                    }
                ],
                "commits": {
                    "commit:c1": {
                        "disposition": "reverted",
                        "story_ids": ["story-context"],
                        "reason": "The attempted implementation was reverted.",
                    }
                },
                "files": {},
                "hunks": {},
            }
            inventory_path = root / "inventory.json"
            coverage_path = root / "coverage.json"
            write_json(inventory_path, inventory)
            write_json(coverage_path, coverage)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inventory",
                    str(inventory_path),
                    "--coverage",
                    str(coverage_path),
                    "--stories-dir",
                    str(stories),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "context story references unknown evidence commits",
                result.stderr,
            )

    def test_validator_rejects_missing_hybrid_hunk_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stories = root / "stories"
            stories.mkdir()
            (stories / "01-outcome.md").write_text(
                story("Outcome", "commit:c1, hunk:h1"),
                encoding="utf-8",
            )
            inventory = {
                "schema_version": 1,
                "base": {"sha": "base"},
                "head": {"sha": "head"},
                "snapshot_sha256": "snapshot",
                "commits": [{"id": "commit:c1"}],
                "files": [{"id": "file:f1"}],
                "hunks": [{"id": "hunk:h1", "file_id": "file:f1"}],
            }
            coverage = {
                "schema_version": 1,
                "base_sha": "base",
                "head_sha": "head",
                "inventory_snapshot_sha256": "snapshot",
                "stories": [
                    {
                        "id": "story-outcome",
                        "file": "01-outcome.md",
                        "kind": "implementation",
                    }
                ],
                "commits": {
                    "commit:c1": {
                        "disposition": "included",
                        "story_ids": ["story-outcome"],
                    }
                },
                "files": {
                    "file:f1": {
                        "disposition": "included",
                        "split_into_hunks": True,
                    }
                },
                "hunks": {},
            }
            inventory_path = root / "inventory.json"
            coverage_path = root / "coverage.json"
            write_json(inventory_path, inventory)
            write_json(coverage_path, coverage)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inventory",
                    str(inventory_path),
                    "--coverage",
                    str(coverage_path),
                    "--stories-dir",
                    str(stories),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("missing hunk coverage: hunk:h1", result.stderr)

    def test_validator_rejects_changed_inventory_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stories = root / "stories"
            stories.mkdir()
            inventory = {
                "schema_version": 1,
                "base": {"sha": "base"},
                "head": {"sha": "head"},
                "snapshot_sha256": "current",
                "commits": [],
                "files": [],
                "hunks": [],
            }
            coverage = {
                "schema_version": 1,
                "base_sha": "base",
                "head_sha": "head",
                "inventory_snapshot_sha256": "stale",
                "stories": [],
                "commits": {},
                "files": {},
                "hunks": {},
            }
            inventory_path = root / "inventory.json"
            coverage_path = root / "coverage.json"
            write_json(inventory_path, inventory)
            write_json(coverage_path, coverage)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--inventory",
                    str(inventory_path),
                    "--coverage",
                    str(coverage_path),
                    "--stories-dir",
                    str(stories),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "coverage inventory_snapshot_sha256 does not match inventory",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
