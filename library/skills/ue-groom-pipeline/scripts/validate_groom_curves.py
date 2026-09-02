"""
Groom Curves Structural Validation for Unreal Engine Export.

Run inside Blender via MCP execute_blender_code or headless CLI.
Validates Hair Curves objects against UE Groom import requirements.

Usage (MCP):
    Paste this script content into execute_blender_code with TARGETS set.

Usage (CLI):
    blender --background scene.blend --python validate_groom_curves.py

Configuration:
    Set TARGETS below to the names of Hair Curves objects to validate.
"""
import bpy
import math
from mathutils import Vector

# ── Configuration ──────────────────────────────────────────────────────
TARGETS = []  # Empty = validate all Hair Curves objects in scene
MAX_STRAND_COUNT = 150_000
EXPECTED_POINTS_PER_STRAND = None  # None = just check uniformity
ROOT_DISTANCE_TOLERANCE = 0.01  # meters (Blender units)
SKIN_MESH_NAME = ""  # Name of the target skin mesh for root anchoring check
# ── End Configuration ──────────────────────────────────────────────────


class GroomValidationResult:
    """Collects pass/fail results for a single curves object."""

    def __init__(self, obj_name):
        self.obj_name = obj_name
        self.passed = True
        self.checks = []

    def check(self, name, passed, detail=""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.passed = False

    def report(self):
        lines = [f"\n{'PASS' if self.passed else 'FAIL'} — {self.obj_name}"]
        for c in self.checks:
            icon = "✓" if c["passed"] else "✗"
            lines.append(f"  {icon} {c['name']}: {c['detail']}")
        return "\n".join(lines)


def get_curve_objects(targets):
    """Return Hair Curves objects to validate."""
    if targets:
        return [bpy.data.objects[n] for n in targets if n in bpy.data.objects]
    return [o for o in bpy.data.objects if o.type == 'CURVES']


def validate_strand_count(curves_data, result, max_count):
    """Check total strand count is within budget."""
    count = len(curves_data.curves)
    if count == 0:
        result.check("Strand Count", False, f"0 strands — empty curves data block")
    elif count > max_count:
        result.check("Strand Count", False,
                      f"{count:,} strands exceeds budget of {max_count:,}")
    else:
        result.check("Strand Count", True, f"{count:,} strands (budget: {max_count:,})")


def validate_point_uniformity(curves_data, result, expected=None):
    """Check all strands have the same number of points."""
    if len(curves_data.curves) == 0:
        result.check("Point Uniformity", False, "No curves to check")
        return

    counts = set()
    for curve in curves_data.curves:
        counts.add(curve.points_length)

    if len(counts) == 1:
        actual = counts.pop()
        if expected is not None and actual != expected:
            result.check("Point Uniformity", False,
                          f"Uniform at {actual} pts but expected {expected}")
        else:
            result.check("Point Uniformity", True,
                          f"All strands have {actual} points")
    else:
        sorted_counts = sorted(counts)
        result.check("Point Uniformity", False,
                      f"Variable point counts: {sorted_counts[:5]}{'...' if len(sorted_counts) > 5 else ''}")


def validate_normal_alignment(curves_data, result, skin_obj=None):
    """Check curve root tangents point outward from surface normals."""
    if len(curves_data.curves) == 0 or skin_obj is None:
        result.check("Normal Alignment", True, "Skipped (no skin mesh specified)")
        return

    inverted_count = 0
    checked = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    skin_eval = skin_obj.evaluated_get(depsgraph)

    for curve in curves_data.curves:
        if curve.points_length < 2:
            continue
        checked += 1
        root_pos = Vector(curves_data.points[curve.points[0].index].position)
        next_pos = Vector(curves_data.points[curve.points[0].index + 1].position)
        tangent = (next_pos - root_pos).normalized()

        # Find closest point on skin mesh
        success, location, normal, _ = skin_eval.closest_point_on_mesh(root_pos)
        if success:
            dot = tangent.dot(normal)
            if dot < 0:  # Growing inward
                inverted_count += 1

    if inverted_count > 0:
        pct = (inverted_count / checked) * 100
        result.check("Normal Alignment", False,
                      f"{inverted_count}/{checked} strands ({pct:.1f}%) grow inward")
    else:
        result.check("Normal Alignment", True,
                      f"All {checked} strands grow outward from surface")


def validate_root_distance(curves_data, result, skin_obj=None, tolerance=0.01):
    """Check root points are within tolerance of skin mesh surface."""
    if len(curves_data.curves) == 0 or skin_obj is None:
        result.check("Root Distance", True, "Skipped (no skin mesh specified)")
        return

    floating_count = 0
    max_dist = 0.0
    checked = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    skin_eval = skin_obj.evaluated_get(depsgraph)

    for curve in curves_data.curves:
        if curve.points_length < 1:
            continue
        checked += 1
        root_pos = Vector(curves_data.points[curve.points[0].index].position)
        success, location, _, _ = skin_eval.closest_point_on_mesh(root_pos)
        if success:
            dist = (root_pos - location).length
            max_dist = max(max_dist, dist)
            if dist > tolerance:
                floating_count += 1

    if floating_count > 0:
        pct = (floating_count / checked) * 100
        result.check("Root Distance", False,
                      f"{floating_count}/{checked} roots ({pct:.1f}%) exceed "
                      f"{tolerance}m tolerance (max: {max_dist:.4f}m)")
    else:
        result.check("Root Distance", True,
                      f"All {checked} roots within {tolerance}m of skin (max: {max_dist:.4f}m)")


def validate_attributes(curves_data, result):
    """Check required groom attributes exist with correct types."""
    attr_names = {a.name: a for a in curves_data.attributes}

    # groom_group_id (required)
    if "groom_group_id" in attr_names:
        a = attr_names["groom_group_id"]
        if a.data_type == 'INT' and a.domain == 'CURVE':
            result.check("Attribute: groom_group_id", True, "INT per-curve ✓")
        else:
            result.check("Attribute: groom_group_id", False,
                          f"Wrong type/domain: {a.data_type}/{a.domain} (need INT/CURVE)")
    else:
        result.check("Attribute: groom_group_id", False, "Missing (required)")

    # groom_width (recommended)
    if "groom_width" in attr_names:
        a = attr_names["groom_width"]
        if a.data_type == 'FLOAT':
            result.check("Attribute: groom_width", True,
                          f"FLOAT per-{a.domain.lower()} ✓")
        else:
            result.check("Attribute: groom_width", False,
                          f"Wrong type: {a.data_type} (need FLOAT)")
    else:
        result.check("Attribute: groom_width", True, "Not present (optional)")


def run_validation():
    """Main entry point."""
    curve_objects = get_curve_objects(TARGETS)
    if not curve_objects:
        print("FAIL — No Hair Curves objects found in scene")
        return False

    skin_obj = None
    if SKIN_MESH_NAME and SKIN_MESH_NAME in bpy.data.objects:
        skin_obj = bpy.data.objects[SKIN_MESH_NAME]

    all_passed = True
    print(f"\n{'='*60}")
    print("GROOM VALIDATION REPORT")
    print(f"{'='*60}")

    for obj in curve_objects:
        curves_data = obj.data
        result = GroomValidationResult(obj.name)

        validate_strand_count(curves_data, result, MAX_STRAND_COUNT)
        validate_point_uniformity(curves_data, result, EXPECTED_POINTS_PER_STRAND)
        validate_normal_alignment(curves_data, result, skin_obj)
        validate_root_distance(curves_data, result, skin_obj, ROOT_DISTANCE_TOLERANCE)
        validate_attributes(curves_data, result)

        print(result.report())
        if not result.passed:
            all_passed = False

    print(f"\n{'='*60}")
    print(f"OVERALL: {'ALL CHECKS PASSED' if all_passed else 'VALIDATION FAILED'}")
    print(f"{'='*60}\n")
    return all_passed


if __name__ == "__main__":
    run_validation()
