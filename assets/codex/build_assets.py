"""Procedural STRAY vehicle fleet and optional studio renders for Blender 4.5."""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OWNER = "STRAY procedural assets"
TAU = math.tau
AXLES = (-1.49, 1.48)
RADIUS = 0.36
HUB_X = 0.835
SIDES = ((-1, "L"), (1, "R"))


def owned_collection(name, scene):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        collection["owner"] = OWNER
    elif collection.get("owner") != OWNER:
        raise RuntimeError(f"Collection {name!r} already exists and is not owned by this script")
    # Keep the collection ID and its existing links for callers that instance it.
    orphaned_data = []
    for obj in list(collection.objects):
        if obj.get("owner") != OWNER:
            continue
        if len(obj.users_collection) > 1:
            collection.objects.unlink(obj)
            continue
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0 and data.get("owner") == OWNER:
            orphaned_data.append(data)
    if orphaned_data:
        # Remove by ID so Blender resolves the datablock type, including TextCurve.
        bpy.data.batch_remove(ids=orphaned_data)
    if collection.name not in scene.collection.children:
        scene.collection.children.link(collection)
    return collection


def material(name, color, metallic=0, roughness=.3, coat=0, glow=0, specular=.5, *, prefix="Hero"):
    name = prefix + "_Mat_" + name
    mat = bpy.data.materials.get(name)
    if mat is not None and mat.get("owner") != OWNER:
        raise RuntimeError(f"Material name collision: {name}")
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat["owner"] = OWNER
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    for key, value in {
        "Base Color": (*color, 1), "Metallic": metallic, "Roughness": roughness,
        "Coat Weight": coat, "Coat Roughness": roughness, "Transmission Weight": 0,
        "Specular IOR Level": specular,
        "Emission Color": (*color, 1), "Emission Strength": glow,
    }.items():
        shader.inputs[key].default_value = value
    return mat


class Geometry:
    def __init__(self, collection, prefix):
        self.collection = collection
        self.prefix = prefix

    def object(self, name, data=None, parent=None, location=(0, 0, 0)):
        if data is not None:
            data["owner"] = OWNER
        obj = bpy.data.objects.new(self.prefix + name, data)
        obj["owner"] = OWNER
        self.collection.objects.link(obj)
        obj.parent = parent
        obj.location = location
        return obj

    def mesh(self, name, verts, faces, mat, parent=None, smooth=False):
        data = bpy.data.meshes.new(self.prefix + name)
        data.from_pydata(verts, [], faces)
        data.update()
        data.materials.append(mat)
        if smooth:
            for face in data.polygons:
                face.use_smooth = True
        return self.object(name, data, parent)

    def strip(self, name, rows, mat, parent=None, smooth=False, flip=False, creases=()):
        stride = len(rows[0])
        faces = []
        for i in range(len(rows) - 1):
            for j in range(stride - 1):
                k = i * stride + j
                face = (k, k + 1, k + 1 + stride, k + stride)
                faces.append(face[::-1] if flip else face)
        obj = self.mesh(name, [v for row in rows for v in row], faces, mat, parent, smooth)
        if creases:
            for edge in obj.data.edges:
                a, b = edge.vertices
                if a % stride == b % stride and a % stride in creases:
                    edge.use_edge_sharp = True
        return obj

    def plate(self, name, outline, offset, mat, parent, bevel=0):
        n = len(outline)
        vertices = outline + [tuple(Vector(v) + Vector(offset)) for v in outline]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
        obj = self.mesh(name, vertices, faces, mat, parent)
        # Recalculate winding for outlines authored on either side of the car.
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
        if bevel:
            modifier = obj.modifiers.new("Machined edges", "BEVEL")
            modifier.width = bevel
            modifier.segments = 2
            obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
        return obj

    def line(self, name, coords, radius, mat, parent):
        data = bpy.data.curves.new(self.prefix + name, "CURVE")
        data.dimensions = "3D"
        data.bevel_depth = radius
        data.bevel_resolution = 2
        data.use_fill_caps = True
        spline = data.splines.new("POLY")
        spline.points.add(len(coords) - 1)
        for point, xyz in zip(spline.points, coords):
            point.co = (*xyz, 1)
        data.materials.append(mat)
        return self.object(name, data, parent)


# Longitudinal coachwork stations. Each row holds Y, shoulder half-width,
# center height, shoulder height and the depth of the undercut.
STATIONS = (
    (-2.40, .76, .685, .637, .24),
    (-2.30, .88, .753, .712, .23),
    (-2.10, .95, .799, .756, .18),
    (-1.71, .982, .836, .782, .18),
    (-1.46, .992, .846, .795, .18),
    (-1.15, .947, .828, .777, .19),
    (-.89, .878, .796, .750, .20),
    (-.57, .821, .765, .723, .21),
    (-.20, .795, .758, .713, .20),
    (.25, .806, .756, .709, .18),
    (.60, .843, .754, .714, .175),
    (.95, .911, .749, .723, .17),
    (1.20, .961, .755, .749, .18),
    (1.48, .985, .766, .774, .18),
    (1.72, .968, .733, .743, .18),
    (1.97, .922, .673, .686, .17),
    (2.19, .862, .578, .604, .16),
    (2.38, .752, .488, .524, .17),
    (2.40, .684, .459, .488, .18),
)


def section(y):
    for a, b in zip(STATIONS, STATIONS[1:]):
        if y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return tuple(p + (q - p) * t for p, q in zip(a[1:], b[1:]))
    return STATIONS[-1][1:]


# Hem follows each tire opening in the Y/Z plane. X follows the bulging
# shoulder, then the arch return moves inward into the wheel well.
ARCH_R = .398
ARCH_CENTER_Z = .354
ARCH_SPAN = .43


def hem(y):
    d = min(abs(y - a) for a in AXLES)
    if d <= ARCH_SPAN:
        angle = math.acos(d / ARCH_SPAN)
        return ARCH_CENTER_Z + ARCH_R * math.sin(angle)
    if d < ARCH_SPAN + .135:
        t = (d - ARCH_SPAN) / .135
        return ARCH_CENTER_Z * (1 - t) + .182 * t
    return .182


def flank(y, t, sign):
    width, _, shoulder, undercut = section(y)
    flare = max(0, 1 - min(abs(y - a) for a in AXLES) / .55)
    z = shoulder * (1 - t) + hem(y) * t
    x = width - (undercut * .54 * (1 - flare) - .002 * flare) * t
    return (sign * x, y, z)


DECK_CROSS = (-1, -.91, -.79, -.67, -.46, -.22, 0, .22, .46, .67, .79, .91, 1)


def deck(y, t):
    width, crown, shoulder, _ = section(y)
    u = abs(t)
    z = crown + (shoulder - crown) * u ** 1.65
    z += .015 * max(0, 1 - abs(u - .79) / .21)
    return (width * t, y, z)


def coachwork(g, body, m):
    ys = {r[0] for r in STATIONS}
    ys.update(-2.4 + 4.8 * i / 96 for i in range(97))
    for a in AXLES:
        ys.update(a + ARCH_SPAN * math.cos(math.pi * i / 36) for i in range(37))
        ys.update((a - ARCH_SPAN - .135, a + ARCH_SPAN + .135))
    ys = sorted(set(round(y, 8) for y in ys))

    g.strip("Sculpted_deck", [[deck(y, t) for t in DECK_CROSS] for y in ys],
            m["paint"], body, smooth=True, creases=(2, 10))
    for s, side in SIDES:
        g.strip("Haunch_" + side, [[flank(y, t, s) for t in (0, 1)] for y in ys],
                m["paint"], body, smooth=True, flip=s < 0)
        lip = []
        for y in ys:
            x, _, z = flank(y, 1, s)
            lip.append([(x, y, z), (x - s * .023, y, z - .012),
                        (x - s * .146, y, z - .018)])
        g.strip("Hem_and_wheelwell_" + side, lip, m["carbon"], body, flip=s < 0)
        for j, axle in enumerate(AXLES):
            rail = []
            for i in range(49):
                y = axle + ARCH_SPAN * math.cos(math.pi * i / 48)
                x, _, z = flank(y, 1, s)
                rail.append([(x + s * .001, y, z + .006),
                             (x - s * .018, y, z - .006)])
            g.strip(f"Arch_edge_{side}_{j}", rail, m["edge"], body, flip=s < 0)

        door = [(-.94, .23), (-.73, .18), (.44, .13), (.72, .20), (.78, .32),
                (.67, .70), (.47, .83), (-.67, .86), (-.89, .71), (-.94, .23)]
        coords = []
        for (y0, t0), (y1, t1) in zip(door, door[1:]):
            for i in range(12):
                f = i / 12
                x, y, z = flank(y0 + (y1 - y0) * f, t0 + (t1 - t0) * f, s)
                coords.append((x + s * .003, y, z))
        coords.append(coords[0])
        g.line("Door_shutline_" + side, coords, .0037, m["void"], body)
        x, y, z = flank(-.61, .27, s)
        g.line("Flush_latch_" + side, [(x+s*.007, y-.066, z), (x+s*.007, y+.061, z+.009)],
               .008, m["edge"], body)
        # A floating rocker blade sits below the side cooling inlet.
        g.plate("Rocker_blade_" + side, [(s*x, y, z) for x, y, z in (
            (.84, -1.015, .214), (.893, -.79, .178), (.834, .53, .179),
            (.866, .947, .226), (.718, .86, .245), (.693, -.86, .246))],
            (0, 0, -.029), m["carbon"], body, .009)
        inlet_profile = [(-.89, .32, .63), (-.57, .40, .72), (-.15, .57, .72), (.04, .72, .72)]

        def intake_point(y, t):
            x, _, z = flank(y, t, s)
            return (x + s * .009, y, z)

        inlet_rows = []
        for (y0, top0, bottom0), (y1, top1, bottom1) in zip(inlet_profile, inlet_profile[1:]):
            for y in [y0] + [y for y in ys if y0 < y < y1]:
                f = (y-y0)/(y1-y0)
                inlet_rows.append([intake_point(y, top0+(top1-top0)*f),
                                   intake_point(y, bottom0+(bottom1-bottom0)*f)])
        tip = intake_point(.04, .72)
        verts = [v for row in inlet_rows for v in row] + [tip]
        faces = [(i, i+1, i+3, i+2) for i in range(0, len(verts)-3, 2)]
        faces.append(tuple(range(len(verts)-3, len(verts))))
        g.mesh("Side_intake_" + side, verts, faces if s > 0 else [f[::-1] for f in faces],
               m["void"], body, smooth=True)
        g.line("Intake_blade_" + side, [row[0] for row in inlet_rows] + [tip],
               .009, m["edge"], body)
        for i in range(3):
            y = -.78 + i * .069
            pts = [flank(y + dy, t, s) for dy, t in ((0, .46), (.055, .65))]
            g.line(f"Intake_vane_{side}_{i}", [(x+s*.017, yy, z) for x, yy, z in pts],
                   .007, m["carbon"], body)

    # Bounded undertray leaves the wheel envelopes open from below.
    g.plate("Undertray", [(-.57, -2.22, .178), (.57, -2.22, .178), (.62, -.94, .178),
                         (.62, .96, .178), (.55, 2.27, .178), (-.55, 2.27, .178),
                         (-.62, .96, .178), (-.62, -.94, .178)],
            (0, 0, -.025), m["carbon"], body, .018)
    # Bonnet seams and opposing radiator louvers follow the surface.
    for s, side in SIDES:
        g.line("Bonnet_seam_" + side, [
            (x, y, z+.003) for x, y, z in
            [deck(.68 + i * .034, s * (.58 - .18*i/43)) for i in range(44)]
        ], .0033, m["void"], body)
        for i in range(5):
            y = 1.11 + i * .064
            vertices = []
            for yy, tx in ((y, .71), (y+.027, .70), (y+.080, .89), (y+.053, .90)):
                x, _, z = deck(yy, tx*s)
                vertices.append((x, yy, z+.007))
            g.plate(f"Fender_louver_{side}_{i}", vertices, (0, 0, -.012),
                    m["void"], body, .003)
        for i in range(5):
            y = -1.97 + i*.065
            coords = [deck(y + .075*u, s*(.12+.39*u)) for u in (0, .45, 1)]
            g.line(f"Engine_louver_{side}_{i}", [(x, yy, z+.009) for x, yy, z in coords],
                   .011, m["carbon"], body)


def canopy(g, body, root, m):
    glass = g.object("Glass", parent=root)
    # Y, roof half-width, apex, roof edge, sill Y, sill half-width, sill height.
    profiles = [
        (-1.35, .30, .860, .835, -1.41, .505, .813),
        (-1.09, .43, .999, .954, -1.16, .584, .811),
        (-.79, .485, 1.127, 1.078, -.87, .636, .799),
        (-.59, .501, 1.181, 1.129, -.64, .654, .780),
        (-.28, .510, 1.200, 1.147, -.28, .667, .762),
        (.035, .496, 1.191, 1.137, .09, .661, .760),
        (.22, .471, 1.158, 1.105, .32, .648, .756),
    ]

    def roof(r, u):
        y, width, apex, edge, *_ = r
        return (width*u, y, apex + (edge-apex)*abs(u)**2)

    def side(r, s, t):
        y, w, _, edge, sy, sw, z = r
        return (s*(w+(sw-w)*t+.018*math.sin(math.pi*t)), y+(sy-y)*t,
                edge+(z-edge)*t)

    def blend(a, b, t):
        return tuple(x+(y-x)*t for x, y in zip(a, b))

    cross = tuple(i/12 for i in range(-12, 13))
    g.strip("Roof_shell", [[roof(r, u) for u in cross] for r in profiles[2:]],
            m["paint"], body, True)
    g.strip("Backlight", [[roof(r, u) for u in cross] for r in profiles[:3]],
            m["glass"], glass, True)
    # Bow the panoramic windshield between a low, wide cowl and the roof.
    rows = []
    for i in range(13):
        t = i / 12
        row = []
        for u in cross:
            a = roof(profiles[-1], u)
            b = (.651*u, .929-.238*abs(u)**1.7, .756-.020*abs(u)**2)
            x, y, z = blend(a, b, t)
            bow = math.sin(t*math.pi)
            row.append((x*(1+.035*bow), y+.061*bow*(1-.44*abs(u)), z+.022*bow))
        rows.append(row)
    g.strip("Panoramic_windshield", rows, m["glass"], glass, True)
    for s, label in SIDES:
        ix = 0 if s == -1 else -1
        a_edge = [row[ix] for row in rows]
        g.line("A_pillar_" + label, a_edge, .014, m["paint"], body)
        for n, (a, b) in enumerate(zip(profiles, profiles[1:])):
            window_rows = [[side(blend(a, b, i/6), s, j/6) for j in range(7)]
                           for i in range(7)]
            g.strip(f"Side_glass_{label}_{n}", window_rows,
                    m["paint"] if n == 0 else m["glass"], body if n == 0 else glass,
                    True, flip=s < 0)
        # A triangular pane closes the windshield return down to the cowl.
        a, b = a_edge[0], side(profiles[-1], s, 1)
        c = a_edge[-1]
        return_rows = [
            [blend(p, blend(b, c, i/12), j/6) for j in range(7)]
            for i, p in enumerate(a_edge[:-1])
        ]
        obj = g.strip("Quarter_glass_" + label, return_rows, m["glass"], glass,
                      True, flip=s < 0)
        # Cap the final narrow segment with triangles so its tip has no double vertices.
        mesh = obj.data
        verts = [tuple(v.co) for v in mesh.vertices] + [c]
        faces = [tuple(p.vertices) for p in mesh.polygons]
        start = len(verts)-8
        for i in range(6):
            face = (start+i, start+i+1, len(verts)-1)
            faces.append(face[::-1] if s < 0 else face)
        mesh.clear_geometry()
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        for poly in mesh.polygons:
            poly.use_smooth = True
        belt = [side(r, s, 1) for r in profiles] + [c]
        g.line("Window_sill_" + label, belt, .012, m["edge"], body)
        g.line("Roof_rail_" + label, [roof(r, s) for r in profiles], .012, m["paint"], body)
        g.line("B_pillar_" + label, [side(profiles[3], s, t/8) for t in range(9)],
               .013, m["paint"], body)
        # Low-profile camera mirrors on the front window corners.
        g.line("Mirror_stalk_" + label, [(s*.612, .593, .773), (s*.825, .523, .813)],
               .012, m["carbon"], body)
        g.plate("Mirror_pod_" + label, [(s*x, y, z) for x,y,z in (
            (.793,.565,.813), (.840,.563,.834), (.914,.518,.830),
            (.922,.470,.805), (.851,.463,.795), (.804,.497,.797))],
            (0,0,-.027), m["paint"], body, .011)
    g.line("Windshield_lower_trim", rows[-1], .010, m["void"], body)
    g.line("Roof_header", rows[0], .010, m["paint"], body)


def fascia(g, body, root, m):
    front = g.object("Headlights", parent=root)
    rear = g.object("Taillights", parent=root)
    # Nose skin sweeps back around the corners.
    def nose(x, z):
        return x, 2.403-.190*(abs(x)/.86)**2 + .023*(.45-z), z

    def tail(x, z):
        return x, -2.400+.122*(abs(x)/.89)**3 - .020*(.51-z), z

    # X, lower lip, intake sill, intake brow and upper skin. Each opening
    # shares its boundary with the painted bands and has a recessed back.
    nose_half = (
        (0, .191, .231, .365, .456),
        (.115, .190, .227, .365, .457),
        (.36, .190, .229, .376, .465),
        (.59, .197, .240, .391, .481),
        (.73, .217, .262, .398, .500),
        (.85, .267, .284, .419, .525),
    )
    stations = [(-x, *zs) for x, *zs in reversed(nose_half[1:])] + list(nose_half)
    skin = [[nose(x, z) for z in zs] for x, *zs in stations]

    def interpolate(profile, x):
        for a, b in zip(profile, profile[1:]):
            if x <= b[0]:
                t = (x-a[0])/(b[0]-a[0])
                return (x, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)
        return profile[-1]

    leading_edge = [deck(2.40, t) for t in DECK_CROSS]
    # Outside the hood's leading edge, follow the narrowing shoulder.
    for x in (.752, .85):
        a, b = STATIONS[-3:-1]
        y = a[0] + (b[0]-a[0])*(a[1]-x)/(a[1]-b[1])
        leading_edge.append((x, y, deck(y, 1)[2]))
    leading_edge = [(-x, y, z) for x, y, z in reversed(leading_edge[-2:])] + leading_edge
    brow_edge = [row[-1] for row in skin]
    xs = sorted({v[0] for v in leading_edge + brow_edge})
    g.strip("Nose_upper_skin", [[interpolate(brow_edge, x), interpolate(leading_edge, x)]
                                for x in xs], m["paint"], body, smooth=True)

    for name, first, last in (("Brow", 2, 3), ("Lower_lip", 0, 1)):
        g.strip("Nose_" + name, [[row[first], row[last]] for row in skin], m["paint"], body,
                smooth=True)
    g.strip("Nose_bridge", [row[1:3] for row in skin[4:7]], m["paint"], body)
    for s, side in SIDES:
        wing = skin[:2] if s < 0 else skin[-2:]
        g.strip("Nose_wing_" + side, [row[1:3] for row in wing], m["paint"], body)
        opening = [row[1:3] for row in (skin[1:5] if s < 0 else skin[6:10])]
        back = [[(x, y-.09, z) for x, y, z in row] for row in opening]
        g.strip("Front_intake_back_" + side, back, m["void"], body)
        for edge, name in enumerate(("sill", "brow")):
            g.strip(f"Front_intake_{name}_{side}",
                    [[front_row[edge], back_row[edge]] for front_row, back_row in zip(opening, back)],
                    m["carbon"], body, flip=edge == 1)
        for i, name in ((0, "left"), (-1, "right")):
            g.strip(f"Front_intake_{name}_return_{side}", [opening[i], back[i]],
                    m["carbon"], body, flip=i < 0)
        for i, t in enumerate((.25, .50, .75)):
            g.line(f"Front_intake_vane_{side}_{i}", [
                (x, y + (top_y-y)*t-.050, z+(top_z-z)*t)
                for (x, y, z), (_, top_y, top_z) in opening
            ], .004, m["carbon"], body)

    for label, fn, outline, depth, mat in (
        ("Tail_mask", tail, [(-.875,.641),(-.70,.641),(0,.675),(.70,.641),(.875,.641),
                             (.806,.350),(.66,.270),(0,.257),(-.66,.270),(-.806,.350)], .13, "paint"),
        ("Rear_extraction_grille", tail, [(-.79,.493),(0,.487),(.79,.493),(.716,.361),
                                         (.53,.310),(-.53,.310),(-.716,.361)], .023, "void"),
    ):
        outline = [fn(x, z) for x, z in outline]
        # Use a tessellated fan for the curved fascia surfaces.
        ctr = tuple(sum(v[i] for v in outline)/len(outline) for i in range(3))
        offset_y = -.010 if label == "Rear_extraction_grille" else 0
        outline = [(x, y+offset_y, z) for x, y, z in outline]
        center_pos = fn(ctr[0], ctr[2])
        ctr = (center_pos[0], center_pos[1]+offset_y, center_pos[2])
        n = len(outline)
        verts = outline + [ctr] + [(x, y+depth, z) for x,y,z in outline]
        faces = [(i, (i+1)%n, n) for i in range(n)]
        faces += [(i, n+1+i, n+1+(i+1)%n, (i+1)%n) for i in range(n)]
        if depth > 0:
            faces = [f[::-1] for f in faces]
        g.mesh(label, verts, faces, m[mat], body)

    for i in range(5):
        g.line(f"Tail_grille_horizontal_{i}", [
            (x, y-.015, zz) for x,y,zz in [tail(j*(.60+i*.037)/12,.359+i*.027)
                                           for j in range(-12,13)]
        ], .004, m["edge"], body)

    for s, side in SIDES:
        # Double swept signatures run back along the shoulders.
        for i, points in enumerate((
            [(.478,2.355,.525),(.620,2.317,.548),(.740,2.252,.582),(.830,2.157,.629)],
            [(.566,2.379,.503),(.691,2.327,.530),(.791,2.258,.562),(.865,2.176,.609)],
        )):
            xyz = [(s*x,y,z) for x,y,z in points]
            g.line(f"Headlight_pocket_{side}_{i}", xyz, .023, m["void"], body)
            g.line(f"Headlight_blade_{side}_{i}", [(x,y+.014,z+.005) for x,y,z in xyz],
                   .0095 if i == 0 else .006, m["white"], front)
        g.line("Cyan_corner_marker_" + side,
               [(s*.849,2.151,.637),(s*.877,2.110,.655)], .006, m["cyan"], front)
        for i in range(4):
            y = -2.27 + i*.058
            g.line(f"Tail_side_gill_{side}_{i}", [(s*(.886+i*.013),y,.555),
                                                  (s*(.839+i*.013),y-.011,.381)],
                   .008, m["void"], body)
        g.plate("Splitter_end_fence_" + side, [(s*x,y,z) for x,y,z in (
            (.827,2.223,.158),(.896,2.11,.162),(.899,2.043,.294),(.856,2.166,.247))],
            (-s*.025,0,0), m["carbon"], body, .006)
    g.plate("Front_splitter", [(x,y,.175) for x,y in (
        (-.88,2.130),(-.71,2.302),(-.30,2.392),(.30,2.392),(.71,2.302),
        (.88,2.130),(.80,2.03),(-.80,2.03))], (0,0,-.033), m["carbon"], body,.011)
    g.plate("Diffuser_ramp", [(x,y,z) for x,y,z in (
        (-.755,-2.34,.250),(-.59,-2.38,.261),(.59,-2.38,.261),(.755,-2.34,.250),
        (.66,-1.83,.145),(-.66,-1.83,.145))], (0,0,-.035), m["carbon"], body,.009)
    for i, x in enumerate((-.70,-.49,-.26,0,.26,.49,.70)):
        tip = -2.385 + abs(x)*.10
        g.plate(f"Diffuser_strake_{i}", [(x, tip, .264),(x,tip,.122),(x,-2.17,.087),
                                           (x,-1.86,.122),(x,-1.86,.162)],
                (.021,0,0), m["carbon"], body,.005)
    for i, end in enumerate((.803, .713)):
        coords = [tail(end*j/30, .575-i*.022+.033*abs(j/30)**3) for j in range(-30,31)]
        if i == 0:
            g.line("Tail_light_channel", [(x,y-.015,z-.007) for x,y,z in coords],
                   .031, m["void"], body)
        g.line(f"Tail_light_bar_{i}", [(x,y-.039,z) for x,y,z in coords],
               .009 if i == 0 else .004, m["red"], rear)
    for s, side in SIDES:
        x, y, z = tail(s*.811,.605)
        g.line("Magenta_corner_marker_" + side, [(x,y-.040,z),(s*.842,y+.009,z+.012)],
               .005, m["magenta"], rear)
    g.line("Nose_signature", [(-.038,2.397,.472),(0,2.407,.457),(.038,2.397,.472)],
           .006, m["edge"], body)


def wheels(g, root, body, m):
    def ring(name, profile, mat, parent, sign, steps=96):
        rows = [[(sign*x, r*math.cos(TAU*i/steps), r*math.sin(TAU*i/steps))
                 for i in range(steps)] for x, r in profile]
        verts = [v for row in rows for v in row]
        faces = []
        for j in range(len(rows)-1):
            for i in range(steps):
                a = j*steps+i
                b = j*steps+(i+1)%steps
                face = (a,b,b+steps,a+steps)
                faces.append(face if sign > 0 else face[::-1])
        return g.mesh(name, verts, faces, mat, parent, True)

    for axle, y in zip(("Rear","Front"), AXLES):
        for s, side in SIDES:
            label = axle + "_" + side
            location = (s*HUB_X,y,RADIUS)
            spin = g.object("Wheel_" + label, parent=root, location=location)
            spin.empty_display_type = "CIRCLE"
            spin.empty_display_size = .13
            spin.rotation_mode = "XYZ"
            spin["spin_axis"] = "local X"
            carrier = g.object("Brake_carrier_" + label, parent=body, location=location)
            ring("Tire_" + label, [
                (-.173,.260),(-.177,.304),(-.156,.339),(-.131,.354),(-.099,.360),
                (.081,.360),(.110,.357),(.135,.345),(.153,.322),(.158,.286),
                (.148,.257),(.112,.254),(-.155,.254),(-.173,.260)],
                m["rubber"],spin,s)
            ring("Sidewall_rib_" + label, [(.153,.295),(.160,.300),(.156,.304),
                 (.153,.300),(.153,.295)],m["rubber_edge"],spin,s)
            ring("Forged_barrel_" + label, [
                (-.15,.248),(-.14,.258),(.126,.258),(.156,.263),(.163,.255),
                (.164,.240),(.145,.232),(.095,.235),(-.15,.233),(-.15,.248)],
                m["rim"],spin,s)
            ring("Diamond_cut_rim_" + label, [(.156,.255),(.164,.255),(.169,.251),
                 (.168,.242),(.163,.240),(.158,.246),(.156,.255)],m["edge"],spin,s)
            ring("Ventilated_rotor_" + label, [(.038,.076),(.038,.193),(.052,.211),
                 (.075,.210),(.078,.202),(.078,.082),(.063,.074),(.038,.076)],
                 m["steel"],spin,s)
            ring("Rotor_hat_" + label, [(.067,.022),(.067,.091),(.079,.086),(.106,.071),
                 (.116,.058),(.116,.002),(.067,.002),(.067,.022)],m["rim"],spin,s)
            ring("Center_lock_" + label, [(.116,.003),(.116,.054),(.136,.057),(.152,.044),
                 (.156,.022),(.156,.002),(.116,.002),(.116,.003)],
                 m["edge"],spin,s,12)
            ring("Center_cap_" + label, [(.154,.001),(.154,.021),(.158,.021),(.161,.001)],
                 m["rim"],spin,s,24)

            def polar(x, r, angle):
                return (s*x,r*math.cos(angle),r*math.sin(angle))

            # Swept, forked spokes. The polished fork and dark inner flank
            # have separate faces and the caliper stays fixed behind them.
            for i in range(6):
                a = TAU*i/6
                for branch in (-1,1):
                    outline = [polar(x,r,a+b*branch) for x,r,b in (
                        (.137,.046,-.14),(.148,.089,-.10),(.157,.167,.105),
                        (.161,.241,.252),(.157,.248,.370),(.154,.173,.280),
                        (.143,.082,.145))]
                    g.plate(f"Spoke_{label}_{i}_{branch:+}",outline,(-s*.029,0,0),
                            m["rim"],spin,.006)
                    g.line(f"Spoke_highlight_{label}_{i}_{branch:+}",
                           [polar(x,r,a+b*branch) for x,r,b in (
                               (.152,.092,-.06),(.162,.167,.130),(.165,.235,.264))],
                           .0025,m["edge"],spin)
            verts, faces = [], []
            for i in range(24):
                for j in range(2):
                    a = TAU*i/24 + j*.077
                    r = .175+j*.017
                    center = len(verts)
                    verts.append(polar(.079,r,a))
                    verts.extend((s*.079,r*math.cos(a)+.0032*math.cos(TAU*k/8),
                                  r*math.sin(a)+.0032*math.sin(TAU*k/8)) for k in range(8))
                    for k in range(8):
                        edge = (center,center+1+k,center+1+(k+1)%8)
                        faces.append(edge if s>0 else edge[::-1])
            g.mesh("Rotor_drill_pattern_" + label,verts,faces,m["void"],spin)
            a = 2.61 if axle == "Front" else .55
            g.plate("Fixed_caliper_" + label, [polar(.091,r,a+t) for r,t in (
                (.167,-.29),(.221,-.35),(.232,-.19),(.232,.20),(.215,.32),(.172,.27))],
                (-s*.059,0,0),m["caliper"],carrier,.009)
            g.line("Caliper_inlay_" + label, [polar(.095,.205,a+t) for t in (-.17,-.10,0,.1,.17)],
                   .0037, m["edge"], carrier)

            # Incised tread accents sit on the four tire bands. Radius is
            # capped at the contact radius, including at the six-o'clock vertex.
            verts, faces = [], []
            for i in range(64):
                a = TAU*i/64
                for x0,x1,r0,r1,skew in ((-.152,-.108,.343,.359,.047),
                        (-.101,-.014,.360,.360,-.055),(.011,.078,.360,.360,-.051),
                        (.087,.129,.360,.350,.047)):
                    start = len(verts)
                    for x,r,t in ((x0,r0,-.006),(x1,r1,skew-.006),
                                  (x1,r1,skew+.006),(x0,r0,.006)):
                        px, py, pz = polar(x,r+.0011,a+t)
                        verts.append((px,py,max(-RADIUS,pz)))
                    face = tuple(range(start,start+4))
                    faces.append(face if s>0 else face[::-1])
            g.mesh("Tread_sipes_" + label,verts,faces,m["void"],spin)
            for j, angle in enumerate((.21,2.31,4.40)):
                g.line(f"Sidewall_index_{label}_{j}",
                       [polar(.157,.309,angle+t) for t in (-.032,0,.032)],
                       .0018,m["rubber_edge"],spin)


def build_hero():
    """Build the Hero collection in the active scene and return the collection."""
    g = Geometry(owned_collection("Hero", bpy.context.scene), "Hero_")
    palette = {
        "paint": ((.009,.011,.015),.30,.33,.10,0,.24),
        "edge": ((.070,.085,.107),.65,.30,.12),
        "carbon": ((.018,.023,.032),.31,.36,.10),
        "void": ((.003,.004,.006),.06,.52),
        "glass": ((.003,.008,.015),0,.205,.035,0,.15),
        "rim": ((.105,.126,.153),.87,.246,.23),
        "steel": ((.259,.278,.297),.72,.37),
        "caliper": ((.125,.031,.058),.51,.31,.30),
        "rubber": ((.013,.015,.019),0,.56),
        "rubber_edge": ((.027,.031,.036),0,.48),
        "white": ((.72,.89,1.0),.16,.20,.2,4.0),
        "red": ((.73,.009,.027),.13,.22,.2,3.8),
        "cyan": ((.011,.64,.84),.20,.25,.1,2.4),
        "magenta": ((.76,.025,.31),.20,.25,.1,2.1),
    }
    m = {key: material(key, *settings) for key, settings in palette.items()}
    root = g.object("Root")
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = .42
    root["forward_axis"] = "+Y"
    root["units"] = "meters"
    body = g.object("Body", parent=root)
    coachwork(g,body,m)
    canopy(g,body,root,m)
    fascia(g,body,root,m)
    wheels(g,root,body,m)
    return g.collection


def fleet_base(collection, prefix, paint, accent):
    g = Geometry(owned_collection(collection, bpy.context.scene), prefix + "_")
    root = g.object("Root")
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = .5
    root["forward_axis"] = "+Y"
    root["units"] = "meters"
    palette = {
        "paint": (paint, .26, .27, .29),
        "accent": (accent, .12, .31, .25),
        "trim": ((.020, .025, .032), .28, .39),
        "glass": ((.008, .019, .028), .12, .22, .22),
        "metal": ((.28, .32, .35), .76, .31),
        "rubber": ((.017, .019, .022), 0, .63),
        "red": ((.85, .009, .015), .05, .23, .2, 2.3),
        "blue": ((.015, .12, 1), .08, .22, .2, 3.2),
        "lamp": ((.84, .94, 1), .12, .20, .2, 2.5),
        "amber": ((1, .26, .023), .08, .24, .2, 1.3),
        "cream": ((.86, .79, .60), .1, .32),
        "gold": ((.80, .47, .10), .48, .34),
    }
    return g, root, {k: material(k, *v, prefix=prefix) for k, v in palette.items()}


def panel_box(g, name, center, size, mat, parent, bevel=.025):
    x, y, z = center
    a, b, c = (n / 2 for n in size)
    return g.plate(name, [(x-a,y-b,z-c), (x+a,y-b,z-c),
                          (x+a,y+b,z-c), (x-a,y+b,z-c)],
                   (0,0,2*c), mat, parent, bevel)


def round_profile(y, width, bottom, top, theta, power=1):
    def shape(v):
        return math.copysign(abs(v) ** power, v)

    return (width * shape(math.sin(theta)), y,
            (bottom + top + (top-bottom) * shape(math.cos(theta))) / 2)


def ring_mesh(g, name, rows, mat, parent, caps=True):
    n = len(rows[0])
    faces = [(i*n+j, i*n+(j+1)%n, (i+1)*n+(j+1)%n, (i+1)*n+j)
             for i in range(len(rows)-1) for j in range(n)]
    if caps:
        faces.extend([tuple(reversed(range(n))), tuple(range((len(rows)-1)*n, len(rows)*n))])
    obj = g.mesh(name, [p for row in rows for p in row], faces, mat, parent, smooth=True)
    if caps:
        for face in list(obj.data.polygons)[-2:]:
            face.use_smooth = False
    return obj


def loft(g, name, stations, mat, parent, power=1, count=48):
    return ring_mesh(g, name, [[round_profile(*s, TAU*i/count, power)
                                for i in range(count)] for s in stations], mat, parent)


def tube(g, name, a, b, radius, mat, parent, count=20):
    direction = (Vector(b) - Vector(a)).normalized()
    across = direction.cross(Vector((0,0,1)))
    u = across.normalized() if across.length > 1e-6 else direction.orthogonal().normalized()
    v = direction.cross(u)
    rows = [[tuple(Vector(p) + radius*(u*math.cos(TAU*i/count) + v*math.sin(TAU*i/count)))
             for i in range(count)] for p in (a,b)]
    return ring_mesh(g, name, rows, mat, parent)


def side_text(g, name, text, x, y, z, side, size, mat, parent):
    font = bpy.data.curves.new(g.prefix + name, "FONT")
    font.body = text
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    font.size = size
    font.extrude = .0006
    font.materials.append(mat)
    obj = g.object(name, font, parent, (x, y, z))
    obj.rotation_euler = (math.pi/2, 0, side*math.pi/2)
    return obj


def side_plate(g, name, outline, side, mat, parent, thickness=.014):
    return g.plate(name, outline, (side*thickness,0,0), mat, parent, .006)


def fleet_wheel(g, root, m, axle, side, sign, y, x, radius, width, dual=False):
    label = axle + "_" + side
    control = g.object("Wheel_" + label, parent=root, location=(sign*x,y,radius))
    control["spin_axis"] = "local X"
    profile = ((-.50,.74),(-.53,.87),(-.47,.95),(-.34,1),
               (-.22,1),(.22,1),(.34,1),(.47,.95),(.53,.87),(.50,.74))
    for suffix, center in (("",0),("_Inner",-sign*(width+.028))) if dual else (("",0),):
        rows = [[(center + width*f, radius*r*math.sin(TAU*i/64),
                  radius*r*math.cos(TAU*i/64)) for i in reversed(range(64))] for f,r in (*profile, profile[0])]
        ring_mesh(g, "Tire_" + label + suffix, rows, m["rubber"], control, caps=False)
        tube(g, "Rim_" + label + suffix, (center-width*.48,0,0),
             (center+width*.48,0,0), radius*.735, m["metal"], control, 48)
        for shoulder in (-.29,.29):
            for index in range(24):
                angle = TAU*(index + (.5 if shoulder > 0 else 0))/24
                def tread(f, theta):
                    return (center + width*f, (radius-.0032)*math.sin(theta),
                            (radius-.0032)*math.cos(theta))
                g.line(f"Tread_{label}{suffix}_{shoulder}_{index}",
                       [tread(shoulder-.10, angle-.02), tread(shoulder+.10, angle+.024)],
                       .003, m["trim"], control)
    face = sign*width*.49
    tube(g, "Hub_" + label, (face,0,0), (face+sign*.045,0,0),
         radius*.29, m["trim"], control)
    for index in range(8):
        a = TAU*index/8
        yy, zz = radius*.46*math.sin(a), radius*.46*math.cos(a)
        tube(g, f"Lug_{label}_{index}", (face,yy,zz), (face+sign*.022,yy,zz),
             radius*.049, m["trim"], control, 8)
    return control


def build_police():
    g, root, m = fleet_base("Police", "Police", (.024,.030,.040), (.88,.90,.87))
    brake_lens = material("Brake_lens", (.68,.008,.016), .07, .22, .2, 1.8, prefix="Police")
    body, glass, head, tail = [g.object(n, parent=root) for n in
                               ("Body", "Glass", "Headlights", "Taillights")]
    stations = [(-2.53,.77,.49,.84),(-2.43,.91,.45,.94),(-2.15,.98,.46,.98),
                (-1.55,.99,.53,1.01),(-1.07,.958,.53,1.01),(-.65,.95,.47,1.03),
                (.65,.95,.47,1.03),(1.18,.97,.51,1.00),(1.53,.99,.54,.96),
                (2.12,.97,.45,.91),(2.43,.91,.42,.83),(2.52,.80,.42,.73)]
    # The upper shell clears the tires. Separate lower skins follow each wheel opening.
    loft(g,"Hood_trunk_and_shoulders",[(y,w,.72,t) for y,w,_,t in stations],
         m["paint"],body,.43)
    ys = sorted(set([r[0] for r in stations] + [i*.05 for i in range(-50,51)] +
                    [a+.435*math.cos(math.pi*i/32) for a in (-1.55,1.53) for i in range(33)]))
    for s, side in SIDES:
        rows = []
        for y in ys:
            for a,b in zip(stations,stations[1:]):
                if y <= b[0]:
                    f = (y-a[0])/(b[0]-a[0])
                    w, low = [a[i]+f*(b[i]-a[i]) for i in (1,2)]
                    break
            d = min(abs(y+1.55), abs(y-1.53))
            arch = .365 + .408*math.sqrt(max(0,1-(d/.435)**2))
            bottom = max(.29, low-.15, arch)
            shoulder = next(a[3]+(y-a[0])/(b[0]-a[0])*(b[3]-a[3])
                            for a,b in zip(stations,stations[1:]) if y <= b[0])
            rows.append([(s*w,y,(.72+shoulder)/2), (s*w*.993,y,bottom),
                         (s*(w-.060),y,bottom-.016)])
        g.strip("Wheel_arch_skin_"+side, rows, m["paint"], body, smooth=True, flip=s<0)
        for name, back, front in (("Rear", -1.08,-.27),("Front",-.25,1.05)):
            side_plate(g, f"Door_{name}_{side}", [(s*.955,back,.42),(s*.955,front-.06,.40),
                       (s*.955,front,.864),(s*.955,back,.872)],s,m["accent"],body,.009)
            panel_box(g,f"Handle_{name}_{side}",(s*.975,back+.18,.813),(.023,.16,.035),
                      m["trim"],body,.010)
        side_text(g,"POLICE_"+side,"POLICE",s*.972,.06,.64,s,.29,m["paint"],body)
        shield = [(s*.974,.76,.77),(s*.974,.64,.72),(s*.974,.66,.60),
                  (s*.974,.76,.545),(s*.974,.86,.60),(s*.974,.88,.72)]
        side_plate(g,"Shield_"+side,shield,s,m["gold"],body,.005)
        side_text(g,"Shield_letter_"+side,"P",s*.982,.76,.664,s,.11,m["paint"],body)
        side_text(g,"Unit_"+side,"17",s*.971,-.88,.58,s,.15,m["paint"],body)
        panel_box(g,"Mirror_mount_"+side,(s*.923,.84,1.01),(.21,.11,.055),m["trim"],body)
        panel_box(g,"Mirror_"+side,(s*1.033,.81,1.04),(.17,.17,.105),m["paint"],body,.042)
        for name,y,z,mat,group in (("Headlamp",2.425,.755,m["lamp"],head),
                                    ("Tail_lamp",-2.435,.786,brake_lens,tail)):
            panel_box(g,name+"_"+side,(s*.678,y,z),(.40,.16,.125),mat,group,.035)
        for name,y in (("Front",1.53),("Rear",-1.55)):
            fleet_wheel(g,root,m,name,side,s,y,.824,.354,.237)
    # The opaque glazing forms the sloping greenhouse; pillars overlay its surface.
    loft(g,"Tinted_greenhouse",[(-1.61,.73,.925,.984),(-1.39,.77,.935,1.12),
         (-.87,.755,.935,1.356),(-.63,.749,.933,1.412),(.35,.735,.932,1.432),
         (.66,.738,.925,1.372),(1.18,.782,.911,1.040),(1.27,.77,.91,.973)],
         m["glass"],glass,.34)
    loft(g,"Roof_cap",[(-.89,.56,1.332,1.37),(-.69,.65,1.366,1.435),
         (.32,.64,1.384,1.454),(.58,.55,1.345,1.416)],m["paint"],body,.50)
    for s,side in SIDES:
        for name,coords in (
            ("A",[(s*.777,1.19,1.004),(s*.748,.89,1.213),(s*.708,.55,1.392)]),
            ("B",[(s*.749,-.25,.95),(s*.747,-.24,1.33),(s*.675,-.24,1.423)]),
            ("C",[(s*.767,-1.44,1.049),(s*.768,-1.12,1.234),(s*.672,-.73,1.419)]),
            ("Sill",[(s*.771,-1.4,.952),(s*.762,-.65,.95),(s*.79,1.21,.94)])):
            g.line(f"Pillar_{name}_{side}",coords,.023,m["paint"],body)
        panel_box(g,"Push_upright_"+side,(s*.40,2.57,.596),(.105,.183,.51),m["trim"],body,.036)
    panel_box(g,"Undertray",(0,0,.374),(1.51,4.70,.12),m["trim"],body,.046)
    for s,side in SIDES:
        panel_box(g,"Rocker_"+side,(s*.883,0,.344),(.153,1.97,.095),m["paint"],body,.027)
    panel_box(g,"Front_valance",(0,2.412,.486),(1.76,.244,.223),m["paint"],body,.064)
    panel_box(g,"Front_grille",(0,2.475,.665),(1.01,.13,.27),m["trim"],body,.061)
    for i in range(4):
        panel_box(g,f"Grille_slat_{i}",(0,2.549,.583+i*.05),(.88,.023,.013),m["metal"],body,.004)
    for z in (.444,.733):
        tube(g,f"Push_crossbar_{z}",(-.43,2.654,z),(.43,2.654,z),.037,m["trim"],body)
    panel_box(g,"Rear_bumper",(0,-2.476,.485),(1.62,.17,.195),m["paint"],body,.059)
    panel_box(g,"Rear_plate",(0,-2.568,.534),(.32,.021,.12),m["cream"],body,.012)
    panel_box(g,"Lightbar_mount",(0,-.09,1.457),(.90,.20,.084),m["trim"],body)
    for name,s,key in (("Red",-1,"red"),("Blue",1,"blue")):
        ctrl = g.object("Lightbar_"+name,parent=root)
        panel_box(g,name+"_housing",(s*.385,-.09,1.514),(.72,.29,.101),m["trim"],body,.032)
        for i in range(4):
            panel_box(g,f"{name}_module_{i}",(s*(.119+i*.175),-.09,1.538),
                      (.147,.301,.066),m[key],ctrl,.021)
    return g.collection


def build_helicopter():
    g, root, m = fleet_base("Heli", "Heli", (.036,.053,.077), (.86,.90,.89))
    body, glass, gear = [g.object(n,parent=root) for n in ("Body","Glass","Skids")]
    cabin = [(-2.07,.25,1.42,2.38),(-1.76,.62,.98,2.63),(-1.31,.88,.78,2.81),
             (-.64,.99,.68,2.92),(.14,1.01,.68,2.92),(.78,1.00,.73,2.88),
             (1.23,.96,.78,2.78),(1.68,.87,.87,2.66),(2.04,.69,.98,2.41),
             (2.29,.47,1.12,2.16),(2.47,.23,1.31,1.95),(2.51,.11,1.42,1.82)]
    loft(g,"Cabin_shell",cabin,m["paint"],body,.69,64)
    # Match the 64-sided shell's angular sampling so glazing and seams clear the skin.
    def skin(station, i, offset=.019):
        y,w,low,high = station
        return round_profile(y,w+offset,low-offset,high+offset,TAU*i/64,.69)

    def window(name, stations, angles):
        g.strip(name,[[skin(row,i) for i in angles] for row in stations],
                m["glass"],glass,smooth=True,flip=True)

    for s,side in SIDES:
        window("Windscreen_"+side,cabin[6:11],range(2,17) if s>0 else range(-16,-1))
        window("Pilot_window_"+side,cabin[4:7],range(8,16) if s>0 else range(-15,-7))
        window("Cabin_window_"+side,cabin[2:4],range(9,16) if s>0 else range(-15,-8))
        # Wide pale side band follows the curved cabin below the windows.
        angles = range(17,24) if s>0 else range(-23,-16)
        g.strip("Livery_"+side,[[skin(row,i,.013) for i in angles] for row in cabin[1:9]],
                m["accent"],body,smooth=True,flip=True)
        side_text(g,"POLICE_"+side,"POLICE",s*1.032,-.12,1.53,s,.34,m["cream"],body)
        coords = [skin(cabin[2],i,.027) for i in (8*s,16*s,23*s)]
        coords += [skin(cabin[k],23*s,.027) for k in (3,4,5)]
        coords += [skin(cabin[5],i,.027) for i in (16*s,8*s)]
        coords += [skin(cabin[k],8*s,.027) for k in (4,3,2)]
        g.line("Sliding_door_seam_"+side,coords,.014,m["trim"],body)
        panel_box(g,"Door_handle_"+side,(s*1.013,-.75,1.81),(.08,.19,.045),m["metal"],body)
        engine = [(-1.66,.21,2.54,3.02),(-1.37,.30,2.52,3.21),
                  (-.85,.32,2.58,3.34),(-.12,.33,2.63,3.40),
                  (.38,.29,2.65,3.34),(.58,.21,2.72,3.20)]
        pod = g.object("Turbine_"+side,parent=body,location=(s*.45,0,0))
        loft(g,"Turbine_cowling_"+side,engine,m["accent"],pod,.61)
        panel_box(g,"Intake_"+side,(0,.571,3.01),(.365,.094,.245),m["trim"],pod,.064)
        for i in range(4):
            panel_box(g,f"Intake_louver_{side}_{i}",(0,.626,2.95+i*.043),
                      (.27,.015,.014),m["metal"],pod,.005)
        tube(g,"Exhaust_"+side,(0,-1.38,2.91),(s*.054,-1.91,2.93),.153,m["metal"],pod,32)
        tube(g,"Exhaust_bore_"+side,(s*.053,-1.899,2.93),(s*.055,-1.914,2.93),.122,m["trim"],pod,32)
        skid_x = s*1.064
        g.line("Skid_"+side,[(skid_x,-1.82,.077),(skid_x,-1.57,.071),
              (skid_x,1.36,.071),(skid_x,1.62,.14),(skid_x,1.86,.31),
              (skid_x,1.96,.47)],.071,m["trim"],gear)
        # Straight lower section has an exact circular tread cross-section.
        runner_radius = .071
        tube(g,"Ground_runner_"+side,(skid_x,-1.57,runner_radius),(skid_x,1.36,runner_radius),
             runner_radius,m["trim"],gear,32)
        for y in (-1.15,.98):
            g.line(f"Skid_strut_{side}_{y}",[(s*.61,y,.99),(s*.86,y,.55),
                   (skid_x,y,.15),(skid_x,y,.08)],.059,m["metal"],gear)
    loft(g,"Tapered_tail_boom",[(-7.46,.095,2.09,2.29),(-7.16,.16,2.035,2.35),
         (-6.1,.21,1.97,2.42),(-4.9,.24,1.87,2.46),(-3.4,.32,1.65,2.55),
         (-2.31,.43,1.46,2.65),(-1.39,.56,1.34,2.74)],m["paint"],body,.82)
    for s,side in SIDES:
        side_text(g,"Tail_ID_"+side,"METRO 17",s*.259,-4.74,2.24,s,.22,m["cream"],body)
    g.plate("Tail_fin",[(-.045,-7.49,1.91),(-.045,-7.46,2.79),(-.045,-6.99,3.55),
                        (-.045,-6.72,3.58),(-.045,-6.81,2.79),(-.045,-6.39,2.22)],
            (.09,0,0),m["accent"],body,.044)
    g.plate("Tailplane",[(-1.34,-5.94,2.25),(-1.39,-5.59,2.28),(-.32,-5.31,2.25),
                         (.32,-5.31,2.25),(1.39,-5.59,2.28),(1.34,-5.94,2.25)],
            (0,0,.085),m["accent"],body,.032)
    panel_box(g,"Fin_beacon",(0,-6.88,3.56),(.16,.23,.115),m["red"],body,.040)
    tube(g,"Mast",(0,-.31,3.13),(0,-.31,3.82),.104,m["metal"],body)
    rotor = g.object("MainRotor",parent=root,location=(0,-.31,3.83))
    rotor["spin_axis"] = "local Z"
    tube(g,"Main_hub",(0,0,-.11),(0,0,.10),.255,m["trim"],rotor)
    for i in range(4):
        blade = g.object(f"MainBlade_{i+1}",parent=rotor)
        blade.rotation_euler.z = i*math.pi/2 + .24
        tube(g,f"Pitch_link_{i+1}",(.16,0,-.095),(.79,0,0),.040,m["metal"],blade)
        rows = []
        for x, leading, trailing, lift, pitch in (
            (.38,.080,-.11,0,.27),(.79,.15,-.20,.018,.21),
            (2.47,.16,-.22,.071,.145),(4.53,.139,-.203,.097,.083),
            (4.87,.097,-.176,.09,.073),(5.01,-.012,-.126,.075,.07)):
            rows.append([(x,y,lift+y*pitch+t) for y,t in
                         ((leading,0),(leading-.055,.030),(trailing+.032,.018),
                          (trailing,0),(trailing+.032,-.012),(leading-.055,-.014))])
        ring_mesh(g,f"Airfoil_{i+1}",rows,m["trim"],blade)
        g.strip(f"Tip_mark_{i+1}",[[(x,y,z+.002) for x,y,z in row[1:3]]
                                  for row in rows[-2:]],m["cream"],blade)
    tail = g.object("TailRotor",parent=root,location=(.27,-7.21,2.53))
    tail["spin_axis"] = "local X"
    tube(g,"Tail_gearbox",(0,-7.21,2.53),(.29,-7.21,2.53),.138,m["metal"],body)
    tube(g,"Tail_hub",(-.014,0,0),(.16,0,0),.112,m["trim"],tail)
    for i in range(4):
        blade = g.object(f"TailBlade_{i+1}",parent=tail)
        blade.rotation_euler.x = i*math.pi/2 + .32
        outline = [(0,-.052,.085),(0,.072,.13),(.028,.105,.71),
                   (.020,.056,.80),(.012,-.049,.753)]
        g.plate(f"Tail_airfoil_{i+1}",outline,(.034,0,0),m["trim"],blade,.012)
        g.plate(f"Tail_tip_{i+1}",[(.032,-.043,.655),(.054,.098,.675),
                (.052,.057,.78),(.041,-.041,.749)],(.006,0,0),m["cream"],blade)
    panel_box(g,"Searchlight_gimbal",(0,1.77,.85),(.36,.30,.26),m["trim"],body,.082)
    tube(g,"Searchlight_lens",(0,1.89,.78),(0,1.93,.76),.118,m["lamp"],body,32)
    # Center the fuselage above the ground origin in asset coordinates.
    center_y = (cabin[-1][0] - 7.46) / 2
    for child in root.children:
        child.location.y -= center_y
    return g.collection


def build_tanker():
    g, root, m = fleet_base("Truck", "Truck", (.49,.022,.025), (.84,.73,.52))
    chassis, cab, glass, tank, head, tail = [g.object(n,parent=root) for n in
        ("Chassis","Cab","Glass","Tank","Headlights","Taillights")]
    for s,side in SIDES:
        panel_box(g,"Frame_rail_"+side,(s*.43,-.14,.68),(.15,8.43,.25),m["trim"],chassis)
    for y in (-4.24,-3.35,-2.06,-.82,.91,2.41,3.52):
        panel_box(g,f"Frame_crossmember_{y}",(0,y,.69),(1.01,.18,.24),m["metal"],chassis)
    axles = (("Front",2.90),("Rear1",-2.14),("Rear2",-3.45))
    for name,y in axles:
        tube(g,"Axle_"+name,(-1.08,y,.527),(1.08,y,.527),.087,m["metal"],chassis)
        if name != "Front":
            loft(g,"Differential_"+name,[(y-.19,.13,.40,.65),(y-.12,.22,.33,.73),
                 (y+.12,.22,.33,.73),(y+.19,.13,.40,.65)],m["trim"],chassis)
        for s,side in SIDES:
            fleet_wheel(g,root,m,name,side,s,y,1.062,.527,.279,name!="Front")
            g.line("Leaf_spring_"+name+"_"+side,[(s*.53,y-.43,.69),(s*.53,y,.58),
                   (s*.53,y+.43,.69)],.051,m["metal"],chassis)
    for name,a,b in (("Prop_shaft",(.0,2.27,.69),(0,-2.08,.54)),
                     ("Inter_axle_shaft",(0,-2.26,.53),(0,-3.33,.53))):
        tube(g,name,a,b,.081,m["metal"],chassis)
    cab_stations = [(1.13,.97,1.05,2.74),(1.25,1.09,.96,2.94),
         (1.56,1.13,.92,3.02),(2.56,1.13,1.06,2.99),(2.96,1.12,1.12,2.85),
         (3.25,1.06,1.09,2.47),(3.42,.95,1.11,2.12)]
    cab_angles = sorted({i*7.5 for i in range(-24,24)} | {-88.75,88.75})
    profiles = {station[0]: [round_profile(*station, math.radians(a), .31)
                             for a in cab_angles] for station in cab_stations}
    # Split the existing loft at the windshield edges. The panes take the
    # place of shell faces and share their boundary vertices with the paint.
    for y, start, end in ((2.91,2.56,2.96), (3.30,3.25,3.42)):
        t = (y-start)/(end-start)
        profiles[y] = [(x0+t*(x1-x0), y, z0+t*(z1-z0))
                       for (x0,_,z0), (x1,_,z1) in zip(profiles[start], profiles[end])]
    stations = sorted(profiles)
    count = len(cab_angles)
    vertices = [p for y in stations for p in profiles[y]]
    shell_faces = [tuple(reversed(range(count))),
                   tuple(range(len(vertices)-count,len(vertices)))]
    windshield_faces = {side: [] for side in (-1,1)}
    door_faces = {s: [] for s,_ in SIDES}
    for i, (back, front) in enumerate(zip(stations, stations[1:])):
        for j, angle in enumerate(cab_angles):
            k = (j+1) % count
            face = (i*count+j, i*count+k, (i+1)*count+k, (i+1)*count+j)
            if 2.91 <= back and front <= 3.30 and -52.5 <= angle < 52.5:
                windshield_faces[-1 if angle < 0 else 1].append(face)
            elif 1.56 <= back and front <= 2.96 and 60 <= angle < 88.75:
                door_faces[1].append(face)
            elif 1.56 <= back and front <= 2.96 and -88.75 <= angle < -60:
                door_faces[-1].append(face)
            else:
                shell_faces.append(face)
    def cab_panel(name, faces, mat, parent):
        indices = dict.fromkeys(index for face in faces for index in face)
        remap = {index: local for local,index in enumerate(indices)}
        return g.mesh(name,[vertices[index] for index in indices],
                      [tuple(remap[index] for index in face) for face in faces],
                      mat,parent,smooth=True)

    shell = cab_panel("Cab_shell",shell_faces,m["paint"],cab)
    for face in list(shell.data.polygons)[:2]:
        face.use_smooth = False
    cab_panel("Windshield",windshield_faces[-1],m["glass"],glass)
    cab_panel("Windshield_right",windshield_faces[1],m["glass"],glass)
    for s,side in SIDES:
        cab_panel("Door_window_"+side,door_faces[s],m["glass"],glass)
    loft(g,"Hood",[(2.98,1.04,1.06,2.15),(3.38,1.07,1.01,2.12),
         (4.14,1.02,.98,2.00),(4.56,.95,1.00,1.94),(4.71,.83,1.04,1.81)],
         m["paint"],cab,.39)
    loft(g,"Cream_roof",[(1.23,.94,2.71,2.91),(1.45,1.06,2.77,3.043),
         (2.54,1.06,2.76,3.023),(2.86,.95,2.71,2.931)],m["accent"],cab,.48)
    center_column = cab_angles.index(0)
    center_edge = [profiles[y][center_column] for y in stations if 2.91 <= y <= 3.30]
    g.line("Windshield_center_post",
           [(x,y+.014,z) for x,y,z in center_edge],.026,m["trim"],cab)
    for s,side in SIDES:
        # Sample the glazing under each wiper so both arms clear the curved pane.
        wiper = []
        for a,t,reach in ((7.5,.06,.40),(7.5,.19,1),(15,.27,1),(22.5,.35,1),(30,.43,1)):
            column = cab_angles.index(s*a)
            lower, upper = (Vector(row[center_column]).lerp(Vector(row[column]),reach)
                            for row in (profiles[3.25],profiles[2.96]))
            x,y,z = lower.lerp(upper,t)
            wiper.append((x,y+.035,z))
        g.line("Wiper_"+side,wiper,.016,m["trim"],cab)
        side_plate(g,"Door_trim_"+side,[(s*1.12,1.40,1.41),(s*1.12,2.67,1.40),
                   (s*1.12,2.81,2.10),(s*1.12,1.40,2.10)],s,m["accent"],cab)
        panel_box(g,"Door_handle_"+side,(s*1.152,1.58,2.00),(.05,.21,.044),m["trim"],cab)
        side_text(g,"Cab_livery_"+side,"STRAY FUEL",s*1.139,2.06,1.77,s,.20,m["paint"],cab)
        panel_box(g,"Step_"+side,(s*1.03,1.87,.57),(.35,.85,.14),m["metal"],chassis)
        panel_box(g,"Step_tread_"+side,(s*1.108,1.87,.65),(.19,.72,.037),m["trim"],chassis)
        g.line("Mirror_arm_"+side,[(s*1.06,2.77,2.08),(s*1.29,2.73,2.12),
               (s*1.31,2.68,2.57),(s*1.08,2.69,2.65)],.027,m["trim"],cab)
        panel_box(g,"Mirror_shell_"+side,(s*1.30,2.65,2.42),(.166,.19,.37),m["trim"],cab,.037)
        panel_box(g,"Mirror_face_"+side,(s*1.30,2.542,2.42),(.114,.026,.30),m["metal"],cab,.020)
        for name,y in axles:
            rad = .597
            fender_angles = [math.pi*i/24 for i in range(25)]
            rows = [[(s*x,y+rad*math.cos(a),.54+rad*math.sin(a))
                     for x in (.77,1.05,1.235)] for a in fender_angles]
            g.strip("Fender_"+name+"_"+side,rows,m["paint"] if name=="Front" else m["trim"],
                    chassis,smooth=True,flip=s<0)
            lip = [(s*1.235,y+rad*math.cos(a),.54+rad*math.sin(a)) for a in fender_angles]
            g.line("Fender_edge_"+name+"_"+side,lip,.020,m["trim"],chassis)
        panel_box(g,"Headlight_bezel_"+side,(s*.774,4.61,1.33),(.35,.18,.29),m["trim"],cab,.041)
        panel_box(g,"Headlamp_"+side,(s*.785,4.709,1.36),(.25,.038,.146),m["lamp"],head,.028)
        panel_box(g,"Marker_"+side,(s*.785,4.705,1.23),(.22,.037,.049),m["amber"],head,.013)
        panel_box(g,"Tail_lamp_"+side,(s*.96,-4.60,.78),(.185,.076,.12),m["red"],tail,.022)
    panel_box(g,"Grille_surround",(0,4.65,1.48),(1.23,.19,.79),m["metal"],cab,.077)
    panel_box(g,"Grille_inset",(0,4.759,1.48),(1.09,.036,.65),m["trim"],cab,.060)
    for i in range(8):
        panel_box(g,f"Grille_louver_{i}",(0,4.786,1.224+i*.073),(.98,.025,.019),m["metal"],cab,.007)
    panel_box(g,"Bumper",(0,4.67,.86),(2.37,.24,.22),m["metal"],chassis,.043)
    panel_box(g,"Rear_underride",(0,-4.57,.61),(2.27,.18,.18),m["trim"],chassis,.03)
    for i in range(5):
        panel_box(g,f"Roof_marker_{i}",((i-2)*.36,2.56,2.991),(.100,.13,.065),
                  m["amber"],head,.018)

    center_z = 2.125
    radius = 1.109
    back, front = -4.03,.44
    sections = [(back-.56*math.sin(a),radius*math.cos(a))
                for a in [math.pi*i/22 for i in range(10,-1,-1)]]
    sections += [(front+.56*math.sin(a),radius*math.cos(a))
                 for a in [math.pi*i/22 for i in range(11)]]
    sections = [(back-.56,.008), *sections, (front+.56,.008)]
    loft(g,"Domed_fuel_vessel",[(y,r,center_z-r,center_z+r) for y,r in sections],
         m["accent"],tank,count=64)
    for y in (-3.49,-2.83,-.16):
        ring_mesh(g,f"Tank_strap_{y}",[
            [round_profile(yy,radius+.024,center_z-radius-.024,center_z+radius+.024,TAU*i/64)
             for i in range(64)] for yy in (y-.067,y+.067)],m["metal"],tank,caps=False)
        panel_box(g,f"Tank_saddle_{y}",(0,y,1.035),(1.79,.31,.33),m["trim"],chassis,.043)
    for s,side in SIDES:
        angles = [s*a for a in (1.63,1.73,1.83)]
        band = [[round_profile(y,radius+.013,center_z-radius-.013,center_z+radius+.013,a)
                 for a in angles] for y in (-4.03,.44)]
        g.strip("Tank_stripe_"+side,band,m["paint"],tank,flip=s>0)
        side_text(g,"Tank_livery_"+side,"STRAY FUEL",s*1.114,-1.53,2.26,s,.33,m["paint"],tank)
        diamond = [(s*1.127,-3.78,2.16),(s*1.127,-3.56,1.94),
                   (s*1.127,-3.78,1.72),(s*1.127,-4.00,1.94)]
        side_plate(g,"Flammable_placard_"+side,diamond,s,m["paint"],tank)
        side_text(g,"Placard_code_"+side,"1203",s*1.147,-3.78,1.94,s,.094,m["cream"],tank)
        rail = s*.37
        g.line("Top_handrail_"+side,[(rail,-3.97,3.16),(rail,-3.79,3.47),
               (rail,.18,3.47),(rail,.37,3.17)],.026,m["metal"],tank)
        for y in (-3.43,-2.21,-.98,.08):
            tube(g,f"Handrail_post_{side}_{y}",(rail,y,3.15),(rail,y,3.47),
                 .022,m["metal"],tank)
    for y in (-2.85,-.91):
        tube(g,f"Manhole_flange_{y}",(0,y,3.19),(0,y,3.272),.28,m["metal"],tank,40)
        tube(g,f"Manhole_lid_{y}",(0,y,3.269),(0,y,3.31),.219,m["trim"],tank,32)
        for i in range(8):
            a = TAU*i/8
            x, yy = .251*math.cos(a),y+.251*math.sin(a)
            tube(g,f"Manhole_bolt_{y}_{i}",(x,yy,3.271),(x,yy,3.29),.018,m["trim"],tank,8)
    for x in (.36,.76):
        g.line(f"Ladder_rail_{x}",[(x,-4.69,.86),(x,-4.69,2.63),
               (x,-4.45,3.10),(x,-3.99,3.34)],.036,m["metal"],tank)
    for i in range(8):
        z = .99+i*.268
        y = -4.69 + max(0,z-2.63)*.50
        tube(g,f"Ladder_rung_{i}",(.36,y,z),(.76,y,z),.026,m["metal"],tank)
    g.line("Fuel_manifold",[(0,.39,1.08),(.75,.39,1.08),(.91,.22,.91),
           (.91,-3.6,.91),(.72,-4.04,.91)],.067,m["metal"],tank)
    for y in (-1.12,-1.51,-1.90):
        tube(g,f"Outlet_{y}",(.88,y,.91),(1.16,y,.91),.074,m["metal"],tank)
        tube(g,f"Outlet_cap_{y}",(1.16,y,.91),(1.20,y,.91),.087,m["paint"],tank)
    return g.collection


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def build_preview(scene):
    collection = owned_collection("Preview", scene)
    g = Geometry(collection, "Preview_")
    floor = material("Studio_floor", (.073,.091,.121), .04, .48)
    g.mesh("Floor", [(-100,-100,-.004),(100,-100,-.004),(100,100,-.004),(-100,100,-.004)],
           [(0,1,2,3)], floor)
    for name, position, target, power, size, size_y in (
        ("Key_softbox", (1.6,1.6,5.4), (0,.3,0), 950, 5.7, 3.4),
        ("Long_rim", (-3.4,-1.15,3.4), (0,-.3,.45), 880, 6.2, 1.9),
        ("Rear_softbox", (2.9,-4.4,3.5), (0,-.6,.45), 620, 4.8, 2.8),
        ("Nose_fill", (-1.4,5.5,2.7), (0,.65,.4), 330, 5.5, 3.0),
        ("Side_fill", (5.1,.2,2.7), (0,.1,.4), 320, 5.0, 2.6),
    ):
        data = bpy.data.lights.new("Preview_" + name, "AREA")
        data.energy, data.shape, data.size, data.size_y = power, "RECTANGLE", size, size_y
        aim(g.object(name,data,location=position), target)

    cameras = {}
    for label, pos, target, scale in (
        ("hero_front_34", (6.8,8.3,3.45), (0,.02,.57), 5.68),
        ("hero_rear_34", (6.7,-8.2,3.18), (0,-.02,.57), 5.68),
        ("hero_side", (9.0,0,1.72), (0,0,.57), 5.66),
    ):
        data = bpy.data.cameras.new("Preview_" + label)
        data.type, data.ortho_scale = "ORTHO", scale
        camera = g.object(label,data,location=pos)
        aim(camera,target)
        cameras[label] = camera
    scene.camera = cameras["hero_front_34"]
    return cameras


# Camera, target, orthographic width, floor color, and individual area lights.
FLEET_STUDIOS = {
    "Police": ("police_preview", (7.9,8.7,3.4), (0,.05,.73), 6.15, (.080,.099,.125), (
        ("Key", (3.4,4.8,6.3), 1200, 5.5, 3.6),
        ("Rim", (-3.5,-2.8,4.6), 1050, 5.0, 2.6),
        ("Fill", (4.4,-3.6,3.4), 510, 5.0, 2.4),
    )),
    "Heli": ("heli_preview", (14.6,11.175,7.0), (0,1.325,1.87), 12.55, (.085,.104,.128), (
        ("Key", (5,7.475,9), 2700, 8.0, 5.5),
        ("Rim", (-5,-2.525,7), 2550, 7.5, 4.5),
        ("Fill", (7,-3.525,5), 1300, 6.5, 4.2),
    )),
    "Truck": ("truck_preview", (13.3,9.7,6.75), (0,.05,1.59), 10.55, (.105,.108,.117), (
        ("Key", (5.4,4,8), 2450, 7.8, 5.3),
        ("Rim", (-5,-3.5,6.5), 2200, 7.8, 3.6),
        ("Fill", (6.8,-5,4.8), 1100, 6.5, 4.6),
    )),
}


def build_fleet_preview(scene, asset):
    label, pos, target, scale, color, lights = FLEET_STUDIOS[asset]
    name = "Preview_" + asset
    collection = owned_collection(name, scene)
    g = Geometry(collection, name + "_")
    floor = material("Floor", color, .04, .48, prefix=name)
    g.mesh("Floor", [(-100,-100,-.004),(100,-100,-.004),(100,100,-.004),(-100,100,-.004)],
           [(0,1,2,3)], floor)
    for label_light, position, power, size, size_y in lights:
        data = bpy.data.lights.new(g.prefix + label_light, "AREA")
        data.energy, data.shape, data.size, data.size_y = power, "RECTANGLE", size, size_y
        aim(g.object(label_light, data, location=position), target)
    data = bpy.data.cameras.new(g.prefix + "Camera")
    data.type, data.ortho_scale = "ORTHO", scale
    camera = g.object("Camera", data, location=pos)
    aim(camera, target)
    return collection, label, camera


def select_preview(assets, previews, active):
    for name in assets:
        hidden = name != active
        for collection in (assets[name], previews[name]):
            collection.hide_render = hidden
            collection.hide_viewport = hidden


def studio_scene():
    name = "STRAY Studio"
    scene = bpy.data.scenes.get(name)
    if scene is None:
        scene = bpy.data.scenes.new(name)
        scene["owner"] = OWNER
    elif scene.get("owner") != OWNER:
        raise RuntimeError(f"Scene name collision: {name}")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    if bpy.context.scene != scene:
        raise RuntimeError("Unable to activate STRAY Studio")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    world = scene.world
    if world is None or world.get("owner") != OWNER:
        world = bpy.data.worlds.new("Preview_World")
        world["owner"] = OWNER
        scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (.32,.37,.48,1)
    bg.inputs["Strength"].default_value = .16
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -.35
    return scene


def resolution(value):
    try:
        width, height = map(int, value.lower().split("x"))
        if not all(4 <= v <= 65536 for v in (width,height)):
            raise ValueError
        return width,height
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use WIDTHxHEIGHT, with each side between 4 and 65536") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    render = parser.add_mutually_exclusive_group()
    render.add_argument("--render", action="store_true", help="render the three studio cameras")
    render.add_argument("--no-render", dest="render", action="store_false", help="save only")
    parser.set_defaults(render=False)
    fleet = parser.add_mutually_exclusive_group()
    fleet.add_argument("--fleet-render", action="store_true", help="render Police, Heli and Truck")
    fleet.add_argument("--fleet-only", choices=tuple(FLEET_STUDIOS),
                       help="render just the selected fleet preview")
    parser.add_argument("--resolution", type=resolution, default=(1280,800))
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--fleet-samples", type=int, default=16,
                        help="Cycles samples per fleet preview (default: %(default)s)")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not 1 <= args.samples <= 4096:
        parser.error("--samples must be between 1 and 4096")
    if not 1 <= args.fleet_samples <= 4096:
        parser.error("--fleet-samples must be between 1 and 4096")
    scene = studio_scene()
    assets = {c.name: c for c in (build_hero(), build_police(), build_helicopter(), build_tanker())}
    cameras = build_preview(scene)
    previews = {"Hero": bpy.data.collections["Preview"]}
    fleet_views = {}
    for name in FLEET_STUDIOS:
        previews[name], label, camera = build_fleet_preview(scene, name)
        fleet_views[name] = (label, camera)
    select_preview(assets, previews, "Hero")
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
    except (TypeError, AttributeError):
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    # Blender defines ortho scale along the wider image axis. Keep the
    # compositions intact when a custom resolution is narrower than default.
    aspect = args.resolution[0] / args.resolution[1]
    for camera in cameras.values():
        camera.data.ortho_scale *= max(1.0, 1.0/aspect, aspect/1.6)
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = "//hero_front_34.png"
    preferences = bpy.context.preferences.filepaths
    save_version = preferences.save_version
    try:
        preferences.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "assets.blend"))
    finally:
        preferences.save_version = save_version
    if args.render:
        for label, camera in cameras.items():
            scene.camera = camera
            scene.render.filepath = str(HERE / (label + ".png"))
            bpy.ops.render.render(write_still=True, scene=scene.name)
    fleet_targets = (args.fleet_only,) if args.fleet_only else tuple(fleet_views) if args.fleet_render else ()
    if fleet_targets:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = args.fleet_samples
        scene.cycles.use_denoising = True
        scene.render.resolution_x, scene.render.resolution_y = (1280,800)
        try:
            for name in fleet_targets:
                label, camera = fleet_views[name]
                select_preview(assets, previews, name)
                scene.camera = camera
                scene.render.filepath = str(HERE / (label + ".png"))
                bpy.ops.render.render(write_still=True, scene=scene.name)
        finally:
            select_preview(assets, previews, "Hero")
            scene.camera = cameras["hero_front_34"]
            scene.render.filepath = "//hero_front_34.png"


if __name__ == "__main__":
    main()
