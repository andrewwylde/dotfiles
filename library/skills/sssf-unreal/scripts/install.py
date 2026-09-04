#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pyyaml"]
# ///
"""Install the Unreal extension into an existing SSSF-enabled repository."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
PROTECTED_FILES = ["scripts/adw_editor_verify.py", "scripts/ue_mcp.py"]

PLANNER_UE = """
  - name: planner_ue
    color: "#8b5cf6"
    thinking: high
    purpose: Turn an Unreal request into an implementation plan and falsifiable editor verification spec.
    prompt_engineering:
      system: adws/adw_data/prompt_engineering/planner_ue/system.md
      user: adws/adw_data/prompt_engineering/planner_ue/user.md
    writes:
      - specs/
    tools:
      - read
      - grep
      - find
      - ls
      - bash
      - write
"""

BUILDER_UE = """
  - name: builder_ue
    color: "#06b6d4"
    purpose: Implement Unreal Editor changes through UCP and report every changed asset or file.
    prompt_engineering:
      system: adws/adw_data/prompt_engineering/builder_ue/system.md
      user: adws/adw_data/prompt_engineering/builder_ue/user.md
    writes:
      - Content/
      - Source/
      - Config/
      - Plugins/
      - tmp_scripts/
      - Saved/
    tools:
      - read
      - grep
      - find
      - ls
      - bash
      - edit
      - write
"""

JUST_RECIPES = """

# sssf-unreal extension
ue-sdlc *ARGS:
    uv run adws/adw_plan_build_verify_ue.py --config {{config}} {{ARGS}}

ue-build *ARGS:
    uv run adws/adw_build_verify_ue.py --config {{config}} {{ARGS}}

character-design *ARGS:
    uv run adws/adw_character_design.py --config {{config}} {{ARGS}}

sssf-ue-onboarding:
    uv run python scripts/sssf_onboarding.py
"""


def stamp(src: Path, dest: Path, force: bool, stamped: list[str], skipped: list[str]) -> None:
    if src.is_dir():
        for child in sorted(src.iterdir()):
            if child.name == "__pycache__":
                continue
            stamp(child, dest / child.name, force, stamped, skipped)
        return
    if dest.exists() and not force:
        skipped.append(str(dest))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    stamped.append(str(dest))


def ensure_config(config_path: Path, changed: list[str]) -> None:
    text = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    agents = data.get("agents", []) or []
    existing_names = {
        agent.get("name") for agent in agents if isinstance(agent, dict)
    }
    missing_agents = [
        ("planner_ue", PLANNER_UE),
        ("builder_ue", BUILDER_UE),
    ]
    missing_agents = [item for item in missing_agents if item[0] not in existing_names]
    if missing_agents:
        if not re.search(r"(?m)^agents:\s*$", text):
            raise RuntimeError(f"Cannot locate top-level agents list in {config_path}")
        for name, block in missing_agents:
            text = text.rstrip() + "\n" + block
            changed.append(f"{config_path} (+{name})")

    defaults = data.get("defaults", {}) or {}
    protected = defaults.get("protected_files", []) or []
    missing = [path for path in PROTECTED_FILES if path not in protected]
    if missing:
        match = re.search(
            r"(?m)^(  protected_files:\s*\r?\n)((?:    - [^\r\n]*\r?\n)+)", text
        )
        if not match:
            raise RuntimeError(f"Cannot locate defaults.protected_files in {config_path}")
        additions = "".join(f"    - {path}\n" for path in missing)
        text = text[:match.end(2)] + additions + text[match.end(2):]
        changed.append(f"{config_path} (+{len(missing)} protected paths)")

    config_path.write_text(text, encoding="utf-8")


def ensure_justfile(justfile: Path, changed: list[str]) -> None:
    text = justfile.read_text(encoding="utf-8")
    if "# sssf-unreal extension" not in text:
        justfile.write_text(text.rstrip() + JUST_RECIPES + "\n", encoding="utf-8")
        changed.append(f"{justfile} (+Unreal recipes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite extension-owned files")
    args = parser.parse_args()

    root = Path.cwd()
    config_path = root / "adws" / "adw_sssf_config" / "sssf.config.yaml"
    justfile = root / "justfile"
    if not (root / "adws" / "adw_modules" / "agents.py").is_file() or not config_path.is_file():
        parser.error("core SSSF is not installed; install the sssf skill first")
    if not justfile.is_file():
        parser.error("core SSSF justfile is missing; repair the core installation first")

    stamped: list[str] = []
    skipped: list[str] = []
    stamp(TEMPLATES / "adws", root / "adws", args.force, stamped, skipped)
    stamp(TEMPLATES / "scripts", root / "scripts", args.force, stamped, skipped)
    stamp(
        TEMPLATES / "prompt_engineering",
        root / "adws" / "adw_data" / "prompt_engineering",
        args.force,
        stamped,
        skipped,
    )
    stamp(TEMPLATES / "rules", root / ".agents" / "rules", args.force, stamped, skipped)
    ensure_config(config_path, stamped)
    ensure_justfile(justfile, stamped)

    print(f"sssf-unreal installed into {root}")
    print(f"  changed: {len(stamped)} file(s)")
    for path in stamped:
        print(f"    + {path}")
    if skipped:
        print(f"  skipped existing extension files: {len(skipped)}")
    print("\nnext steps:")
    print("  1. Enable the UnrealClientProtocol plugin and open the Unreal Editor")
    print("  2. just sssf-ue-onboarding")
    print('  3. just ue-sdlc "<editor task>"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
