"""Build the independent comic facade scene. Pass --render after Blender's --."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from comic_look import apply_comic_look


def material(name, color, roughness=0.72, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


def screen_material(filename):
    path = ROOT / "textures" / filename
    image = bpy.data.images.load(str(path), check_existing=False)
    image.pack()
    image.filepath = "//textures/" + filename
    mat = material(path.stem, (1, 1, 1), 0.48)
    mat["comic_look_skip"] = True
    tree = mat.node_tree
    texture = tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    tree.links.new(tree.nodes.new('ShaderNodeTexCoord').outputs["UV"],
                   texture.inputs["Vector"])
    shader = tree.nodes.get("Principled BSDF")
    for name in ("Base Color", "Emission Color"):
        tree.links.new(texture.outputs["Color"], shader.inputs[name])
    shader.inputs["Emission Strength"].default_value = 0.75
    return mat, image.size[0] / image.size[1]


def build():
    scene = bpy.data.scenes.new("Comic Look · Corner at Dusk")
    collection = bpy.data.collections.new("Comic Look Demo")
    scene.collection.children.link(collection)

    def link(name, data, position):
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        obj.location = position
        return obj

    def mesh(name, verts, faces, position, mat):
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, [], faces)
        data.update()
        data.materials.append(mat)
        return link(name, data, position)

    def box(name, position, size, mat, bevel=0.025, angle=0):
        x, y, z = (component / 2 for component in size)
        verts = [(-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
                 (-x,-y,z), (x,-y,z), (x,y,z), (-x,y,z)]
        faces = [(3,2,1,0), (4,5,6,7), (0,1,5,4),
                 (1,2,6,5), (2,3,7,6), (3,0,4,7)]
        obj = mesh(name, verts, faces, position, mat)
        obj.rotation_euler.z = angle
        if bevel:
            modifier = obj.modifiers.new("Machined bevel", 'BEVEL')
            modifier.width = bevel
            modifier.segments = 2
        return obj

    def pipe(name, points, radius, mat):
        data = bpy.data.curves.new(name, 'CURVE')
        data.dimensions = '3D'
        data.bevel_depth = radius
        data.bevel_resolution = 2
        spline = data.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for point, xyz in zip(spline.points, points):
            point.co = (*xyz, 1)
        data.materials.append(mat)
        link(name, data, (0, 0, 0))

    magenta = material("Guava enamel", (0.68, 0.055, 0.20))
    cyan = material("Pool blue concrete", (0.055, 0.47, 0.59))
    yellow = material("Marigold castings", (0.95, 0.56, 0.055))
    lavender = material("Lavender concrete", (0.39, 0.22, 0.54))
    violet = material("Deep violet mortar", (0.10, 0.045, 0.18))
    plum = material("Plum shadow panels", (0.25, 0.08, 0.28))
    ink = material("Aubergine trim", (0.027, 0.012, 0.043), 0.52)
    ground = material("Dusty pink stage", (0.38, 0.24, 0.36))
    glass = material("Blue inset window glazing", (0.16, 0.45, 0.58), 0.20)
    glass.node_tree.nodes.get("Principled BSDF").inputs["Transmission Weight"].default_value = 0.32

    box("Studio ground", (1, 1, -0.15), (200, 200, 0.26), ground, 0)
    box("Chamfered pavement", (2.6, 2.35, 0.02), (7.8, 7.3, 0.20), lavender)
    box("Building structure", (2.8, 2.55, 2.73), (5.6, 5.1, 5.18), violet)
    box("Roof coping", (2.8, 2.55, 5.43), (5.9, 5.4, 0.22), yellow, 0.04)
    box("Roof cap", (2.8, 2.55, 5.58), (5.73, 5.23, 0.10), ink)
    box("Rooftop service housing", (3.0, 2.75, 5.79), (2.3, 1.55, 0.35), lavender)
    box("Corner concrete pier", (-0.02, -0.02, 2.75), (0.33, 0.33, 5.24), yellow, 0.055)

    def facade(label, width, origin, angle, base, trim, ad_file):
        across = Vector((math.cos(angle), math.sin(angle), 0))
        outward = Vector((math.sin(angle), -math.cos(angle), 0))
        origin = Vector(origin)

        def at(u, depth, z):
            return origin + across * u + outward * depth + Vector((0, 0, z))

        def part(name, u, depth, z, w, d, h, mat, bevel=0.025):
            return box(f"{label} · {name}", at(u, depth, z), (w, d, h), mat, bevel, angle)

        dot_blocks = []
        for row in range(4):
            for col in range(5):
                pitch = (width - 0.46) / 5
                dot_blocks.append(part("Cast concrete block", 0.23 + (col + 0.5)*pitch,
                                       0.055, 0.51 + row*0.44, pitch-0.026, 0.20, 0.41, base))
        for u in (0.33, width - 0.33):
            for z in (2.79, 4.43):
                dot_blocks.append(part("Concrete pilaster", u, 0.10, z, 0.34,
                                       0.32, 1.53, base))
        for z in (0.24, 2.12, 3.41, 5.12):
            part("Projecting ledge", width/2, 0.16, z, width-0.18, 0.42, 0.13, trim)

        for u in (width*0.27, width*0.73):
            part("Recessed window surround", u, 0.08, 2.75, 1.45, 0.21, 0.96, ink)
            part("Dark window backing", u, 0.19, 2.75, 1.25, 0.05, 0.77, violet)
            part("Inset window glazing", u, 0.225, 2.75, 1.21, 0.035, 0.74, glass, 0.008)
            for du in (-0.66, 0, 0.66):
                part("Vertical mullion", u+du, 0.29, 2.75, 0.066, 0.12, 0.92, trim)
            for z in (2.31, 2.76, 3.19):
                part("Horizontal mullion", u, 0.29, z, 1.38, 0.12, 0.066, trim)
            part("Window sill", u, 0.30, 2.25, 1.53, 0.33, 0.09, ink)

        shadow = part("Crosshatched panel behind billboard", width/2, 0.06, 4.25,
                      width-1.06, 0.20, 1.59, plum)
        plane = "XZ" if angle == 0 else "YZ"
        apply_comic_look([shadow], plane=plane, spacing=0.105, dots=False, hatch=True)
        apply_comic_look(dot_blocks, plane=plane, spacing=0.064,
                         ink_color=(0.18, 0.15, 0.27))

        ad, ratio = screen_material(ad_file)
        screen_h = min(1.37, (width-1.49)/ratio)
        screen_w = screen_h*ratio
        u, z = width/2, 4.25
        for du in (-screen_w*0.40, screen_w*0.40):
            part("Steel billboard bracket", u+du, 0.23, z, 0.12, 0.44, screen_h*0.86, ink)
        backing = part("Billboard chassis", u, 0.43, z, screen_w+0.23, 0.22,
                       screen_h+0.19, ink, 0.04)
        apply_comic_look([backing], dots=False, outlines=True, outline_radius=0.012)
        for du in (-screen_w/2-0.042, screen_w/2+0.042):
            part("Billboard side extrusion", u+du, 0.56, z, 0.085, 0.12, screen_h+0.16, trim)
        for dz in (-screen_h/2-0.039, screen_h/2+0.039):
            part("Billboard horizontal extrusion", u, 0.56, z, screen_w, 0.12, 0.078, trim)
        x, h = screen_w/2, screen_h/2
        panel = mesh(f"{label} · UV advertising display",
                     [(-x,0,-h), (x,0,-h), (x,0,h), (-x,0,h)],
                     [(0,1,2,3)], at(u, 0.575, z), ad)
        panel.rotation_euler.z = angle
        uv = panel.data.uv_layers.new(name="Advertisement UV")
        for loop, value in zip(uv.data, ((0,0), (1,0), (1,1), (0,1))):
            loop.uv = value

        p = width - 0.52
        pipe(f"{label} · Bent utility conduit",
             [at(p, 0.27, 0.31), at(p, 0.27, 1.67), at(p-0.12, 0.27, 1.82),
              at(p-0.56, 0.27, 1.82), at(p-0.67, 0.27, 2.01)], 0.048, trim)
        for z in (0.55, 1.25, 1.60):
            part("Conduit mount", p, 0.19, z, 0.15, 0.27, 0.09, ink)
        part("Street canopy", width*0.34, 0.40, 1.68, 1.90, 0.81, 0.12, ink)
        part("Canopy fascia", width*0.34, 0.82, 1.65, 1.94, 0.09, 0.20, trim)

    facade("Electric Soda", 5.6, (0, 0, 0), 0, magenta, yellow, "ad_electric_soda.jpg")
    facade("Cloud Courier", 5.1, (0, 5.1, 0), -math.pi/2, cyan, lavender,
           "ad_cloud_courier.jpg")

    def point_at(obj, target):
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()

    camera = link("Corner camera", bpy.data.cameras.new("Corner camera"), (-10, -12, 7.8))
    point_at(camera, (2.25, 2.10, 2.72))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 12.7
    scene.camera = camera

    def area(name, position, target, power, color, size):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = power
        data.color = color
        data.shape = 'DISK'
        data.size = size
        point_at(link(name, data, position), target)

    area("Apricot key", (0, -5, 10), (1, 1, 2.5), 1750, (1, 0.80, 0.68), 7)
    area("Cool facade fill", (-6, 2, 6), (0, 2, 2.8), 1200, (0.61, 0.83, 1), 6)
    area("Pink roof rim", (4, 7, 9), (2, 2, 3.4), 2000, (1, 0.49, 0.66), 5)
    scene.world = bpy.data.worlds.new("Dusk studio ambient")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.30, 0.24, 0.38, 1)
    background.inputs["Strength"].default_value = 0.38
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = "//comic_demo.png"
    scene.view_settings.view_transform = 'AgX'
    return scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    scene = build()
    bpy.context.window.scene = scene
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "comic_demo.blend"), relative_remap=False)
    if args.render:
        bpy.ops.render.render(write_still=True, scene=scene.name)


if __name__ == "__main__":
    main()
