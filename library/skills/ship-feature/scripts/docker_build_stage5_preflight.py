#!/usr/bin/env python3
"""Stage 5 docker build CI pre-flight: path-filtered docker build before push.

Mirrors PR #4371 docker-build-validation using .github/docker-build.json SSOT.
Writes `.context/docker-build-stage5-preflight.json` for stage5_push_gate.py.

Default push-phase behavior (via commit_push_pr_preflight): --detect-only defers
builds to CI. Use without --detect-only for local image builds (capped).

Usage (repo root):
  python3 .claude/skills/ship-feature/scripts/docker_build_stage5_preflight.py \\
    --base origin/main \\
    --out .context/docker-build-stage5-preflight.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUN_BY_SCRIPT = "docker_build_stage5_preflight.py"
ARTIFACT_DEFAULT = ".context/docker-build-stage5-preflight.json"
MATRIX_REL = ".github/scripts/docker-build-matrix.py"
SCHEMAS_MARKER = "platform-schemas/dist/types/python/enums/pyproject.toml"

TOOLING_ONLY_PREFIXES = (
    ".github/docker-build.json",
    ".github/scripts/docker-build-matrix.py",
    ".claude/skills/ship-feature/",
    ".cursor/skills/ship-feature/",
    ".cursor/skills/andrew-ship-feature/",
)

DEFAULT_MAX_IMAGES = 3
DEFAULT_MAX_MINUTES = 15


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def repo_root() -> Path:
    proc = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "not a git repository")
    return Path(proc.stdout.strip())


def head_sha(root: Path) -> str:
    proc = run(["git", "rev-parse", "HEAD"], root)
    if proc.returncode != 0:
        raise SystemExit("git rev-parse HEAD failed")
    return proc.stdout.strip()


def changed_files(root: Path, base: str, head: str) -> list[str]:
    proc = run(["git", "diff", f"{base}...{head}", "--name-only"], root)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def tooling_only_in_diff(root: Path, base: str, head: str) -> bool:
    files = changed_files(root, base, head)
    if not files:
        return False
    for path in files:
        normalized = path.replace("\\", "/")
        if not any(normalized.startswith(prefix) for prefix in TOOLING_ONLY_PREFIXES):
            return False
    return True


def matrix_script(root: Path) -> Path:
    return root / MATRIX_REL


def config_rel_path(root: Path, config: Path) -> str:
    try:
        return str(config.relative_to(root))
    except ValueError:
        return str(config)


def load_config(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def image_by_key(cfg: dict, key: str) -> dict:
    for img in cfg["images"]:
        if img["key"] == key:
            return img
    raise KeyError(key)


def detect_keys(root: Path, base: str, head: str, config: Path) -> list[str]:
    script = matrix_script(root)
    if not script.is_file():
        raise SystemExit(f"missing matrix script: {script}")
    cmd = [
        sys.executable,
        str(script),
        "--detect-keys",
        "--base",
        base,
        "--head",
        head,
        "--config",
        str(config),
    ]
    proc = run(cmd, root)
    if proc.returncode != 0:
        raise SystemExit(
            f"docker-build-matrix.py --detect-keys failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return json.loads(proc.stdout.strip())


def docker_available() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "docker binary not found on PATH"
    proc = run(["docker", "info"], Path.cwd())
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "docker daemon unreachable"
    return True, ""


def schemas_present(root: Path) -> bool:
    return (root / SCHEMAS_MARKER).is_file()


def write_artifact(root: Path, out: str, payload: dict) -> None:
    out_path = root / out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def build_image(root: Path, img: dict, key: str) -> dict:
    dockerfile = root / img["dockerfile"]
    context = root / img["context"]
    tag = f"parable-gate-{key}:local"
    cmd = [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "-f",
        str(dockerfile),
        "-t",
        tag,
        str(context),
    ]
    proc = run(cmd, root)
    return {
        "key": key,
        "dockerfile": img["dockerfile"],
        "context": img["context"],
        "passed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def skip_payload(
    root: Path,
    *,
    reason: str,
    base: str,
    config: Path,
    keys: list[str] | None = None,
    detail: str = "",
) -> dict:
    payload: dict = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": True,
        "skipped": True,
        "reason": reason,
        "head_sha": head_sha(root),
        "base": base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "config_path": config_rel_path(root, config),
        "images_built": [],
        "steps": [],
    }
    if keys is not None:
        payload["detected_keys"] = keys
    if detail:
        payload["detail"] = detail
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--out", default=ARTIFACT_DEFAULT)
    parser.add_argument(
        "--config",
        default=None,
        help="Path to docker-build.json (default: .github/docker-build.json)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Detect only; write skip artifact (tests)",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Detect keys and defer builds to CI (default for push-phase router)",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=DEFAULT_MAX_IMAGES,
        help=f"Max local docker builds (default {DEFAULT_MAX_IMAGES})",
    )
    parser.add_argument(
        "--max-minutes",
        type=int,
        default=DEFAULT_MAX_MINUTES,
        help=f"Wall-clock budget for local builds (default {DEFAULT_MAX_MINUTES})",
    )
    args = parser.parse_args()

    root = repo_root()
    config = Path(args.config) if args.config else root / ".github/docker-build.json"
    if not config.is_file():
        raise SystemExit(f"missing docker build config: {config}")

    if tooling_only_in_diff(root, args.base, args.head):
        write_artifact(
            root,
            args.out,
            skip_payload(
                root,
                reason="tooling_only_in_diff",
                base=args.base,
                config=config,
            ),
        )
        return

    keys = detect_keys(root, args.base, args.head, config)
    if not keys:
        write_artifact(
            root,
            args.out,
            skip_payload(
                root,
                reason="no_docker_inputs_in_diff",
                base=args.base,
                config=config,
            ),
        )
        return

    if args.detect_only or args.skip_build:
        reason = "skip_build_flag" if args.skip_build else "detect_only_deferred_to_ci"
        payload = skip_payload(
            root,
            reason=reason,
            base=args.base,
            config=config,
            keys=keys,
        )
        write_artifact(root, args.out, payload)
        return

    ok, reason = docker_available()
    if not ok:
        write_artifact(
            root,
            args.out,
            skip_payload(
                root,
                reason="docker_unavailable",
                base=args.base,
                config=config,
                keys=keys,
                detail=reason,
            ),
        )
        return

    if len(keys) > args.max_images:
        write_artifact(
            root,
            args.out,
            skip_payload(
                root,
                reason="budget_exceeded",
                base=args.base,
                config=config,
                keys=keys,
                detail=f"detected {len(keys)} images; max {args.max_images}",
            ),
        )
        return

    cfg = load_config(config)
    steps: list[dict] = []
    schemas_built = False
    all_passed = True
    deadline = time.monotonic() + args.max_minutes * 60
    built_keys: list[str] = []

    for key in keys:
        if time.monotonic() >= deadline:
            write_artifact(
                root,
                args.out,
                skip_payload(
                    root,
                    reason="budget_exceeded",
                    base=args.base,
                    config=config,
                    keys=keys,
                    detail=f"wall-clock budget {args.max_minutes}m exceeded",
                ),
            )
            return

        img = image_by_key(cfg, key)
        if img.get("needs_schemas") and not schemas_built:
            if not schemas_present(root):
                proc = run(["make", "build-schemas"], root)
                steps.append(
                    {
                        "step": "make build-schemas",
                        "passed": proc.returncode == 0,
                        "returncode": proc.returncode,
                    }
                )
                if proc.returncode != 0:
                    all_passed = False
                    break
            schemas_built = True

        step = build_image(root, img, key)
        steps.append(step)
        built_keys.append(key)
        if not step["passed"]:
            all_passed = False
            break

        if len(built_keys) >= args.max_images:
            break

    payload = {
        "RUN_BY_SCRIPT": RUN_BY_SCRIPT,
        "passed": all_passed,
        "skipped": False,
        "head_sha": head_sha(root),
        "base": args.base,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "config_path": config_rel_path(root, config),
        "images_built": built_keys,
        "detected_keys": keys,
        "steps": steps,
    }
    write_artifact(root, args.out, payload)
    if not all_passed:
        raise SystemExit("one or more docker builds failed")


if __name__ == "__main__":
    main()
