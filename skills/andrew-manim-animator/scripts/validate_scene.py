#!/usr/bin/env python3
"""
Validate a generated Manim scene against the five reliability criteria.

Run:
    python validate_scene.py path/to/scene.py

Exit code 0 = pass, 1 = fail. Prints per-criterion pass/fail with evidence.
"""
import ast
import re
import sys
from pathlib import Path


TRANSFORM_NAMES = {
    "Transform",
    "ReplacementTransform",
    "Write",
    "Create",
    "FadeIn",
    "FadeOut",
    "GrowFromCenter",
    "GrowFromEdge",
    "DrawBorderThenFill",
    "MoveAlongPath",
    "Indicate",
    "ShowPassingFlash",
    "Circumscribe",
    "Uncreate",
    "Unwrite",
    "ApplyMethod",
    "ApplyFunction",
    "ApplyWave",
    "Rotate",
    "ScaleInPlace",
    "AnimationGroup",
    "LaggedStart",
    "Succession",
}

SCENE_BASES = {
    "Scene",
    "MovingCameraScene",
    "ZoomedScene",
    "ThreeDScene",
    "LinearTransformationScene",
    "VectorScene",
    "GraphScene",
    "SpecialThreeDScene",
}


def check(name: str, passed: bool, evidence: str) -> dict:
    return {"name": name, "passed": passed, "evidence": evidence}


def validate(path: Path) -> list[dict]:
    results: list[dict] = []
    source = path.read_text()

    # 1. Valid Python (AST parse)
    try:
        tree = ast.parse(source)
        results.append(check("valid_python", True, "ast.parse succeeded"))
    except SyntaxError as e:
        results.append(check("valid_python", False, f"SyntaxError: {e}"))
        return results  # can't continue if unparseable

    # 2. At least one Scene subclass
    scene_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_names.append(base.id)
                elif isinstance(base, ast.Attribute):
                    base_names.append(base.attr)
            if any(b in SCENE_BASES for b in base_names):
                scene_classes.append(node.name)
    if scene_classes:
        results.append(
            check(
                "has_scene_subclass",
                True,
                f"Found Scene subclass(es): {', '.join(scene_classes)}",
            )
        )
    else:
        results.append(
            check(
                "has_scene_subclass",
                False,
                "No class inherits from Scene/MovingCameraScene/etc.",
            )
        )

    # 3. At least one transform-family call
    transforms_used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in TRANSFORM_NAMES:
                transforms_used.add(name)
    if transforms_used:
        results.append(
            check(
                "has_transform_reveal",
                True,
                f"Transform-family calls found: {', '.join(sorted(transforms_used))}",
            )
        )
    else:
        results.append(
            check(
                "has_transform_reveal",
                False,
                "No Transform/Write/Create/FadeIn/etc. call found — "
                "the scene has no motion, which defeats the purpose of Manim.",
            )
        )

    # 4. At least one self.wait(...) pacing beat
    wait_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "wait"
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
            ):
                wait_calls += 1
    if wait_calls >= 1:
        results.append(
            check(
                "has_pacing_beat",
                True,
                f"self.wait(...) called {wait_calls} time(s)",
            )
        )
    else:
        results.append(
            check(
                "has_pacing_beat",
                False,
                "No self.wait(...) call — the scene has no pacing, which is "
                "the 3b1b teaching discipline we want to preserve.",
            )
        )

    # 5. No hard-coded config.background_color
    # Matches: config.background_color = "...", config.background_color="...",
    # manim.config.background_color = ..., etc.
    bg_pattern = re.compile(r"config\s*\.\s*background_color\s*=")
    match = bg_pattern.search(source)
    if match:
        line_no = source[: match.start()].count("\n") + 1
        results.append(
            check(
                "no_hardcoded_background",
                False,
                f"config.background_color set at line {line_no} — the skill "
                "should leave surface aesthetics to the user's environment.",
            )
        )
    else:
        results.append(
            check(
                "no_hardcoded_background",
                True,
                "No config.background_color assignment found",
            )
        )

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_scene.py <path-to-scene.py>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    results = validate(path)
    all_passed = all(r["passed"] for r in results)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['name']}: {r['evidence']}")
    print()
    print("VERDICT:", "PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
