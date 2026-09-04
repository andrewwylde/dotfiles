#!/usr/bin/env python3
"""
Pre-flight check and pipeline state detection for /ship-feature.

Verifies all prerequisites are met and determines which pipeline stage
to resume from based on artifacts on disk and git/GitHub state.

Usage:
    python pipeline_status.py [--branch BRANCH] [--ticket TICKET_ID]

Output: Structured JSON to stdout + human-readable summary to stderr.

Examples:
    python pipeline_status.py
    python pipeline_status.py --branch feat/cd-1234-add-freshness
    python pipeline_status.py --ticket CD-1234
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PreflightResult:
    tool: str
    ok: bool
    detail: str


@dataclass
class StageArtifact:
    stage: int
    name: str
    found: bool
    path: str | None = None
    detail: str = ""


@dataclass
class PipelineStatus:
    branch: str
    ticket_id: str | None
    preflight: list[PreflightResult]
    artifacts: list[StageArtifact]
    resume_stage: int
    resume_reason: str
    pr_number: int | None = None
    pr_url: str | None = None
    unpushed_commits: int = 0
    warnings: list[str] = field(default_factory=list)


def run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=check)


def find_main_workspace() -> Path | None:
    """Resolve the main git workspace when running inside a worktree.

    Git worktrees created by best-of-n-runner lack locally-excluded files
    (e.g. .cursor/commands/). This finds the main workspace so we can locate
    those files even when cwd is a worktree.
    """
    result = run(["git", "worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return None
    main_path = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = Path(line.split(" ", 1)[1])
            main_path = candidate
            break
    if main_path and main_path != Path.cwd():
        return main_path
    return None


def check_tool(name: str, test_args: list[str] | None = None) -> PreflightResult:
    """Check if a CLI tool is available."""
    which = run(["which", name])
    if which.returncode != 0:
        return PreflightResult(name, False, "not found in PATH")
    if test_args:
        result = run(test_args)
        if result.returncode != 0:
            return PreflightResult(name, False, result.stderr.strip()[:200])
    return PreflightResult(name, True, which.stdout.strip())


def check_gh_auth() -> PreflightResult:
    """Verify gh CLI is authenticated."""
    result = run(["gh", "auth", "status"])
    combined = result.stdout + result.stderr
    if result.returncode != 0 or "not logged in" in combined.lower():
        return PreflightResult("gh-auth", False, "not authenticated — run `gh auth login`")
    match = re.search(r"Logged in to ([^\s]+) as ([^\s]+)", combined)
    if match:
        return PreflightResult("gh-auth", True, f"{match.group(2)}@{match.group(1)}")
    return PreflightResult("gh-auth", True, "authenticated")


def check_directory(name: str, path: Path) -> PreflightResult:
    if path.is_dir():
        return PreflightResult(f"dir:{name}", True, str(path))
    return PreflightResult(f"dir:{name}", False, f"{path} does not exist")


def check_command_file(name: str, path: Path) -> PreflightResult:
    if path.is_file():
        return PreflightResult(f"cmd:{name}", True, str(path))
    return PreflightResult(f"cmd:{name}", False, f"{path} not found")


def resolve_command_file(name: str, main_workspace: Path | None) -> PreflightResult:
    """Resolve a slash command from project, main workspace, or global dirs.

    Project worktrees often do not carry `.cursor/commands`. The user's global
    commands are the intended source of truth for shared workflows, so a missing
    repo-local file is not a failure when a global command exists.
    """
    search_paths = [
        Path.home() / ".cursor" / "commands",
        Path.home() / ".claude" / "commands",
        Path(".cursor/commands"),
    ]
    if main_workspace:
        search_paths.append(main_workspace / ".cursor" / "commands")

    for command_dir in search_paths:
        candidate = command_dir / f"{name}.md"
        if candidate.is_file():
            return PreflightResult(f"cmd:{name}", True, str(candidate))

    return PreflightResult(
        f"cmd:{name}",
        True,
        f"not found on disk; use runtime command surface or bundled stage-details fallback for /{name}",
    )


def get_branch() -> str:
    result = run(["git", "branch", "--show-current"])
    return result.stdout.strip() or "HEAD"


def extract_ticket_id(branch: str) -> str | None:
    match = re.search(r"([A-Z]+-\d+)", branch, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _stem_word(word: str) -> str:
    """Reduce a word to a rough stem for fuzzy matching.

    Handles common suffixes so 'transform'/'transformation'/'transforming'
    and 'persist'/'persistence'/'persistent' converge to the same stem.
    """
    for suffix in ("ation", "tion", "ence", "ance", "ment", "ing", "ive", "ent", "ant", "ity", "ous", "ful", "ness", "able", "ible"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def find_plan_files(ticket_id: str | None, branch: str) -> list[Path]:
    """Find plan files matching ticket or branch name.

    Uses stemmed word overlap so 'transform-health-persistence' matches plans
    named with 'transformation', 'persist', etc. Warns when multiple plans
    match the same feature (likely stale artifact from a prior session).
    """
    plans_dir = Path("plans")
    if not plans_dir.is_dir():
        return []

    candidates = sorted(plans_dir.glob("*.plan.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        matched = [p for p in candidates if ticket_lower in p.name.lower().replace("-", "_")]
        if matched:
            if len(matched) > 1:
                print(f"  WARNING: {len(matched)} plans match ticket {ticket_id}:")
                for m in matched:
                    print(f"    - {m.name} (modified {_fmt_mtime(m)})")
                print("  Consider deleting stale plans before proceeding.")
            return matched

    slug = branch.split("/")[-1].replace("-", "_").lower()
    noise = {"feat", "fix", "refactor", "chore", "feature", "bug", "docs"}
    slug_words = set(slug.split("_")) - noise
    slug_stems = {_stem_word(w) for w in slug_words}

    matched = []
    for p in candidates:
        plan_words = set(p.stem.lower().split("_")) - noise
        plan_stems = {_stem_word(w) for w in plan_words}
        if len(slug_stems & plan_stems) >= 2:
            matched.append(p)

    if len(matched) > 1:
        print(f"  WARNING: {len(matched)} plans match branch '{branch}':")
        for m in matched:
            print(f"    - {m.name} (modified {_fmt_mtime(m)})")
        print("  This likely means a prior session created a plan that was not cleaned up.")
        print("  Delete stale plans or specify which to use before proceeding.")

    return matched or candidates[:1]


def _fmt_mtime(p: Path) -> str:
    """Format file mtime as a readable timestamp."""
    import datetime
    return datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def find_plan_review(plan_path: Path | None) -> Path | None:
    """Find plan review matching a plan file."""
    review_dir = Path(".context/reviews")
    if not review_dir.is_dir() or plan_path is None:
        return None

    plan_stem = plan_path.stem.replace(".plan", "")
    for review in review_dir.glob("plan_*.md"):
        if plan_stem in review.name:
            return review
    return None


def find_pr_review(pr_number: int | None) -> Path | None:
    """Find self-review for a PR."""
    review_dir = Path(".context/prs/reviews")
    if not review_dir.is_dir() or pr_number is None:
        return None

    for pattern in [f"PR_REVIEW_#{pr_number}.md", f"PR_REVIEW_{pr_number}.md"]:
        candidate = review_dir / pattern
        if candidate.is_file():
            return candidate
    return None


def get_unpushed_count() -> int:
    result = run(["git", "rev-list", "--count", "@{upstream}..HEAD"])
    if result.returncode != 0:
        result = run(["git", "rev-list", "--count", "origin/main..HEAD"])
        if result.returncode != 0:
            return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


# Stage sequence: 35=3.5, 375=3.75, 351=3.5b, 37=3.7, 38=3.8,
# 385=3.85 reference audit, 39=3.9 impl approval, 48=4.8 visual after, 49=4.9 visual approval
STAGE_SEQUENCE = [0, 1, 2, 3, 35, 375, 37, 38, 351, 385, 39, 4, 48, 49, 5, 6, 645, 65, 66, 665, 67]


def fmt_stage_label(stage: int) -> str:
    if stage == 35:
        return "3.5"
    if stage == 375:
        return "3.75"
    if stage == 351:
        return "3.5b"
    if stage == 37:
        return "3.7"
    if stage == 38:
        return "3.8"
    if stage == 385:
        return "3.85"
    if stage == 39:
        return "3.9"
    if stage == 48:
        return "4.8"
    if stage == 49:
        return "4.9"
    if stage == 645:
        return "6.45"
    if stage == 65:
        return "6.5"
    if stage == 66:
        return "6.6"
    if stage == 665:
        return "6.65"
    if stage == 67:
        return "6.7"
    return str(stage)


def next_resume_stage(completed_stage: int) -> int:
    try:
        idx = STAGE_SEQUENCE.index(completed_stage)
    except ValueError:
        return 0
    if idx + 1 < len(STAGE_SEQUENCE):
        return STAGE_SEQUENCE[idx + 1]
    return -1  # pipeline complete


def find_plan_level_benchmark(ticket_id: str | None, branch: str) -> Path | None:
    """Find plan-level test benchmark scorecard (Stage 3.75)."""
    bench_dir = Path(".context/test-benchmarks")
    if not bench_dir.is_dir():
        return None
    candidates = sorted(
        bench_dir.glob("*_plan-level.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        for p in candidates:
            if ticket_lower in p.name.lower().replace("-", "_"):
                return p
    slug = branch.split("/")[-1].replace("-", "_").lower()
    for p in candidates:
        if any(part in p.stem.lower() for part in slug.split("_") if len(part) > 3):
            return p
    return candidates[0]


def find_adversarial_review(plan_path: Path | None, ticket_id: str | None, branch: str) -> Path | None:
    """Find DE adversarial review for the plan (Stage 3.5)."""
    if plan_path is None:
        return None
    plan_stem = plan_path.stem.replace(".plan", "")
    search_dirs = [Path(".context/adversarial"), Path(".context/reviews")]
    candidates: list[Path] = []
    for directory in search_dirs:
        if directory.is_dir():
            candidates.extend(directory.glob("adversarial_*.md"))
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        for path in candidates:
            if plan_stem in path.name and ticket_lower in path.name.lower().replace("-", "_"):
                return path
    for path in candidates:
        if plan_stem in path.name:
            return path
    slug = branch.split("/")[-1].replace("-", "_").lower()
    for path in candidates:
        if any(part in path.stem.lower() for part in slug.split("_") if len(part) > 3):
            return path
    return None


def find_deferral_register(ticket_id: str | None, branch: str) -> Path | None:
    """Find Stage 3.5b deferral register."""
    defer_dir = Path(".context/deferrals")
    if not defer_dir.is_dir():
        return None
    candidates = sorted(defer_dir.glob("*_deferrals.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        for p in candidates:
            if ticket_lower in p.name.lower().replace("-", "_"):
                return p
    slug = branch.split("/")[-1].replace("-", "_").lower()
    for p in candidates:
        if any(part in p.stem.lower() for part in slug.split("_") if len(part) > 3):
            return p
    return candidates[0]


def find_code_level_benchmark(ticket_id: str | None, branch: str) -> Path | None:
    """Find code-level test benchmark scorecard."""
    bench_dir = Path(".context/test-benchmarks")
    if not bench_dir.is_dir():
        return None
    candidates = sorted(
        bench_dir.glob("*_code-level.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        for p in candidates:
            if ticket_lower in p.name.lower().replace("-", "_"):
                return p
    slug = branch.split("/")[-1].replace("-", "_").lower()
    for p in candidates:
        if any(part in p.stem.lower() for part in slug.split("_") if len(part) > 3):
            return p
    return candidates[0]


def find_proof_harness_gate() -> Path | None:
    """Find Stage 6.45 proof harness gate JSON."""
    gate = Path(".context/proof-harness-gate.json")
    if not gate.is_file():
        return None
    try:
        data = json.loads(gate.read_text())
        if "triggered" in data:
            return gate
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable gate artifact — treat as missing, non-fatal.
        pass
    return None


def find_rust_complexity_gate() -> Path | None:
    """Find Stage 6.6 gate JSON artifact."""
    gate = Path(".context/rust-cognitive-complexity-gate.json")
    if not gate.is_file():
        return None
    try:
        data = json.loads(gate.read_text())
        if "triggered" in data:
            return gate
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable gate artifact — treat as missing, non-fatal.
        pass
    return None


def find_psgen_gate(mode: str) -> Path | None:
    """Find Stage 3.7 (plan) or 6.65 (code) psgen gate JSON artifact."""
    gate = Path(f".context/psgen-gate-{mode}.json")
    if not gate.is_file():
        return None
    try:
        data = json.loads(gate.read_text())
        if "triggered" in data and data.get("mode") == mode:
            return gate
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable psgen gate JSON — treat as missing, non-fatal.
        pass
    return None


def find_scalar_gate(mode: str) -> Path | None:
    """Find Stage 3.8 (plan) or 6.7 (code) scalar-lib gate JSON artifact."""
    gate = Path(f".context/scalar-lib-gate-{mode}.json")
    if not gate.is_file():
        return None
    try:
        data = json.loads(gate.read_text())
        if "triggered" in data and data.get("mode") == mode:
            return gate
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable scalar gate JSON — treat as missing, non-fatal.
        pass
    return None


def find_scalar_audit(mode: str, ticket_id: str | None, branch: str) -> Path | None:
    """Find scalar-lib-it audit report when gate was triggered."""
    audit_dir = Path(".context/scalar-lib-audits")
    if not audit_dir.is_dir():
        return None
    suffix = "_design.md" if mode == "plan" else "_code.md"
    candidates = sorted(
        audit_dir.glob(f"*{suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    if ticket_id:
        ticket_lower = ticket_id.lower().replace("-", "_")
        for path in candidates:
            if ticket_lower in path.name.lower().replace("-", "_"):
                return path
    slug = branch.split("/")[-1].replace("-", "_").lower()
    for path in candidates:
        if any(part in path.stem.lower() for part in slug.split("_") if len(part) > 3):
            return path
    return candidates[0]


def find_pr_for_branch(branch: str) -> tuple[int | None, str | None]:
    """Check if a PR exists for the current branch."""
    result = run(["gh", "pr", "view", "--json", "number,url", "-q", '.number,.url'])
    if result.returncode != 0:
        return None, None
    lines = result.stdout.strip().split("\n")
    if len(lines) >= 2:
        try:
            return int(lines[0]), lines[1]
        except (ValueError, IndexError):
            # Malformed gh pr view output — treat as no PR, non-fatal.
            pass
    return None, None


def detect_pipeline_state(
    branch: str, ticket_id: str | None
) -> tuple[list[StageArtifact], int, str, int | None, str | None, int]:
    """Detect which pipeline stages have completed based on artifacts."""
    artifacts: list[StageArtifact] = []

    # Stage 0: Validate — no persistent artifact (skip detection)
    artifacts.append(StageArtifact(0, "validate (vibe-test)", False, detail="No persistent artifact — assumed pending"))

    # Stage 1: Plan
    plan_files = find_plan_files(ticket_id, branch)
    if plan_files:
        path = plan_files[0]
        detail = f"Found {len(plan_files)} matching plan(s)"
        if len(plan_files) > 1:
            detail += " *** DUPLICATE PLANS DETECTED -- delete stale plans before proceeding ***"
            for pf in plan_files:
                detail += f"\n    - {pf.name}"
        artifacts.append(StageArtifact(1, "plan", True, str(path), detail))
    else:
        artifacts.append(StageArtifact(1, "plan", False, detail="No matching plan found"))

    # Stage 2: Plan review
    plan_path = plan_files[0] if plan_files else None
    review = find_plan_review(plan_path)
    if review:
        artifacts.append(StageArtifact(2, "plan-review", True, str(review)))
    else:
        artifacts.append(StageArtifact(2, "plan-review", False, detail="No plan review found"))

    # Stage 3: Plan update — check if plan was modified after review
    if plan_path and review:
        plan_mtime = plan_path.stat().st_mtime
        review_mtime = review.stat().st_mtime
        if plan_mtime > review_mtime:
            artifacts.append(StageArtifact(3, "plan-update", True, detail="Plan modified after review"))
        else:
            artifacts.append(StageArtifact(3, "plan-update", True, detail="Plan unchanged (review passed)"))
    else:
        artifacts.append(StageArtifact(3, "plan-update", False))

    # Stage 3.5: DE adversarial review
    adversarial = find_adversarial_review(plan_path, ticket_id, branch)
    if adversarial:
        artifacts.append(StageArtifact(35, "DE adversarial", True, str(adversarial)))
    else:
        artifacts.append(StageArtifact(
            35, "DE adversarial", False,
            detail="No adversarial review in .context/adversarial/ or .context/reviews/",
        ))

    # Stage 3.75: Plan-level test benchmark
    plan_benchmark = find_plan_level_benchmark(ticket_id, branch)
    if plan_benchmark:
        artifacts.append(StageArtifact(375, "test benchmark (plan-level)", True, str(plan_benchmark)))
    else:
        artifacts.append(StageArtifact(
            375, "test benchmark (plan-level)", False,
            detail="No *_plan-level.md in .context/test-benchmarks/",
        ))

    # Stage 3.7: psgen plan gate (conditional)
    psgen_plan_gate = find_psgen_gate("plan")
    if psgen_plan_gate:
        try:
            gate_data = json.loads(psgen_plan_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(37, "psgen (plan)", True, str(psgen_plan_gate), detail))
    else:
        artifacts.append(StageArtifact(
            37, "psgen (plan)", False,
            detail="No .context/psgen-gate-plan.json",
        ))

    # Stage 3.8: Scalar-lib plan gate (conditional design audit)
    scalar_plan_gate = find_scalar_gate("plan")
    scalar_plan_audit = find_scalar_audit("plan", ticket_id, branch)
    if scalar_plan_gate:
        try:
            gate_data = json.loads(scalar_plan_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
            if triggered and scalar_plan_audit:
                detail += f"; audit={scalar_plan_audit.name}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(38, "scalar-lib-it (plan)", True, str(scalar_plan_gate), detail))
    else:
        artifacts.append(StageArtifact(
            38, "scalar-lib-it (plan)", False,
            detail="No .context/scalar-lib-gate-plan.json",
        ))

    # Stage 3.5b: Deferral register
    deferral = find_deferral_register(ticket_id, branch)
    if deferral:
        artifacts.append(StageArtifact(351, "deferral register", True, str(deferral)))
    else:
        artifacts.append(StageArtifact(
            351, "deferral register", False,
            detail="No .context/deferrals/*_deferrals.md",
        ))

    # PARABLE-609 campaign stages (user-scoped). Detect via .context/campaign-gate.json
    campaign_ticket = None
    campaign_triggered = False
    campaign_gate = Path(".context/campaign-gate.json")
    if campaign_gate.is_file():
        try:
            cg = json.loads(campaign_gate.read_text())
            campaign_triggered = bool(cg.get("triggered"))
            campaign_ticket = cg.get("ticket")
        except (json.JSONDecodeError, OSError):
            campaign_triggered = False

    if campaign_triggered and campaign_ticket:
        state_root = Path.home() / ".cursor" / "ship-feature-state" / "parable-609" / str(campaign_ticket).lower()
        audit = state_root / "reference-audit.md"
        artifacts.append(StageArtifact(
            385,
            "reference audit",
            audit.is_file(),
            str(audit) if audit.is_file() else None,
            detail=None if audit.is_file() else "missing reference-audit.md",
        ))
        impl = state_root / "implementation-approval.json"
        artifacts.append(StageArtifact(
            39,
            "implementation approval",
            impl.is_file(),
            str(impl) if impl.is_file() else None,
            detail="HUMAN GATE — do not edit source without approval" if not impl.is_file() else "approved",
        ))
    else:
        # Non-campaign: mark as complete so sequence advances
        artifacts.append(StageArtifact(385, "reference audit", True, detail="skipped (non-campaign)"))
        artifacts.append(StageArtifact(39, "implementation approval", True, detail="skipped (non-campaign)"))

    # Stage 4: Implement — check for commits on branch beyond main
    # Campaign mode: commits alone do NOT satisfy Stage 4 if implementation approval missing
    unpushed = get_unpushed_count()
    total_result = run(["git", "rev-list", "--count", "origin/main..HEAD"])
    total_commits = 0
    if total_result.returncode == 0:
        try:
            total_commits = int(total_result.stdout.strip())
        except ValueError:
            # Non-integer rev-list output — keep default total_commits=0.
            pass

    impl_approved = True
    if campaign_triggered and campaign_ticket:
        impl_approved = (
            Path.home()
            / ".cursor"
            / "ship-feature-state"
            / "parable-609"
            / str(campaign_ticket).lower()
            / "implementation-approval.json"
        ).is_file()

    if total_commits > 0 and impl_approved:
        artifacts.append(StageArtifact(
            4, "implement", True,
            detail=f"{total_commits} commit(s) on branch ({unpushed} unpushed)"
        ))
    elif total_commits > 0 and not impl_approved:
        artifacts.append(StageArtifact(
            4,
            "implement",
            False,
            detail=(
                f"{total_commits} commit(s) exist but Stage 3.9 approval missing — "
                "resume at 3.9, not Stage 5"
            ),
        ))
    else:
        artifacts.append(StageArtifact(4, "implement", False, detail="No commits beyond main"))

    if campaign_triggered and campaign_ticket:
        state_root = Path.home() / ".cursor" / "ship-feature-state" / "parable-609" / str(campaign_ticket).lower()
        after = state_root / "visual-proof" / "after.json"
        artifacts.append(StageArtifact(
            48,
            "visual after",
            after.is_file(),
            str(after) if after.is_file() else None,
            detail=None if after.is_file() else "missing after.json visual proof",
        ))
        visual = state_root / "visual-qa-approval.json"
        artifacts.append(StageArtifact(
            49,
            "visual approval",
            visual.is_file(),
            str(visual) if visual.is_file() else None,
            detail="HUMAN GATE — do not create PR without visual sign-off" if not visual.is_file() else "approved",
        ))
    else:
        artifacts.append(StageArtifact(48, "visual after", True, detail="skipped (non-campaign)"))
        artifacts.append(StageArtifact(49, "visual approval", True, detail="skipped (non-campaign)"))

    # Stage 5: Ship — check for PR
    pr_number, pr_url = find_pr_for_branch(branch)
    if pr_number:
        artifacts.append(StageArtifact(5, "ship (PR)", True, pr_url, f"PR #{pr_number}"))
    else:
        artifacts.append(StageArtifact(5, "ship (PR)", False, detail="No PR found for this branch"))

    # Stage 6: Self-review
    pr_review = find_pr_review(pr_number)
    if pr_review:
        artifacts.append(StageArtifact(6, "self-review", True, str(pr_review)))
    else:
        artifacts.append(StageArtifact(6, "self-review", False, detail="No self-review found"))

    # Stage 6.45: Proof harness
    proof_gate = find_proof_harness_gate()
    proof_log = Path(".context/implementation/proof-harness-log.md")
    proof_in_review = False
    if pr_review and pr_review.is_file():
        try:
            proof_in_review = "Stage 6.45" in pr_review.read_text()
        except OSError:
            # Unreadable PR review — treat as not documented in review, non-fatal.
            proof_in_review = False
    if proof_gate:
        try:
            gate_data = json.loads(proof_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(645, "proof harness", True, str(proof_gate), detail))
    elif proof_in_review or proof_log.is_file():
        detail = "documented in PR review or proof log"
        artifacts.append(StageArtifact(645, "proof harness", True, str(proof_log) if proof_log.is_file() else None, detail))
    else:
        artifacts.append(StageArtifact(
            645, "proof harness", False,
            detail="No .context/proof-harness-gate.json",
        ))

    # Stage 6.5: Code-level test benchmark
    code_benchmark = find_code_level_benchmark(ticket_id, branch)
    benchmark_in_review = False
    if pr_review and pr_review.is_file():
        try:
            review_text = pr_review.read_text()
            benchmark_in_review = (
                "Stage 6.5" in review_text
                or "Test Quality Assessment" in review_text
            )
        except OSError:
            # Unreadable PR review — treat as not documented in review, non-fatal.
            benchmark_in_review = False
    if code_benchmark or benchmark_in_review:
        detail = str(code_benchmark) if code_benchmark else "documented in PR review"
        artifacts.append(StageArtifact(65, "test benchmark (code-level)", True, detail))
    else:
        artifacts.append(StageArtifact(
            65, "test benchmark (code-level)", False,
            detail="No code-level scorecard found",
        ))

    # Stage 6.6: Rust cognitive complexity gate
    complexity_gate = find_rust_complexity_gate()
    gate_in_review = False
    if pr_review and pr_review.is_file():
        try:
            gate_in_review = "Stage 6.6" in pr_review.read_text()
        except OSError:
            # Unreadable PR review — treat as not documented in review, non-fatal.
            gate_in_review = False
    if complexity_gate:
        try:
            gate_data = json.loads(complexity_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(66, "rust complexity gate", True, str(complexity_gate), detail))
    elif gate_in_review:
        artifacts.append(StageArtifact(66, "rust complexity gate", True, detail="documented in PR review"))
    else:
        artifacts.append(StageArtifact(
            66, "rust complexity gate", False,
            detail="No .context/rust-cognitive-complexity-gate.json",
        ))

    # Stage 6.65: psgen code gate
    psgen_code_gate = find_psgen_gate("code")
    psgen_in_review = False
    psgen_review_read_error: str | None = None
    if pr_review and pr_review.is_file():
        try:
            review_text = pr_review.read_text()
            psgen_in_review = "Stage 6.65" in review_text or "Schema-first / psgen" in review_text
        except OSError as exc:
            psgen_review_read_error = str(exc)
    if psgen_code_gate:
        try:
            gate_data = json.loads(psgen_code_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(665, "psgen (code)", True, str(psgen_code_gate), detail))
    elif psgen_in_review:
        artifacts.append(StageArtifact(665, "psgen (code)", True, detail="documented in PR review"))
    else:
        detail = "No .context/psgen-gate-code.json"
        if psgen_review_read_error:
            detail = f"{detail}; pr_review read failed: {psgen_review_read_error}"
        artifacts.append(StageArtifact(
            665, "psgen (code)", False,
            detail=detail,
        ))

    # Stage 6.7: Scalar-lib code gate (conditional PR audit)
    scalar_code_gate = find_scalar_gate("code")
    scalar_code_audit = find_scalar_audit("code", ticket_id, branch)
    audit_in_review = False
    scalar_review_read_error: str | None = None
    if pr_review and pr_review.is_file():
        try:
            review_text = pr_review.read_text()
            audit_in_review = "Stage 6.7" in review_text or "Scalar-lib conformance" in review_text
        except OSError as exc:
            # Unreadable PR review — keep audit optional; surface read failure in detail.
            scalar_review_read_error = str(exc)
    if scalar_code_gate:
        try:
            gate_data = json.loads(scalar_code_gate.read_text())
            triggered = gate_data.get("triggered", False)
            detail = f"triggered={triggered}; reason={gate_data.get('reason', 'n/a')}"
            if triggered and scalar_code_audit:
                detail += f"; audit={scalar_code_audit.name}"
        except (json.JSONDecodeError, OSError):
            detail = "gate JSON present"
        artifacts.append(StageArtifact(67, "scalar-lib-it (code)", True, str(scalar_code_gate), detail))
    elif audit_in_review:
        artifacts.append(StageArtifact(67, "scalar-lib-it (code)", True, detail="documented in PR review"))
    else:
        detail = "No .context/scalar-lib-gate-code.json"
        if scalar_review_read_error:
            detail = f"{detail}; pr_review read failed: {scalar_review_read_error}"
        artifacts.append(StageArtifact(
            67, "scalar-lib-it (code)", False,
            detail=detail,
        ))

    # Determine resume stage
    resume_stage = 0
    resume_reason = "Starting fresh — no artifacts found"

    for art in reversed(artifacts):
        if art.found:
            nxt = next_resume_stage(art.stage)
            if nxt == -1:
                resume_stage = -1
                resume_reason = (
                    f"Stage {fmt_stage_label(art.stage)} ({art.name}) complete "
                    f"→ pipeline complete"
                )
            else:
                resume_stage = nxt
                resume_reason = (
                    f"Stage {fmt_stage_label(art.stage)} ({art.name}) complete "
                    f"→ resume at Stage {fmt_stage_label(resume_stage)}"
                )
            break

    return artifacts, resume_stage, resume_reason, pr_number, pr_url, unpushed


def run_preflight() -> tuple[list[PreflightResult], Path | None]:
    """Run preflight checks. Returns (results, main_workspace_or_None)."""
    results: list[PreflightResult] = []

    results.append(check_tool("git", ["git", "rev-parse", "--git-dir"]))
    results.append(check_tool("gh"))
    results.append(check_gh_auth())
    results.append(check_tool("make"))
    results.append(check_tool("uv"))

    results.append(check_directory("plans", Path("plans")))
    results.append(check_directory(".context/prs", Path(".context/prs")))
    results.append(check_directory(".context/prs/reviews", Path(".context/prs/reviews")))

    main_ws = find_main_workspace()
    for cmd in ["plan-create", "plan-review", "plan-update", "spec-driven", "commit-push-pr"]:
        results.append(resolve_command_file(cmd, main_ws))

    if main_ws:
        results.append(PreflightResult(
            "worktree", True,
            f"Running in worktree; main workspace: {main_ws}"
        ))

    return results, main_ws


def format_summary(status: PipelineStatus) -> str:
    """Format human-readable summary for stderr."""
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  SHIP-FEATURE PIPELINE STATUS")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Branch:  {status.branch}")
    lines.append(f"  Ticket:  {status.ticket_id or '(none detected)'}")
    if status.pr_number:
        lines.append(f"  PR:      #{status.pr_number} — {status.pr_url}")
    lines.append("")

    # Preflight
    failed = [p for p in status.preflight if not p.ok]
    if failed:
        lines.append("  ❌ PREFLIGHT FAILURES:")
        for f in failed:
            lines.append(f"     • {f.tool}: {f.detail}")
        lines.append("")
    else:
        lines.append("  ✅ All preflight checks passed")
        lines.append("")

    # Pipeline stages
    lines.append("  PIPELINE STATE:")
    stage_icons = {True: "✅", False: "⬜"}
    for art in status.artifacts:
        icon = stage_icons[art.found]
        detail = f" — {art.detail}" if art.detail else ""
        label = fmt_stage_label(art.stage)
        lines.append(f"     {icon} Stage {label}: {art.name}{detail}")

    lines.append("")
    if status.resume_stage == -1:
        lines.append("  ▶ RESUME: complete (all stages done)")
    else:
        lines.append(f"  ▶ RESUME: Stage {fmt_stage_label(status.resume_stage)}")
    lines.append(f"    {status.resume_reason}")

    if status.unpushed_commits > 0:
        lines.append(f"\n  ⚠ {status.unpushed_commits} unpushed commit(s)")

    if status.warnings:
        lines.append("")
        for w in status.warnings:
            lines.append(f"  ⚠ {w}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ship-feature pipeline status check.")
    parser.add_argument("--branch", default=None, help="Override branch detection")
    parser.add_argument("--ticket", default=None, help="Override ticket ID detection")
    args = parser.parse_args()

    branch = args.branch or get_branch()
    ticket_id = args.ticket or extract_ticket_id(branch)

    preflight, main_ws = run_preflight()

    artifacts, resume_stage, resume_reason, pr_number, pr_url, unpushed = detect_pipeline_state(
        branch, ticket_id
    )

    warnings: list[str] = []
    if branch in ("main", "master"):
        warnings.append("On main/master -- create a feature branch before shipping")
    if main_ws:
        warnings.append(
            f"Worktree detected. Command files resolve from global command dirs first, "
            f"then project/main workspace ({main_ws}), runtime command surface, then bundled fallback."
        )

    status = PipelineStatus(
        branch=branch,
        ticket_id=ticket_id,
        preflight=preflight,
        artifacts=artifacts,
        resume_stage=resume_stage,
        resume_reason=resume_reason,
        pr_number=pr_number,
        pr_url=pr_url,
        unpushed_commits=unpushed,
        warnings=warnings,
    )

    print(json.dumps(asdict(status), indent=2, default=str), file=sys.stdout)
    print(format_summary(status), file=sys.stderr)


if __name__ == "__main__":
    main()
