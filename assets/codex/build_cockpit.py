"""Build the STRAY Hero cockpit or save and optionally render its night variant."""

import argparse
import math
import runpy
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
OWNER = "STRAY Hero cockpit"
ANCHOR = (0.0, -.04, .715)
CAMERA = (-.327, -.53, .966)
TARGET = (-.29, .68, .876)


def prepare_cabin_opening(root):
    """Trim the hidden deck in this in-memory Hero, using a private mesh."""
    deck, = (obj for obj in root.children_recursive
             if obj.name.split(".")[0] == "Hero_Sculpted_deck")
    if deck.data.get("stray_cabin_opening"):
        return deck
    original = deck.data
    mesh = original.copy()
    mesh.name = "Hero_Sculpted_deck_Cabin"
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        # Use the existing longitudinal and crosswise grids. The .67 deck
        # columns lie inside the canopy sills. Keep the .68+ bonnet seams
        # outboard of the opening and retain the cowl under the windshield.
        faces = [
            face for face in bm.faces
            if all(-1.15001 <= v.co.y <= .65001 and abs(v.co.x) <= .592
                   for v in face.verts)
        ]
        if not faces:
            raise ValueError("Hero deck does not match the authored cabin opening")
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()
    mesh["stray_cabin_opening"] = True
    deck.data = mesh
    # Keep the source datablock intact for any external users.
    return deck


def _palette():
    materials = {}
    for name, color, roughness, glow in (
        ("Shell", (.024, .032, .047), .48, 0),
        ("Leather", (.069, .077, .097), .59, 0),
        ("Rubber", (.014, .017, .023), .69, 0),
        ("Alloy", (.24, .29, .35), .32, 0),
        ("Screen", (.007, .017, .027), .31, .26),
        ("Cyan", (.085, .77, .97), .34, 1.7),
        ("Magenta", (.88, .047, .29), .38, 1.35),
        ("White", (.65, .91, 1.), .36, 1.35),
    ):
        full_name = f"Hero_Cockpit_Mat_{name}"
        material = next((mat for mat in bpy.data.materials
                         if mat.get("stray_cockpit_palette") == full_name), None)
        if material is None:
            material = bpy.data.materials.new(full_name)
            material["stray_cockpit_palette"] = full_name
            material.use_nodes = True
            material.diffuse_color = (*color, 1)
            shader = material.node_tree.nodes["Principled BSDF"]
            shader.inputs["Base Color"].default_value = (*color, 1)
            shader.inputs["Roughness"].default_value = roughness
            shader.inputs["Emission Color"].default_value = (*color, 1)
            shader.inputs["Emission Strength"].default_value = glow
        materials[name] = material
    return materials


def _box(g, name, center, size, material, parent, bevel=.01, pitch=0):
    x, y, z = (dimension / 2 for dimension in size)
    corners = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
               (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = g.mesh(name, corners, faces, material, parent)
    obj.location = center
    obj.rotation_euler.x = pitch
    if bevel:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return obj


def build_cockpit(*, root=None):
    """Open the existing Hero deck and build its interior under Hero_CockpitRoot."""
    if root is None:
        root = bpy.data.objects.get("Hero_Root")
    if root is None:
        raise ValueError("Append Hero or open assets.blend first")
    hero_collection = next((col for col in root.users_collection
                            if col.name.split(".")[0] == "Hero"), None)
    if hero_collection is None:
        raise ValueError("Hero_Root must belong to the Hero asset collection")
    Geometry = runpy.run_path(str(HERE / "build_assets.py"))["Geometry"]
    prepare_cabin_opening(root)

    collection = next((col for col in hero_collection.children
                       if col.get("owner") == OWNER), None)
    if collection is None:
        collection = bpy.data.collections.new("Hero_Cockpit")
        collection["owner"] = OWNER
        hero_collection.children.link(collection)
    else:
        for obj in list(collection.objects):
            if obj.get("stray_cockpit_owned") and obj.type != "EMPTY":
                if len(obj.users_collection) > 1 or obj.children:
                    collection.objects.unlink(obj)
                    continue
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if data and data.users == 0 and data.get("stray_cockpit_owned"):
                    bpy.data.batch_remove(ids=(data,))

    existing = set(collection.objects)
    g = Geometry(collection, "Hero_Cockpit_")
    m = _palette()
    cockpit = next((obj for obj in collection.objects if obj.get("stray_cockpit_root")), None)
    if cockpit is None:
        cockpit = g.object("Root", parent=root)
        cockpit.name = "Hero_CockpitRoot"
        cockpit["stray_cockpit_root"] = True
        cockpit.empty_display_size = .17
    anchor = next((obj for obj in collection.objects if obj.get("stray_map_anchor")), None)
    if anchor is None:
        anchor = g.object("Anchor", parent=cockpit, location=ANCHOR)
        anchor.name = "Hero_MapAnchor"
        anchor["stray_map_anchor"] = True
        anchor.empty_display_type = "ARROWS"
        anchor.empty_display_size = .11

    def box(name, center, size, material, bevel=.01, pitch=0):
        return _box(g, name, center, size, m[material], cockpit, bevel, pitch)

    def line(name, coords, radius, material):
        return g.line(name, coords, radius, m[material], cockpit)

    def label(name, body, xyz, size, material):
        font = bpy.data.curves.new("Hero_Cockpit_" + name, "FONT")
        font.body = body
        font.size = size
        font.materials.append(m[material])
        obj = g.object(name, font, cockpit, xyz)
        obj.rotation_euler.x = math.pi / 2

    box("Floor", (0, -.18, .313), (1.10, 1.74, .066), "Rubber")
    box("Rear_bulkhead", (0, -1.092, .54), (1.10, .085, .46), "Shell", .025)
    box("Pedal_bulkhead", (0, .666, .52), (1.12, .12, .40), "Shell", .025)
    box("Console", (0, -.12, .464), (.189, 1.29, .237), "Shell", .031)
    box("Console_insert", (0, -.06, .588), (.142, .47, .023), "Rubber", .009)
    box("Console_control", (0, -.26, .608), (.078, .081, .03), "Alloy", .012)
    box("Dashboard", (0, .466, .709), (1.16, .35, .197), "Shell", .045)
    box("Dash_top", (0, .458, .8), (1.13, .285, .06), "Leather", .024)
    line("Dash_inlay", [(-.555, .283, .735), (-.44, .279, .718),
                        (.44, .279, .718), (.555, .283, .735)], .005, "Magenta")
    box("Cluster_housing", (-.33, .384, .817), (.366, .151, .139), "Rubber", .026)
    box("Cluster_screen", (-.33, .304, .816), (.312, .012, .096), "Screen", .009)
    label("Speed_readout", "087", (-.451, .296, .800), .064, "White")
    label("Speed_units", "KM/H", (-.304, .296, .802), .024, "Cyan")
    label("Drive_status", "D", (-.239, .296, .836), .029, "Magenta")
    line("Cluster_bar", [(-.445, .294, .783), (-.272, .294, .783)], .0024, "Cyan")
    box("Center_display", (.163, .282, .764), (.255, .021, .115), "Screen", .012)
    label("Center_status", "STRAY", (.067, .268, .768), .038, "White")
    label("Center_mode", "NIGHT DRIVE", (.069, .268, .735), .019, "Cyan")

    wheel = Vector((-.325, .11, .694))
    rim = [tuple(wheel + Vector((.135 * math.cos(a), .026 * math.sin(a),
                                 .125 * math.sin(a))))
           for a in (math.tau * i / 48 for i in range(49))]
    line("Steering_rim", rim, .014, "Rubber")
    for name, idx in (("Right", 0), ("Left", 24), ("Lower", 36)):
        line("Steering_spoke_" + name, [wheel, rim[idx]], .011, "Alloy")
    box("Steering_hub", wheel, (.102, .054, .064), "Shell", .016)
    line("Steering_column", [wheel, (-.325, .37, .645)], .028, "Shell")

    for sign, side in ((-1, "L"), (1, "R")):
        x = sign * .327
        box("Seat_base_" + side, (x, -.456, .403), (.405, .49, .132), "Shell", .04)
        box("Seat_cushion_" + side, (x, -.407, .483), (.386, .461, .125), "Leather", .037)
        box("Seat_back_" + side, (x, -.647, .664), (.378, .113, .421),
            "Leather", .042, .23)
        box("Headrest_" + side, (x, -.707, .889), (.221, .085, .11),
            "Shell", .029, .23)
        for offset in (-.153, .153):
            suffix = side + ("_Inner" if offset * sign < 0 else "_Outer")
            box("Seat_bolster_" + suffix, (x + offset, -.404, .534),
                (.072, .414, .073), "Shell", .024)
        box("Door_card_" + side, (sign * .597, -.202, .547),
            (.116, 1.52, .39), "Shell", .038)
        box("Armrest_" + side, (sign * .542, -.194, .634), (.104, .57, .067),
            "Leather", .024)
        line("Door_strip_" + side, [(sign * .537, -.713, .692),
                                     (sign * .532, .36, .692)], .0034, "Cyan")
        line("Sill_inner_" + side, [(sign * .55, -1.062, .75),
                                    (sign * .628, -.48, .746),
                                    (sign * .622, .30, .737),
                                    (sign * .597, .65, .727)], .027, "Rubber")
        line("Pillar_inner_" + side, [(sign * .460, .219, 1.092),
                                      (sign * .550, .469, .928),
                                      (sign * .629, .672, .747)], .011, "Rubber")

    for obj in collection.objects:
        if obj not in existing and obj.parent == cockpit and obj.type != "EMPTY":
            obj["stray_cockpit_owned"] = True
            obj.data["stray_cockpit_owned"] = True
    return collection


def _preview(scene):
    recipe = runpy.run_path(str(HERE / "build_assets.py"))
    collection = bpy.data.collections.new("Preview_Cockpit")
    scene.collection.children.link(collection)
    g = recipe["Geometry"](collection, "Preview_Cockpit_")
    for child in scene.collection.children:
        visible = child == collection or child.name == "Hero"
        child.hide_render = child.hide_viewport = not visible

    world = bpy.data.worlds.new("Preview_Cockpit_World")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (.065, .113, .218, 1)
    background.inputs["Strength"].default_value = .37
    scene.world = world

    def preview_mat(name, color, emission=0):
        return recipe["material"](name, color, roughness=.64, glow=emission,
                                  prefix="Preview_Cockpit")

    road = preview_mat("Road", (.024, .031, .048), .22)
    lane = preview_mat("Lane", (.38, .52, .64), .55)
    cyan = preview_mat("Cyan", (.012, .64, .95), 2.4)
    pink = preview_mat("Magenta", (.95, .018, .32), 2.4)
    _box(g, "Road", (0, 24, -.055), (16, 76, .10), road, None, 0)
    for i in range(11):
        y = 4.8 + 4.35 * i
        _box(g, f"Lane_{i}", (0, y, .001), (.052, 1.8, .01), lane, None, 0)
        for side, marker in ((-1, cyan), (1, pink)):
            x = side * 2.35
            _box(g, f"Road_edge_{side}_{i}", (x, y, .011),
                 (.037, 2.5, .015), marker, None, 0)
            _box(g, f"Road_marker_{side}_{i}", (x, y + .25, .318),
                 (.063, .068, .64), marker, None, .008)

    def aim(obj, target):
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

    def area(name, position, target, color, energy, size, width):
        light = bpy.data.lights.new("Preview_Cockpit_" + name, "AREA")
        obj = g.object(name, light, location=position)
        light.shape = "RECTANGLE"
        light.size, light.size_y = size, width
        light.energy, light.color = energy, color
        aim(obj, target)

    camera = bpy.data.cameras.new("Preview_Cockpit_Camera")
    obj = g.object("Camera", camera, location=CAMERA)
    camera.lens = 19
    camera.clip_start = .015
    aim(obj, TARGET)
    scene.camera = obj
    area("Cabin_key", (.25, -.09, 1.075), (-.25, .39, .67),
         (.64, .79, 1), 14, .46, .23)
    area("Cabin_fill", (.37, -.32, .995), (-.30, .13, .69),
         (1, .46, .59), 3.5, .32, .22)
    area("Road_fill", (1, 8, 5), (0, 8, 0), (.40, .64, 1), 760, 7, 6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    directory = Path.cwd()
    source = directory / "assets.blend"
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError("Start Blender with the local assets.blend")
    variant = directory / "assets_night.blend"
    if variant.is_symlink() or (variant.exists() and variant.samefile(source)):
        raise RuntimeError("assets_night.blend must be separate from assets.blend")
    apply_materials = runpy.run_path(str(HERE / "hero_night_materials.py"))[
        "apply_hero_night_materials"]
    apply_materials()
    build_cockpit()
    scene = bpy.context.scene
    _preview(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.transmission_bounces = 8
    render = scene.render
    render.threads_mode, render.threads = "FIXED", 4
    render.resolution_x, render.resolution_y = 1280, 800
    render.resolution_percentage = 100
    render.use_border = False
    render.film_transparent = False
    render.use_compositing = render.use_sequencer = False
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGB"
    preview = directory / "hero_cockpit_preview.png"
    if args.render and (preview.is_symlink() or (preview.exists() and preview.samefile(source))):
        raise RuntimeError("hero_cockpit_preview.png must be separate from assets.blend")
    render.filepath = "//hero_cockpit_preview.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(variant))
    if args.render:
        bpy.ops.render.render(write_still=True, scene=scene.name)


if __name__ == "__main__":
    main()
