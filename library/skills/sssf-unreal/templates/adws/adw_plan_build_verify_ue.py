#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic", "python-dotenv", "pyyaml", "rich"]
# ///
"""ADW Plan Build Verify UE — Unreal Editor-aware SDLC chain.

Usage:
    uv run adws/adw_plan_build_verify_ue.py "<prompt or path/to/prompt.md>" [--config adws/adw_sssf_config/sssf.config.yaml] [--adw-id a1b2c3d4]

Phases: engineer(request) -> planner -> builder_ue -> code(compile) -> code(verify_state) [-> builder_ue(fix) ... bounded] -> git(commit)
"""

import argparse
import sys
from pathlib import Path

from adw_modules import agents, git_helper, session, ue_gates, ue_quality, utils
from adw_modules.data_types import (AgentCall, BuildOutput, PhaseParams, PlanOutput,
                                     SSSFConfig, VerifyOutput)

REQUIRED_AGENTS = ["planner_ue", "builder_ue"]
MAX_FIX_LOOPS = 3


def main(prompt: str, config: str | SSSFConfig = "adws/adw_sssf_config/sssf.config.yaml",
         adw_id: str | None = None, from_plan: str | None = None) -> int:
    cfg = agents.load_config(config)
    agents.validate(cfg, ["builder_ue"] if from_plan else REQUIRED_AGENTS)
    run = session.ensure(cfg, adw_id)

    def record(ph, result) -> None:
        if hasattr(result, "checks"):
            passed = sum(1 for check in result.checks if check.passed)
            ph.log(passed=result.passed, checks=f"{passed}/{len(result.checks)}",
                   artifacts=", ".join(result.artifacts))
        else:
            ph.log(passed=result.passed, checks="1/1" if result.passed else "0/1",
                   artifacts=result.output_artifact)

    verify_yaml = run.context_handoff_dir / "verify.yaml"
    verify_plan = run.context_handoff_dir / "plan.md"
    verify_cmd = ue_gates.editor_verify_command(verify_yaml)

    with run.phase(PhaseParams(name="request", kind="engineer", owner=run.engineer,
                                description="Capture the Unreal Editor task request")) as ph:
        ph.log(input=prompt)
        if from_plan:
            ph.log(from_plan=from_plan)

    if from_plan:
        plan_src = Path(from_plan)
        if not plan_src.exists():
            raise SystemExit(f"Specified --from-plan file does not exist: {from_plan}")
        plan_text = plan_src.read_text(encoding="utf-8")
        verify_plan.write_text(plan_text, encoding="utf-8")

        # Copy companion verify.yaml if present
        companion_yaml = plan_src.parent / "verify.yaml"
        if not companion_yaml.exists():
            companion_yaml = plan_src.parent / "context_handoff" / "verify.yaml"
        if companion_yaml.exists():
            verify_yaml.write_text(companion_yaml.read_text(encoding="utf-8"), encoding="utf-8")

        plan = PlanOutput(
            status="success",
            summary=f"Loaded from pre-existing plan: {from_plan}",
            artifacts=[str(verify_plan), str(from_plan)],
            notes_for_next_agent="Loaded pre-existing plan from prior run.",
        )
    else:
        with run.phase(PhaseParams(name="plan_ue", kind="agent", owner="planner_ue", retries=1,
                                    description="Generate Unreal implementation plan and companion verification assertion spec")) as ph:
            plan = ph.call(AgentCall(output_type=PlanOutput, prompt=prompt,
                                      gates=[ue_gates.artifacts_exist, ue_gates.files_non_empty,
                                             ue_gates.assets_referenced_exist(verify_yaml, verify_plan),
                                             ue_gates.verify_spec_falsifiable(verify_cmd, verify_yaml)]))

    ue_gates.snapshot_binary_files(run)
    with run.phase(PhaseParams(name="build_ue", kind="agent", owner="builder_ue", retries=1,
                                description="Implement the plan in the live Unreal Editor via MCP tools")) as ph:
        previous = ph.call(AgentCall(output_type=BuildOutput, prompt=prompt, previous=plan,
                                      gates=[ue_gates.diff_matches_claims, ue_gates.binary_hashes_changed,
                                             ue_gates.no_op_success]))

    compile_result = None
    with run.phase(PhaseParams(name="compile", kind="code", owner="quality",
                                description="Run the Live Coding compilation protocol")) as ph:
        compile_result = ue_quality.test(run, changed_files=previous.changed_files if previous else None)
        record(ph, compile_result)

    state_result = None
    if verify_yaml.exists():
        with run.phase(PhaseParams(name="verify_state", kind="code", owner="quality",
                                    description="Run editor-state assertion spec to confirm changes were applied")) as ph:
            state_result = ue_quality._run(ue_quality.UEQualityCheckSpec(
                name="verify_editor_state",
                area="unreal_engine",
                operation="editor_verification",
                argv=["uv", "run", "--with", "pyyaml", "python",
                      "scripts/adw_editor_verify.py", "--spec", str(verify_yaml)],
                timeout_seconds=120,
            ), run)
            record(ph, state_result)

    test_passed = (compile_result is not None and compile_result.passed and
                   (state_result is None or state_result.passed))

    for i in range(1, MAX_FIX_LOOPS + 1):
        if test_passed:
            break

        failures = []
        if compile_result and not compile_result.passed:
            failures.append(f"compilation: `{compile_result.command}` exited {compile_result.returncode}\n{compile_result.output_tail}")
        if state_result and not state_result.passed:
            failures.append(f"editor state: `{state_result.command}` exited {state_result.returncode}\n{state_result.output_tail}")

        with run.phase(PhaseParams(name=f"fix_{i}", kind="agent", owner="builder_ue", retries=1,
                                    description="Repair compilation or editor-state failures from verbatim verification output")) as ph:
            fix_envelope = VerifyOutput(
                status="fail",
                summary=f"Verification failed: {len(failures)} check(s)",
                artifacts=[],
                notes_for_next_agent="Fix every failure below. The output is verbatim.",
                passed=False,
                failures=failures,
            )
            previous = ph.call(AgentCall(output_type=BuildOutput, prompt=prompt,
                                          previous=fix_envelope,
                                          gates=[ue_gates.diff_matches_claims, ue_gates.binary_hashes_changed,
                                                 ue_gates.no_op_success]))

        with run.phase(PhaseParams(name=f"compile_{i}", kind="code", owner="quality",
                                    description="Re-verify compilation after builder fix")) as ph:
            compile_result = ue_quality.test(run, changed_files=previous.changed_files if previous else None)
            record(ph, compile_result)

        if verify_yaml.exists():
            with run.phase(PhaseParams(name=f"verify_state_{i}", kind="code", owner="quality",
                                        description="Re-verify editor state after builder fix")) as ph:
                state_result = ue_quality._run(ue_quality.UEQualityCheckSpec(
                    name="verify_editor_state",
                    area="unreal_engine",
                    operation="editor_verification",
                    argv=["uv", "run", "--with", "pyyaml", "python",
                          "scripts/adw_editor_verify.py", "--spec", str(verify_yaml)],
                    timeout_seconds=120,
                ), run)
                record(ph, state_result)

        test_passed = (compile_result is not None and compile_result.passed and
                       (state_result is None or state_result.passed))

    if test_passed:
        with run.phase(PhaseParams(name="commit", kind="code", owner="git",
                                    description="Land the editor changes only after compilation and state checks pass")) as ph:
            message = previous.commit_message or f"sssf({run.adw_id}): {previous.summary}"
            ph.log(sha=git_helper.commit_all(message), message=message)

    return run.finish(accepted=test_passed,
                      reason=f"verification still failed after {MAX_FIX_LOOPS} fix attempt(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="inline text or a path to a prompt file")
    parser.add_argument("--from-plan", default=None,
                        help="path to a pre-existing plan markdown file to skip the planning phase")
    parser.add_argument("--config", default="adws/adw_sssf_config/sssf.config.yaml",
                        help="path to the SSSF agent roster")
    parser.add_argument("--adw-id", default=None, help="join or pin an existing session")
    args = parser.parse_args()
    sys.exit(main(utils.resolve_prompt(args.prompt), config=args.config,
                  adw_id=args.adw_id, from_plan=args.from_plan))