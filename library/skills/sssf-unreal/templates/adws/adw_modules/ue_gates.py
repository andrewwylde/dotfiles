"""Validation gates: verify the envelope's CLAIMS, never guesses.

A gate is `gate(envelope, run) -> GateReport` — one check per item it looked at.
Violations are derived from the failed checks and sent back to the SAME agent
session as a correction. Every check is recorded either way, so a green gate
says WHAT it verified instead of only that it passed.

Gates check what is mechanically checkable; plan quality is a reviewer's job.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path

from .data_types import EnvelopeBase, GateReport

TAIL_CHARS = 1000
_BINARY_EXTS = {".uasset", ".umap"}        # command output kept as evidence on a failure


def snapshot_binary_files(run) -> None:
    """Capture tracked/dirty Unreal binary hashes immediately before a UE build phase."""
    run.binary_snapshot = {}
    for root_name in ("Content", "Plugins"):
        root = run.repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in _BINARY_EXTS or not path.is_file():
                continue
            relative = path.relative_to(run.repo_root).as_posix()
            run.binary_snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()


def _size(path: Path) -> str:
    n = path.stat().st_size
    return f"{n}B" if n < 1024 else f"{n / 1024:.1f}KB"


def artifacts_exist(envelope: EnvelopeBase, run) -> GateReport:
    report = GateReport()
    for a in envelope.artifacts:
        p = Path(a)
        if not p.is_absolute():
            # Check in repo root or context handoff directory
            p_repo = run.repo_root / p
            p_handoff = run.context_handoff_dir / p
            if p_repo.exists():
                p = p_repo
            elif p_handoff.exists():
                p = p_handoff
        report.check(a, p.exists(),
                     f"exists, {_size(p)}" if p.exists() else "declared artifact does not exist")
    return report


def files_non_empty(envelope: EnvelopeBase, run) -> GateReport:
    report = GateReport()
    for a in envelope.artifacts:
        p = Path(a)
        if not p.is_absolute():
            p_repo = run.repo_root / p
            p_handoff = run.context_handoff_dir / p
            if p_repo.exists():
                p = p_repo
            elif p_handoff.exists():
                p = p_handoff
        if not (p.exists() and p.is_file()):
            continue                       # existence is artifacts_exist's job
        empty = p.stat().st_size == 0
        report.check(a, not empty, "declared artifact is empty" if empty else _size(p))
    return report


def json_parses(envelope: EnvelopeBase, run) -> GateReport:
    report = GateReport()
    for a in envelope.artifacts:
        p = Path(a)
        if p.suffix != ".json" or not p.exists():
            continue
        try:
            parsed = json.loads(p.read_text())
            report.check(a, True, f"parses, {type(parsed).__name__}")
        except json.JSONDecodeError as e:
            report.check(a, False, f"declared JSON artifact does not parse: {e}")
    return report


def diff_matches_claims(envelope: EnvelopeBase, run) -> GateReport:
    """Every file claimed changed must exist on disk."""
    report = GateReport()
    for f in getattr(envelope, "changed_files", []):
        p = Path(f)
        if not p.is_absolute():
            p = run.repo_root / p
        report.check(f, p.exists(),
                     f"exists, {_size(p)}" if p.exists() else "claimed changed file does not exist")
    return report


def verdict_consistent(envelope: EnvelopeBase, run) -> GateReport:
    """A review's verdict must agree with the findings it just wrote down.

    Nothing here judges the code — that is the reviewer's job. This checks the
    envelope against itself: an approval that ships blocking items, or a
    rejection that names no problem, is a claim the harness can refute without
    reading a line of the diff.
    """
    report = GateReport()
    approved = bool(getattr(envelope, "approved", False))
    blocking = list(getattr(envelope, "blocking", []))
    unmet = [f.requirement for f in getattr(envelope, "findings", []) if not f.met]

    report.check("approved vs blocking", not (approved and blocking),
                 "no blocking items" if not blocking
                 else f"{len(blocking)} blocking item(s) while approved=true"
                 if approved else f"{len(blocking)} blocking item(s), not approved")
    report.check("approved vs findings", not (approved and unmet),
                 "every requirement met" if not unmet
                 else f"{len(unmet)} unmet requirement(s) while approved=true"
                 if approved else f"{len(unmet)} unmet requirement(s), not approved")
    report.check("rejection names a problem", approved or bool(blocking or unmet),
                 "verdict is supported" if approved or blocking or unmet
                 else "approved=false but no blocking item or unmet requirement was given")
    return report


def tests_pass(command: str):
    """Gate factory: the given shell command must exit 0."""
    def gate(envelope: EnvelopeBase, run) -> GateReport:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        ok = result.returncode == 0
        note = f"exit {result.returncode}"
        if not ok:
            note += "\n" + (result.stdout + result.stderr)[-TAIL_CHARS:]
        return GateReport().check(command, ok, note)
    gate.__name__ = f"tests_pass({command})"
    return gate


def no_op_success(envelope: EnvelopeBase, run) -> GateReport:
    """A success envelope must claim at least one changed file.

    `status: "success"` with an empty `changed_files` list is a no-op false
    positive — the agent did nothing but claimed the task is done. If the
    task genuinely cannot be completed the agent must report `fail`, not
    success. Envelopes without a `changed_files` field (e.g. plans) pass.
    """
    report = GateReport()
    if not hasattr(envelope, "changed_files"):
        return report
    changed = list(getattr(envelope, "changed_files", []))
    report.check("success implies changed files",
                 bool(changed) or getattr(envelope, "status", "") != "success",
                 f"{len(changed)} changed file(s)" if changed
                 else "status=success but no changed files claimed — a no-op success is not a result")
    return report


def verify_spec_falsifiable(command: str, spec_path):
    """Gate factory: the given verify command must FAIL against the untouched project.

    Runs the editor-state assertion spec BEFORE the builder runs. A spec that
    passes pre-build asserts only pre-existing state — it can never prove the
    builder's change (a vacuous spec, e.g. b57bba0a's verify.yaml). Exit 0 is
    a violation fed back to the planner; any non-zero exit (spec fails on the
    untouched project) is the expected, passing condition. Skips when the spec
    file is absent — the chain's verify_state phase is skipped there too.
    """
    def gate(envelope: EnvelopeBase, run) -> GateReport:
        report = GateReport()
        if not Path(spec_path).exists():
            return report
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        ok = result.returncode != 0
        note = f"exit {result.returncode}"
        if not ok:
            note += " — spec passes on the untouched project, so it cannot prove the change\n" \
                    + (result.stdout + result.stderr)[-TAIL_CHARS:]
        return report.check("verify spec falsifiable pre-build", ok, note)
    gate.__name__ = f"verify_spec_falsifiable({command})"
    return gate


_ASSET_CREATION_MARKERS = (
    "AppendSphere", "AppendCone", "AppendBox",
    "CreateDynamicMesh", "CopyToNewStaticMeshAsset",
    "ApplyMeshBoolean", "GeometryScript",
)


def _game_path_to_uasset(game_path: str) -> Path:
    """/Game/Folder/Name.ClassName -> Content/Folder/Name.uasset (class suffix stripped)."""
    rel = game_path[len("/Game/"):]
    if "." in rel.rsplit("/", 1)[-1]:
        rel = rel.rsplit(".", 1)[0]
    return Path("Content") / (rel + ".uasset")


def assets_referenced_exist(spec_path, plan_path):
    """Gate factory: every /Game/ asset path asserted in the verify spec must
    exist in Content/ on disk, or plan.md must name that path next to a
    procedural creation directive (a GeometryScript marker).

    Skips when the spec file is absent (the chain's verify_state phase is
    skipped there too, matching verify_spec_falsifiable's behavior).
    """
    def gate(envelope: EnvelopeBase, run) -> GateReport:
        report = GateReport()
        spec = Path(spec_path)
        if not spec.exists():
            return report
        import yaml
        try:
            data = yaml.safe_load(spec.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            return report.check("verify.yaml", False, f"does not parse: {e}")
        assertions = data.get("assertions", []) if isinstance(data, dict) else []
        plan_text = Path(plan_path).read_text(encoding="utf-8") if Path(plan_path).exists() else ""
        for assertion in assertions:
            if not isinstance(assertion, dict):
                continue
            for key, value in assertion.items():
                if isinstance(value, str) and value.startswith("/Game/"):
                    asset = run.repo_root / _game_path_to_uasset(value)
                    if asset.exists():
                        report.check(value, True, f"exists on disk ({asset.name})")
                        continue
                    bare = value.rsplit(".", 1)[0] if "." in value.rsplit("/", 1)[-1] else value
                    created = bare in plan_text and any(
                        m in plan_text for m in _ASSET_CREATION_MARKERS)
                    report.check(value, created,
                                 "creation recipe in plan.md" if created else
                                 f"missing from Content/ and plan.md has no creation recipe for {value}")
        return report
    gate.__name__ = "assets_referenced_exist"
    return gate


def binary_hashes_changed(envelope: EnvelopeBase, run) -> GateReport:
    """Every claimed binary file must have had its bytes change during the phase.

    A builder that claims it modified a .uasset when the hash is identical
    hallucinated — this gate catches that by comparing the snapshot taken before
    the agent ran against the file on disk now.
    """
    report = GateReport()
    for f in getattr(envelope, "changed_files", []):
        p = Path(f)
        if not p.is_absolute():
            p = run.repo_root / p
        if p.suffix not in _BINARY_EXTS or not p.exists():
            continue
        after_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        relative = p.relative_to(run.repo_root).as_posix()
        before_hash = run.binary_snapshot.get(relative)
        if before_hash is None:
            report.check(f, True, "new binary file, no prior hash to compare")
        elif before_hash != after_hash:
            report.check(f, True, "hash changed")
        else:
            report.check(f, False, "hash unchanged — claimed modification did not occur")
    return report


def editor_verify_command(spec_path: str) -> str:
    """Standard command for running verify_ue.py against a spec.

    Uses posix paths and shlex.quote to ensure Windows paths with spaces or
    backslashes don't break the shell command.
    """
    path = Path(spec_path).as_posix()
    return f"uv run --with pyyaml python scripts/adw_editor_verify.py --spec {shlex.quote(path)}"
