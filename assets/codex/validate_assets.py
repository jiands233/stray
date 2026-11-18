"""Validate the STRAY fleet in Blender background mode and write validation.json."""
import json
import math
import runpy
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TOL = 1e-5


def descendants_of(obj, parent):
    while obj.parent is not None:
        obj = obj.parent
        if obj == parent:
            return True
    return False


def data_inventory(hero):
    return {
        "collections": {
            c.name: (c.as_pointer(), tuple(sorted(o.name for o in c.objects)),
                     tuple(sorted(k.name for k in c.children)))
            for c in bpy.data.collections if c != hero
        },
        "scene_links": {
            s.name: tuple(sorted(c.name for c in s.collection.children if c != hero))
            for s in bpy.data.scenes
        },
        "objects": {
            o.name: o.as_pointer() for o in bpy.data.objects
            if hero is None or hero not in o.users_collection or len(o.users_collection) > 1
        },
    }


def shape_inventory(hero):
    return {
        o.name: (
            o.type, o.parent.name if o.parent else None, tuple(o.location),
            tuple(o.rotation_euler), tuple(o.scale),
            tuple(slot.material.name for slot in o.material_slots if slot.material),
            len(o.data.vertices) if o.type == "MESH" else None,
            len(o.data.polygons) if o.type == "MESH" else None,
        )
        for o in hero.objects
    }


def evaluated_bounds(objects, depsgraph):
    extrema = [[(math.inf, None) for _ in range(3)],
               [(-math.inf, None) for _ in range(3)]]
    for original in objects:
        if original.type not in {"MESH", "CURVE", "FONT"}:
            continue
        obj = original.evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        if mesh is None:
            raise RuntimeError(f"Could not evaluate geometry for {original.name}")
        try:
            matrix = obj.matrix_world
            for vertex in mesh.vertices:
                for axis, value in enumerate(matrix @ vertex.co):
                    if not math.isfinite(value):
                        raise RuntimeError(f"Non-finite vertex in {original.name}")
                    if value < extrema[0][axis][0]:
                        extrema[0][axis] = (value, original.name)
                    if value > extrema[1][axis][0]:
                        extrema[1][axis] = (value, original.name)
        finally:
            obj.to_mesh_clear()
    if extrema[0][0][1] is None:
        raise RuntimeError("No evaluated mesh, curve, or text vertices")
    return extrema


FLEET_COMPONENTS = {
    "Police": ("Body", "Glass", "Headlights", "Taillights", "Lightbar_Red", "Lightbar_Blue"),
    "Heli": ("Body", "Glass", "Skids", "MainRotor", "TailRotor"),
    "Truck": ("Chassis", "Cab", "Glass", "Tank", "Headlights", "Taillights"),
}
FLEET_DIMENSIONS = {
    "Police": ((1.91,2.27), (4.98,5.36), (1.45,1.64)),
    "Heli": ((9.1,10.3), (11.3,13.2), (3.75,4.12)),
    "Truck": ((2.37,2.83), (9.3,9.8), (3.37,3.62)),
}


def inspect_fleet(collection, phase, report):
    prefix = collection.name
    label = prefix + "_" + phase

    def check(name, condition):
        report["checks"][label + "_" + name] = bool(condition)

    def get(name):
        return collection.objects.get(prefix + "_" + name)

    def bounds(objects):
        lower, upper = evaluated_bounds(objects, bpy.context.evaluated_depsgraph_get())
        return [entry[0] for entry in lower], [entry[0] for entry in upper]

    def independent(control):
        return (control is not None and control.type == "EMPTY" and
                control.parent == root and bool(control.children))

    def spin(control, member, axis_index):
        basis = Vector(tuple(float(i == axis_index) for i in range(3)))
        world_axis = control.matrix_world.to_3x3() @ basis
        old = control.rotation_euler.copy()
        before = member.matrix_world.copy()
        pivot = control.matrix_world.translation.copy()
        try:
            control.rotation_euler[axis_index] += .37
            bpy.context.view_layer.update()
            after = member.matrix_world.copy()
            return ((world_axis - basis).length < TOL and
                    (control.matrix_world.translation - pivot).length < TOL and
                    (before.col[(axis_index+1)%3] - after.col[(axis_index+1)%3]).length > .30)
        finally:
            control.rotation_euler = old
            bpy.context.view_layer.update()

    hidden = collection.hide_viewport
    collection.hide_viewport = False
    try:
        bpy.context.view_layer.update()
        objects = list(collection.objects)
        root = get("Root")
        check("root_at_origin", root is not None and root.type == "EMPTY" and
              root.parent is None and root.matrix_world.translation.length < TOL and
              all(abs(root.matrix_world[i][j] - (i == j)) < TOL
                  for i in range(3) for j in range(3)))
        check("axis_and_units", root is not None and root.get("forward_axis") == "+Y"
              and root.get("units") == "meters")
        check("names", bool(objects) and all(o.name.startswith(prefix + "_") for o in objects))
        check("parentage", root is not None and
              all(o == root or descendants_of(o, root) for o in objects))
        check("materials", all(o.material_slots and all(
              slot.material and slot.material.name.startswith(prefix + "_Mat_")
              for slot in o.material_slots) for o in objects if o.type in {"MESH","CURVE","FONT"}))
        lo, hi = bounds(objects)
        dimensions = [b-a for a,b in zip(lo,hi)]
        report[label + "_dimensions_m"] = dict(zip(("width","length","height"),dimensions))
        report[label + "_bounds_m"] = dict(zip("xyz",zip(lo,hi)))
        check("dimensions", all(a <= value <= b for value,(a,b) in
                                zip(dimensions,FLEET_DIMENSIONS[prefix])))
        check("ground", abs(lo[2]) <= .0015)
        for name in FLEET_COMPONENTS[prefix]:
            check("independent_" + name, independent(get(name)))

        if prefix in {"Police","Truck"}:
            axles = ("Front","Rear") if prefix == "Police" else ("Front","Rear1","Rear2")
            for axle in axles:
                for side, sign in (("L",-1),("R",1)):
                    name = axle + "_" + side
                    control = get("Wheel_" + name)
                    tire = get("Tire_" + name)
                    valid = independent(control) and tire is not None and tire.parent == control
                    check("independent_wheel_" + name, valid)
                    if not valid:
                        continue
                    low, high = bounds([tire])
                    check("contact_" + name, abs(low[2]) < TOL and
                          abs(control.location.z - (high[2]-low[2])/2) < TOL)
                    check("position_" + name, sign*control.location.x > 0 and
                          (control.location.y > 0 if axle == "Front" else control.location.y < 0))
                    check("spin_" + name, control.get("spin_axis") == "local X" and spin(control,tire,0))
                    if prefix == "Truck" and axle != "Front":
                        inner = get("Tire_" + name + "_Inner")
                        good = inner is not None and inner.parent == control
                        if good:
                            inner_lo, inner_hi = bounds([inner])
                            good = abs(inner_lo[2]) < TOL and (
                                inner_hi[0] < low[0] if sign > 0 else inner_lo[0] > high[0])
                        check("dual_contact_" + name, good)
            if prefix == "Police":
                for name in ("Red","Blue"):
                    control = get("Lightbar_" + name)
                    check("emitter_" + name, independent(control) and len(control.children) == 4
                          and all(o.type == "MESH" and o.active_material.name == prefix+"_Mat_"+name.lower()
                                  and o.active_material.node_tree.nodes.get("Principled BSDF")
                                  .inputs["Emission Strength"].default_value > 0
                                  for o in control.children))
                for side in ("L","R"):
                    text = get("POLICE_" + side)
                    check("lettering_" + side, text is not None and text.type == "FONT"
                          and text.data.body == "POLICE" and get("Shield_" + side) is not None)
        else:
            for name, axis, axis_index in (("Main","Z",2),("Tail","X",0)):
                control = get(name + "Rotor")
                blades = [get(f"{name}Blade_{i}") for i in range(1,5)]
                valid = independent(control) and all(b is not None and b.parent == control and
                                                      b.children for b in blades)
                check(name + "_blades", valid)
                check(name + "_spin", valid and control.get("spin_axis") == "local " + axis
                      and spin(control,blades[0],axis_index))
            for side in ("L","R"):
                runner = get("Ground_runner_" + side)
                check("skid_contact_" + side, runner is not None and
                      abs(bounds([runner])[0][2]) < .0015)
            cabin = get("Cabin_shell")
            boom = get("Tapered_tail_boom")
            if cabin is not None and boom is not None:
                lower,upper = bounds([cabin,boom])
                check("fuselage_length", 9.7 <= upper[1]-lower[1] <= 10.3)
            else:
                check("fuselage_length", False)
    finally:
        collection.hide_viewport = hidden
        bpy.context.view_layer.update()


def main(report):
    checks = report["checks"]

    def check(name, result):
        checks[name] = bool(result)

    def inspect(hero, label):
        bpy.context.view_layer.update()
        objects = list(hero.objects)
        root = hero.objects.get("Hero_Root")
        check(label + "_root_at_origin", root is not None and root.type == "EMPTY"
              and root.parent is None and root.matrix_world.translation.length < TOL)
        check(label + "_names", all(o.name.startswith("Hero_") for o in objects))
        meshes = [o for o in objects if o.type == "MESH"]
        check(label + "_mesh_parentage", bool(root and meshes) and
              all(descendants_of(o,root) for o in meshes))
        check(label + "_all_parentage", bool(root) and
              all(o == root or descendants_of(o, root) for o in objects))

        depsgraph = bpy.context.evaluated_depsgraph_get()
        lower, upper = evaluated_bounds(objects, depsgraph)
        lo, hi = ([value for value, _ in limits] for limits in (lower, upper))
        report[label + "_bounds_m"] = {
            axis: {"min": low[0], "min_object": low[1],
                   "max": high[0], "max_object": high[1]}
            for axis, low, high in zip("xyz", lower, upper)
        }
        width, length, height = [b-a for a,b in zip(lo,hi)]
        report[label + "_dimensions_m"] = {"width": width, "length": length, "height": height}
        check(label + "_dimensions", 1.90 <= width <= 2.10 and
              4.65 <= length <= 4.95 and 1.12 <= height <= 1.22 and
              abs(lo[2]) < TOL and hi[2] <= 1.22)
        independent = ("Body","Glass","Headlights","Taillights",
                       "Wheel_Front_L","Wheel_Front_R","Wheel_Rear_L","Wheel_Rear_R")
        for name in independent:
            group = hero.objects.get("Hero_" + name)
            valid = bool(root and group and group.type == "EMPTY" and group.parent == root
                         and group.children)
            check(f"{label}_independent_{name}", valid)
            if not name.startswith("Wheel_") or not valid:
                continue
            tire = hero.objects.get("Hero_Tire_" + name.removeprefix("Wheel_"))
            if tire is None:
                check(f"{label}_contact_{name}", False)
                continue
            contact = min((tire.matrix_world @ v.co).z for v in tire.data.vertices)
            report.setdefault(label + "_contacts_m", {})[name] = contact
            check(f"{label}_contact_{name}", tire.parent == group and abs(contact) < TOL
                  and math.isclose(group.location.z, .36, abs_tol=TOL))
            before = tire.matrix_world.copy()
            group.rotation_euler.x += .37
            bpy.context.view_layer.update()
            after = tire.matrix_world.copy()
            axis = group.matrix_world.to_3x3() @ Vector((1,0,0))
            check(f"{label}_spin_{name}", (axis-Vector((1,0,0))).length < TOL
                  and (before.translation-after.translation).length < TOL
                  and (before.col[2]-after.col[2]).length > .3)
            group.rotation_euler.x -= .37
            bpy.context.view_layer.update()
        front = hero.objects.get("Hero_Wheel_Front_L")
        rear = hero.objects.get("Hero_Wheel_Rear_L")
        check(label + "_forward_axis", bool(front and rear) and front.location.y > 0 > rear.location.y)

    builders = runpy.run_path(str(HERE / "build_assets.py"))
    build_hero = builders["build_hero"]
    initial = bpy.data.collections.get("Hero")
    check("saved_hero_exists", initial is not None)
    if initial is not None:
        check("saved_hero_visible", not initial.hide_viewport and not initial.hide_render)
        inspect(initial, "saved")

    probe = bpy.data.collections.new("STRAY Validation Probe")
    bpy.context.scene.collection.children.link(probe)
    witness = bpy.data.objects.new("STRAY Validation Witness", None)
    probe.objects.link(witness)
    foreign_scene = bpy.data.scenes.new("STRAY Validation Foreign Scene")
    foreign_scene.collection.children.link(probe)
    try:
        original = data_inventory(initial)
        hero = build_hero()
        first = shape_inventory(hero)
        check("other_data_preserved_first_build", original == data_inventory(hero))
        inspect(hero, "built")
        second = build_hero()
        check("hero_collection_reused", hero == second)
        check("idempotent_object_inventory", first == shape_inventory(second))
        check("idempotent_hero_collection_count",
              sum(c.name == "Hero" or c.name.startswith("Hero.") for c in bpy.data.collections) == 1)
        check("other_data_preserved_second_build", original == data_inventory(second))
        inspect(second, "rebuilt")
        for collection_name, builder in (("Police", "build_police"),
                                         ("Heli", "build_helicopter"),
                                         ("Truck", "build_tanker")):
            saved = bpy.data.collections.get(collection_name)
            check(f"{collection_name}_saved_exists", saved is not None)
            if saved is not None:
                check(f"{collection_name}_saved_hidden", saved.hide_viewport and saved.hide_render)
                inspect_fleet(saved, "saved", report)
            original = data_inventory(saved)
            fleet = builders[builder]()
            first = shape_inventory(fleet)
            check(f"{collection_name}_foreign_data_after_build", original == data_inventory(fleet))
            inspect_fleet(fleet, "built", report)
            # A user-added object linked directly into an owned collection must survive too.
            fleet.objects.link(witness)
            try:
                rebuilt = builders[builder]()
                check(f"{collection_name}_local_foreign_object_preserved",
                      rebuilt.objects.get(witness.name) == witness)
            finally:
                if fleet.objects.get(witness.name) == witness:
                    fleet.objects.unlink(witness)
            check(f"{collection_name}_collection_reused", rebuilt == fleet)
            check(f"{collection_name}_idempotent_inventory", first == shape_inventory(rebuilt))
            check(f"{collection_name}_collection_count",
                  sum(c.name == collection_name or c.name.startswith(collection_name + ".")
                      for c in bpy.data.collections) == 1)
            check(f"{collection_name}_foreign_data_after_rebuild", original == data_inventory(rebuilt))
            inspect_fleet(rebuilt, "rebuilt", report)
    finally:
        bpy.data.scenes.remove(foreign_scene)
        bpy.data.objects.remove(witness, do_unlink=True)
        bpy.data.collections.remove(probe)


if __name__ == "__main__":
    report = {"checks": {}}
    try:
        main(report)
    except Exception:
        report["error"] = traceback.format_exc()
    report["passed"] = bool(report["checks"]) and all(report["checks"].values()) and "error" not in report
    path = HERE / "validation.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(f"Validation {'passed' if report['passed'] else 'failed'} — {path}")
    if not report["passed"]:
        failed = [name for name, result in report["checks"].items() if not result]
        raise RuntimeError(report.get("error") or ", ".join(failed))
