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
|------|---------|----------|
| Groom Curves Object | `CRV_Hair_[Region]` | `CRV_Hair_Scalp`, `CRV_Hair_Beard` |
| Groom Collection | `COL_Groom_[Character]` | `COL_Groom_Hero` |
| Exported Alembic | `GRM_[Character]_[Region].abc` | `GRM_Hero_Scalp.abc` |
| UE Groom Asset | `GRM_[Character]_[Region]` | `GRM_Hero_Scalp` |
| UE Binding Asset | `GRM_[Character]_[Region]_Binding` | `GRM_Hero_Scalp_Binding` |
