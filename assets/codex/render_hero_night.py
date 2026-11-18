"""Render the Hero night preview from the saved assets.blend studio."""

from pathlib import Path

import bpy
from mathutils import Vector


def set_surface(material, color, roughness, metallic, specular):
    rgba = (*color, 1.0)
    material.diffuse_color = rgba
    shader = material.node_tree.nodes["Principled BSDF"]
    for name, value in {
        "Base Color": rgba,
        "Roughness": roughness,
        "Metallic": metallic,
        "Specular IOR Level": specular,
        "Coat Weight": 0.0,
    }.items():
        shader.inputs[name].default_value = value


def set_strip(light, position, target, color, power, width, height):
    light.location = position
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    light.hide_render = False
    light.data.color = color
    light.data.energy = power
    light.data.shape = "RECTANGLE"
    light.data.size = width
    light.data.size_y = height


def main():
    directory = Path.cwd()
    source = directory / "assets.blend"
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != source.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(source))

    scene = bpy.data.scenes["STRAY Studio"]
    for collection in scene.collection.children:
        collection.hide_render = collection.name not in {"Hero", "Preview"}
    preview = scene.collection.children["Preview"]
    scene.camera = preview.objects["Preview_hero_front_34"]

    materials = bpy.data.materials
    set_surface(materials["Hero_Mat_paint"], (0.008, 0.009, 0.011), 0.34, 0.05, 0.19)
    set_surface(materials["Hero_Mat_glass"], (0.003, 0.005, 0.008), 0.23, 0.0, 0.16)
    floor = preview.objects["Preview_Floor"]
    floor.hide_render = False
    set_surface(floor.active_material, (0.010, 0.015, 0.025), 0.37, 0.02, 0.24)
    # The studio floor extends through the camera background.
    floor_shader = floor.active_material.node_tree.nodes["Principled BSDF"]
    floor_shader.inputs["Emission Color"].default_value = (0.0012, 0.0025, 0.0055, 1.0)
    floor_shader.inputs["Emission Strength"].default_value = 1.0

    for obj in preview.all_objects:
        if obj.type == "LIGHT":
            obj.hide_render = True

    # A broad, low-power key lifts the hood while the far-side strip traces the roof.
    set_strip(
        preview.objects["Preview_Key_softbox"],
        (1.6, 2.6, 5.4), (0.0, 1.0, 0.6),
        (0.82, 0.90, 1.0), 100, 5.7, 3.4,
    )
    set_strip(
        preview.objects["Preview_Long_rim"],
        (-2.4, -1.7, 3.7), (0.0, -0.3, 1.15),
        (0.68, 0.82, 1.0), 110, 4.2, 0.38,
    )

    # Low, narrow sources pick up the front and flank contours.
    set_strip(
        preview.objects["Preview_Nose_fill"],
        (0.8, 4.5, 1.65), (0.0, 1.1, 0.55),
        (0.15, 0.70, 0.86), 200, 3.0, 0.65,
    )
    set_strip(
        preview.objects["Preview_Side_fill"],
        (4.25, 1.65, 1.9), (0.0, 0.45, 0.6),
        (0.16, 0.70, 0.88), 290, 3.8, 0.55,
    )
    set_strip(
        preview.objects["Preview_Rear_softbox"],
        (2.65, -4.1, 1.8), (0.0, -0.85, 0.55),
        (0.82, 0.12, 0.45), 350, 3.4, 0.55,
    )

    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.016, 0.027, 0.050, 1.0)
    background.inputs["Strength"].default_value = 0.10

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = True

    render = scene.render
    render.threads_mode = "FIXED"
    render.threads = 4
    render.resolution_x = 1280
    render.resolution_y = 800
    render.resolution_percentage = 100
    render.use_border = False
    render.film_transparent = False
    render.use_compositing = False
    render.use_sequencer = False
    render.dither_intensity = 0.0
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGB"
    render.filepath = str(directory / "hero_night.png")

    bpy.ops.render.render(write_still=True, scene=scene.name)


if __name__ == "__main__":
    main()
