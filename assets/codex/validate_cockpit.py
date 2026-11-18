"""Run from Blender with assets.blend or assets_night.blend loaded."""

import hashlib
import json
import math
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
ASSETS = {"Hero", "Police", "Heli", "Truck"}
TOLERANCE = 1e-5


def source_digest():
    return hashlib.sha256((HERE / "assets.blend").read_bytes()).hexdigest()


def matrix(value):
    return tuple(tuple(row) for row in value)


def geometry(data):
    if isinstance(data, bpy.types.Mesh):
        return (data.as_pointer(), tuple(tuple(v.co) for v in data.vertices),
                tuple(tuple(edge.vertices) for edge in data.edges),
                tuple(tuple(p.vertices) for p in data.polygons))
    if isinstance(data, bpy.types.Curve):
        return (data.as_pointer(), tuple(
            (s.type, tuple(tuple(p.co) for p in s.points),
             tuple(tuple(p.co) for p in s.bezier_points)) for s in data.splines),
            data.body if isinstance(data, bpy.types.TextCurve) else None)
    return data.as_pointer() if data else None


def value(v):
    return v if isinstance(v, (str, float, int, bool)) or v is None else tuple(v)


def nodes(tree):
    if tree is None:
        return None
    return (tuple((n.name, n.type, tuple(
        (s.identifier, value(s.default_value)) for s in n.inputs
        if hasattr(s, "default_value"))) for n in tree.nodes),
        tuple((link.from_node.name, link.from_socket.identifier, link.to_node.name,
               link.to_socket.identifier) for link in tree.links))


def objects_state(objects, *, materials=False):
    def describe(obj):
        data = obj.data
        state = (obj.as_pointer(), obj.parent, matrix(obj.matrix_basis),
                 matrix(obj.matrix_parent_inverse), tuple(c.name for c in obj.users_collection),
                 obj.hide_viewport, obj.hide_render, obj.hide_select,
                 obj.visible_camera, obj.visible_transmission, geometry(data),
                 tuple((m.name, m.type, m.show_render, m.show_viewport) for m in obj.modifiers))
        if isinstance(data, bpy.types.Camera):
            state += (data.lens, data.type, data.clip_start, data.clip_end)
        if isinstance(data, bpy.types.Light):
            state += (data.type, data.energy, tuple(data.color))
        if materials:
            state += (tuple((slot.link, slot.material, tuple(slot.material.diffuse_color),
                             nodes(slot.material.node_tree)) if slot.material else None
                            for slot in obj.material_slots),)
        return state

    return {obj.name: describe(obj) for obj in objects}


def scene_state():
    def layers(layer):
        return (layer.name, layer.exclude, layer.hide_viewport, layer.holdout,
                layer.indirect_only, tuple(layers(child) for child in layer.children))

    return (
        {s.name: (s.camera, s.world, nodes(s.world.node_tree) if s.world else None,
                  tuple((vl.name, layers(vl.layer_collection),
                         tuple((obj.name, obj.hide_get(view_layer=vl)) for obj in vl.objects))
                        for vl in s.view_layers),
                  tuple(c.name for c in s.collection.children))
         for s in bpy.data.scenes},
        {c.name: (c.hide_render, c.hide_viewport, tuple(o.name for o in c.objects),
                  tuple(child.name for child in c.children)) for c in bpy.data.collections},
        tuple(mesh.name for mesh in bpy.data.meshes),
        tuple(camera.name for camera in bpy.data.cameras),
        tuple(light.name for light in bpy.data.lights),
        tuple(world.name for world in bpy.data.worlds),
    )


def bounds(root, objects):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    inverse = root.matrix_world.inverted()
    lower = [math.inf] * 3
    upper = [-math.inf] * 3
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "FONT"}:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh is None:
            raise RuntimeError(f"Could not evaluate geometry for {obj.name}")
        try:
            transform = inverse @ evaluated.matrix_world
            for vertex in mesh.vertices:
                for axis, coordinate in enumerate(transform @ vertex.co):
                    if not math.isfinite(coordinate):
                        raise RuntimeError(f"Non-finite vertex in {obj.name}")
                    lower[axis] = min(lower[axis], coordinate)
                    upper[axis] = max(upper[axis], coordinate)
        finally:
            evaluated.to_mesh_clear()
    if lower[0] == math.inf:
        raise RuntimeError("No evaluated mesh, curve, or text vertices")
    return tuple(lower), tuple(upper)


def ray(root, obj, start, direction, distance=12):
    transform = obj.matrix_world.inverted() @ root.matrix_world
    origin = transform @ Vector(start)
    aim = transform.to_3x3() @ Vector(direction).normalized()
    return obj.ray_cast(origin, aim.normalized(), distance=distance * aim.length)[0]


def validate(report):
    cockpit = runpy.run_path(str(HERE / "build_cockpit.py"))
    apply_materials = runpy.run_path(str(HERE / "hero_night_materials.py"))[
        "apply_hero_night_materials"]

    def check(name, condition):
        report["checks"][name] = bool(condition)
        assert condition, name

    expected = (HERE / "assets_original.sha256").read_text().split()[0]
    report["original_sha256"] = source_digest()
    check("original_blend_matches_recorded_hash", report["original_sha256"] == expected)
    scene = bpy.context.scene
    check("four_assets_in_scene", ASSETS <= {c.name for c in scene.collection.children})
    roots = [obj for obj in bpy.data.objects if obj.name.split(".")[0] == "Hero_Root"]
    check("one_hero_root_initially", len(roots) == 1 and roots[0].name == "Hero_Root")
    root = roots[0]
    root_basis = matrix(root.matrix_basis)
    original_hero = bpy.data.collections["Hero"]
    exterior = tuple(original_hero.objects)
    original_bounds = bounds(root, exterior)
    deck = original_hero.objects["Hero_Sculpted_deck"]
    roof = original_hero.objects["Hero_Roof_shell"]
    roof_state = objects_state([roof])
    if not deck.data.get("stray_cabin_opening"):
        check("source_has_closed_deck", ray(root, deck, (0, -.2, .48), (0, 0, 1)))

    # A foreign object sharing the roof mesh exercises the material isolation
    # path and gives the repeat build a concrete external datablock to preserve.
    sentinel_collection = bpy.data.collections.new("Cockpit_Validation_External")
    scene.collection.children.link(sentinel_collection)
    sentinel = bpy.data.objects.new("Cockpit_Validation_Shared_Roof", roof.data)
    sentinel_collection.objects.link(sentinel)
    external = tuple(obj for obj in bpy.data.objects
                     if obj != root and obj not in root.children_recursive)
    external_before = objects_state(external, materials=True)
    collection_before = {
        c.name: (c.as_pointer(), c.hide_render, c.hide_viewport,
                 tuple(o.name for o in c.objects), tuple(k.name for k in c.children))
        for c in bpy.data.collections if c != original_hero and c.get("owner") != cockpit["OWNER"]
    }
    scene_ids = set(bpy.data.scenes)
    studio = scene.camera, scene.world

    immutable_objects = objects_state(bpy.data.objects)
    immutable_scenes = scene_state()
    first_materials = apply_materials(root=root)
    first_material_state = {key: nodes(mat.node_tree) for key, mat in first_materials.items()}
    material_ids = set(bpy.data.materials)
    second_materials = apply_materials(root=root)
    check("material_repeat_uses_same_ids_and_values",
          first_materials == second_materials and material_ids == set(bpy.data.materials)
          and first_material_state == {key: nodes(mat.node_tree)
                                       for key, mat in second_materials.items()})
    check("materials_leave_geometry_transforms_lighting_and_visibility_alone",
          immutable_objects == objects_state(bpy.data.objects) and immutable_scenes == scene_state())
    glass = first_materials["glass"].node_tree.nodes["Principled BSDF"]
    check("glass_is_low_roughness_transmission",
          glass.inputs["Transmission Weight"].default_value == 1
          and glass.inputs["Roughness"].default_value < .04)

    collection = cockpit["build_cockpit"](root=root)
    part = collection.objects["Hero_CockpitRoot"]
    anchor = collection.objects["Hero_MapAnchor"]
    opening_mesh = deck.data
    foreign_child = bpy.data.objects.new("Cockpit_Validation_Foreign_Child", roof.data)
    collection.objects.link(foreign_child)
    foreign_child.parent = part
    bpy.context.view_layer.update()
    foreign_child_state = objects_state([foreign_child], materials=True)

    def inventory():
        return sorted((o.name, o.type, matrix(o.matrix_basis),
                       o.parent.name if o.parent else None,
                       tuple(s.material.name for s in o.material_slots if s.material))
                      for o in collection.objects)

    first_inventory = inventory()
    sizes = tuple(len(data) for data in (bpy.data.objects, bpy.data.meshes,
                                        bpy.data.curves, bpy.data.materials, bpy.data.collections))
    check("repeat_keeps_collection", cockpit["build_cockpit"](root=root) == collection)
    check("repeat_keeps_inventory_without_data_growth",
          first_inventory == inventory()
          and sizes == tuple(len(data) for data in (bpy.data.objects, bpy.data.meshes,
                                                   bpy.data.curves, bpy.data.materials,
                                                   bpy.data.collections)))
    check("trim_is_reused", deck.data == opening_mesh)
    check("build_preserves_external_objects_and_materials",
          external_before == objects_state(external, materials=True)
          and foreign_child_state == objects_state([foreign_child], materials=True))
    check("build_preserves_external_collections_and_scene_studio",
          collection_before == {
              c.name: (c.as_pointer(), c.hide_render, c.hide_viewport,
                       tuple(o.name for o in c.objects), tuple(k.name for k in c.children))
              for c in bpy.data.collections
              if c != original_hero and c.get("owner") != cockpit["OWNER"]
          } and scene_ids == set(bpy.data.scenes) and studio == (scene.camera, scene.world))
    bpy.data.objects.remove(foreign_child, do_unlink=True)
    bpy.data.objects.remove(sentinel, do_unlink=True)
    bpy.data.collections.remove(sentinel_collection)

    check("cockpit_parented_to_existing_root",
          collection.name == "Hero_Cockpit" and collection.name in original_hero.children
          and part.parent == root and part.matrix_basis.is_identity
          and all(o == part or o.parent == part for o in collection.objects))
    check("hero_root_unique_and_untransformed",
          [obj for obj in bpy.data.objects if obj.name.split(".")[0] == "Hero_Root"] == [root]
          and matrix(root.matrix_basis) == root_basis)
    check("map_anchor_root_relative_position_and_axes",
          anchor.parent == part and anchor.type == "EMPTY"
          and (anchor.location - Vector(cockpit["ANCHOR"])).length < TOLERANCE
          and anchor.matrix_basis.to_3x3().is_identity and anchor.matrix_parent_inverse.is_identity)
    new_bounds = bounds(root, exterior)
    interior_bounds = bounds(root, collection.objects)
    report.update(exterior_bounds_before=original_bounds, exterior_bounds_after=new_bounds,
                  interior_bounds=interior_bounds, map_anchor=list(anchor.location))
    check("exterior_bounds_and_roof_preserved",
          all(abs(a - b) <= TOLERANCE for before, after in zip(original_bounds, new_bounds)
              for a, b in zip(before, after)) and roof_state == objects_state([roof]))
    check("interior_inside_exterior_bounds", all(
        new_bounds[0][i] <= interior_bounds[0][i] <= interior_bounds[1][i] <= new_bounds[1][i]
        for i in range(3)))

    for x in (-.36, 0, .36):
        for y in (-.9, -.35, .13, .53):
            check(f"open_deck_above_{x}_{y}", not ray(root, deck, (x, y, .47), (0, 0, 1)))
    check("deck_retained_at_cowl_and_haunch",
          ray(root, deck, (0, .81, .43), (0, 0, 1))
          and ray(root, deck, (.72, -.2, .43), (0, 0, 1)))

    windshield = original_hero.objects["Hero_Panoramic_windshield"]
    side_panes = [o for o in exterior if o.name.startswith(("Hero_Side_glass_", "Hero_Quarter_glass_"))
                  and o.parent == windshield.parent]
    check("front_and_side_panes_are_separate_and_share_clear_glass",
          windshield.type == "MESH" and len(side_panes) == 12
          and all(o.type == "MESH" and o.active_material == first_materials["glass"]
                  for o in [windshield, *side_panes]))
    opaque = [o for o in (*exterior, *collection.objects)
              if o.type == "MESH" and all(s.material != first_materials["glass"]
                                         for s in o.material_slots)]
    for label, eye in (("driver", (-.327, -.48, .966)), ("passenger", (.327, -.48, .966)),
                       ("driver_camera", cockpit["CAMERA"])):
        forward = (Vector(cockpit["TARGET"]) - Vector(eye) if label == "driver_camera"
                   else Vector((-eye[0] * .14, 1, -.015)))
        check(f"{label}_has_roof_clearance", ray(
            root, roof, eye, (0, 0, 1)))
        check(f"{label}_sees_windshield", ray(root, windshield, eye, forward, 2))
        check(f"{label}_has_unobstructed_forward_ray",
              not any(ray(root, o, eye, forward, 3) for o in opaque))
    check("source_hash_unchanged_after_builds", source_digest() == expected)


if __name__ == "__main__":
    report = {"checks": {}, "status": "failed"}
    try:
        validate(report)
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (Path.cwd() / "cockpit_validation.json").write_text(json.dumps(report, indent=2) + "\n")
