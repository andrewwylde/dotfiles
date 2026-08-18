#!/usr/bin/env python3
"""
Generalized skill gate script for enforcing multi-phase workflow preconditions.

This pattern prevents "inline implementation" where an agent bypasses skill
protocols by directly editing files without completing required phases.

CRITICAL: Gates are now TASK-AWARE. They check if artifacts exist FOR THE
CURRENT TASK, not just if any matching artifact exists. This prevents the
"old artifact bypass" where artifacts from a previous task allow skipping
phases for a new task.

Usage:
    python3 ~/.cursor/skills/_shared/skill_gate.py check \
        --skill <skill-name> \
        --action <intended-action> \
        [--file <target-file>]

Exit codes:
    0 = ALLOWED (preconditions met)
    1 = BLOCKED (preconditions not met, message explains why)
"""

import argparse
import json
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class GateResult:
    """Result of a gate check."""
    allowed: bool
    phase: str
    message: str
    missing_artifact: Optional[str] = None
    action_required: Optional[str] = None
    task_id: Optional[str] = None


class SkillGate(ABC):
    """
    Base class for skill-specific gate implementations.

    Subclass this and implement:
    - get_phases(): Return list of phase names in order
    - get_phase_artifacts(): Return dict of phase -> required artifact pattern
    - get_phase_allowed_actions(): Return dict of phase -> list of allowed actions
    """

    def __init__(self, workspace_root: Path = None):
        self.workspace_root = workspace_root or Path.cwd()
        self._session_cache = None

    @abstractmethod
    def get_phases(self) -> list[str]:
        """Return ordered list of phase names."""
        pass

    @abstractmethod
    def get_phase_artifacts(self) -> dict[str, str]:
        """Return dict mapping phase -> glob pattern for required artifact."""
        pass

    @abstractmethod
    def get_phase_allowed_actions(self) -> dict[str, list[str]]:
        """Return dict mapping phase -> list of allowed action types."""
        pass

    def get_session_file_path(self) -> Path:
        """Return path to session file. Override in subclass if different."""
        return self.workspace_root / ".context" / f"{self.get_skill_name()}-session.json"

    def get_skill_name(self) -> str:
        """Return skill name. Override in subclass."""
        return "unknown"

    def load_session(self) -> Optional[dict]:
        """Load session file if it exists."""
        if self._session_cache is not None:
            return self._session_cache

        session_file = self.get_session_file_path()
        if session_file.exists():
            try:
                with open(session_file) as f:
                    session = json.load(f)
                    if self._is_valid_session(session):
                        self._session_cache = session
                        return self._session_cache
            except (json.JSONDecodeError, IOError):
                # Corrupt or unreadable session file — treat as no session, non-fatal.
                pass

        self._session_cache = {}
        return None

    def _is_valid_session(self, session: dict) -> bool:
        """Reject stale/mismatched sessions to avoid false activation."""
        if not isinstance(session, dict):
            return False

        session_workspace = session.get("workspace")
        if session_workspace:
            try:
                if Path(session_workspace).resolve() != self.workspace_root.resolve():
                    return False
            except Exception:
                return False

        session_branch = str(session.get("branch", "")).strip()
        if session_branch:
            try:
                import subprocess

                cp = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                )
                if cp.returncode == 0 and cp.stdout.strip() and cp.stdout.strip() != session_branch:
                    return False
            except Exception:
                return False

        activated_at = session.get("activated_at")
        if activated_at:
            try:
                ts = datetime.fromisoformat(str(activated_at).replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - ts > timedelta(hours=24):
                    return False
            except Exception:
                return False

        return True

    def get_task_id(self) -> Optional[str]:
        """Get current task ID from session."""
        session = self.load_session()
        if session:
            return session.get("task_id")
        return None

    def artifact_matches_task(self, artifact_path: Path, task_id: str) -> bool:
        """Check if an artifact matches the current task.

        Uses fuzzy word matching: if 2+ words from task_id appear in the
        artifact name, consider it a match.
        """
        if not task_id:
            return True  # No task context, allow anything (legacy behavior)

        # Normalize both
        artifact_name = artifact_path.stem.lower().replace("_", "-")
        task_words = set(w for w in task_id.lower().split("-") if len(w) > 2)
        artifact_words = set(w for w in artifact_name.split("-") if len(w) > 2)

        # Check for overlap
        overlap = task_words & artifact_words

        # Also check if task_id is a substring
        if task_id.lower() in artifact_name:
            return True

        return len(overlap) >= 2

    def detect_current_phase(self) -> str:
        """Detect current phase based on which TASK-MATCHING artifacts exist."""
        phases = self.get_phases()
        artifacts = self.get_phase_artifacts()
        task_id = self.get_task_id()

        # If no session exists, we're in INIT (or equivalent first phase)
        session = self.load_session()
        if not session:
            return phases[0]

        current_phase = phases[0]

        for phase in phases:
            pattern = artifacts.get(phase)
            if pattern:
                matches = list(self.workspace_root.glob(pattern))
                # Filter to only artifacts matching current task
                if task_id:
                    matches = [m for m in matches if self.artifact_matches_task(m, task_id)]

                if matches:
                    phase_idx = phases.index(phase)
                    if phase_idx + 1 < len(phases):
                        current_phase = phases[phase_idx + 1]
                    else:
                        current_phase = phase

        return current_phase

    def check_action(self, action: str, target_file: Optional[str] = None) -> GateResult:
        """Check if an action is allowed in the current phase."""
        task_id = self.get_task_id()
        session = self.load_session()

        # CRITICAL: If no session exists, BLOCK all non-read actions
        # This prevents the "no context, allow everything" bypass
        if not session:
            if action in ("read", "grep", "shell_readonly"):
                return GateResult(
                    allowed=True,
                    phase="NO_SESSION",
                    message=f"ALLOWED: {action} permitted (read-only, no session required)",
                    task_id=task_id,
                )
            return GateResult(
                allowed=False,
                phase="NO_SESSION",
                message="BLOCKED: No active session. Run activate_session.py first.",
                action_required="python3 ~/.cursor/skills/ship-feature/scripts/activate_session.py --from-branch",
                task_id=task_id,
            )

        current_phase = self.detect_current_phase()
        allowed_actions = self.get_phase_allowed_actions()

        phase_actions = allowed_actions.get(current_phase, [])

        if action in phase_actions or "all" in phase_actions:
            return GateResult(
                allowed=True,
                phase=current_phase,
                message=f"ALLOWED: {action} permitted in {current_phase} phase (task: {task_id})",
                task_id=task_id,
            )

        # Action not allowed
        artifacts = self.get_phase_artifacts()

        for phase, actions in allowed_actions.items():
            if action in actions or "all" in actions:
                if phase in artifacts:
                    return GateResult(
                        allowed=False,
                        phase=current_phase,
                        message=f"BLOCKED: {action} not allowed in {current_phase} phase",
                        missing_artifact=artifacts.get(phase),
                        action_required=f"Complete {phase} phase first (create artifact matching task '{task_id}')",
                        task_id=task_id,
                    )

        return GateResult(
            allowed=False,
            phase=current_phase,
            message=f"BLOCKED: {action} not allowed in {current_phase} phase",
            action_required=f"Check skill protocol for when {action} is permitted",
            task_id=task_id,
        )

    def get_state(self) -> dict:
        """Return current state as dict for JSON output."""
        session = self.load_session()
        task_id = self.get_task_id()

        if not session:
            return {
                "current_phase": "NO_SESSION",
                "task_id": None,
                "session_required": True,
                "allowed_actions": ["read", "grep", "shell_readonly"],
                "blocked_actions": ["strreplace", "write", "task_plan", "git_commit"],
                "existing_artifacts": {},
                "matching_artifacts": {},
                "next_artifact_needed": "Session file (.context/<skill>-session.json)",
                "action_required": "Run activate_session.py first",
            }

        current_phase = self.detect_current_phase()
        allowed_actions = self.get_phase_allowed_actions()
        artifacts = self.get_phase_artifacts()

        existing_artifacts = {}
        matching_artifacts = {}

        for phase, pattern in artifacts.items():
            if pattern:
                matches = list(self.workspace_root.glob(pattern))
                if matches:
                    existing_artifacts[phase] = str(matches[0])
                    # Check which match the current task
                    task_matches = [m for m in matches if self.artifact_matches_task(m, task_id)]
                    if task_matches:
                        matching_artifacts[phase] = str(task_matches[0])

        return {
            "current_phase": current_phase,
            "task_id": task_id,
            "session_file": str(self.get_session_file_path()),
            "allowed_actions": allowed_actions.get(current_phase, []),
            "blocked_actions": self._get_blocked_actions(current_phase),
            "existing_artifacts": existing_artifacts,
            "matching_artifacts": matching_artifacts,
            "next_artifact_needed": self._get_next_artifact(current_phase),
        }

    def _get_blocked_actions(self, current_phase: str) -> list[str]:
        """Get actions that are blocked in current phase."""
        allowed = self.get_phase_allowed_actions()
        all_actions = set()
        for actions in allowed.values():
            all_actions.update(actions)

        current_allowed = set(allowed.get(current_phase, []))
        if "all" in current_allowed:
            return []

        return list(all_actions - current_allowed - {"all"})

    def _get_next_artifact(self, current_phase: str) -> Optional[str]:
        """Get the artifact needed to advance to next phase."""
        phases = self.get_phases()
        artifacts = self.get_phase_artifacts()

        try:
            phase_idx = phases.index(current_phase)
            if phase_idx < len(phases):
                return artifacts.get(current_phase)
        except (ValueError, IndexError):
            # Unknown phase name — no next artifact; fall through to None.
            return None

        return None


# === SKILL IMPLEMENTATIONS ===

class ShipFeatureGate(SkillGate):
    """
    Gate for /ship-feature skill with CONTENT VALIDATION.

    Unlike simple file-existence gates, this validates that artifacts contain
    required sections and meet quality criteria. This prevents the "garbage
    plan, rubber-stamp review" bypass.

    Full pipeline stages:
      0. VALIDATE   - vibe-test produces gap report or explicit skip
      1. PLAN       - plan-create produces plan WITH Assumption Ledger
      2. REVIEW     - plan-review produces READY status + Assumption Audit
      3. UPDATE     - plan-update if NOT READY (max 2 cycles)
      3.5 ADVERSARIAL - de-adversarial-reviewer produces APPROVE (not BLOCK)
      3.75 BENCHMARK  - test-benchmark produces score >= 7
      4. IMPLEMENT  - code changes allowed
      5. SHIP       - git commit/push/PR
      6. PR_REVIEW  - pr-review produces review artifact
      6.5 CODE_BENCH - test-benchmark (code-level) score >= 5
    """

    def get_skill_name(self) -> str:
        return "ship-feature"

    def get_phases(self) -> list[str]:
        return [
            "INIT",           # Session created, nothing else
            "VALIDATING",     # After vibe-test
            "PLANNING",       # After plan exists
            "PLAN_REVIEWED",  # After plan review with READY
            "HARDENED",       # After adversarial + benchmark pass
            "IMPLEMENTING",   # Code changes allowed
            "SHIPPED",        # PR created
            "PR_REVIEWED",    # After pr-review artifact
            "CODE_BENCHMARKED", # After code-level test benchmark artifact
            "COMPLETE",       # All done
        ]

    def get_phase_artifacts(self) -> dict[str, str]:
        return {
            "INIT": ".context/ship-feature-session.json",
            "VALIDATING": ".context/vibetest/*.md",
            "PLANNING": "plans/*.plan.md",
            "PLAN_REVIEWED": ".context/reviews/plan_*.md",
            "HARDENED": ".context/adversarial/*.md",
            "IMPLEMENTING": ".context/implementation/*.md",
            "SHIPPED": None,
            "PR_REVIEWED": ".context/prs/reviews/PR_REVIEW_*.md",
            "CODE_BENCHMARKED": ".context/test-benchmarks/*_code-level.md",
        }

    def get_phase_allowed_actions(self) -> dict[str, list[str]]:
        return {
            "INIT": ["read", "grep", "context_pack", "shell_readonly", "task_vibetest", "task_plan"],
            "VALIDATING": ["read", "grep", "task_vibetest", "task_plan", "shell_readonly"],
            "PLANNING": ["read", "grep", "task_plan", "shell_readonly", "strreplace", "write", "applypatch"],
            "PLAN_REVIEWED": ["read", "grep", "task_review", "task_update", "shell_readonly", "strreplace", "write", "applypatch"],
            "HARDENED": ["read", "grep", "task_adversarial", "task_benchmark", "shell_readonly"],
            "IMPLEMENTING": ["read", "grep", "strreplace", "write", "shell_test", "applypatch"],
            "SHIPPED": ["git_commit", "git_push", "gh_pr_create", "read", "grep", "task_pr_review", "shell_readonly"],
            "PR_REVIEWED": [
                "read",
                "grep",
                "task_pr_review",
                "task_benchmark",
                "shell_readonly",
                "strreplace",
                "write",
                "applypatch",
                "git_commit",
                "git_push",
            ],
            "CODE_BENCHMARKED": [
                "read",
                "grep",
                "task_pr_review",
                "task_benchmark",
                "shell_readonly",
                "shell_test",
                "strreplace",
                "write",
                "applypatch",
                "git_commit",
                "git_push",
            ],
            "COMPLETE": ["all"],
        }

    def validate_artifact_content(self, phase: str, artifact_path: Path) -> tuple[bool, str]:
        """
        Validate that an artifact contains required content for its phase.
        Returns (is_valid, reason).
        """
        if not artifact_path.exists():
            return False, f"Artifact does not exist: {artifact_path}"

        try:
            content = artifact_path.read_text()
        except IOError as e:
            return False, f"Cannot read artifact: {e}"

        content_lower = content.lower()

        def has_provenance(marker: str) -> bool:
            return marker.lower() in content_lower

        if phase == "VALIDATING":
            # Vibe-test must have gap report OR explicit skip
            has_gaps = "## gaps" in content_lower or "gap report" in content_lower
            has_skip = "skip" in content_lower and ("no specs" in content_lower or "proceed" in content_lower)
            if not (has_gaps or has_skip):
                return False, "Vibe-test artifact missing gap report or skip note"
            return True, "Vibe-test validated"

        if phase == "PLANNING":
            if not has_provenance("RUN_BY_COMMAND: plan-create"):
                return False, "Plan missing provenance marker RUN_BY_COMMAND: plan-create"
            # Plan must have Assumption Ledger
            if "## assumption ledger" not in content_lower and "assumption ledger" not in content_lower:
                return False, "Plan missing required Assumption Ledger section"
            return True, "Plan has Assumption Ledger"

        if phase == "PLAN_REVIEWED":
            if not has_provenance("RUN_BY_COMMAND: plan-review"):
                return False, "Plan review missing provenance marker RUN_BY_COMMAND: plan-review"
            # Review must have READY status (not NOT READY)
            if "not ready" in content_lower:
                return False, "Plan review status is NOT READY - run plan-update"
            if "ready to execute" not in content_lower and "ready with changes" not in content_lower:
                if "## decision" in content_lower or "decision:" in content_lower:
                    if "ready" not in content_lower:
                        return False, "Plan review decision is not READY"
            # Must also have assumption audit
            if "assumption audit" not in content_lower:
                return False, "Plan review missing Assumption Audit section"
            # Plan must not be newer than review (Stage 3 requires re-review after plan-update)
            review_path = artifact_path
            plan_matches = list(self.workspace_root.glob("plans/*.plan.md"))
            task_id = self.get_task_id()
            if task_id:
                plan_matches = [p for p in plan_matches if self.artifact_matches_task(p, task_id)]
            for plan_path in plan_matches:
                if plan_path.stat().st_mtime > review_path.stat().st_mtime + 1:
                    return False, "Plan modified after review — re-delegate /plan-review after /plan-update"
            return True, "Plan review READY with Assumption Audit"

        if phase == "HARDENED":
            if not has_provenance("RUN_BY_SKILL: de-adversarial-reviewer"):
                return False, "Adversarial review missing provenance marker RUN_BY_SKILL: de-adversarial-reviewer"
            # Adversarial review must have APPROVE (not BLOCK)
            if "block" in content_lower and "## decision" in content_lower:
                return False, "Adversarial review BLOCKED the plan"
            if "approve" not in content_lower:
                return False, "Adversarial review missing APPROVE decision"

            # Also need test benchmark score >= 7
            benchmark_pattern = ".context/test-benchmarks/*_plan-level.md"
            benchmarks = list(self.workspace_root.glob(benchmark_pattern))
            task_id = self.get_task_id()
            if task_id:
                benchmarks = [b for b in benchmarks if self.artifact_matches_task(b, task_id)]

            if not benchmarks:
                return False, "Missing plan-level test benchmark artifact (Stage 3.75 — delegate /test-benchmark plan)"

            benchmark_content = benchmarks[0].read_text()
            if "run_by_skill: test-benchmark" not in benchmark_content.lower():
                return False, "Test benchmark missing provenance marker RUN_BY_SKILL: test-benchmark"
            score_match = re.search(r"score[:\s]*(\d+)", benchmark_content.lower())
            if score_match:
                score = int(score_match.group(1))
                if score < 7:
                    return False, f"Test benchmark score {score} < 7 - run plan-update"

            deferrals = list(self.workspace_root.glob(".context/deferrals/*_deferrals.md"))
            if task_id:
                deferrals = [d for d in deferrals if self.artifact_matches_task(d, task_id)]
            if not deferrals:
                return False, "Missing deferral register (Stage 3.5b)"
            deferral_content = deferrals[0].read_text()
            if "run_by_skill: ship-feature" not in deferral_content.lower():
                return False, "Deferral register missing RUN_BY_SKILL: ship-feature"

            for gate_name in ("psgen-gate-plan.json", "scalar-lib-gate-plan.json"):
                gate_path = self.workspace_root / ".context" / gate_name
                if not gate_path.is_file():
                    return False, f"Missing .context/{gate_name} (Stages 3.7/3.8)"
                try:
                    gate_data = json.loads(gate_path.read_text())
                    if "triggered" not in gate_data:
                        return False, f".context/{gate_name} missing triggered field"
                except (json.JSONDecodeError, OSError):
                    return False, f".context/{gate_name} unreadable"

            return True, "Adversarial APPROVE + benchmark >= 7 + deferrals + plan gates"

        if phase == "IMPLEMENTING":
            if not has_provenance("RUN_BY_COMMAND: spec-driven"):
                return False, "Implementation artifact missing provenance marker RUN_BY_COMMAND: spec-driven"
            if "## implementation summary" not in content_lower:
                return False, "Implementation artifact missing Implementation Summary section"
            if "## verification" not in content_lower:
                return False, "Implementation artifact missing Verification section"
            if "passed" not in content_lower:
                return False, "Implementation artifact must record passing verification"
            return True, "Implementation completed with verification"

        if phase == "PR_REVIEWED":
            has_pr_review = (
                has_provenance("RUN_BY_COMMAND: pr-review-local")
                or has_provenance("RUN_BY_SKILL: pr-review")
            )
            if not has_pr_review:
                return False, "PR review missing provenance (RUN_BY_COMMAND: pr-review-local or RUN_BY_SKILL: pr-review)"
            # PR review artifact must exist with actual findings
            if len(content) < 500:
                return False, "PR review artifact too short - run full pr-review"
            if "## summary" not in content_lower and "## findings" not in content_lower:
                return False, "PR review missing required sections"
            return True, "PR review artifact validated"

        if phase == "CODE_BENCHMARKED":
            if not has_provenance("RUN_BY_SKILL: test-benchmark"):
                return False, "Code benchmark missing provenance marker RUN_BY_SKILL: test-benchmark"
            if "code-level" not in content_lower and "code level" not in content_lower:
                return False, "Code benchmark must identify itself as code-level"
            score_match = re.search(r"score[:\s]*(\d+)", content_lower)
            if score_match:
                score = int(score_match.group(1))
                if score < 5:
                    return False, f"Code benchmark score {score} < 5 - add/repair tests"
            return True, "Code benchmark artifact validated"

        return True, "No content validation for this phase"

    def _is_gated_source_path(self, target_file: Optional[str]) -> bool:
        if not target_file:
            return False
        p = target_file.replace("\\", "/").lstrip("./")
        if p.startswith("plans/") or "/plans/" in p:
            return False
        if p.startswith(".context/") or "/.context/" in p:
            return False
        prefixes = ("services/", "apps/", "infrastructure/", "utils/", "platform-schemas/")
        return any(p.startswith(prefix) or f"/{prefix}" in p for prefix in prefixes)

    def _run_compliance_script(self, gate: str, extra: list[str] | None = None) -> tuple[bool, str]:
        script = Path.home() / ".cursor/skills/ship-feature/scripts/stage_compliance_check.py"
        cmd = ["python3", str(script), "--gate", gate]
        task_id = self.get_task_id()
        if task_id and gate in ("stage4", "stage5-pr"):
            cmd.extend(["--task", task_id])
        if extra:
            cmd.extend(extra)
        proc = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output.strip()[-800:]

    def _delegation_allows_path(self, target_file: str) -> tuple[bool, str | None]:
        """Return (allowed, required_stage) for delegated artifact paths."""
        recovery_script = Path.home() / ".cursor/skills/ship-feature/scripts/harness_recovery.py"
        check_script = Path.home() / ".cursor/skills/ship-feature/scripts/delegation_window.py"
        if not recovery_script.is_file() or not check_script.is_file():
            return True, None

        sys_path_insert = str(Path.home() / ".cursor/skills/ship-feature/scripts")
        if sys_path_insert not in sys.path:
            sys.path.insert(0, sys_path_insert)
        try:
            from harness_recovery import delegation_stages_for_path
        except ImportError:
            return True, None

        stages = delegation_stages_for_path(target_file)
        if not stages:
            return True, None

        session = self.load_session() or {}
        delegation = session.get("delegation")
        if isinstance(delegation, dict):
            expires = delegation.get("expires_at")
            active = True
            if expires:
                try:
                    exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
                    active = datetime.now(timezone.utc) <= exp
                except ValueError:
                    active = False
            if active and delegation.get("stage") in stages:
                return True, None
        return False, stages[0]

    def _harness_recovery_message(self, gate: str = "auto", blocked_path: str | None = None) -> str:
        script = Path.home() / ".cursor/skills/ship-feature/scripts/harness_recovery.py"
        if not script.is_file():
            return f"python3 ~/.cursor/skills/ship-feature/scripts/stage_compliance_check.py --gate {gate}"
        cmd = ["python3", str(script), "--gate", gate, "--format", "text"]
        task_id = self.get_task_id()
        if task_id:
            cmd.extend(["--task", task_id])
        if blocked_path:
            cmd.extend(["--blocked-path", blocked_path])
        proc = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True)
        output = (proc.stdout or "").strip()
        if output:
            return output
        return f"python3 {script} --gate {gate}"

    def check_action(self, action: str, target_file: Optional[str] = None) -> GateResult:
        write_actions = {"strreplace", "write", "applypatch"}
        if action in write_actions and target_file:
            allowed, required_stage = self._delegation_allows_path(target_file)
            if not allowed:
                recovery = self._harness_recovery_message("auto", blocked_path=target_file)
                return GateResult(
                    allowed=False,
                    phase=self.detect_current_phase(),
                    message=(
                        f"BLOCKED: delegated artifact `{target_file}` requires subagent "
                        f"(delegation window stage={required_stage})"
                    ),
                    action_required=recovery,
                    task_id=self.get_task_id(),
                )

        result = super().check_action(action, target_file)
        write_actions = {"strreplace", "write", "applypatch"}
        source_edit = action in write_actions and self._is_gated_source_path(target_file)

        if source_edit:
            ok, _detail = self._run_compliance_script("stage4")
            if ok:
                return GateResult(
                    allowed=True,
                    phase=result.phase,
                    message=f"ALLOWED: Stage 4 compliance passed ({action} on implementation path)",
                    task_id=self.get_task_id(),
                )
            if result.allowed:
                return GateResult(
                    allowed=False,
                    phase=result.phase,
                    message=(
                        "BLOCKED: Stage 4 compliance failed — complete stages "
                        "3→3.5→3.75→3.7→3.8→3.5b before editing source"
                    ),
                    action_required=self._harness_recovery_message("stage4"),
                    task_id=self.get_task_id(),
                )
            return result

        if not result.allowed:
            return result

        if action == "gh_pr_create" or (
            action == "git_push" and result.phase in ("SHIPPED", "PR_REVIEWED", "CODE_BENCHMARKED")
        ):
            # PARABLE-609: block PR create until visual sign-off (Stage 4.9 / stage5-pr).
            # Non-campaign runs pass through immediately (gate reports skipped).
            ok5, detail5 = self._run_compliance_script("stage5-pr")
            if not ok5 and action == "gh_pr_create":
                return GateResult(
                    allowed=False,
                    phase=result.phase,
                    message=(
                        "BLOCKED: Stage 5 PR create requires PARABLE-609 visual proof "
                        "and Stage 4.9 human sign-off (or campaign skip)"
                    ),
                    action_required=self._harness_recovery_message("stage5-pr"),
                    task_id=self.get_task_id(),
                )

            ok, _detail = self._run_compliance_script("stage6-complete")
            if not ok:
                return GateResult(
                    allowed=False,
                    phase=result.phase,
                    message="BLOCKED: Phase 6 incomplete — finish 6→6.45→6.5→6.6→6.65→6.7 first",
                    action_required=self._harness_recovery_message("stage6-complete"),
                    task_id=self.get_task_id(),
                )

        return result

    def detect_current_phase(self) -> str:
        """
        Detect current phase based on which TASK-MATCHING artifacts exist
        AND pass content validation.
        """
        phases = self.get_phases()
        artifacts = self.get_phase_artifacts()
        task_id = self.get_task_id()

        session = self.load_session()
        if not session:
            return phases[0]

        current_phase = phases[0]

        for phase in phases:
            pattern = artifacts.get(phase)
            if pattern:
                matches = list(self.workspace_root.glob(pattern))
                if task_id:
                    matches = [m for m in matches if self.artifact_matches_task(m, task_id)]

                if matches:
                    # CONTENT VALIDATION: Check if artifact passes validation
                    is_valid, reason = self.validate_artifact_content(phase, matches[0])
                    if is_valid:
                        phase_idx = phases.index(phase)
                        if phase_idx + 1 < len(phases):
                            current_phase = phases[phase_idx + 1]
                        else:
                            current_phase = phase
                    # If not valid, don't advance phase

        return current_phase

    def get_validation_status(self) -> dict:
        """Return detailed validation status for all artifacts."""
        artifacts = self.get_phase_artifacts()
        task_id = self.get_task_id()

        status = {}
        for phase, pattern in artifacts.items():
            if pattern:
                matches = list(self.workspace_root.glob(pattern))
                if task_id:
                    matches = [m for m in matches if self.artifact_matches_task(m, task_id)]

                if matches:
                    is_valid, reason = self.validate_artifact_content(phase, matches[0])
                    status[phase] = {
                        "artifact": str(matches[0]),
                        "valid": is_valid,
                        "reason": reason,
                    }
                else:
                    status[phase] = {
                        "artifact": None,
                        "valid": False,
                        "reason": f"No matching artifact for pattern: {pattern}",
                    }

        return status

    def get_state(self) -> dict:
        """Return current state with validation details."""
        base_state = super().get_state()
        base_state["validation_status"] = self.get_validation_status()
        return base_state


class InvestigateGate(SkillGate):
    """Gate for /investigate skill."""

    def get_skill_name(self) -> str:
        return "investigate"

    def get_phases(self) -> list[str]:
        return ["NO_GOAL", "DIAGNOSING", "PLANNING", "IMPLEMENTING", "SHIPPING", "REVIEWING"]

    def get_phase_artifacts(self) -> dict[str, str]:
        return {
            "NO_GOAL": ".context/goals/*.json",
            "DIAGNOSING": ".context/debug/*.md",
            "PLANNING": "plans/*.plan.md",
            "IMPLEMENTING": None,
            "SHIPPING": None,
        }

    def get_phase_allowed_actions(self) -> dict[str, list[str]]:
        return {
            "NO_GOAL": ["read", "grep", "shell_readonly", "goal_create"],
            "DIAGNOSING": ["read", "grep", "shell_readonly", "task_diagnostic", "write_debug"],
            "PLANNING": ["read", "grep", "shell_readonly", "task_plan"],
            "IMPLEMENTING": ["all"],
            "SHIPPING": ["git_commit", "git_push", "gh_pr_create"],
            "REVIEWING": ["read", "write_review"],
        }


class SpecDrivenGate(SkillGate):
    """Gate for /spec-driven skill (TDD enforcement)."""

    def get_skill_name(self) -> str:
        return "spec-driven"

    def get_phases(self) -> list[str]:
        return ["RED", "GREEN", "REFACTOR"]

    def get_phase_artifacts(self) -> dict[str, str]:
        return {
            "RED": None,
            "GREEN": None,
        }

    def check_action(self, action: str, target_file: Optional[str] = None) -> GateResult:
        """Check if an action is allowed in the current phase."""
        action = self._normalize_tdd_action(action, target_file)
        return super().check_action(action, target_file)

    @staticmethod
    def _is_test_path(target_file: Optional[str]) -> bool:
        if not target_file:
            return False
        norm = target_file.replace("\\", "/")
        name = norm.rsplit("/", 1)[-1]
        return (
            "/tests/" in f"/{norm}"
            or norm.startswith("tests/")
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith("_test.go")
            or ".test." in name
            or ".spec." in name
        )

    def _normalize_tdd_action(self, action: str, target_file: Optional[str]) -> str:
        """Map Write/StrReplace to write_test vs write_impl from the target path.

        enforce-gate.sh sends action=write; RED only allows write_test. Without
        this remap, agents cannot create failing tests under /spec-driven.
        """
        if action not in ("write", "strreplace", "write_impl", "write_test"):
            return action
        if self._is_test_path(target_file):
            return "write_test"
        if action == "write":
            return "write_impl"
        return action

    def get_phase_allowed_actions(self) -> dict[str, list[str]]:
        return {
            "RED": ["read", "write_test", "shell_test_expect_fail"],
            "GREEN": ["read", "strreplace", "write_impl", "write", "shell_test"],
            "REFACTOR": ["read", "strreplace", "write", "shell_test"],
        }


# === CLI ===

GATES = {
    "investigate": InvestigateGate,
    "ship-feature": ShipFeatureGate,
    "spec-driven": SpecDrivenGate,
}


def main():
    parser = argparse.ArgumentParser(description="Skill gate checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Check if action is allowed")
    check_parser.add_argument("--skill", required=True, choices=GATES.keys())
    check_parser.add_argument("--action", required=True, help="Action type to check")
    check_parser.add_argument("--file", help="Target file")
    check_parser.add_argument("--workspace", default=".", help="Workspace root")

    state_parser = subparsers.add_parser("state", help="Show current state")
    state_parser.add_argument("--skill", required=True, choices=GATES.keys())
    state_parser.add_argument("--workspace", default=".", help="Workspace root")

    subparsers.add_parser("list", help="List available skills with gates")

    args = parser.parse_args()

    if args.command == "list":
        print("Available skill gates:")
        for name in GATES.keys():
            print(f"  - {name}")
        sys.exit(0)

    gate_class = GATES[args.skill]
    gate = gate_class(Path(args.workspace))

    if args.command == "state":
        state = gate.get_state()
        print(json.dumps(state, indent=2))
        sys.exit(0)

    elif args.command == "check":
        result = gate.check_action(args.action, args.file)

        print(result.message)
        if result.action_required:
            print(f"ACTION: {result.action_required}")

        sys.exit(0 if result.allowed else 1)


if __name__ == "__main__":
    main()
