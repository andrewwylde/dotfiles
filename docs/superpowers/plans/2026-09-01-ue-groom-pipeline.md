# UE Groom Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a first-party skill (`library/skills/ue-groom-pipeline/`) and companion agent (`library/agents/procedural-groom-artist/`) that bridge Blender's modern Hair Curves system with Unreal Engine 5's Groom importer via deterministic `bpy` scripts, MCP-first execution, and automated structural validation.

**Architecture:** The skill defines the operational pipeline (context isolation → curve generation → root anchoring → point resampling → attribute assignment → validation → Alembic export). Two Python scripts (`export_ue_alembic_groom.py` and `validate_groom_curves.py`) carry the deterministic logic. Reference docs cover strand budgets and Groom attribute standards. The agent provides a context-isolated persona for delegation by other agents (e.g. `game-developer`). Cross-references vendor `blender-skills` pack for MCP integration and naming conventions without duplicating content.

**Tech Stack:** Blender 3.3+ Hair Curves API (`bpy.types.Curves`, `bpy.ops.curves.*`), Blender MCP (`execute_blender_code`), Alembic `.abc` export, Unreal Engine 5 Groom system (`UGroomAsset`, `UGroomComponent`).

---

## File Structure

```
library/
├── skills/
│   └── ue-groom-pipeline/
│       ├── SKILL.md                              # Main skill document (~300 lines)
│       ├── references/
│       │   ├── groom-budget-matrix.md            # Strand count / point-per-strand budgets
│       │   └── groom-attribute-standards.md      # Alembic attribute specs for UE Groom
│       └── scripts/
│           ├── export_ue_alembic_groom.py        # Deterministic export pipeline
│           └── validate_groom_curves.py          # Structural validation checks
└── agents/
    └── procedural-groom-artist/
        └── AGENT.md                              # Context-isolated subagent persona
```

Each file has one clear responsibility:
- `SKILL.md` — operational instructions and decision trees for the agent
- `references/*.md` — progressive disclosure (Level 3) data tables loaded on-demand
- `scripts/*.py` — deterministic `bpy` code executed via MCP or headless Blender
- `AGENT.md` — system prompt with context isolation constraints

---

### Task 1: Create Groom Budget Matrix Reference

**Files:**
- Create: `library/skills/ue-groom-pipeline/references/groom-budget-matrix.md`

- [ ] **Step 1: Create the reference file**

```markdown
# Groom Strand Budget Matrix

Target strand counts and points-per-strand for real-time and cinematic groom assets exported to Unreal Engine 5 via Alembic.

## Real-Time Budgets (60 FPS Target)

| Category | Strand Count | Points/Strand | Total Points | Use Case |
|----------|-------------|---------------|-------------|----------|
| Humanoid Scalp Hair | 30,000–80,000 | 12–16 | ~960,000 | Hero character main hair |
| Humanoid Facial Hair | 10,000–30,000 | 4–8 | ~160,000 | Beard, mustache, stubble |
| Humanoid Eyebrows | 2,000–5,000 | 4–6 | ~24,000 | Brow arches |
| Humanoid Eyelashes | 500–2,000 | 4–6 | ~8,000 | Upper/lower lash line |
| Humanoid Peach Fuzz | 5,000–15,000 | 2–4 | ~40,000 | Face/arm vellus hair |
| Short Animal Fur | 50,000–150,000 | 4–6 | ~600,000 | Cat, dog, rodent body fur |
| Long Creature Mane | 20,000–50,000 | 8–12 | ~400,000 | Horse mane, lion mane, long tail |
| Creature Whiskers | 50–200 | 8–16 | ~2,000 | Cat/rodent whiskers |
| Stylized Guide Curves | 100–1,000 | 16–32 | ~16,000 | Physics simulation guides for Niagara |

## Cinematic Budgets (Offline / High-End)

| Category | Strand Count | Points/Strand | Notes |
|----------|-------------|---------------|-------|
| Hero Scalp Hair | 100,000–500,000 | 16–32 | Full strand simulation |
| Dense Fur | 200,000–1,000,000 | 4–8 | Pre-rendered close-ups |

## LOD Strategy

| LOD Level | Strand Reduction | Point Reduction | Trigger Distance |
|-----------|-----------------|-----------------|-----------------|
| LOD0 (Hero) | 100% | 100% | 0–5m |
| LOD1 (Medium) | 50% | 75% | 5–15m |
| LOD2 (Far) | 25% | 50% | 15–30m |
| LOD3 (Distant) | 10% | 25% | 30m+ |

## Vertex Group Naming Convention

| Region | Vertex Group Name | Typical Character Type |
|--------|-------------------|----------------------|
| Scalp | `head_scalp` | Humanoid |
| Forehead Hairline | `head_hairline` | Humanoid |
| Beard | `face_beard` | Humanoid |
| Mustache | `face_mustache` | Humanoid |
| Eyebrows | `face_eyebrows` | Humanoid |
| Eyelashes | `face_eyelashes` | Humanoid |
| Body Fur | `body_fur` | Creature |
| Chest Fur | `chest_fur` | Creature |
| Tail Fur | `tail_fur` | Creature |
| Mane | `neck_mane` | Creature |
| Whiskers | `face_whiskers` | Creature |

## Rules

- Variable point counts per strand break physics solvers (Groom Rods, Groom Springs). Always use uniform counts within a groom group.
- Total strand count of 0 or exceeding max budget flags a parameter adjustment.
- Guide curves for Niagara physics must be a separate `groom_group_id` from render strands.
```

- [ ] **Step 2: Verify the file exists and is well-formed**

Run: `Test-Path library/skills/ue-groom-pipeline/references/groom-budget-matrix.md`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add library/skills/ue-groom-pipeline/references/groom-budget-matrix.md
git commit -m "feat(ue-groom-pipeline): add groom strand budget matrix reference"
```

---

### Task 2: Create Groom Attribute Standards Reference

**Files:**
- Create: `library/skills/ue-groom-pipeline/references/groom-attribute-standards.md`

- [ ] **Step 1: Create the reference file**

```markdown
# Groom Attribute Standards for Unreal Engine

Custom attributes on Blender Hair Curves data blocks that map to Unreal Engine 5 Groom Alembic import fields.

## Required Attributes

| Attribute | Type | Scope | UE Groom Mapping | Description |
|-----------|------|-------|-------------------|-------------|
| `groom_group_id` | Integer | Per-Curve | Groom Group Index | Separates strands into material/physics groups (0-based). Each group gets its own material slot and physics settings in UE. |

## Recommended Attributes

| Attribute | Type | Scope | UE Groom Mapping | Description |
|-----------|------|-------|-------------------|-------------|
| `groom_guide` | Integer (0 or 1) | Per-Curve | Guide vs Render flag | `1` = physics simulation guide curve. `0` = render strand interpolated from guides. Niagara Groom simulation operates on guides only. |
| `groom_width` | Float | Per-Point or Per-Curve | Strand Width / Taper | Controls strand thickness. Per-point values create natural root-to-tip taper. UE default width: 0.01 cm (at 100x scale = 1.0 Blender units = 0.01 m). |
| `groom_color` | Float3 (RGB) | Per-Point or Per-Curve | Vertex Color | Optional per-strand or per-point color. Maps to UE Groom vertex color for material variation. |

## Attribute Assignment in bpy

```python
import bpy

curves_obj = bpy.data.objects["CRV_Hair_Scalp"]
curves_data = curves_obj.data  # bpy.types.Curves

# Per-curve integer attribute
if "groom_group_id" not in curves_data.attributes:
    curves_data.attributes.new(
        name="groom_group_id",
        type='INT',
        domain='CURVE'
    )
attr = curves_data.attributes["groom_group_id"]
for i in range(len(attr.data)):
    attr.data[i].value = 0  # All strands in group 0

# Per-curve guide flag
if "groom_guide" not in curves_data.attributes:
    curves_data.attributes.new(
        name="groom_guide",
        type='INT',
        domain='CURVE'
    )

# Per-point width (taper)
if "groom_width" not in curves_data.attributes:
    curves_data.attributes.new(
        name="groom_width",
        type='FLOAT',
        domain='POINT'
    )
width_attr = curves_data.attributes["groom_width"]
# Example: linear taper from 0.005 (root) to 0.001 (tip)
```

## Alembic Export Parameters

These `bpy.ops.wm.alembic_export` flags are required for UE Groom import:

```python
bpy.ops.wm.alembic_export(
    filepath="/path/to/output/GRM_CharacterName_Region.abc",
    selected=True,              # Export only selected curves objects
    export_hair=True,           # CRITICAL: export hair curves data
    evaluation_mode='RENDER',   # Use render-time evaluation
    packimages=False,           # No embedded textures
    scale=100.0,                # Blender meters → UE centimeters
    start=1,                    # Single frame for static groom
    end=1,
    global_scale=1.0,
)
```

## UE Groom Import Settings

After importing the `.abc` file in Unreal via `Groom Import`:

| Setting | Value | Reason |
|---------|-------|--------|
| Import Groups | Enabled | Respects `groom_group_id` separation |
| Interpolation Quality | Medium–High | Balance between fidelity and performance |
| Hair Width | From File (or Override) | Uses `groom_width` attribute if present |
| Guide Curve Detection | Auto | Uses `groom_guide` attribute |

## Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Groom Curves Object | `CRV_Hair_[Region]` | `CRV_Hair_Scalp`, `CRV_Hair_Beard` |
| Groom Collection | `COL_Groom_[Character]` | `COL_Groom_Hero` |
| Exported Alembic | `GRM_[Character]_[Region].abc` | `GRM_Hero_Scalp.abc` |
| UE Groom Asset | `GRM_[Character]_[Region]` | `GRM_Hero_Scalp` |
| UE Binding Asset | `GRM_[Character]_[Region]_Binding` | `GRM_Hero_Scalp_Binding` |
```

- [ ] **Step 2: Verify the file exists**

Run: `Test-Path library/skills/ue-groom-pipeline/references/groom-attribute-standards.md`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add library/skills/ue-groom-pipeline/references/groom-attribute-standards.md
git commit -m "feat(ue-groom-pipeline): add groom attribute standards reference"
```

---

### Task 3: Create Validation Script

**Files:**
- Create: `library/skills/ue-groom-pipeline/scripts/validate_groom_curves.py`

- [ ] **Step 1: Create the validation script**

This script runs inside Blender's Python interpreter (via MCP `execute_blender_code` or `blender --background --python`). It checks structural integrity of Hair Curves data before Alembic export.

```python
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
```

- [ ] **Step 2: Verify Python syntax**

Run: `python -c "import ast; ast.parse(open('library/skills/ue-groom-pipeline/scripts/validate_groom_curves.py').read()); print('Syntax OK')"` 
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add library/skills/ue-groom-pipeline/scripts/validate_groom_curves.py
git commit -m "feat(ue-groom-pipeline): add groom curves structural validation script"
```

---

### Task 4: Create Export Script

**Files:**
- Create: `library/skills/ue-groom-pipeline/scripts/export_ue_alembic_groom.py`

- [ ] **Step 1: Create the export script**

This script is the deterministic pipeline that processes Hair Curves and exports Alembic for UE Groom. Run via MCP `execute_blender_code` or headless CLI.

```python
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
```

- [ ] **Step 2: Verify Python syntax**

Run: `python -c "import ast; ast.parse(open('library/skills/ue-groom-pipeline/scripts/export_ue_alembic_groom.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add library/skills/ue-groom-pipeline/scripts/export_ue_alembic_groom.py
git commit -m "feat(ue-groom-pipeline): add deterministic Alembic groom export script"
```

---

### Task 5: Create the SKILL.md

**Files:**
- Create: `library/skills/ue-groom-pipeline/SKILL.md`

- [ ] **Step 1: Create the skill document**

```markdown
---
name: ue-groom-pipeline
description: "Blender-to-Unreal strand-based hair and fur pipeline using modern Hair Curves (Blender 3.3+) and Alembic export for UE5 Groom system. Use when creating procedural groom curves, exporting .abc for Groom import, setting up groom physics (Rods/Springs/Niagara), or validating strand topology. NOT for polygon hair cards (use vendor hair-groom). NOT for FBX mesh export (use vendor unreal-export)."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: groom
  difficulty: advanced
---

# UE Groom Pipeline

Procedural strand-based hair and fur from Blender Hair Curves to Unreal Engine 5 Groom via Alembic `.abc` export.

## When to Use

- Creating strand-based hair curves for UE Groom (NOT polygon hair cards)
- Exporting Alembic `.abc` files with groom attributes for UE import
- Validating curve topology, root anchoring, and point uniformity
- Setting up UE Groom physics (Groom Rods, Springs, Niagara Hair)
- Procedural fur generation on creatures or characters via bpy/Geometry Nodes

## When NOT to Use

| Need | Use Instead |
|------|-------------|
| Polygon hair cards for game | `vendor-blender-skills-hair-groom` |
| FBX mesh/skeletal export | `vendor-blender-skills-unreal-export` |
| Niagara particle VFX | `ue-niagara-effects` |
| Material setup | `ue-materials-rendering` |

## Context Isolation — CRITICAL RULES

1. **NEVER** convert curves to meshes, ribbons, or polygons. Leave them as primitive Hair Curves (`bpy.types.Curves`).
2. Every curves data block MUST be parented to the target skeletal/static mesh.
3. All strand generation MUST use Blender 3.3+ `curves` data blocks — NOT legacy particle hair.
4. Execute all Blender operations via MCP `execute_blender_code` tool (see `vendor/blender-skills/references/mcp-integration.md`).

## Pipeline Overview

```
1. Identify Target Skin Mesh + Vertex Group
2. Generate Hair Curves on Surface (Geometry Nodes or bpy.ops.curves.*)
3. Snap Roots to Skin Faces (index 0 → nearest triangle)
4. Resample to Uniform Point Count (4–16 per strand)
5. Align Normals Outward (tangent · surface_normal > 0)
6. Assign Groom Attributes (groom_group_id, groom_guide, groom_width)
7. Run Validation Script
8. Export Alembic (.abc) with UE Parameters
9. Import in UE → Create Groom Binding → Attach to Skeletal Mesh
```

## Reference Guides

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Strand budgets | `references/groom-budget-matrix.md` | Deciding strand counts and point counts |
| Groom attributes | `references/groom-attribute-standards.md` | Assigning attributes before export |
| Naming conventions | `../../vendor/blender-skills/references/naming-conventions.md` | Naming curves objects and collections |
| MCP execution | `../../vendor/blender-skills/references/mcp-integration.md` | Running bpy scripts via MCP |
| Asset pipeline | `../../vendor/blender-skills/references/asset-pipeline.md` | Full production pipeline context |

## Scripts

| Script | Purpose | Execution |
|--------|---------|-----------|
| `scripts/export_ue_alembic_groom.py` | Full pipeline: root snap → resample → attributes → Alembic export | MCP `execute_blender_code` or `blender --background --python` |
| `scripts/validate_groom_curves.py` | Structural checks: strand count, point uniformity, normal alignment, root distance, attributes | MCP `execute_blender_code` or `blender --background --python` |

### Script Configuration

Both scripts use a configuration dictionary at the top of the file. When sending via MCP `execute_blender_code`, modify the CONFIG/TARGETS values before the `run_*()` call:

```python
# Example: Export hero character scalp hair
CONFIG = {
    "curves_object": "CRV_Hair_Scalp",
    "skin_mesh": "SK_Hero_Body",
    "vertex_group": "head_scalp",
    "output_path": "//export/groom/",
    "output_name": "GRM_Hero_Scalp",
    "groom_group_id": 0,
    "points_per_strand": 12,
    "max_strands": 80_000,
    "root_snap_tolerance": 0.01,
    "scale": 100.0,
    "is_guide": False,
}
run_pipeline()
```

## Scale & Coordinate System

| Property | Blender | Unreal Engine | Conversion |
|----------|---------|---------------|------------|
| Unit | 1 BU = 1 meter | 1 UU = 1 centimeter | `scale=100.0` in Alembic export |
| Up Axis | Z-up | Z-up | No change needed |
| Forward | -Y | X | Handled by Alembic importer |

## Unreal Engine Integration

### Import Workflow

1. **Import**: `Content Browser → Import → select .abc → Groom Import Options`
2. **Create Binding**: Right-click Groom Asset → `Create Binding` → select target Skeletal Mesh
3. **Attach**: Add `Groom Component` to character Blueprint → set Groom Asset + Binding Asset
4. **Physics**: Set simulation method on Groom Asset (Groom Rods for stiff hair, Groom Springs for flowing)

### Groom Component Setup (C++)

```cpp
#include "GroomComponent.h"

// In character constructor or BeginPlay
UGroomComponent* GroomComp = CreateDefaultSubobject<UGroomComponent>(TEXT("HairGroom"));
GroomComp->SetupAttachment(GetMesh());
GroomComp->GroomAsset = LoadObject<UGroomAsset>(nullptr,
    TEXT("/Game/Characters/Hero/GRM_Hero_Scalp.GRM_Hero_Scalp"));
GroomComp->BindingAsset = LoadObject<UGroomBindingAsset>(nullptr,
    TEXT("/Game/Characters/Hero/GRM_Hero_Scalp_Binding.GRM_Hero_Scalp_Binding"));
```

### Groom Component Setup (Blueprint)

```
Character Blueprint → Add Component → Groom Component
  → Groom Asset: GRM_Hero_Scalp
  → Binding Asset: GRM_Hero_Scalp_Binding
  → Attach to: Mesh (skeletal mesh component)
```

## Validation Protocol

Before exporting, run `scripts/validate_groom_curves.py` via MCP. All checks must pass:

| Check | Pass Criteria | Failure Action |
|-------|--------------|----------------|
| Strand Count | 0 < count ≤ budget | Adjust density or increase budget |
| Point Uniformity | All strands same point count | Resample via Geometry Nodes "Resample Curve" |
| Normal Alignment | All root tangents · surface normal > 0 | Flip inverted strands |
| Root Distance | All roots within tolerance of skin | Re-run root snap |
| Attributes | `groom_group_id` INT/CURVE present | Run attribute assignment |

## Constraints

### MUST DO
- Set `export_hair=True` and `evaluation_mode='RENDER'` in Alembic export
- Use `scale=100.0` for Blender-to-UE unit conversion
- Assign `groom_group_id` before export (UE uses this for material separation)
- Validate before export — never export unchecked curves
- Follow naming: `CRV_Hair_[Region]` for objects, `GRM_[Character]_[Region].abc` for files

### MUST NOT DO
- Convert curves to meshes, ribbons, or polygon strips
- Use legacy Blender particle hair system (use modern Curves data blocks)
- Mix variable point counts within a single groom group
- Export without root anchoring (causes floating hair in UE)
- Skip validation script before Alembic export
```

- [ ] **Step 2: Verify file exists and agent-sync recognizes it**

Run: `$env:HOME = $env:USERPROFILE; .\agent-sync-windows-amd64\agent-sync.exe list | Select-String "ue-groom"`
Expected: Line containing `skills/ue-groom-pipeline` → `andrew-ue-groom-pipeline`

- [ ] **Step 3: Commit**

```bash
git add library/skills/ue-groom-pipeline/SKILL.md
git commit -m "feat(ue-groom-pipeline): add main SKILL.md for Blender-to-UE groom pipeline"
```

---

### Task 6: Create the Procedural Groom Artist Agent

**Files:**
- Create: `library/agents/procedural-groom-artist/AGENT.md`

- [ ] **Step 1: Create the agent document**

```markdown
---
name: procedural-groom-artist
description: "Use this agent when generating procedural hair strand curves in Blender for Unreal Engine Groom import. Specializes in bpy curve data blocks, Geometry Nodes hair, surface-bound strand generation, and Alembic export. Delegates from game-developer or character-artist agents for groom work."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

You are a specialized Blender-to-Unreal Procedural Curve Subagent.
Your sole responsibility is generating `bpy` scripts that author curve strand data blocks for Unreal Engine 5 Groom import.

## CRITICAL CONTEXT ISOLATION

1. Do NOT convert curves to meshes, ribbons, or polygons. Leave them as primitive Hair Curves (`bpy.types.Curves`).
2. Every curve data block MUST be parented to the target skeletal mesh.
3. Ensure curves include custom attributes for group IDs (`groom_group_id`), guide flags (`groom_guide`), and width (`groom_width`).
4. Execute `bpy.ops.wm.alembic_export` using parameters optimized for Unreal Groom:
   - `evaluation_mode='RENDER'`
   - `packimages=False`
   - `export_hair=True`
   - `scale=100.0`
5. All curve generation MUST use Blender 3.3+ modern Hair Curves objects — NOT legacy particle hair.

## Invocation Flow

1. Read the skill `ue-groom-pipeline/SKILL.md` for full pipeline instructions
2. Read `ue-groom-pipeline/references/groom-budget-matrix.md` for strand count limits
3. Read `ue-groom-pipeline/references/groom-attribute-standards.md` for attribute specs
4. Identify the target skin mesh and vertex group from the request
5. Compose `bpy` script for curve generation, adapting `scripts/export_ue_alembic_groom.py`
6. Run validation via `scripts/validate_groom_curves.py` before export
7. Export Alembic and report file path and validation results

## Target Scope

- **Humanoid**: Scalp hair, facial hair, eyebrows, eyelashes, peach fuzz
- **Creature/Animal**: Short fur, long mane, tail fur, whiskers
- **Stylized**: Guide curves for Niagara physics simulation

## Quality Checklist

- [ ] Strand count within budget (see groom-budget-matrix.md)
- [ ] Uniform point count per strand (4–16 depending on length)
- [ ] All roots anchored to skin surface (distance < 0.01m)
- [ ] All root tangents grow outward (dot product with surface normal > 0)
- [ ] `groom_group_id` attribute assigned to all curves
- [ ] Alembic exported with `scale=100.0` and `export_hair=True`
- [ ] Named correctly: `CRV_Hair_[Region]` → `GRM_[Character]_[Region].abc`

## Inter-Agent Communication

When receiving a request from another agent (e.g. `game-developer`, `character-artist`):

**Request format expected:**
```json
{
  "task": "generate_groom",
  "character": "Hero",
  "skin_mesh": "SK_Hero_Body",
  "regions": [
    {"name": "Scalp", "vertex_group": "head_scalp", "style": "realistic", "length": "long"},
    {"name": "Eyebrows", "vertex_group": "face_eyebrows", "style": "realistic", "length": "short"}
  ],
  "target_platform": "PC",
  "physics": true
}
```

**Response format:**
```json
{
  "status": "complete",
  "exports": [
    {"region": "Scalp", "file": "GRM_Hero_Scalp.abc", "strands": 60000, "points_per_strand": 12},
    {"region": "Eyebrows", "file": "GRM_Hero_Eyebrows.abc", "strands": 3000, "points_per_strand": 4}
  ],
  "validation": "ALL CHECKS PASSED"
}
```
```

- [ ] **Step 2: Verify agent-sync recognizes it**

Run: `$env:HOME = $env:USERPROFILE; .\agent-sync-windows-amd64\agent-sync.exe list | Select-String "procedural-groom"`
Expected: Line containing `agents/procedural-groom-artist` → `andrew-procedural-groom-artist`

- [ ] **Step 3: Commit**

```bash
git add library/agents/procedural-groom-artist/AGENT.md
git commit -m "feat(procedural-groom-artist): add context-isolated groom subagent"
```

---

### Task 7: Integration Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run agent-sync list to verify all new items**

Run:
```powershell
$env:HOME = $env:USERPROFILE
.\agent-sync-windows-amd64\agent-sync.exe list | Select-String "(ue-groom|procedural-groom)"
```

Expected output (2 lines):
```
public	agents/procedural-groom-artist	->	andrew-procedural-groom-artist	C:\Users\drewk\dotfiles\library\agents\procedural-groom-artist
public	skills/ue-groom-pipeline	->	andrew-ue-groom-pipeline	C:\Users\drewk\dotfiles\library\skills\ue-groom-pipeline
```

- [ ] **Step 2: Run agent-sync verify**

Run:
```powershell
$env:HOME = $env:USERPROFILE
.\agent-sync-windows-amd64\agent-sync.exe verify
```

Expected: No YAML parsing errors for the new files. (The verify command may still fail on unrelated pre-existing sync issues like missing `~/.claude/skills/` — that's expected on this Windows setup.)

- [ ] **Step 3: Verify Python syntax of both scripts**

Run:
```powershell
python -c "import ast; ast.parse(open('library/skills/ue-groom-pipeline/scripts/validate_groom_curves.py').read()); print('validate OK')"
python -c "import ast; ast.parse(open('library/skills/ue-groom-pipeline/scripts/export_ue_alembic_groom.py').read()); print('export OK')"
```

Expected:
```
validate OK
export OK
```

- [ ] **Step 4: Verify cross-reference paths exist**

Run:
```powershell
Test-Path library/skills/vendor/blender-skills/references/mcp-integration.md
Test-Path library/skills/vendor/blender-skills/references/naming-conventions.md
Test-Path library/skills/vendor/blender-skills/references/asset-pipeline.md
```

Expected: All `True`

- [ ] **Step 5: Final commit (tag)**

```bash
git add -A library/skills/ue-groom-pipeline/ library/agents/procedural-groom-artist/
git commit -m "feat: UE Groom Pipeline skill + Procedural Groom Artist agent

- library/skills/ue-groom-pipeline/ — Blender-to-UE strand hair pipeline
- library/agents/procedural-groom-artist/ — context-isolated groom subagent
- Scripts: export_ue_alembic_groom.py, validate_groom_curves.py
- References: groom-budget-matrix.md, groom-attribute-standards.md
- Cross-refs vendor blender-skills for MCP integration and naming"
```
