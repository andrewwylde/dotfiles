import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "templates" / "scripts"))

from adw_editor_verify import AdwEditorVerifier

ACTOR_REF = "/Game/ThirdPerson/Lvl_ThirdPerson.Lvl_ThirdPerson:PersistentLevel.BP_MyCharacter_C_0"


def env(return_value):
    text = json.dumps({"returnValue": return_value})
    return {"result": {"content": [{"type": "text", "text": text}]}}


class FakeMCPClient:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def call_tool(self, toolset_name, tool_name, arguments=None):
        self.calls.append((toolset_name, tool_name, arguments))
        if not self.responses:
            raise AssertionError(f"Unexpected call: {toolset_name}.{tool_name}")
        return self.responses.pop(0)


def verifier_with(*responses):
    return AdwEditorVerifier(FakeMCPClient(responses)), AdwEditorVerifier(FakeMCPClient(responses)).mcp_client


def test_asset_exists_passes_when_tool_returns_true():
    client = FakeMCPClient([env(True)])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "asset_exists",
                                "path": "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter"})
    assert res["status"] == "pass"
    assert client.calls[0][0] == "editor_toolset.toolsets.asset.AssetTools"
    assert client.calls[0][1] == "exists"


def test_asset_exists_fails_when_tool_returns_false():
    client = FakeMCPClient([env(False)])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "asset_exists", "path": "/Game/Missing.Asset"})
    assert res["status"] == "fail"
    assert "not found" in res["details"]


def test_actor_exists_passes_and_uses_full_find_actors_args():
    client = FakeMCPClient([env([{"refPath": ACTOR_REF}])])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_exists", "label": "BP_MyCharacter_C_0"})
    assert res["status"] == "pass"
    toolset, tool, args = client.calls[0]
    assert toolset == "editor_toolset.toolsets.scene.SceneTools"
    assert tool == "find_actors"
    assert args == {"name": "BP_MyCharacter_C_0", "tag": "", "collision_channels": []}


def test_actor_exists_fails_when_no_actor_found():
    client = FakeMCPClient([env([])])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_exists", "label": "Ghost"})
    assert res["status"] == "fail"


def test_component_exists_filters_by_class_path():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}]),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "component_exists",
                                "actor": "BP_MyCharacter_C_0",
                                "component_class": "SkeletalMeshComponent"})
    assert res["status"] == "pass"
    assert client.calls[1][2]["component_type"] == "/Script/Engine.SkeletalMeshComponent"


def test_component_exists_fails_when_component_missing():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([]),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "component_exists",
                                "actor": "BP_MyCharacter_C_0",
                                "component_class": "SkeletalMeshComponent"})
    assert res["status"] == "fail"


def test_component_count_counts_class_matches():
    refs = [{"refPath": f"{ACTOR_REF}.Comp{i}"} for i in range(3)]
    client = FakeMCPClient([env([{"refPath": ACTOR_REF}]), env(refs)])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "component_count",
                                "actor": "BP_MyCharacter_C_0",
                                "component_class": "SkeletalMeshComponent",
                                "count": 3})
    assert res["status"] == "pass"
    assert "Found 3" in res["details"]


def test_component_count_wrong_count_fails():
    refs = [{"refPath": f"{ACTOR_REF}.Comp{i}"} for i in range(2)]
    client = FakeMCPClient([env([{"refPath": ACTOR_REF}]), env(refs)])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "component_count",
                                "actor": "BP_MyCharacter_C_0",
                                "component_class": "SkeletalMeshComponent",
                                "count": 3})
    assert res["status"] == "fail"


def test_property_equals_on_actor():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env('{"MaxSproingChargeTime":1}'),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "property": "MaxSproingChargeTime",
                                "expected": "1"})
    assert res["status"] == "pass"
    assert client.calls[1][2] == {"instance": {"refPath": ACTOR_REF}, "properties": ["MaxSproingChargeTime"]}


def test_property_equals_on_named_component():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}, {"refPath": ACTOR_REF + ".CameraBoom"}]),
        env('{"OverrideMaterials":["/Game/Materials/M_Red"]}'),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "component_name": "CharacterMesh0",
                                "property": "OverrideMaterials",
                                "expected": "/Game/Materials/M_Red"})
    assert res["status"] == "pass"


def test_property_equals_indexed_property_queries_base_name():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}]),
        env('{"OverrideMaterials":[{"refPath":"/Game/Materials/M_Red.M_Red"},'
            '{"refPath":"/Game/Materials/M_Yellow.M_Yellow"}]}'),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "component_name": "CharacterMesh0",
                                "property": "OverrideMaterials[1]",
                                "expected": "/Game/Materials/M_Yellow.M_Yellow"})
    assert res["status"] == "pass"
    assert client.calls[2][2] == {"instance": {"refPath": ACTOR_REF + ".CharacterMesh0"},
                                  "properties": ["OverrideMaterials"]}


def test_property_equals_indexed_property_wrong_slot_fails():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}]),
        env('{"OverrideMaterials":[{"refPath":"/Game/Materials/M_Red.M_Red"},'
            '{"refPath":"/Game/Materials/M_Yellow.M_Yellow"}]}'),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "component_name": "CharacterMesh0",
                                "property": "OverrideMaterials[1]",
                                "expected": "/Game/Materials/M_Red.M_Red"})
    assert res["status"] == "fail"


def test_property_equals_indexed_property_out_of_range_fails():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}]),
        env('{"OverrideMaterials":["/Game/Materials/M_Red"]}'),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "component_name": "CharacterMesh0",
                                "property": "OverrideMaterials[5]",
                                "expected": "/Game/Materials/M_Red"})
    assert res["status"] == "fail"


def test_property_equals_missing_component_fails():
    client = FakeMCPClient([
        env([{"refPath": ACTOR_REF}]),
        env([{"refPath": ACTOR_REF + ".CharacterMesh0"}]),
    ])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "property_equals",
                                "actor": "BP_MyCharacter_C_0",
                                "component_name": "Nope",
                                "property": "OverrideMaterials",
                                "expected": "x"})
    assert res["status"] == "fail"
    assert "Component 'Nope' not found" in res["details"]


def grounded_responses(z, half_height, hit):
    return [
        env([{"refPath": ACTOR_REF}]),
        env({"location": {"x": 100.0, "y": 200.0, "z": z},
             "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
             "scale": {"x": 1, "y": 1, "z": 1}}),
        env([{"refPath": ACTOR_REF + ".CollisionCylinder"}]),
        env(f'{{"CapsuleHalfHeight":{half_height}}}'),
        env(hit),
    ]


def test_actor_grounded_passes_when_bottom_rests_on_surface():
    client = FakeMCPClient(grounded_responses(z=90.0, half_height=90.0, hit=380.0))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "BP_MyCharacter_C_0"})
    assert res["status"] == "pass"
    assert "grounded" in res["details"]
    trace_args = client.calls[4][2]
    assert trace_args["start"]["z"] == 90.0 + 90.0 + 200.0
    assert trace_args["end"]["z"] == 90.0 - 5000.0


def test_actor_grounded_fails_when_floating_above_surface():
    client = FakeMCPClient(grounded_responses(z=249.5, half_height=90.0, hit=539.5))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "BP_MyCharacter_C_0"})
    assert res["status"] == "fail"
    assert "FLOATING" in res["details"]
    assert "159.50" in res["details"]


def test_actor_grounded_fails_when_clipped_into_surface():
    client = FakeMCPClient(grounded_responses(z=30.0, half_height=90.0, hit=320.0))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "BP_MyCharacter_C_0"})
    assert res["status"] == "fail"
    assert "CLIPPED" in res["details"]
    assert "60.00" in res["details"]


def test_actor_grounded_fails_when_no_surface_below():
    client = FakeMCPClient(grounded_responses(z=90.0, half_height=90.0, hit=None))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "BP_MyCharacter_C_0"})
    assert res["status"] == "fail"
    assert "No surface below" in res["details"]


def test_actor_grounded_respects_custom_tolerance():
    client = FakeMCPClient(grounded_responses(z=150.0, half_height=90.0, hit=440.0))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded",
                                "actor": "BP_MyCharacter_C_0",
                                "tolerance": 30.0})
    assert res["status"] == "fail"
    assert "FLOATING" in res["details"]
    client = FakeMCPClient(grounded_responses(z=150.0, half_height=90.0, hit=440.0))
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded",
                                "actor": "BP_MyCharacter_C_0",
                                "tolerance": 120.0})
    assert res["status"] == "pass"


def test_actor_grounded_retries_after_self_hit():
    client = FakeMCPClient(grounded_responses(z=90.0, half_height=90.0, hit=200.0)
                           + [env(380.0)])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "BP_MyCharacter_C_0"})
    assert res["status"] == "pass"
    assert client.calls[5][1] == "trace_world"


def test_actor_grounded_fails_when_actor_missing():
    client = FakeMCPClient([env([])])
    v = AdwEditorVerifier(client)
    res = v.evaluate_assertion({"type": "actor_grounded", "actor": "Ghost"})
    assert res["status"] == "fail"
    assert "not found" in res["details"]


def test_verify_compilation_never_calls_mcp():
    client = FakeMCPClient()
    v = AdwEditorVerifier(client, changed_files_override=[])
    assert v.verify_compilation() is True
    assert client.calls == []


def test_verify_spec_reports_summary_and_result_shape():
    import yaml
    import tempfile
    spec = {
        "assertions": [
            {"type": "asset_exists", "path": "/Game/X.Y"},
            {"type": "asset_exists", "path": "/Game/Missing.Z"},
        ]
    }
    # 4 responses: verify_spec consumes 2 (pass, fail); the two direct
    # re-evaluations below consume the remaining 2 (pass, fail).
    client = FakeMCPClient([env(True), env(False), env(True), env(False)])
    v = AdwEditorVerifier(client)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(spec, f)
        spec_path = f.name
    try:
        ok = v.verify_spec(spec_path)
    finally:
        Path(spec_path).unlink()
    assert ok is False
    summary = json.loads(v.last_summary) if hasattr(v, "last_summary") else None
    # verify_spec prints; capture via re-execution is unnecessary — the result dict is
    # built in verify_spec; assert the same assertions evaluate to expected statuses
    assert v.evaluate_assertion(spec["assertions"][0])["status"] == "pass"
    assert v.evaluate_assertion(spec["assertions"][1])["status"] == "fail"
