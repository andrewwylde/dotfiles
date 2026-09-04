#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic", "python-dotenv", "pyyaml", "rich"]
# ///
"""ADW Character Pipeline — Unreal character design and technical specification workflow.

Phases:
  1. engineer(request) -> capture character concept ask
  2. planner -> generate technical character specification (C++ class hierarchy, components, skeletal mesh requirements)
  3. scout -> verify project mesh/material paths and dependencies
  4. reviewer -> verify design spec against Unreal Engine conventions
"""

import argparse
import sys

from adw_modules import agents, gates, session, utils
from adw_modules.data_types import (AgentCall, GenericOutput, PhaseParams,
                                     PlanOutput, ScoutOutput, SSSFConfig)

REQUIRED_AGENTS = ["planner_ue", "scout", "reviewer"]


def main(prompt: str, config: str | SSSFConfig = "adws/adw_sssf_config/sssf.config.yaml", adw_id: str | None = None) -> int:
    cfg = agents.load_config(config)
    agents.validate(cfg, REQUIRED_AGENTS)
    run = session.ensure(cfg, adw_id)

    # Phase 1: Capture Request
    with run.phase(PhaseParams(name="request", kind="engineer", owner=run.engineer,
                               description="Capture the character design request")) as ph:
        ph.log(input=prompt)

    # Phase 2: Planner (Generate Spec)
    with run.phase(PhaseParams(name="plan_character", kind="agent", owner="planner_ue",
                               description="Generate character specification & C++ component structure")) as ph:
        plan_envelope = ph.call(AgentCall(output_type=PlanOutput, prompt=prompt,
                                          gates=[gates.artifacts_exist, gates.files_non_empty]))

    # Phase 3: Scout (Asset & Codebase Verification)
    with run.phase(PhaseParams(name="verify_paths", kind="agent", owner="scout",
                               description="Scout C++ source and Content directory for mesh/material assets")) as ph:
        scout_prompt = f"Verify existing character C++ classes and Content assets for implementing:\n{prompt}"
        ph.call(AgentCall(output_type=ScoutOutput, prompt=scout_prompt, previous=plan_envelope,
                          gates=[gates.artifacts_exist]))

    # Phase 4: Reviewer (Architecture Review)
    with run.phase(PhaseParams(name="review_design", kind="agent", owner="reviewer",
                               description="Review character C++ architecture and UPROPERTY declarations")) as ph:
        review_prompt = "Review the generated character spec and asset paths for Unreal Engine standards."
        ph.call(AgentCall(output_type=GenericOutput, prompt=review_prompt, previous=plan_envelope))

    return run.finish()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="inline text or a path to a character prompt file")
    parser.add_argument("--config", default="adws/adw_sssf_config/sssf.config.yaml",
                        help="path to the SSSF agent roster")
    parser.add_argument("--adw-id", default=None, help="join or pin an existing session")
    args = parser.parse_args()
    sys.exit(main(utils.resolve_prompt(args.prompt), config=args.config, adw_id=args.adw_id))
