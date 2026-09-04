"""Deterministic Unreal Editor verification blocks for SSSF UE workflows."""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .data_types import EventRecord
from .utils import now_iso, operator_env

TAIL_CHARS = 4_000


@dataclass(frozen=True)
class UEQualityCheckSpec:
    name: str
    argv: list[str]
    timeout_seconds: int = 120
    area: str = "unreal_engine"
    operation: str = "editor_verification"


@dataclass(frozen=True)
class UEQualityCheckResult:
    name: str
    area: str
    operation: str
    command: str
    returncode: int
    passed: bool
    duration_seconds: float
    output_artifact: str
    output_tail: str


def _check_dir(run, name: str) -> Path:
    seq = run.phases[-1].seq if run.phases else 0
    path = run.context_handoff_dir / "quality" / f"{seq:02d}_{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run(spec: UEQualityCheckSpec, run) -> UEQualityCheckResult:
    phase = run.phases[-1]
    output_artifact = _check_dir(run, spec.name) / "command.log"
    command = shlex.join(spec.argv)
    started_at = now_iso()
    clock = time.monotonic()
    stdout = ""
    stderr = ""

    run.console.note(f"quality {spec.name}: {command}")
    try:
        completed = subprocess.run(
            spec.argv,
            cwd=run.repo_root,
            env=operator_env(),
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as error:
        returncode = 124
        stdout = error.stdout or ""
        stderr = (error.stderr or "") + f"\nTimed out after {spec.timeout_seconds}s."
    except OSError as error:
        returncode = 127
        stderr = str(error)

    duration = time.monotonic() - clock
    output_artifact.write_text(
        f"$ {command}\nexit: {returncode}\nduration_seconds: {duration:.3f}\n"
        f"\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n",
        encoding="utf-8",
    )
    passed = returncode == 0
    run.tracer.event(EventRecord(
        adw_id=run.adw_id,
        phase_id=phase.phase_id,
        type="tool_call",
        name=f"quality:{spec.name}",
        payload={
            "area": spec.area,
            "operation": spec.operation,
            "command": command,
            "returncode": returncode,
            "passed": passed,
            "output_artifact": str(output_artifact),
        },
        started_at=started_at,
        ended_at=now_iso(),
    ))
    run.console.note(
        f"quality {spec.name}: {'passed' if passed else 'failed'} "
        f"(exit {returncode}, {duration:.1f}s)"
    )
    return UEQualityCheckResult(
        name=spec.name,
        area=spec.area,
        operation=spec.operation,
        command=command,
        returncode=returncode,
        passed=passed,
        duration_seconds=duration,
        output_artifact=str(output_artifact),
        output_tail=(stdout + stderr)[-TAIL_CHARS:],
    )


def test(run, changed_files=None) -> UEQualityCheckResult:
    """Compile changed Unreal source through the editor verification harness."""
    argv = [
        "uv", "run", "--with", "pyyaml", "python",
        "scripts/adw_editor_verify.py", "--verify-compilation",
    ]
    if changed_files:
        argv += ["--changed-files", ",".join(changed_files)]
    return _run(UEQualityCheckSpec(
        name="compile",
        argv=argv,
        timeout_seconds=600,
    ), run)
