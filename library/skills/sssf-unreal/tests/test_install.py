from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent
CORE_INSTALLER = SKILL_ROOT.parent / "sssf" / "scripts" / "install.py"
UE_INSTALLER = SKILL_ROOT / "scripts" / "install.py"


def run(script: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_installer_requires_core_sssf(tmp_path: Path):
    result = run(UE_INSTALLER, tmp_path)
    assert result.returncode != 0
    assert "core SSSF is not installed" in result.stderr


def test_installer_is_additive_and_idempotent(tmp_path: Path):
    core = run(CORE_INSTALLER, tmp_path)
    assert core.returncode == 0, core.stderr

    first = run(UE_INSTALLER, tmp_path)
    assert first.returncode == 0, first.stderr
    second = run(UE_INSTALLER, tmp_path)
    assert second.returncode == 0, second.stderr
    assert "changed: 0 file(s)" in second.stdout

    config_path = tmp_path / "adws" / "adw_sssf_config" / "sssf.config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    names = [agent["name"] for agent in config["agents"]]
    assert names.count("planner_ue") == 1
    assert names.count("builder_ue") == 1

    protected = config["defaults"]["protected_files"]
    assert "scripts/adw_editor_verify.py" in protected
    assert "scripts/ue_mcp.py" in protected

    planner = next(agent for agent in config["agents"] if agent["name"] == "planner_ue")
    assert planner["prompt_engineering"]["system"].endswith("planner_ue/system.md")

    builder = next(agent for agent in config["agents"] if agent["name"] == "builder_ue")
    assert "scripts/" not in builder["writes"]
    assert "tmp_scripts/" in builder["writes"]

    justfile = (tmp_path / "justfile").read_text(encoding="utf-8")
    assert justfile.count("# sssf-unreal extension") == 1
    assert "ue-sdlc *ARGS:" in justfile

    assert (tmp_path / "adws" / "adw_modules" / "ue_gates.py").is_file()
    assert (tmp_path / "adws" / "adw_modules" / "ue_quality.py").is_file()
    assert (tmp_path / "scripts" / "adw_editor_verify.py").is_file()

    for script in (
        "adw_plan_build_verify_ue.py",
        "adw_build_verify_ue.py",
        "adw_character_design.py",
    ):
        result = subprocess.run(
            ["uv", "run", str(tmp_path / "adws" / script), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
