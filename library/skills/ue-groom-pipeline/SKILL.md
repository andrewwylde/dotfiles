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
