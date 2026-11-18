"""Material-only night look for an existing, local STRAY Hero hierarchy."""

import bpy


def apply_hero_night_materials(*, glass="clear", root=None):
    """Return paint/glass Material datablocks keyed by role.

    "clear" uses low-roughness transmission for the existing single-surface
    panes. "dark" uses the opaque glass look from render_hero_night.py.
    Pass the root explicitly if Blender renamed an appended Hero.
    """
    if glass not in {"clear", "dark"}:
        raise ValueError("glass must be 'clear' or 'dark'")
    if root is None:
        root = bpy.data.objects.get("Hero_Root")
    if root is None:
        raise ValueError("Append Hero or open assets.blend first")
    hero = set(root.children_recursive)
    settings = {
        "paint": ((.008, .009, .011, 1), .34, .05, .19, 0, 1.45),
        "glass": ((.97, .99, 1, 1), .025, 0, .5, 1, 1.04)
        if glass == "clear" else ((.003, .005, .008, 1), .23, 0, .16, 0, 1.45),
    }

    changed = {}
    for role, values in settings.items():
        base = f"Hero_Mat_{role}"
        slots = [
            slot for obj in sorted(hero, key=lambda obj: obj.name)
            for slot in obj.material_slots
            if slot.material and (
                slot.material.name == base
                or slot.material.name.startswith(base + ".")
                or slot.material.get("stray_night_role") == role
            )
        ]
        sources = {slot.material for slot in slots}
        if not sources:
            raise ValueError(f"No {base} material in {root.name}")
        # Isolate this Hero when another object uses its material. Object-linked
        # overrides also protect foreign objects using the same mesh datablock.
        foreign = {
            slot.material for obj in bpy.data.objects if obj not in hero
            for slot in obj.material_slots if slot.material in sources
        }
        material = slots[0].material
        if material in foreign or material.library:
            material = material.copy()
            material["stray_night_role"] = role
        for slot in slots:
            if slot.material != material:
                slot.link = "OBJECT"
                slot.material = material

        color, roughness, metallic, specular, transmission, ior = values
        material.diffuse_color = color
        shader = material.node_tree.nodes["Principled BSDF"]
        for name, value in {
            "Base Color": color,
            "Roughness": roughness,
            "Metallic": metallic,
            "Specular IOR Level": specular,
            "Coat Weight": 0.0,
            "Transmission Weight": transmission,
            "IOR": ior,
            "Alpha": 1.0,
        }.items():
            shader.inputs[name].default_value = value
        changed[role] = material
    return changed
