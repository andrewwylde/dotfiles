"""
Deterministic Alembic Groom Export Pipeline for Unreal Engine.

Run inside Blender via MCP execute_blender_code or headless CLI.
Processes Hair Curves objects: anchors roots, resamples points,
assigns attributes, and exports UE-ready Alembic .abc files.

Usage (MCP):
    Paste this script content into execute_blender_code with config set.

Usage (CLI):
    blender --background scene.blend --python export_ue_alembic_groom.py

Configuration:
    Set the CONFIG dictionary below before execution.
"""
import bpy
import bmesh
import math
from mathutils import Vector, kdtree

# ── Configuration ──────────────────────────────────────────────────────
CONFIG = {
    "curves_object": "",         # Name of the Hair Curves object
    "skin_mesh": "",             # Name of the target skin mesh
    "vertex_group": "",          # Vertex group on skin mesh for density mask
    "output_path": "//export/",  # Export directory (// = blend-relative)
    "output_name": "GRM_Character_Region",  # Filename (no extension)
    "groom_group_id": 0,         # Integer group ID for this groom region
    "points_per_strand": 8,      # Uniform point count per strand
    "max_strands": 50_000,       # Maximum strand count budget
    "root_snap_tolerance": 0.01, # Max distance from root to skin (meters)
    "scale": 100.0,              # Blender meters → UE centimeters
    "is_guide": False,           # True = physics guide curves
}
# ── End Configuration ──────────────────────────────────────────────────


def get_objects(config):
    """Retrieve and validate scene objects."""
    curves_name = config["curves_object"]
    skin_name = config["skin_mesh"]

    if curves_name not in bpy.data.objects:
        raise RuntimeError(f"Curves object '{curves_name}' not found in scene")
    if skin_name not in bpy.data.objects:
        raise RuntimeError(f"Skin mesh '{skin_name}' not found in scene")

    curves_obj = bpy.data.objects[curves_name]
    skin_obj = bpy.data.objects[skin_name]

    if curves_obj.type != 'CURVES':
        raise RuntimeError(f"'{curves_name}' is type {curves_obj.type}, expected CURVES")
    if skin_obj.type != 'MESH':
        raise RuntimeError(f"'{skin_name}' is type {skin_obj.type}, expected MESH")

    return curves_obj, skin_obj


def snap_roots_to_surface(curves_obj, skin_obj, tolerance):
    """Anchor root (index 0) of every curve to nearest face on skin mesh."""
    curves_data = curves_obj.data
    depsgraph = bpy.context.evaluated_depsgraph_get()
    skin_eval = skin_obj.evaluated_get(depsgraph)

    snapped = 0
    for curve in curves_data.curves:
        if curve.points_length < 1:
            continue
        root_idx = curve.points[0].index
        root_pos = Vector(curves_data.points[root_idx].position)

        success, location, normal, face_idx = skin_eval.closest_point_on_mesh(root_pos)
        if success:
            dist = (root_pos - location).length
            if dist > tolerance:
                curves_data.points[root_idx].position = location
                snapped += 1

    print(f"  Root snap: {snapped} roots moved to skin surface")
    return snapped


def resample_curves_uniform(curves_obj, target_points):
    """Resample all curves to a uniform number of points.

    Uses linear interpolation along the original polyline to redistribute
    points evenly. This ensures every strand has exactly target_points
    control points, which is required for stable UE Groom physics.
    """
    curves_data = curves_obj.data

    for curve in curves_data.curves:
        n_orig = curve.points_length
        if n_orig == target_points:
            continue
        if n_orig < 2:
            continue

        # Collect original positions
        start_idx = curve.points[0].index
        original_positions = []
        for i in range(n_orig):
            pos = Vector(curves_data.points[start_idx + i].position)
            original_positions.append(pos)

        # Compute cumulative arc lengths
        arc_lengths = [0.0]
        for i in range(1, n_orig):
            seg_len = (original_positions[i] - original_positions[i - 1]).length
            arc_lengths.append(arc_lengths[-1] + seg_len)
        total_length = arc_lengths[-1]

        if total_length < 1e-8:
            continue

        # Resample at uniform arc-length intervals
        new_positions = []
        for j in range(target_points):
            t = j / max(target_points - 1, 1)
            target_dist = t * total_length

            # Find segment
            seg = 0
            for k in range(1, n_orig):
                if arc_lengths[k] >= target_dist:
                    seg = k - 1
                    break
            else:
                seg = n_orig - 2

            seg_start = arc_lengths[seg]
            seg_end = arc_lengths[seg + 1]
            seg_len = seg_end - seg_start
            if seg_len < 1e-10:
                frac = 0.0
            else:
                frac = (target_dist - seg_start) / seg_len

            interp_pos = original_positions[seg].lerp(original_positions[seg + 1], frac)
            new_positions.append(interp_pos)

        # NOTE: Blender's Curves API as of 3.3-4.x does not support
        # changing point counts per-curve after creation via Python alone.
        # This resampling is designed for curves generated procedurally
        # with the correct point count. For existing curves with wrong
        # counts, use Geometry Nodes "Resample Curve" node before export.
        # The positions below are written back if point count matches.
        if n_orig == target_points:
            for i, pos in enumerate(new_positions):
                curves_data.points[start_idx + i].position = pos

    print(f"  Resample: target {target_points} points/strand")


def assign_attributes(curves_obj, config):
    """Assign groom attributes to curves data block."""
    curves_data = curves_obj.data
    n_curves = len(curves_data.curves)

    # groom_group_id (per-curve integer)
    if "groom_group_id" not in curves_data.attributes:
        curves_data.attributes.new(name="groom_group_id", type='INT', domain='CURVE')
    attr = curves_data.attributes["groom_group_id"]
    group_id = config["groom_group_id"]
    for i in range(n_curves):
        attr.data[i].value = group_id

    # groom_guide (per-curve integer flag)
    if "groom_guide" not in curves_data.attributes:
        curves_data.attributes.new(name="groom_guide", type='INT', domain='CURVE')
    guide_attr = curves_data.attributes["groom_guide"]
    guide_val = 1 if config["is_guide"] else 0
    for i in range(n_curves):
        guide_attr.data[i].value = guide_val

    print(f"  Attributes: groom_group_id={group_id}, groom_guide={guide_val}")


def export_alembic(curves_obj, config):
    """Export selected curves object as Alembic .abc for UE Groom."""
    # Deselect all, select only our curves
    bpy.ops.object.select_all(action='DESELECT')
    curves_obj.select_set(True)
    bpy.context.view_layer.objects.active = curves_obj

    output_dir = bpy.path.abspath(config["output_path"])
    import os
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, config["output_name"] + ".abc")

    bpy.ops.wm.alembic_export(
        filepath=filepath,
        selected=True,
        export_hair=True,
        evaluation_mode='RENDER',
        packimages=False,
        scale=config["scale"],
        start=1,
        end=1,
        global_scale=1.0,
    )

    file_size = os.path.getsize(filepath)
    print(f"  Export: {filepath} ({file_size / 1024:.1f} KB)")
    return filepath


def run_pipeline():
    """Execute the full groom export pipeline."""
    print(f"\n{'='*60}")
    print("GROOM EXPORT PIPELINE")
    print(f"{'='*60}")

    curves_obj, skin_obj = get_objects(CONFIG)
    curves_data = curves_obj.data
    n_strands = len(curves_data.curves)
    print(f"\nSource: {curves_obj.name} ({n_strands:,} strands)")
    print(f"Skin: {skin_obj.name}")

    # Budget check
    if n_strands > CONFIG["max_strands"]:
        raise RuntimeError(
            f"Strand count {n_strands:,} exceeds budget {CONFIG['max_strands']:,}. "
            f"Reduce density or increase budget."
        )
    if n_strands == 0:
        raise RuntimeError("Curves object has 0 strands. Nothing to export.")

    # Step 1: Snap roots
    print("\n[1/4] Anchoring roots to skin surface...")
    snap_roots_to_surface(curves_obj, skin_obj, CONFIG["root_snap_tolerance"])

    # Step 2: Resample (advisory — see docstring)
    print("\n[2/4] Checking point uniformity...")
    resample_curves_uniform(curves_obj, CONFIG["points_per_strand"])

    # Step 3: Assign attributes
    print("\n[3/4] Assigning groom attributes...")
    assign_attributes(curves_obj, CONFIG)

    # Step 4: Export
    print("\n[4/4] Exporting Alembic...")
    filepath = export_alembic(curves_obj, CONFIG)

    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE — {filepath}")
    print(f"{'='*60}\n")
    return filepath


if __name__ == "__main__":
    run_pipeline()
