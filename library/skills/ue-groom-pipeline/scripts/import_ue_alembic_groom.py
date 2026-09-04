"""
Deterministic Alembic Groom Ingestion and Binding Pipeline for Unreal Engine.

Run inside Unreal Engine via Python MCP, Editor Python Console, or commandlet.
Automates:
1. Ingestion of Alembic (.abc) grooms via unreal.AssetImportTask and unreal.GroomImportOptions.
2. Programmatic validation: asserts hair group count > 0 and bounding box is non-degenerate.
3. Automated UGroomBindingAsset generation via unreal.GroomBlueprintLibrary when targeting SkeletalMesh.
4. Deterministic component assignment and property assertions via set_editor_property/get_editor_property.
5. Viewport capture staging: copies screenshots to conversation artifact directories with forward-slash paths.

Usage:
    Configure CONFIG below and execute within Unreal Python environment.
"""

import os
import shutil
import unreal

# ── Configuration ──────────────────────────────────────────────────────
CONFIG = {
    "alembic_filepath": "",               # Absolute path to source .abc file
    "destination_path": "/Game/Grooms",  # UE package destination path
    "destination_name": "",               # Destination asset name (without extension)
    "conversion_scale": (1.0, 1.0, 1.0),  # Scale (1.0 assumes Blender exported at scale=100.0)
    "conversion_rotation": (0.0, 0.0, 0.0), # Pitch, Yaw, Roll
    "target_actor": None,                 # Existing AActor reference or None
    "target_mesh_component": None,        # USceneComponent or USkeletalMeshComponent to attach to
    "skeletal_mesh_path": "",             # Optional: /Game/Path/To/SK_Mesh for auto GroomBindingAsset
    "artifact_output_dir": "",            # Optional: <appDataDir>/brain/<conversation-id> for preview copy
    "save_assets": True,                  # Save .uasset files immediately upon creation
}
# ── End Configuration ──────────────────────────────────────────────────


def import_alembic_groom(filepath, dest_path, dest_name, scale=(1.0, 1.0, 1.0), rotation=(0.0, 0.0, 0.0)):
    """Import Alembic file as UGroomAsset with deterministic conversion options."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Alembic file not found: {filepath}")

    print(f"\n[1/4] Importing Alembic groom: {filepath} -> {dest_path}/{dest_name}")

    task = unreal.AssetImportTask()
    task.filename = filepath.replace("\\", "/")
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.replace_existing = True
    task.automated = True
    task.save = True

    options = unreal.GroomImportOptions()
    conversion = unreal.GroomConversionSettings()
    conversion.scale = unreal.Vector(scale[0], scale[1], scale[2])
    conversion.rotation = unreal.Rotator(rotation[0], rotation[1], rotation[2])
    options.conversion_settings = conversion
    task.options = options

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    asset_uri = f"{dest_path}/{dest_name}"
    groom_asset = unreal.load_asset(asset_uri)
    if not groom_asset:
        raise RuntimeError(f"GroomAsset import failed: could not load asset at {asset_uri}")

    return groom_asset


def validate_groom_geometry(groom_asset):
    """Deterministic geometric gate: verify strand groups and bounding volume."""
    print("\n[2/4] Executing deterministic geometric validation gate...")

    # Check 1: Hair Groups count
    num_groups = groom_asset.get_num_hair_groups()
    print(f"  • Hair group count: {num_groups}")
    if num_groups <= 0:
        raise ValueError(
            f"Validation Failed: GroomAsset '{groom_asset.get_name()}' contains 0 hair groups! "
            "The Alembic file was empty or lacked hair curve geometry."
        )

    # Check 2: Bounding Box volume / radius
    bounds = groom_asset.get_bounds()
    extent = bounds.box_extent
    radius = bounds.sphere_radius
    print(f"  • Bounds extent: ({extent.x:.2f}, {extent.y:.2f}, {extent.z:.2f}), Sphere radius: {radius:.2f}")

    if radius <= 0.1 or (extent.x < 0.1 and extent.y < 0.1 and extent.z < 0.1):
        raise ValueError(
            f"Validation Failed: GroomAsset '{groom_asset.get_name()}' has degenerate bounds (radius={radius:.4f}). "
            "Strands collapsed to origin or exported with zero length."
        )

    print("  ✓ Geometric assertion passed: Valid hair geometry confirmed.")
    return True


def create_and_bind_groom_binding(groom_asset, skel_mesh_path, dest_path, dest_name):
    """Generate and save UGroomBindingAsset for skeletal mesh deformation."""
    print(f"\n[3/4] Generating UGroomBindingAsset for skeletal mesh: {skel_mesh_path}...")
    skel_mesh = unreal.load_asset(skel_mesh_path)
    if not skel_mesh:
        raise FileNotFoundError(f"Target SkeletalMesh not found: {skel_mesh_path}")

    binding_name = f"{dest_name}_Binding"
    binding_uri = f"{dest_path}/{binding_name}"

    # Attempt to load existing or create new binding asset
    binding_asset = unreal.load_asset(binding_uri)
    if not binding_asset:
        binding_asset = unreal.GroomBlueprintLibrary.create_groom_binding_asset(
            groom_asset,
            skel_mesh,
            num_interpolation_points=100,
            matching_section=0
        )
        if not binding_asset:
            raise RuntimeError(f"Failed to generate GroomBindingAsset for {groom_asset.get_name()} on {skel_mesh_path}")

        # Rename and save package
        unreal.EditorAssetLibrary.rename_asset(binding_asset.get_path_name(), binding_uri)
        unreal.EditorAssetLibrary.save_loaded_asset(binding_asset)

    print(f"  ✓ UGroomBindingAsset ready: {binding_uri}")
    return binding_asset


def setup_groom_component(actor, groom_asset, parent_comp=None, binding_asset=None):
    """Attach and verify GroomComponent on an actor using editor properties."""
    print("\n[4/4] Setting up and asserting GroomComponent...")

    # Find or add GroomComponent
    groom_comp = actor.get_component_by_class(unreal.GroomComponent)
    if not groom_comp:
        groom_comp = actor.add_component_by_class(unreal.GroomComponent, False, unreal.Transform(), False)

    if parent_comp:
        groom_comp.attach_to_component(parent_comp, unreal.AttachmentTransformRules.SNAP_TO_TARGET_NOT_INCLUDING_SCALE, "")

    # Set properties using snake_case get_editor_property/set_editor_property
    groom_comp.set_editor_property("groom_asset", groom_asset)
    if binding_asset:
        groom_comp.set_editor_property("binding_asset", binding_asset)

    # MANDATORY ASSERTION GATE: Never declare success without verifying asset attachment!
    assigned_groom = groom_comp.get_editor_property("groom_asset")
    if assigned_groom is None or assigned_groom != groom_asset:
        raise AssertionError(
            f"Component Asset Binding Gate Failed: GroomComponent.groom_asset is {assigned_groom}, expected {groom_asset}!"
        )

    if binding_asset:
        assigned_binding = groom_comp.get_editor_property("binding_asset")
        if assigned_binding is None or assigned_binding != binding_asset:
            raise AssertionError(
                f"Component Asset Binding Gate Failed: GroomComponent.binding_asset is {assigned_binding}, expected {binding_asset}!"
            )

    print(f"  ✓ GroomComponent successfully verified with {assigned_groom.get_name()}")
    return groom_comp


def stage_preview_capture(screenshot_source_path, artifact_dir, preview_filename="groom_preview.png"):
    """Copy captured viewport image to conversation artifact directory with forward-slash URI."""
    if not artifact_dir or not os.path.exists(artifact_dir):
        print("  • No artifact directory provided; skipping preview staging.")
        return None

    if not os.path.exists(screenshot_source_path):
        print(f"  • Source screenshot not found at {screenshot_source_path}; skipping staging.")
        return None

    os.makedirs(artifact_dir, exist_ok=True)
    target_path = os.path.join(artifact_dir, preview_filename).replace("\\", "/")
    shutil.copyfile(screenshot_source_path, target_path)

    print(f"  ✓ Staged preview image to artifact dir: {target_path}")
    print(f"  • Markdown embed format: ![{preview_filename}](/{target_path})")
    return target_path


def run_ingestion(config=CONFIG):
    """Execute complete ingestion, validation, and component binding pipeline."""
    print("=" * 60)
    print("UNREAL ENGINE DETERMINISTIC GROOM INGESTION PIPELINE")
    print("=" * 60)

    groom_asset = import_alembic_groom(
        filepath=config["alembic_filepath"],
        dest_path=config["destination_path"],
        dest_name=config["destination_name"],
        scale=config["conversion_scale"],
        rotation=config["conversion_rotation"],
    )

    validate_groom_geometry(groom_asset)

    binding_asset = None
    if config.get("skeletal_mesh_path"):
        binding_asset = create_and_bind_groom_binding(
            groom_asset=groom_asset,
            skel_mesh_path=config["skeletal_mesh_path"],
            dest_path=config["destination_path"],
            dest_name=config["destination_name"],
        )

    if config.get("target_actor"):
        setup_groom_component(
            actor=config["target_actor"],
            groom_asset=groom_asset,
            parent_comp=config.get("target_mesh_component"),
            binding_asset=binding_asset,
        )

    if config.get("save_assets"):
        unreal.EditorAssetLibrary.save_loaded_asset(groom_asset)
        if binding_asset:
            unreal.EditorAssetLibrary.save_loaded_asset(binding_asset)

    print("=" * 60)
    print(f"INGESTION COMPLETE: {groom_asset.get_path_name()} successfully validated.")
    print("=" * 60)
    return groom_asset


if __name__ == "__main__":
    run_ingestion()
