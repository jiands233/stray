"""Object-scoped printed material overrides and optional mesh crease curves."""
import math
import uuid

import bpy
import bmesh
from mathutils import Vector


_STATE = "_comic_look_state"
_OWNER = "_comic_look_owner"
_SOURCE = "_comic_look_source"
_INK = "_comic_look_ink"
OPT_OUT = "comic_look_skip"


def _principled(material):
    if not material or not material.use_nodes or material.get(OPT_OUT):
        return None
    tree = material.node_tree
    # Restrict edits to a direct, opaque Principled surface. Nested graphs
    # and mixed surfaces can hide transmission, so leave them alone.
    output = tree.get_output_node('CYCLES')
    if not output or not output.inputs["Surface"].is_linked:
        return None
    shader = output.inputs["Surface"].links[0].from_node
    if shader.type != 'BSDF_PRINCIPLED':
        return None
    if any(n.type in {'BSDF_GLASS', 'BSDF_REFRACTION', 'BSDF_TRANSPARENT',
                      'BSDF_TRANSLUCENT', 'TEX_IMAGE', 'TEX_ENVIRONMENT', 'GROUP'}
           for n in tree.nodes):
        return None
    for name, expected in (("Transmission Weight", 0), ("Alpha", 1)):
        socket = shader.inputs[name]
        if socket.is_linked or socket.default_value != expected:
            return None
    strength = shader.inputs["Emission Strength"]
    color = shader.inputs["Emission Color"]
    if strength.is_linked or color.is_linked:
        return None
    if strength.default_value and any(color.default_value[:3]):
        return None
    return shader


def _math(tree, op, label, a, b=None):
    node = tree.nodes.new('ShaderNodeMath')
    node.operation = op
    node.label = label
    for i, value in enumerate((a, b)):
        if isinstance(value, (float, int)):
            node.inputs[i].default_value = value
        elif value is not None:
            tree.links.new(value, node.inputs[i])
    return node.outputs[0]


def _print_pattern(material, scale, plane, spacing, dots, hatch, ink_color):
    tree = material.node_tree
    base = _principled(material).inputs["Base Color"]
    source = base.links[0].from_socket if base.is_linked else None
    uv = tree.nodes.new('ShaderNodeTexCoord')
    uv.label = "Object-local print coordinates"
    split = tree.nodes.new('ShaderNodeSeparateXYZ')
    tree.links.new(uv.outputs["Object"], split.inputs[0])
    axes = [
        _math(tree, 'MULTIPLY', f"{axis} in print cells", split.outputs[axis],
              scale["XYZ".index(axis)] / spacing)
        for axis in plane
    ]
    masks = []
    if dots:
        offsets = [
            _math(tree, 'SUBTRACT', "Offset from cell center",
                  _math(tree, 'FRACT', "Repeat each cell", axis), 0.5)
            for axis in axes
        ]
        squares = [_math(tree, 'MULTIPLY', "Squared offset", v, v) for v in offsets]
        radius_sq = _math(tree, 'ADD', "Squared distance from cell center", *squares)
        masks.append(_math(tree, 'LESS_THAN', "Round printed dot", radius_sq, 0.20**2))
    if hatch:
        for op in ('ADD', 'SUBTRACT'):
            diagonal = _math(tree, op, "Diagonal hatch coordinate", *axes)
            repeat = _math(tree, 'FRACT', "Repeat at diagonal intervals", diagonal)
            masks.append(_math(tree, 'LESS_THAN', "Diagonal ink stroke", repeat, 0.12))
    mask = masks[0]
    for layer in masks[1:]:
        mask = _math(tree, 'MAXIMUM', "Combine print marks", mask, layer)
    mix = tree.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.label = "Tint base color under printed ink"
    tree.links.new(mask, mix.inputs[0])
    if source is None:
        mix.inputs[1].default_value = base.default_value
    else:
        tree.links.new(source, mix.inputs[1])
    mix.inputs[2].default_value = (*ink_color, 1.0)
    tree.links.new(mix.outputs[0], base)


def _outline(obj, eligible, owner, radius, edge_cap, crease_angle):
    if not obj.users_collection:
        return
    mesh = bmesh.new()
    segments = []
    try:
        mesh.from_mesh(obj.data)
        for edge in mesh.edges:
            faces = edge.link_faces
            # Keep glass and other ineligible faces free of helper geometry.
            if not faces or any(f.material_index not in eligible for f in faces):
                continue
            sharp = len(faces) == 1 or (
                edge.is_manifold and edge.calc_face_angle(0.0) >= crease_angle)
            if sharp:
                segments.append(tuple(v.co.copy() for v in edge.verts))
                if len(segments) >= edge_cap:
                    break
    finally:
        mesh.free()
    if not segments:
        return
    curve = bpy.data.curves.new("Comic crease edges", 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 0
    for segment in segments:
        spline = curve.splines.new('POLY')
        spline.points.add(1)
        for point, coord in zip(spline.points, segment):
            point.co = (*coord, 1.0)
    ink = bpy.data.materials.new("Comic crease ink")
    ink[_OWNER] = owner
    ink.use_nodes = True
    surface = ink.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = (0.008, 0.004, 0.012, 1.0)
    surface.inputs["Roughness"].default_value = 0.82
    curve.materials.append(ink)
    helper = bpy.data.objects.new(f"{obj.name} · comic edges", curve)
    helper[_OWNER] = owner
    helper[_INK] = True
    helper.parent = obj
    helper.hide_select = True
    helper.hide_render = obj.hide_render
    for collection in obj.users_collection:
        collection.objects.link(helper)


def apply_comic_look(objects, *, spacing=0.055, plane="XZ", dots=True, hatch=False,
                     ink_color=(0.25, 0.19, 0.33), outlines=False,
                     outline_radius=0.008, edge_cap=2000,
                     crease_angle=math.radians(50)):
    """Apply once to eligible material slots of the given local mesh objects.

    Select a projection plane per patch. Use remove before changing options.
    """
    if plane not in {"XY", "XZ", "YZ"} or not math.isfinite(spacing) or spacing <= 0:
        raise ValueError("Choose XY, XZ or YZ and a positive finite spacing")
    if outlines and (not math.isfinite(outline_radius) or outline_radius <= 0
                     or not isinstance(edge_cap, int) or edge_cap < 1
                     or not 0 < crease_angle <= math.pi):
        raise ValueError("Outline radius, edge cap and crease angle must be positive")
    if not (dots or hatch or outlines):
        return
    for obj in objects:
        if obj.type != 'MESH' or obj.library or obj.get(OPT_OUT) or _STATE in obj:
            continue
        eligible = {i: slot.material for i, slot in enumerate(obj.material_slots)
                    if _principled(slot.material) is not None}
        if not eligible:
            continue
        owner = uuid.uuid4().hex
        obj[_STATE] = {"owner": owner, "data_slots": [
            i for i in eligible if obj.material_slots[i].link == 'DATA'
        ] if dots or hatch else []}
        if dots or hatch:
            copies = {}
            scale = tuple((obj.matrix_world.to_3x3() @ Vector(axis)).length
                          for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
            for index, source in eligible.items():
                if source not in copies:
                    override = source.copy()
                    override.name = f"{source.name} · comic"
                    override[_OWNER] = owner
                    override[_SOURCE] = source
                    override.use_fake_user = False
                    _print_pattern(override, scale, plane, spacing, dots, hatch, ink_color)
                    copies[source] = override
                slot = obj.material_slots[index]
                slot.link = 'OBJECT'
                slot.material = copies[source]
        if outlines:
            _outline(obj, eligible, owner, outline_radius, edge_cap, crease_angle)


def remove_comic_look(objects):
    """Remove owned overrides and helper objects from explicitly passed objects."""
    for obj in objects:
        state = obj.get(_STATE)
        if state is None:
            continue
        owner = state["owner"]
        data_slots = set(state["data_slots"])
        for index, slot in enumerate(obj.material_slots):
            material = slot.material
            if (slot.link != 'OBJECT' or material is None
                    or material.get(_OWNER) != owner or _SOURCE not in material):
                continue
            if index in data_slots:
                slot.material = None
                slot.link = 'DATA'
            else:
                slot.material = material[_SOURCE]
        for helper in list(obj.children):
            if helper.get(_OWNER) != owner or not helper.get(_INK):
                continue
            curve = helper.data
            bpy.data.objects.remove(helper, do_unlink=True)
            if curve and not curve.users:
                bpy.data.curves.remove(curve)
        for material in list(bpy.data.materials):
            if material.get(_OWNER) == owner and not material.users:
                bpy.data.materials.remove(material)
        del obj[_STATE]
