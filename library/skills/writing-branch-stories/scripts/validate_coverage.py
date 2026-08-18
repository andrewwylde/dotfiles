#!/usr/bin/env python3
"""Validate branch-story coverage and Markdown story structure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


COMMIT_DISPOSITIONS = {"included", "excluded", "reverted", "superseded"}
CHANGE_DISPOSITIONS = {"included", "excluded"}
REQUIREMENT_LABELS = ("Confirmed:", "Inferred:", "Needs decision:")
READINESS_LABELS = (
    "Release blocker:",
    "Required follow-up:",
    "Present in branch, not runtime-verified:",
    "Not applicable:",
)
REQUIRED_SECTIONS = ("Problem", "Requirements", "Implementation")
SCOPE_DISPOSITIONS = {
    "included",
    "excluded",
    "reverted",
    "superseded",
    "ambiguous",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def require_reason(
    errors: list[str],
    label: str,
    entry: dict[str, Any],
) -> None:
    if not str(entry.get("reason", "")).strip():
        errors.append(f"{label} requires a reason")


def validate_story(
    path: Path,
    story_entry: dict[str, Any],
    allow_extra_sections: bool,
) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return [f"cannot read story {path.name}: {error}"]

    h1_lines = [line for line in lines if line.startswith("# ")]
    if len(h1_lines) != 1:
        errors.append(f"{path.name}: expected exactly one title")

    section_indexes: dict[str, int] = {}
    extra_sections: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        section = line[3:].strip()
        if section in section_indexes:
            errors.append(f"{path.name}: duplicate section {section}")
        section_indexes[section] = index
        if section not in REQUIRED_SECTIONS:
            extra_sections.append(section)

    missing_sections = [
        section for section in REQUIRED_SECTIONS if section not in section_indexes
    ]
    if missing_sections:
        errors.append(
            f"{path.name}: missing sections: {', '.join(missing_sections)}"
        )
        return errors
    if extra_sections and not allow_extra_sections:
        errors.append(
            f"{path.name}: unexpected sections: {', '.join(extra_sections)}"
        )

    section_content: dict[str, list[str]] = {}
    ordered_sections = sorted(section_indexes.items(), key=lambda item: item[1])
    for position, (section, start) in enumerate(ordered_sections):
        end = len(lines)
        if position + 1 < len(ordered_sections):
            end = ordered_sections[position + 1][1]
        section_content[section] = lines[start + 1 : end]

    for section in REQUIRED_SECTIONS:
        if not any(line.startswith("- ") for line in section_content[section]):
            errors.append(f"{path.name}: {section} must contain a bullet")

    requirement_bullets = [
        line[2:].strip()
        for line in section_content["Requirements"]
        if line.startswith("- ")
    ]
    for bullet in requirement_bullets:
        if not bullet.startswith(REQUIREMENT_LABELS):
            errors.append(
                f"{path.name}: requirement must start with "
                "Confirmed:, Inferred:, or Needs decision:"
            )

    implementation = section_content["Implementation"]
    current = [
        line
        for line in implementation
        if line.startswith("- Current branch implementation:")
    ]
    recommended = [
        line
        for line in implementation
        if line.startswith("- Recommended implementation:")
    ]
    readiness_indexes = [
        index
        for index, line in enumerate(implementation)
        if line.startswith("- Production readiness:")
    ]
    if len(current) != 1:
        errors.append(
            f"{path.name}: expected one Current branch implementation bullet"
        )
    elif "Evidence:" not in current[0]:
        errors.append(
            f"{path.name}: Current branch implementation must include inline Evidence"
        )
    if len(recommended) != 1:
        errors.append(f"{path.name}: expected one Recommended implementation bullet")
    if len(readiness_indexes) != 1:
        errors.append(f"{path.name}: expected one Production readiness bullet")
    else:
        readiness_start = readiness_indexes[0] + 1
        nested = [
            line.strip()[2:].strip()
            for line in implementation[readiness_start:]
            if line.startswith("  - ")
        ]
        if not nested:
            errors.append(
                f"{path.name}: Production readiness requires a severity bullet"
            )
        for bullet in nested:
            if not bullet.startswith(READINESS_LABELS):
                errors.append(
                    f"{path.name}: readiness finding has an invalid severity label"
                )

    if story_entry.get("kind") == "context":
        evidence = story_entry.get("evidence_commit_ids", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{path.name}: context story requires evidence_commit_ids")
        if current and "no surviving implementation" not in current[0].lower():
            errors.append(
                f"{path.name}: context story must state that no implementation survives"
            )
    return errors


def validate_handoff(
    handoff: dict[str, Any],
    inventory_commit_ids: set[str],
    inventory_file_ids: set[str],
    inventory_hunk_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    role = handoff.get("role")
    label = str(role or "handoff")
    if handoff.get("schema_version") != 1:
        errors.append(f"{label}: schema_version must be 1")
    if not isinstance(role, str) or not role.strip():
        errors.append("handoff role must be a non-empty string")

    partition = handoff.get("partition")
    if not isinstance(partition, dict):
        errors.append(f"{label}: partition must be an object")
        partition = {}
    partition_commits = partition.get("commit_ids", [])
    partition_files = partition.get("file_ids", [])
    if not isinstance(partition_commits, list) or not isinstance(partition_files, list):
        errors.append(f"{label}: partition IDs must be arrays")
    else:
        unknown_commits = sorted(set(partition_commits) - inventory_commit_ids)
        unknown_files = sorted(set(partition_files) - inventory_file_ids)
        if unknown_commits:
            errors.append(
                f"{label}: unknown partition commits: {', '.join(unknown_commits)}"
            )
        if unknown_files:
            errors.append(
                f"{label}: unknown partition files: {', '.join(unknown_files)}"
            )

    findings = handoff.get("findings")
    if not isinstance(findings, list):
        return [*errors, f"{label}: findings must be an array"]
    known_change_ids = inventory_file_ids | inventory_hunk_ids
    for index, finding in enumerate(findings):
        finding_label = f"{label} finding {index + 1}"
        if not isinstance(finding, dict):
            errors.append(f"{finding_label}: must be an object")
            continue
        change_ids = finding.get("change_ids", [])
        commit_ids = finding.get("commit_ids", [])
        paths = finding.get("paths", [])
        evidence = finding.get("evidence", [])
        if not isinstance(change_ids, list) or not change_ids:
            errors.append(f"{finding_label}: change_ids must be a non-empty array")
        else:
            unknown = sorted(set(change_ids) - known_change_ids)
            if unknown:
                errors.append(
                    f"{finding_label}: unknown change IDs: {', '.join(unknown)}"
                )
        if not isinstance(commit_ids, list):
            errors.append(f"{finding_label}: commit_ids must be an array")
        else:
            unknown = sorted(set(commit_ids) - inventory_commit_ids)
            if unknown:
                errors.append(
                    f"{finding_label}: unknown commit IDs: {', '.join(unknown)}"
                )
        if not isinstance(paths, list) or not paths:
            errors.append(f"{finding_label}: paths must be a non-empty array")
        if not str(finding.get("observed_behavior", "")).strip():
            errors.append(f"{finding_label}: observed_behavior is required")
        if finding.get("scope_disposition") not in SCOPE_DISPOSITIONS:
            errors.append(f"{finding_label}: invalid scope_disposition")
        candidate_story = finding.get("candidate_story")
        if candidate_story is not None and not str(candidate_story).strip():
            errors.append(f"{finding_label}: candidate_story must be null or non-empty")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{finding_label}: evidence must be a non-empty array")
        if finding.get("confidence") not in CONFIDENCE_LEVELS:
            errors.append(f"{finding_label}: confidence must be low, medium, or high")
        readiness_gaps = finding.get("readiness_gaps", [])
        if not isinstance(readiness_gaps, list):
            errors.append(f"{finding_label}: readiness_gaps must be an array")
        else:
            for gap in readiness_gaps:
                if not isinstance(gap, dict):
                    errors.append(f"{finding_label}: readiness gap must be an object")
                    continue
                if gap.get("severity") not in {
                    label.removesuffix(":") for label in READINESS_LABELS
                }:
                    errors.append(f"{finding_label}: invalid readiness severity")
                if not str(gap.get("detail", "")).strip():
                    errors.append(f"{finding_label}: readiness detail is required")
    return errors


def validate(
    inventory: dict[str, Any],
    coverage: dict[str, Any],
    stories_dir: Path,
    handoffs: list[dict[str, Any]],
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    if inventory.get("schema_version") != 1:
        errors.append("inventory schema_version must be 1")
    if coverage.get("schema_version") != 1:
        errors.append("coverage schema_version must be 1")
    if coverage.get("base_sha") != inventory.get("base", {}).get("sha"):
        errors.append("coverage base_sha does not match inventory")
    if coverage.get("head_sha") != inventory.get("head", {}).get("sha"):
        errors.append("coverage head_sha does not match inventory")
    if coverage.get("inventory_snapshot_sha256") != inventory.get(
        "snapshot_sha256"
    ):
        errors.append(
            "coverage inventory_snapshot_sha256 does not match inventory"
        )

    story_entries = coverage.get("stories", [])
    if not isinstance(story_entries, list):
        errors.append("coverage stories must be an array")
        story_entries = []
    story_ids = [entry.get("id") for entry in story_entries if isinstance(entry, dict)]
    known_story_ids = {story_id for story_id in story_ids if isinstance(story_id, str)}
    if len(story_ids) != len(known_story_ids):
        errors.append("story IDs must be unique non-empty strings")
    story_files = [
        entry.get("file") for entry in story_entries if isinstance(entry, dict)
    ]
    if len(story_files) != len(set(story_files)):
        errors.append("story files must be unique")

    inventory_commits = {
        entry["id"] for entry in inventory.get("commits", []) if "id" in entry
    }
    commit_coverage = coverage.get("commits", {})
    if not isinstance(commit_coverage, dict):
        errors.append("coverage commits must be an object")
        commit_coverage = {}
    missing_commits = sorted(inventory_commits - set(commit_coverage))
    extra_commits = sorted(set(commit_coverage) - inventory_commits)
    if missing_commits:
        errors.append(f"missing commit coverage: {', '.join(missing_commits)}")
    if extra_commits:
        errors.append(f"unknown commit coverage: {', '.join(extra_commits)}")
    excluded_commits = 0
    reverted_commits = 0
    superseded_commits = 0
    for commit_id, entry in commit_coverage.items():
        if not isinstance(entry, dict):
            errors.append(f"{commit_id} coverage must be an object")
            continue
        disposition = entry.get("disposition")
        if disposition not in COMMIT_DISPOSITIONS:
            errors.append(f"{commit_id} has invalid disposition")
            continue
        story_refs = entry.get("story_ids", [])
        if not isinstance(story_refs, list):
            errors.append(f"{commit_id} story_ids must be an array")
            story_refs = []
        unknown_refs = sorted(set(story_refs) - known_story_ids)
        if unknown_refs:
            errors.append(f"{commit_id} references unknown stories: {unknown_refs}")
        if disposition == "included" and not story_refs:
            errors.append(f"{commit_id} included coverage requires a story")
        if disposition != "included":
            require_reason(errors, commit_id, entry)
        excluded_commits += disposition == "excluded"
        reverted_commits += disposition == "reverted"
        superseded_commits += disposition == "superseded"

    for story_entry in story_entries:
        if not isinstance(story_entry, dict) or story_entry.get("kind") != "context":
            continue
        evidence = story_entry.get("evidence_commit_ids", [])
        if not isinstance(evidence, list):
            continue
        unknown_evidence = sorted(set(evidence) - inventory_commits)
        if unknown_evidence:
            errors.append(
                "context story references unknown evidence commits: "
                f"{', '.join(unknown_evidence)}"
            )
        nonhistorical = sorted(
            commit_id
            for commit_id in evidence
            if commit_id in commit_coverage
            and commit_coverage[commit_id].get("disposition")
            not in {"reverted", "superseded"}
        )
        if nonhistorical:
            errors.append(
                "context story evidence must be reverted or superseded: "
                f"{', '.join(nonhistorical)}"
            )

    inventory_files = {
        entry["id"]: entry for entry in inventory.get("files", []) if "id" in entry
    }
    inventory_hunks = {
        entry["id"]: entry for entry in inventory.get("hunks", []) if "id" in entry
    }
    file_coverage = coverage.get("files", {})
    hunk_coverage = coverage.get("hunks", {})
    if not isinstance(file_coverage, dict):
        errors.append("coverage files must be an object")
        file_coverage = {}
    if not isinstance(hunk_coverage, dict):
        errors.append("coverage hunks must be an object")
        hunk_coverage = {}
    missing_files = sorted(set(inventory_files) - set(file_coverage))
    extra_files = sorted(set(file_coverage) - set(inventory_files))
    if missing_files:
        errors.append(f"missing file coverage: {', '.join(missing_files)}")
    if extra_files:
        errors.append(f"unknown file coverage: {', '.join(extra_files)}")

    required_hunks: set[str] = set()
    non_split_hunks: set[str] = set()
    change_units = 0
    excluded_changes = 0
    for file_id, entry in file_coverage.items():
        if not isinstance(entry, dict) or file_id not in inventory_files:
            continue
        disposition = entry.get("disposition")
        if disposition not in CHANGE_DISPOSITIONS:
            errors.append(f"{file_id} has invalid disposition")
            continue
        split = entry.get("split_into_hunks") is True
        file_hunks = {
            hunk_id
            for hunk_id, hunk in inventory_hunks.items()
            if hunk.get("file_id") == file_id
        }
        if split:
            if not file_hunks:
                errors.append(f"{file_id} cannot split because it has no hunks")
            required_hunks.update(file_hunks)
            change_units += len(file_hunks)
            if entry.get("story_id"):
                errors.append(f"{file_id} split coverage cannot have a story_id")
        else:
            non_split_hunks.update(file_hunks)
            change_units += 1
            if disposition == "included":
                story_id = entry.get("story_id")
                if story_id not in known_story_ids:
                    errors.append(f"{file_id} requires a known story_id")
            else:
                require_reason(errors, file_id, entry)
                excluded_changes += 1

    missing_hunks = sorted(required_hunks - set(hunk_coverage))
    extra_hunks = sorted(set(hunk_coverage) - required_hunks)
    if missing_hunks:
        errors.append(f"missing hunk coverage: {', '.join(missing_hunks)}")
    if extra_hunks:
        errors.append(f"unexpected hunk coverage: {', '.join(extra_hunks)}")
    for hunk_id, entry in hunk_coverage.items():
        if not isinstance(entry, dict) or hunk_id not in required_hunks:
            continue
        disposition = entry.get("disposition")
        if disposition not in CHANGE_DISPOSITIONS:
            errors.append(f"{hunk_id} has invalid disposition")
        elif disposition == "included":
            if entry.get("story_id") not in known_story_ids:
                errors.append(f"{hunk_id} requires a known story_id")
        else:
            require_reason(errors, hunk_id, entry)
            excluded_changes += 1

    allow_extra = coverage.get("allow_extra_sections") is True
    for entry in story_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            errors.append("each story requires an id and file")
            continue
        story_path = stories_dir / entry["file"]
        errors.extend(validate_story(story_path, entry, allow_extra))
    actual_markdown = {path.name for path in stories_dir.glob("*.md")}
    expected_markdown = {name for name in story_files if isinstance(name, str)}
    extras = sorted(actual_markdown - expected_markdown)
    if extras:
        errors.append(f"unexpected story files: {', '.join(extras)}")
    for handoff in handoffs:
        errors.extend(
            validate_handoff(
                handoff,
                inventory_commits,
                set(inventory_files),
                set(inventory_hunks),
            )
        )

    summary = {
        "commits": len(inventory_commits),
        "change_units": change_units,
        "stories": len(known_story_ids),
        "excluded_commits": excluded_commits,
        "reverted_commits": reverted_commits,
        "superseded_commits": superseded_commits,
        "excluded_change_units": excluded_changes,
        "handoffs": len(handoffs),
    }
    return errors, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--stories-dir", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inventory = load_json(args.inventory)
        coverage = load_json(args.coverage)
        handoffs = [load_json(path) for path in args.handoff]
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    errors, summary = validate(inventory, coverage, args.stories_dir, handoffs)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
