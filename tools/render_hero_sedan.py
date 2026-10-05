"""Render independent Blender 4.5 studio diagnostics without changing the source.

Usage from the repository root::

    blender --background --factory-startup --python tools/render_hero_sedan.py -- \
        --width 1280 --height 800 --samples 48

The model collection is appended into a separate scene. No .blend is saved.
EEVEE uses the available graphics backend; this script does not claim or force
a particular GPU. PNG outputs and render_receipt.json are the only writes.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
VIEW_NAMES = ("front3q", "side", "rear3q", "hero-dark-front3q")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "assets/hero-sedan/legion-sedan.blend")
    parser.add_argument("--out", type=Path, default=ROOT / "output/playwright/hero-model")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--views", nargs="+", choices=VIEW_NAMES, default=list(VIEW_NAMES))
    parser.add_argument("--lights-on", action="store_true", help="Illuminate the model's existing emissive lamp materials.")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def area(collection, name, location, target, energy, width, height, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "RECTANGLE"
    data.size = width
    data.size_y = height
    data.color = color
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def studio_rig(scene, dark=False):
    rig = bpy.data.collections.new("DarkStudioRig" if dark else "DiagnosticStudioRig")
    scene.collection.children.link(rig)
    if dark:
        # Long, narrow softboxes trace the curved shoulders. Wide overhead fill
        # makes black paint look silver and hides the silhouette differences.
        area(rig, "Dark_Key", (3.3, -4.5, 5.4), (0, 0, .8), 760, 4.6, .85)
        area(rig, "Dark_Long_Rim", (3.8, .8, 3.5), (0, 0, .8), 1900, 5.8, .32, (.89, .94, 1))
        area(rig, "Dark_Roof_Rim", (-2, 2.8, 4.4), (0, 0, 1), 1300, 4.5, .42)
        area(rig, "Dark_Front_Fill", (-4, -5, 1.8), (0, -.4, .7), 190, 3.3, 1.8)
    else:
        area(rig, "Studio_Key", (2, -3.8, 6.2), (0, 0, .6), 1400, 5, 3.2)
        area(rig, "Studio_Roof", (0, .6, 6.5), (0, 0, 0), 1100, 5.5, 3)
        area(rig, "Studio_Left_Strip", (-4.2, .6, 3.5), (0, 0, .8), 1400, 5, 2.2)
        area(rig, "Studio_Right_Fill", (4.8, .5, 3), (0, 0, .7), 950, 4, 3)
        area(rig, "Studio_Rear_Strip", (0, 5, 3), (0, 0, .7), 1150, 4.5, 2)
        area(rig, "Studio_Front_Fill", (-1, -5, 2.2), (0, 0, .7), 650, 3, 2)
    return rig


def contact_shadow(scene):
    """Soft grounding cue, like the inexpensive shadow used by the web hero.

    Explicitly a procedural approximation, not an assertion of physical GI.
    This also keeps diagnostic renders readable on graphics backends where
    EEVEE screen-space contact shadows have different precision.
    """
    mesh = bpy.data.meshes.new("StudioContactShadowGeometry")
    mesh.from_pydata([(-1.14, -2.58, -.003), (1.14, -2.58, -.003), (1.14, 2.58, -.003), (-1.14, 2.58, -.003)], [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new("StudioContactShadow", mesh)
    scene.collection.objects.link(obj)
    material = bpy.data.materials.new("StudioContactShadowMaterial")
    material.use_nodes = True
    material.surface_render_method = "DITHERED"
    nodes = material.node_tree.nodes
    nodes.clear()
    links = material.node_tree.links
    coord = nodes.new("ShaderNodeTexCoord")
    flat = nodes.new("ShaderNodeVectorMath")
    flat.operation = "MULTIPLY"
    flat.inputs[1].default_value = (1, 1, 0)
    links.new(coord.outputs["Generated"], flat.inputs[0])
    centered = nodes.new("ShaderNodeVectorMath")
    centered.operation = "SUBTRACT"
    centered.inputs[1].default_value = (.5, .5, 0)
    links.new(flat.outputs["Vector"], centered.inputs[0])
    radius = nodes.new("ShaderNodeVectorMath")
    radius.operation = "LENGTH"
    links.new(centered.outputs["Vector"], radius.inputs[0])
    alpha = nodes.new("ShaderNodeMapRange")
    alpha.interpolation_type = "SMOOTHSTEP"
    alpha.inputs["From Min"].default_value = .15
    alpha.inputs["From Max"].default_value = .57
    alpha.inputs["To Min"].default_value = .68
    alpha.inputs["To Max"].default_value = 0
    links.new(radius.outputs["Value"], alpha.inputs["Value"])
    clear = nodes.new("ShaderNodeBsdfTransparent")
    black = nodes.new("ShaderNodeEmission")
    black.inputs["Color"].default_value = (0, 0, 0, 1)
    mix = nodes.new("ShaderNodeMixShader")
    links.new(alpha.outputs["Result"], mix.inputs[0])
    links.new(clear.outputs[0], mix.inputs[1])
    links.new(black.outputs[0], mix.inputs[2])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(mix.outputs[0], output.inputs["Surface"])
    obj.data.materials.append(material)
    return obj


def main():
    args = arguments()
    source = args.source.resolve(strict=True)
    source_hash = sha256(source)
    args.out.mkdir(parents=True, exist_ok=True)
    scene = bpy.data.scenes.new("LegionHeroDiagnostics")
    bpy.context.window.scene = scene

    # Append copies of the collection. The authoring file remains closed and immutable.
    with bpy.data.libraries.load(str(source), link=False) as (available, destination):
        if "LEGION_SEDAN" not in available.collections:
            raise RuntimeError("Source must contain the LEGION_SEDAN model collection")
        destination.collections = ["LEGION_SEDAN"]
    model_collection = destination.collections[0]
    scene.collection.children.link(model_collection)
    meshes = [obj for obj in model_collection.all_objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("Source collection has no mesh geometry")

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = max(8, args.samples)
    scene.eevee.use_raytracing = True
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 2
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = .35

    world = bpy.data.worlds.new("HeroDiagnosticWorld")
    world.use_nodes = True
    scene.world = world
    world_background = world.node_tree.nodes.get("Background")

    floor_mesh = bpy.data.meshes.new("StudioFloorGeometry")
    floor_mesh.from_pydata([(-100, -100, -.008), (100, -100, -.008), (100, 100, -.008), (-100, 100, -.008)], [], [(0, 1, 2, 3)])
    floor_mesh.update()
    floor = bpy.data.objects.new("StudioFloor", floor_mesh)
    scene.collection.objects.link(floor)
    floor_material = bpy.data.materials.new("StudioFloorMaterial")
    floor_material.use_nodes = True
    floor_bsdf = floor_material.node_tree.nodes.get("Principled BSDF")
    floor.data.materials.append(floor_material)
    contact_shadow(scene)

    camera_data = bpy.data.cameras.new("ModelDiagnosticCamera")
    camera = bpy.data.objects.new("ModelDiagnosticCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.lens = 56
    camera_data.clip_start = .05
    camera_data.clip_end = 250
    camera_data.dof.use_dof = False

    bright_rig = studio_rig(scene)
    dark_rig = studio_rig(scene, dark=True)
    for rig in (bright_rig, dark_rig):
        for light in rig.objects:
            light.data.energy *= .55
    positions = {
        "front3q": (7.2, -9.0, 3.1),
        "side": (9.6, 0, 2.7),
        "rear3q": (7.2, 9.0, 3.1),
        "hero-dark-front3q": (-7.2, -9.6, 1.7),
    }
    if args.lights_on:
        for material in bpy.data.materials:
            if material.name not in {"Headlight_Lens", "Taillight_Lens"} or not material.use_nodes:
                continue
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                bsdf.inputs["Emission Color"].default_value = (1, .004, .006, 1) if material.name.startswith("Taillight") else (.76, .87, 1, 1)
                bsdf.inputs["Emission Strength"].default_value = 3

    rendered = []
    for name in args.views:
        dark = name.startswith("hero-dark")
        bright_rig.hide_render = dark
        dark_rig.hide_render = not dark
        world_background.inputs["Color"].default_value = (.009, .011, .014, 1) if dark else (.24, .27, .31, 1)
        world_background.inputs["Strength"].default_value = .12 if dark else .35
        scene.view_settings.exposure = -.45 if dark else -.15
        floor_bsdf.inputs["Base Color"].default_value = (.004, .005, .006, 1) if dark else (.14, .16, .19, 1)
        floor_bsdf.inputs["Metallic"].default_value = .46 if dark else .08
        floor_bsdf.inputs["Roughness"].default_value = .23 if dark else .47
        camera.location = positions[name]
        camera_data.lens = 68 if dark else 56
        camera_data.shift_x = -.15 if dark else 0
        camera_data.shift_y = .07 if dark else 0
        aim(camera, (0, 0, .60 if dark else .78))
        output = (args.out / (name + ".png")).resolve()
        scene.render.filepath = str(output)
        started = time.monotonic()
        bpy.ops.render.render(write_still=True, scene=scene.name)
        rendered.append({"view": name, "path": str(output), "seconds": round(time.monotonic() - started, 2), "bytes": output.stat().st_size, "sha256": sha256(output)})
        print(json.dumps(rendered[-1]), flush=True)

    if sha256(source) != source_hash:
        raise RuntimeError("Source changed while rendering; receipt cannot assert a stable source")
    receipt = {"source": str(source), "source_sha256": source_hash, "source_modified": False, "blender": bpy.app.version_string, "renderer": scene.render.engine, "raytracing": scene.eevee.use_raytracing, "contact_shadow": "Procedural soft grounding plane, matching the web scene technique", "resolution": [args.width, args.height], "samples": args.samples, "lights_on": args.lights_on, "views": rendered}
    (args.out / "render_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"render_receipt": str(args.out / "render_receipt.json"), "views": len(rendered)}), flush=True)


if __name__ == "__main__":
    main()
