"""Plant: a cord that grows out of the jack, branching into unrolling leaves.

Growth is timed like a speedlapse: the stem extends, branches sprout off it one
after another, and each leaf unfurls from its branch tip while the branch is
still reaching out.

Leaves are built as a single mesh (blade + centre vein) with a "Furled" shape
key, so they genuinely unroll from a coiled shoot instead of just scaling up.
They are also placed slightly toward the camera so the vines never draw over
them.
"""
import math
import bmesh
import bpy
from .scene_setup import link
from .animation import Animator
from . import curves

#: mesh-local leaf points +X, faces +Z; this upright rotation maps it into the
#: world XZ plane facing the camera
UPRIGHT_LEAF = (math.radians(90), 0.0, 0.0)

#: branch taper: joins the stem thick, ends thin at the leaf
BRANCH_PROFILE = ((0.0, 0.068), (0.45, 0.050), (1.0, 0.026))

#: leaves sit this far in FRONT of the cord (the camera looks along +Y), so the
#: stem/branch tubes always render behind them
LEAF_DEPTH = -0.20

FURLED_KEY = "Furled"


def screen_rotation(screen_angle_deg):
    """Euler that aims a leaf at `screen_angle_deg` in the XZ plane.

    0deg = +X (right), 90deg = +Z (up), 180deg = -X (left).
    """
    return (UPRIGHT_LEAF[0], math.radians(-screen_angle_deg), 0.0)


def curved_branch(start, angle_deg, length, curve_deg, count=26):
    """Walk outward from `start`, turning by `curve_deg` over the length.

    Integrating a turning heading gives naturally arcing branches instead of
    straight spokes.
    """
    x, z = start[0], start[2]
    a = math.radians(angle_deg)
    steps = max(2, count - 1)
    step = length / steps
    turn = math.radians(curve_deg) / steps
    pts = [(x, 0.0, z)]
    for _ in range(steps):
        a += turn
        x += math.cos(a) * step
        z += math.sin(a) * step
        pts.append((x, 0.0, z))
    return pts


def furl(x, y, length, turns=0.78, width_scale=0.30):
    """Map a flat leaf point onto a coiled shoot (the 'Furled' shape key).

    u walks along the leaf and winds it into a gentle inward curl, keeping the
    base pinned at the origin so the blade unrolls outward from where it joins.
    """
    u = min(1.0, max(0.0, x / max(1e-6, length)))
    r0 = 0.62 * length
    th = turns * 2.0 * math.pi * u
    r = r0 * (1.0 - 0.30 * u)
    cx, cy = math.cos(th) * r, math.sin(th) * r
    # width collapses onto the roll's radius
    rad = (math.cos(th), math.sin(th))
    return (cx - r0 + rad[0] * y * width_scale,
            cy + rad[1] * y * width_scale)


class LeafBuilder:
    """Leaf blade + centre vein in one mesh, with an unroll shape key."""

    def __init__(self, mats):
        self.mats = mats

    def build(self, name, length, width, mat, vein_mat=None, segs=40,
              bend=0.14, sharp=0.55, blunt=0.85, vein_offset=0.006,
              vein_half=0.014):
        profile = [(t / segs) ** sharp * (1.0 - t / segs) ** blunt
                   for t in range(segs + 1)]
        peak = max(profile) or 1.0

        def centre(t):
            return bend * length * (t ** 2)

        coords = []           # flat positions, creation order
        outline = []
        for i in range(segs + 1):
            t = i / segs
            outline.append((length * t, centre(t) + width * profile[i] / peak))
        for i in range(segs - 1, 0, -1):
            t = i / segs
            outline.append((length * t, centre(t) - width * profile[i] / peak))

        mesh = bpy.data.meshes.new(name + "_Mesh")
        bm = bmesh.new()
        verts = [bm.verts.new((x, y, 0.0)) for x, y in outline]
        coords.extend([(x, y, 0.0) for x, y in outline])
        try:
            bm.faces.new(verts)
        except ValueError:
            pass

        # centre vein: a thin strip floated just in front of the blade
        if vein_mat is not None:
            samples = 10
            strip = []
            for i in range(samples):
                t = 0.06 + 0.82 * i / (samples - 1)
                x = length * t
                hw = vein_half * (1.0 - 0.55 * t)
                strip.append((x, centre(t) - hw, x, centre(t) + hw))
                coords.append((x, centre(t) - hw, vein_offset))
                coords.append((x, centre(t) + hw, vein_offset))
            vs = [bm.verts.new(c) for c in coords[-2 * samples:]]
            for i in range(samples - 1):
                a, b = vs[2 * i], vs[2 * i + 1]
                c, d = vs[2 * i + 2], vs[2 * i + 3]
                try:
                    f = bm.faces.new((a, b, d, c))
                    f.material_index = 1
                except ValueError:
                    pass

        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(name, mesh)
        link(obj)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        if vein_mat is not None:
            obj.data.materials.append(vein_mat)
        obj.rotation_euler = UPRIGHT_LEAF

        # "Furled" shape key: the coiled shoot it unrolls from
        obj.shape_key_add(name="Basis", from_mix=False)
        furled = obj.shape_key_add(name=FURLED_KEY, from_mix=False)
        for i, (x, y, z) in enumerate(coords):
            fx, fy = furl(x, y, length)
            furled.data[i].co = (fx, fy, z)
        furled.value = 0.0
        return obj


def unfurl_leaf(obj, f_start, f_end, base_rotation, start_scale=0.55,
                sweep=0.5, key=FURLED_KEY):
    """Unroll a leaf: the coil opens while the blade leans into place."""
    start_rot = list(base_rotation)
    start_rot[1] = start_rot[1] + sweep

    keys = obj.data.shape_keys
    block = keys.key_blocks.get(key) if keys else None

    obj.scale = (0.001,) * 3
    obj.rotation_euler = start_rot
    if block:
        block.value = 1.0
    obj.keyframe_insert(data_path="scale", frame=1)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    if block:
        block.keyframe_insert(data_path="value", frame=1)
    Animator.set_key_interpolation(obj, "scale", 1, "CONSTANT", "AUTO")
    Animator.set_key_interpolation(obj, "rotation_euler", 1, "CONSTANT",
                                   "AUTO")

    obj.scale = (start_scale,) * 3
    obj.rotation_euler = start_rot
    if block:
        block.value = 1.0
    obj.keyframe_insert(data_path="scale", frame=f_start)
    obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
    if block:
        block.keyframe_insert(data_path="value", frame=f_start)

    obj.scale = (1.0, 1.0, 1.0)
    obj.rotation_euler = base_rotation
    if block:
        block.value = 0.0
    obj.keyframe_insert(data_path="scale", frame=f_end)
    obj.keyframe_insert(data_path="rotation_euler", frame=f_end)
    if block:
        block.keyframe_insert(data_path="value", frame=f_end)

    Animator.set_key_interpolation(obj, "scale", f_start, "BACK", "OUT")
    Animator.set_key_interpolation(obj, "rotation_euler", f_start, "SINE", "OUT")
    if block:
        Animator.ease_owner(keys, 'key_blocks["%s"].value' % key, "SINE", "OUT")
    return obj


class PlantBuilder:
    """Cord-stem + branches + leaves, animated as one speedlapse."""

    def __init__(self, mats):
        self.mats = mats

    def build(self, mat_stem, mat_leaf, root, stem_control, stem_profile,
              branches, f_grow0, f_grow1, mat_vein=None, tip_leaf=None,
              leaf_depth=LEAF_DEPTH):
        span = max(1, f_grow1 - f_grow0)
        stem_points = curves.sample_bezier(stem_control, 90)
        stem_points[0] = (root[0], root[1], root[2])
        stem = curves.build_profiled_tube("LogoAnim_Stem", stem_points,
                                          stem_profile, mat_stem, link)
        # the stem is the cord: it must be fully grown before the name appears
        curves.animate_draw_on(stem, f_grow0, f_grow0 + int(span * 0.42))

        leaf_builder = LeafBuilder(self.mats)
        made_branches, made_leaves = [], []
        for i, spec in enumerate(branches):
            t = spec["t"]
            base = _point_at(stem_points, t)
            normal = _normal_at(stem_points, t)
            side = 1.0 if spec.get("side", 1) >= 0 else -1.0
            off = spec.get("offset", 0.045)
            start = (base[0] + normal[0] * off, 0.0, base[2] + normal[1] * off)

            angle = spec["angle"]
            curve = spec.get("curve", 0.0) * side
            length = spec["length"]
            branch = curves.build_profiled_tube(
                "LogoAnim_Branch%d" % i,
                curved_branch(start, angle, length, curve),
                spec.get("profile", BRANCH_PROFILE), mat_stem, link)
            b0 = f_grow0 + int(span * spec.get("at", 0.3))
            b1 = b0 + int(span * spec.get("span", 0.22))
            curves.animate_draw_on(branch, b0, b1)
            made_branches.append((branch, b0, b1))

            leaf_spec = spec["leaf"]
            tip = curved_branch(start, angle, length, curve)[-1]
            leaf_angle = leaf_spec.get("angle", angle + curve)
            leaf = self._place_leaf(leaf_builder, mat_leaf, mat_vein, i, tip,
                                    leaf_angle, leaf_spec, side, leaf_depth,
                                    pull_back=leaf_spec.get("back", 0.09))
            l0 = f_grow0 + int(span * leaf_spec.get("at", 0.45))
            l1 = l0 + int(span * leaf_spec.get("span", 0.22))
            unfurl_leaf(leaf, l0, l1, screen_rotation(leaf_angle),
                        start_scale=leaf_spec.get("scale", 0.55),
                        sweep=leaf_spec.get("sweep", 0.55) * side)
            made_leaves.append((leaf, l0, l1))

        # the top leaf continues the stem itself: no extra twig to leave a
        # visible stub where it joins
        if tip_leaf:
            tip = stem_points[-1]
            end_angle = _end_angle(stem_points)
            leaf_angle = tip_leaf.get("angle", end_angle)
            leaf = self._place_leaf(leaf_builder, mat_leaf, mat_vein,
                                    len(branches), tip, leaf_angle, tip_leaf,
                                    1.0, leaf_depth,
                                    pull_back=tip_leaf.get("back", 0.10))
            l0 = f_grow0 + int(span * tip_leaf.get("at", 0.6))
            l1 = l0 + int(span * tip_leaf.get("span", 0.22))
            unfurl_leaf(leaf, l0, l1, screen_rotation(leaf_angle),
                        start_scale=tip_leaf.get("scale", 0.55),
                        sweep=tip_leaf.get("sweep", 0.5))
            made_leaves.append((leaf, l0, l1))

        return {"stem": stem, "branches": made_branches,
                "leaves": made_leaves}

    def _place_leaf(self, builder, mat_leaf, mat_vein, index, tip, leaf_angle,
                    spec, side, depth, pull_back=0.0):
        """Leaf at a tip, pulled back along its heading so it hides the tip."""
        a = math.radians(leaf_angle)
        base = (tip[0] - math.cos(a) * pull_back, depth,
                tip[2] - math.sin(a) * pull_back)
        leaf = builder.build("LogoAnim_Leaf%d" % index, spec["length"],
                             spec["width"], mat_leaf, vein_mat=mat_vein,
                             bend=spec.get("bend", 0.15) * side)
        leaf.location = base
        leaf.rotation_euler = screen_rotation(leaf_angle)
        return leaf


def _index_at(points, t):
    return max(1, min(len(points) - 1, int(round(t * (len(points) - 1)))))


def _point_at(points, t):
    return points[_index_at(points, t)]


def _normal_at(points, t):
    a = points[max(0, _index_at(points, t) - 1)]
    b = points[min(len(points) - 1, _index_at(points, t) + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    n = math.hypot(dx, dz) or 1.0
    return (-dz / n, dx / n)


def _end_angle(points, back=6):
    """Screen angle (degrees) of the stem's final heading."""
    a = points[max(0, len(points) - 1 - back)]
    b = points[-1]
    return math.degrees(math.atan2(b[2] - a[2], b[0] - a[0]))
