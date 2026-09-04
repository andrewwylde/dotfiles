#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic", "python-dotenv", "pyyaml", "rich"]
# ///
"""ADW Build Verify UE — Unreal Editor implementation, compilation & state verification from an existing plan.

Usage:
    uv run adws/adw_build_verify_ue.py "specs/my_plan.md" [--config adws/adw_sssf_config/sssf.config.yaml] [--adw-id a1b2c3d4]

Phases: engineer(request) -> builder_ue -> code(compile) -> code(verify_state) [-> builder_ue(fix) ... bounded] -> git(commit)
"""

import argparse
import sys
from pathlib import Path

from adw_modules import agents, git_helper, session, ue_gates, ue_quality, utils
from adw_modules.data_types import (AgentCall, BuildOutput, PhaseParams, PlanOutput,
                                     SSSFConfig, VerifyOutput)

REQUIRED_AGENTS = ["builder_ue"]
MAX_FIX_LOOPS = 3


def main(plan_path: str, config: str | SSSFConfig = "adws/adw_sssf_config/sssf.config.yaml",
         adw_id: str | None = None, prompt: str | None = None) -> int:
    cfg = agents.load_config(config)
    agents.validate(cfg, REQUIRED_AGENTS)
    run = session.ensure(cfg, adw_id)

    plan_src = Path(plan_path)
    if not plan_src.exists():
        raise SystemExit(f"Plan file does not exist: {plan_path}")

    plan_text = plan_src.read_text(encoding="utf-8")
    effective_prompt = prompt or plan_text

    verify_yaml = run.context_handoff_dir / "verify.yaml"
    verify_plan = run.context_handoff_dir / "plan.md"
    verify_plan.write_text(plan_text, encoding="utf-8")

    companion_yaml = plan_src.parent / "verify.yaml"
    if not companion_yaml.exists():
        companion_yaml = plan_src.parent / "context_handoff" / "verify.yaml"
    if companion_yaml.exists():
        verify_yaml.write_text(companion_yaml.read_text(encoding="utf-8"), encoding="utf-8")

    def record(ph, result) -> None:
        if hasattr(result, "checks"):
            passed = sum(1 for check in result.checks if check.passed)
            ph.log(passed=result.passed, checks=f"{passed}/{len(result.checks)}",
                   artifacts=", ".join(result.artifacts))
        else:
            ph.log(passed=result.passed, checks="1/1" if result.passed else "0/1",
                   artifacts=result.output_artifact)

    with run.phase(PhaseParams(name="request", kind="engineer", owner=run.engineer,
                                description="Load plan and prepare Unreal Editor build")) as ph:
        ph.log(plan=plan_path)

    plan_output = PlanOutput(
        status="success",
        summary=f"Loaded from pre-existing plan: {plan_path}",
        artifacts=[str(verify_plan), str(plan_path)],
        notes_for_next_agent="Loaded pre-existing plan.",
    )

    ue_gates.snapshot_binary_files(run)
    with run.phase(PhaseParams(name="build_ue", kind="agent", owner="builder_ue", retries=1,
                                description="Implement the plan in the live Unreal Editor via MCP tools")) as ph:
        previous = ph.call(AgentCall(output_type=BuildOutput, prompt=effective_prompt, previous=plan_output,
                                      gates=[ue_gates.diff_matches_claims, ue_gates.binary_hashes_changed,
                                             ue_gates.no_op_success]))

    compile_result = None
    with run.phase(PhaseParams(name="compile", kind="code", owner="quality",
                                description="Run the Live Coding compilation protocol")) as ph:
        compile_result = ue_quality.test(
            run, changed_files=previous.changed_files if previous else None)
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
            previous = ph.call(AgentCall(output_type=BuildOutput, prompt=effective_prompt,
                                          previous=fix_envelope,
                                          gates=[ue_gates.diff_matches_claims, ue_gates.binary_hashes_changed,
                                                 ue_gates.no_op_success]))

        with run.phase(PhaseParams(name=f"compile_{i}", kind="code", owner="quality",
                                    description="Re-verify compilation after builder fix")) as ph:
            compile_result = ue_quality.test(
                run, changed_files=previous.changed_files if previous else None)
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
    parser.add_argument("plan", help="path to plan markdown file")
    parser.add_argument("--prompt", default=None, help="optional original prompt context")
    parser.add_argument("--config", default="adws/adw_sssf_config/sssf.config.yaml",
                        help="path to the SSSF agent roster")
    parser.add_argument("--adw-id", default=None, help="join or pin an existing session")
    args = parser.parse_args()
    sys.exit(main(args.plan, config=args.config, adw_id=args.adw_id, prompt=args.prompt))
