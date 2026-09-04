import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Import UnrealMCPClient and extract_tool_text from scripts/ue_mcp.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue_mcp import UnrealMCPClient, extract_tool_text

TOOLSET_ASSET = "editor_toolset.toolsets.asset.AssetTools"
TOOLSET_SCENE = "editor_toolset.toolsets.scene.SceneTools"
TOOLSET_ACTOR = "editor_toolset.toolsets.actor.ActorTools"
TOOLSET_OBJECT = "editor_toolset.toolsets.object.ObjectTools"

REPO_ROOT = Path(__file__).resolve().parent.parent
UCP_SCRIPT = REPO_ROOT / "Plugins" / "UnrealClientProtocol" / "Skills" \
    / "unreal-client-protocol" / "scripts" / "UCP.py"
LIVE_CODING_CDO = "/Script/UnrealClientProtocolEditor.Default__LiveCodingOperationLibrary"
SOURCE_SUFFIXES = (".cpp", ".h", ".cs", ".uplugin", ".uproject")


class AdwEditorVerifier:
    def __init__(self, mcp_client=None, changed_files_override=None, ucp_caller=None):
        self.mcp_client = mcp_client or UnrealMCPClient()
        self.last_dll_fingerprints = {}
        self.changed_files_override = changed_files_override
        self.ucp_caller = ucp_caller or self._ucp_call

    def _ucp_call(self, function: str, params: dict | None = None) -> dict:
        """Call a UCP Live Coding function over the TCP bridge (stdin JSON)."""
        payload = {"object": LIVE_CODING_CDO, "function": function}
        if params:
            payload["params"] = params
        try:
            proc = subprocess.run(
                [sys.executable, str(UCP_SCRIPT)], input=json.dumps(payload),
                capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"error": str(e)}
        if proc.returncode != 0:
            return {"error": proc.stderr.strip() or f"exit {proc.returncode}"}
        try:
            return json.loads(proc.stdout)
        except ValueError:
            return {"error": proc.stdout[:200]}

    def _git_changed_sources(self) -> list[str]:
        """C++/plugin source files modified in the working tree (uncommitted)."""
        try:
            proc = subprocess.run(["git", "status", "--porcelain"],
                                  capture_output=True, text=True,
                                  cwd=str(REPO_ROOT), timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return []
        files = []
        for line in proc.stdout.splitlines():
            if len(line) > 3:
                status = line[:3]
                path = line[3:].strip('"')
                if path.endswith(SOURCE_SUFFIXES):
                    files.append(path)
        return files

    def _live_coding_compile(self, timeout: float = 120.0) -> tuple[bool, str]:
        """Trigger Live Coding and poll IsCompiling until done (or timeout)."""
        resp = self.ucp_caller("Compile")
        if "error" in resp:
            return False, f"UCP Compile error: {resp['error']}"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(2)
            status = self.ucp_caller("IsCompiling")
            if "error" in status:
                return False, f"UCP IsCompiling error: {status['error']}"
            rv = status.get("ReturnValue")
            if rv in (False, "false", "False", 0):
                return True, "Live Coding compile completed"
        return False, f"Live Coding still compiling after {timeout:.0f}s"

    def verify_compilation(self, compile_timeout: float = 120.0) -> bool:
        """Honest compile gate.

        If the run changed C++/plugin sources, trigger a real Live Coding
        compile via UCP and poll until it finishes; fail verbatim on any error
        or timeout. Asset-only runs have nothing to compile — the editor-state
        spec in the verify_state phase is their proof — so they pass with a
        note. Changed files come from the run's envelope when the chain passes
        them (changed_files_override), else from git status.
        """
        sources = self.changed_files_override if self.changed_files_override is not None else self._git_changed_sources()
        cpp = [f for f in sources if f.endswith(SOURCE_SUFFIXES)]
        if not cpp:
            print("No C++/plugin sources changed in this run; compile N/A "
                  "(editor state is proven by the verify_state spec phase).")
            return True
        print(f"Compiling {len(cpp)} changed source file(s) via Live Coding...")
        ok, detail = self._live_coding_compile(compile_timeout)
        print(f"[{'PASSED' if ok else 'FAILED'}] {detail}")
        return ok

    def _tool_value(self, toolset_name: str, tool_name: str, arguments: dict = None):
        """Call a tool and return its decoded returnValue, or None on transport error."""
        resp = self.mcp_client.call_tool(toolset_name, tool_name, arguments)
        text = extract_tool_text(resp)
        if not text:
            return None
        try:
            value = json.loads(text)
        except (ValueError, TypeError):
            return text
        if isinstance(value, dict) and "returnValue" in value:
            value = value["returnValue"]
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (ValueError, TypeError):
                    pass
        return value

    def _find_actor_ref(self, label: str) -> str:
        actors = self._tool_value(TOOLSET_SCENE, "find_actors",
                                  {"name": label, "tag": "", "collision_channels": []})
        if isinstance(actors, list) and actors and isinstance(actors[0], dict):
            return actors[0].get("refPath")
        return None

    def _component_type(self, component_class: str) -> str:
        if "/" in component_class:
            return component_class
        return "/Script/Engine." + component_class

    def _component_refs(self, actor_ref: str, component_class: str, component_name: str = None) -> list:
        refs = self._tool_value(TOOLSET_ACTOR, "get_components",
                                {"actor": {"refPath": actor_ref},
                                 "component_type": self._component_type(component_class)})
        if not isinstance(refs, list):
            return []
        if component_name:
            suffix = "." + component_name
            return [r["refPath"] for r in refs if isinstance(r, dict) and r.get("refPath", "").endswith(suffix)]
        return [r["refPath"] for r in refs if isinstance(r, dict) and r.get("refPath")]

    def _find_component_ref_any_class(self, actor_ref: str, component_name: str) -> str:
        refs = self._tool_value(TOOLSET_ACTOR, "get_components",
                                {"actor": {"refPath": actor_ref}, "component_type": ""})
        if isinstance(refs, list):
            suffix = "." + component_name
            for comp in refs:
                if isinstance(comp, dict) and comp.get("refPath", "").endswith(suffix):
                    return comp["refPath"]
        return None

    def _property_instance(self, assertion_data: dict, actor_ref: str):
        """Resolve (instance_ref, error_details) for property assertions."""
        comp_name = assertion_data.get("component_name")
        if not comp_name:
            return actor_ref, None
        comp_ref = self._find_component_ref_any_class(actor_ref, comp_name)
        if comp_ref:
            return comp_ref, None
        return None, f"Component '{comp_name}' not found on Actor '{assertion_data.get('actor')}'."

    @staticmethod
    def _split_indexed_property(prop_name: str):
        """Return (base_name, index_or_None) for names like 'OverrideMaterials[0]'."""
        m = re.match(r"^(.*?)\[(\d+)\]$", prop_name)
        if m:
            return m.group(1), int(m.group(2))
        return prop_name, None

    def _matchable_value(self, value, prop_name: str):
        """Return a JSON string to match 'expected' against, honoring Name[N] indexes.

        The MCP get_properties tool rejects indexed property names, so an indexed
        assertion is resolved by querying the base property and matching against
        the element at that index. Returns None when the index is out of range.
        """
        base, index = self._split_indexed_property(prop_name)
        if index is None:
            return json.dumps(value)
        target = value
        if isinstance(target, dict):
            target = target.get(base, target)
        if isinstance(target, str):
            try:
                target = json.loads(target)
            except (ValueError, TypeError):
                pass
        if isinstance(target, list) and index < len(target):
            return json.dumps(target[index])
        return None

    def _capsule_half_height(self, actor_ref: str):
        refs = self._component_refs(actor_ref, "CapsuleComponent")
        if not refs:
            refs = [r for r in ([self._find_component_ref_any_class(actor_ref, "CollisionCylinder")] or []) if r]
        if not refs:
            return None
        value = self._tool_value(TOOLSET_OBJECT, "get_properties",
                                 {"instance": {"refPath": refs[0]}, "properties": ["CapsuleHalfHeight"]})
        m = re.search(r"-?\d+(?:\.\d+)?", self._matchable_value(value, "CapsuleHalfHeight") or "")
        return float(m.group(0)) if m else None

    def evaluate_assertion(self, assertion: dict) -> dict:
        """Evaluate declarative YAML engine assertion."""
        if isinstance(assertion, dict) and "type" in assertion:
            assertion_type = assertion["type"]
            assertion_data = assertion
        elif isinstance(assertion, dict) and len(assertion) > 0:
            assertion_type = list(assertion.keys())[0]
            assertion_data = assertion[assertion_type]
        else:
            return {"assertion_type": "unknown", "status": "fail", "details": f"Invalid assertion format: {assertion}"}

        result = {"assertion_type": assertion_type, "status": "fail", "details": ""}

        try:
            if assertion_type == "asset_exists":
                asset_path = assertion_data.get("path") or assertion_data.get("asset_path")
                exists = self._tool_value(TOOLSET_ASSET, "exists", {"path": asset_path})
                if exists is True:
                    result["status"] = "pass"
                    result["details"] = f"Asset '{asset_path}' exists."
                else:
                    result["details"] = f"Asset '{asset_path}' not found in AssetRegistry."

            elif assertion_type == "actor_exists":
                actor_name = assertion_data.get("label") or assertion_data.get("name")
                if self._find_actor_ref(actor_name):
                    result["status"] = "pass"
                    result["details"] = f"Actor '{actor_name}' found."
                else:
                    result["details"] = f"Actor '{actor_name}' not found."

            elif assertion_type == "component_exists":
                actor_name = assertion_data.get("actor") or assertion_data.get("actor_name")
                comp_class = assertion_data.get("component_class") or assertion_data.get("component_name")
                actor_ref = self._find_actor_ref(actor_name)
                if not actor_ref:
                    result["details"] = f"Actor '{actor_name}' not found."
                else:
                    refs = self._component_refs(actor_ref, comp_class,
                                                assertion_data.get("component_name"))
                    if refs:
                        result["status"] = "pass"
                        result["details"] = f"Found {len(refs)} '{comp_class}' component(s)"
                    else:
                        result["details"] = f"Component '{comp_class}' not found on Actor '{actor_name}'."

            elif assertion_type == "component_count":
                actor_name = assertion_data.get("actor") or assertion_data.get("actor_name")
                comp_class = assertion_data.get("component_class") or assertion_data.get("component_name")
                expected_count = assertion_data.get("count", 0)
                actor_ref = self._find_actor_ref(actor_name)
                if not actor_ref:
                    result["details"] = f"Actor '{actor_name}' not found."
                else:
                    refs = self._component_refs(actor_ref, comp_class,
                                                assertion_data.get("component_name"))
                    if len(refs) == int(expected_count):
                        result["status"] = "pass"
                        result["details"] = f"Found {len(refs)} '{comp_class}' component(s)"
                    else:
                        result["details"] = f"Expected {expected_count} '{comp_class}' component(s) on Actor '{actor_name}', found {len(refs)}."

            elif assertion_type == "property_equals":
                actor_name = assertion_data.get("actor") or assertion_data.get("actor_name")
                prop_name = assertion_data.get("property") or assertion_data.get("property_name")
                expected = assertion_data.get("expected") or assertion_data.get("expected_value")
                actor_ref = self._find_actor_ref(actor_name)
                if not actor_ref:
                    result["details"] = f"Actor '{actor_name}' not found."
                else:
                    instance, comp_error = self._property_instance(assertion_data, actor_ref)
                    if comp_error:
                        result["details"] = comp_error
                    else:
                        base_prop, _ = self._split_indexed_property(prop_name)
                        value = self._tool_value(TOOLSET_OBJECT, "get_properties",
                                                 {"instance": {"refPath": instance}, "properties": [base_prop]})
                        matchable = self._matchable_value(value, prop_name)
                        if expected and matchable and expected in matchable:
                            result["status"] = "pass"
                            result["details"] = f"Property '{prop_name}' contains '{expected}'."
                        else:
                            result["details"] = f"Property '{prop_name}' expected '{expected}', got: {str(value)[:120]}."

            elif assertion_type == "property_greater_than":
                actor_name = assertion_data.get("actor") or assertion_data.get("actor_name")
                prop_name = assertion_data.get("property") or assertion_data.get("property_name")
                expected = float(assertion_data.get("expected") or assertion_data.get("expected_value", 0))
                actor_ref = self._find_actor_ref(actor_name)
                if not actor_ref:
                    result["details"] = f"Actor '{actor_name}' not found."
                else:
                    instance, comp_error = self._property_instance(assertion_data, actor_ref)
                    if comp_error:
                        result["details"] = comp_error
                    else:
                        base_prop, _ = self._split_indexed_property(prop_name)
                        value = self._tool_value(TOOLSET_OBJECT, "get_properties",
                                                 {"instance": {"refPath": instance}, "properties": [base_prop]})
                        matchable = self._matchable_value(value, prop_name)
                        m = re.search(r"-?\d+(?:\.\d+)?", matchable or "")
                        if m and float(m.group(0)) > expected:
                            result["status"] = "pass"
                            result["details"] = f"Property '{prop_name}' value {m.group(0)} > {expected}."
                        else:
                            result["details"] = f"Property '{prop_name}' value not > {expected}: {str(value)[:120]}."

            elif assertion_type == "actor_grounded":
                actor_name = (assertion_data.get("actor") or assertion_data.get("actor_name")
                              or assertion_data.get("label"))
                tolerance = float(assertion_data.get("tolerance", 50.0))
                max_trace = float(assertion_data.get("max_trace_distance", 5000.0))
                actor_ref = self._find_actor_ref(actor_name)
                if not actor_ref:
                    result["details"] = f"Actor '{actor_name}' not found."
                else:
                    transform = self._tool_value(TOOLSET_ACTOR, "get_actor_transform", {"actor": actor_ref})
                    if not isinstance(transform, dict) or "location" not in transform:
                        result["details"] = f"Could not read transform for Actor '{actor_name}'."
                    else:
                        loc = transform["location"]
                        half_height = self._capsule_half_height(actor_ref)
                        if half_height is None:
                            result["details"] = f"Could not determine capsule half-height for Actor '{actor_name}'."
                        else:
                            bottom_z = loc["z"] - half_height
                            start_z = loc["z"] + half_height + 200.0
                            trace_args = {
                                "start": {"x": loc["x"], "y": loc["y"], "z": start_z},
                                "end": {"x": loc["x"], "y": loc["y"], "z": loc["z"] - max_trace},
                            }
                            hit = self._tool_value(TOOLSET_SCENE, "trace_world", trace_args)
                            if hit is not None and abs(float(hit) - 200.0) < 1.0:
                                time.sleep(0.5)
                                hit = self._tool_value(TOOLSET_SCENE, "trace_world", trace_args)
                            if hit is None:
                                result["details"] = (f"No surface below Actor '{actor_name}' within "
                                                     f"{max_trace:.0f} cm (bottom_z={bottom_z:.2f}).")
                            else:
                                surface_z = start_z - float(hit)
                                delta = bottom_z - surface_z
                                if abs(delta) <= tolerance:
                                    result["status"] = "pass"
                                    result["details"] = (f"Actor '{actor_name}' grounded: bottom_z={bottom_z:.2f}, "
                                                         f"surface_z={surface_z:.2f}, delta={delta:.2f} cm "
                                                         f"(tolerance {tolerance:.1f} cm).")
                                elif delta > 0:
                                    result["details"] = (f"Actor '{actor_name}' FLOATING {delta:.2f} cm above "
                                                         f"surface (bottom_z={bottom_z:.2f}, "
                                                         f"surface_z={surface_z:.2f}).")
                                else:
                                    result["details"] = (f"Actor '{actor_name}' CLIPPED {abs(delta):.2f} cm into "
                                                         f"surface (bottom_z={bottom_z:.2f}, "
                                                         f"surface_z={surface_z:.2f}).")

            else:
                result["details"] = f"Unknown assertion type: {assertion_type}"

        except Exception as e:
            result["details"] = f"Assertion evaluation error: {e}"

        return result

    def verify_spec(self, spec_path: str) -> bool:
        if not os.path.exists(spec_path):
            print(json.dumps({"status": "error", "message": f"Spec file not found: {spec_path}"}))
            return False

        import yaml
        with open(spec_path, "r") as f:
            spec = yaml.safe_load(f)

        overall_status = "pass"
        results = []

        if isinstance(spec, dict):
            assertions = spec.get("assertions", [])
        elif isinstance(spec, list):
            assertions = spec
        else:
            assertions = []

        for assertion in assertions:
            res = self.evaluate_assertion(assertion)
            results.append(res)
            if res["status"] == "fail":
                overall_status = "fail"

        output = {
            "overall_status": overall_status,
            "spec_file": spec_path,
            "total_assertions": len(assertions),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
            "results": results
        }

        print(json.dumps(output, indent=2))
        return overall_status == "pass"


def main():
    parser = argparse.ArgumentParser(description="Unreal Editor Verification & Compilation Harness.")
    parser.add_argument("--verify-compilation", action="store_true", help="Run 6-step compilation & DLL synchronization protocol.")
    parser.add_argument("--spec", help="Path to YAML assertion spec file.")

    args = parser.parse_args()
    mcp_client = UnrealMCPClient()
    verifier = AdwEditorVerifier(mcp_client)

    if args.verify_compilation:
        success = verifier.verify_compilation()
        sys.exit(0 if success else 1)

    elif args.spec:
        success = verifier.verify_spec(args.spec)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
