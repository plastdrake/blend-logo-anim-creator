"""Curve geometry helpers: sampling and tube building.

Used by the plant (stems/branches) and anywhere a light-trail-like tube is
needed. All sampling returns plain (x, y, z) tuples in world units.
"""
import math
import bpy
from mathutils import Vector


def sample_bezier(control_points, count):
    """Sample a cubic Bezier curve (4 control points) as world points.

    More than 4 points fall back to piecewise-linear interpolation, so callers
    can pass a coarse polyline without special-casing.
    """
    pts = [Vector(p) for p in control_points]
    if len(pts) != 4:
        out = []
        for i in range(count):
            t = i / max(1, count - 1)
            seg = t * (len(pts) - 1)
            i0 = min(int(seg), len(pts) - 2)
            out.append(tuple(pts[i0].lerp(pts[i0 + 1], seg - i0)))
        return out
    p0, p1, p2, p3 = pts
    out = []
    for i in range(count):
        t = i / max(1, count - 1)
        u = 1.0 - t
        p = (p0 * (u ** 3) + p1 * (3 * u * u * t) +
             p2 * (3 * u * t * t) + p3 * (t ** 3))
        out.append((p.x, p.y, p.z))
    return out


def sample_profile(profile, count):
    """Resample a piecewise-linear (t, radius) profile evenly."""
    out = []
    for i in range(count):
        t = i / max(1, count - 1)
        for j in range(len(profile) - 1):
            t0, r0 = profile[j]
            t1, r1 = profile[j + 1]
            if t0 <= t <= t1 and t1 > t0:
                out.append((t, r0 + (r1 - r0) * (t - t0) / (t1 - t0)))
                break
        else:
            out.append((t, profile[-1][1]))
    return out


def build_profiled_tube(name, points, profile, mat, collection_link,
                        bevel_resolution=3):
    """One continuous tube whose thickness follows a radius profile.

    `profile` is a sequence of (t, radius) with t from 0 (start) to 1 (end), so
    a stem can sprout thin, swell, then taper. A taper object drives the bevel,
    which means there are no seams between thickness changes.
    """
    r_max = max(r for _, r in profile)
    cu = bpy.data.curves.new(name + "_Curve", type="CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r_max
    cu.bevel_resolution = bevel_resolution
    cu.use_fill_caps = True
    spline = cu.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for i, pt in enumerate(points):
        spline.points[i].co = (pt[0], pt[1], pt[2], 1.0)

    tname = name + "_Taper"
    old = bpy.data.objects.get(tname)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    tcu = bpy.data.curves.new(tname + "_Curve", type="CURVE")
    tsp = tcu.splines.new("POLY")
    samples = sample_profile(profile, 24)
    tsp.points.add(len(samples) - 1)
    for i, (t, radius) in enumerate(samples):
        # x maps along the curve, y scales bevel_depth
        tsp.points[i].co = (t, max(0.002, radius / r_max), 0.0, 1.0)
    taper = bpy.data.objects.new(tname, tcu)
    collection_link(taper)
    cu.taper_object = taper

    obj = bpy.data.objects.new(name, cu)
    collection_link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def animate_draw_on(curve_obj, f_start, f_end):
    """Reveal the tube progressively (light-painting / growing effect)."""
    from .animation import Animator
    cu = curve_obj.data
    cu.bevel_factor_end = 0.0
    cu.keyframe_insert(data_path="bevel_factor_end", frame=f_start)
    cu.bevel_factor_end = 1.0
    cu.keyframe_insert(data_path="bevel_factor_end", frame=f_end)
    try:
        action = cu.animation_data.action
        for fc in Animator.fcurves(action):
            if fc.data_path == "bevel_factor_end":
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    except Exception:
        pass
