"""Procedural icon factory (Strategy registry: new icons plug in, no edits).

Register: ICON_BUILDERS["MY_ICON"] = my_builder_fn
Each builder fn(parent, mat_icon, mat_ring) creates meshes parented to parent.
"""
import math
import bpy
from .scene_setup import link


def _add(op, name, mat, parent, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    op(location=(0, 0, 0))
    o = bpy.context.view_layer.objects.active
    o.name = name
    link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    if scale:
        o.scale = scale
    o.data.materials.clear()
    o.data.materials.append(mat)
    return o


def gem_rings(parent, mat, ring_mat):
    gem = _add(bpy.ops.mesh.primitive_ico_sphere_add, "LogoAnim_IconGem",
               mat, parent, scale=(1.0,) * 3)
    gem.data.polygons.foreach_set("use_smooth", [True] * len(gem.data.polygons))
    r1 = _add(bpy.ops.mesh.primitive_torus_add, "LogoAnim_IconRing1",
              ring_mat, parent, rot=(math.radians(75), 0, 0), scale=(1.5,) * 3)
    try:
        r1.data.major_radius = 1.0
        r1.data.minor_radius = 0.06
    except Exception:
        pass
    r2 = _add(bpy.ops.mesh.primitive_torus_add, "LogoAnim_IconRing2",
              ring_mat, parent, rot=(math.radians(90), 0, math.radians(40)),
              scale=(1.9,) * 3)


def torus_knot(parent, mat, _ring):
    k = _add(bpy.ops.mesh.primitive_torus_add, "LogoAnim_IconKnot",
             mat, parent)
    try:
        k.data.major_radius = 0.8
        k.data.minor_radius = 0.28
    except Exception:
        pass
    k.modifiers.new("Subdiv", "SUBSURF").levels = 2


def shield(parent, mat, _ring):
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    sh = bpy.context.view_layer.objects.active
    sh.name = "LogoAnim_IconShield"
    link(sh)
    sh.parent = parent
    sh.scale = (1.0, 0.35, 1.3)
    sh.data.materials.clear()
    sh.data.materials.append(mat)
    try:
        bev = sh.modifiers.new("Bevel", "BEVEL")
        bev.width = 0.15
        bev.segments = 3
    except Exception:
        pass


def cube_abstract(parent, mat, ring_mat):
    for i, loc in enumerate([(0, 0, 0), (0.9, 0.3, 0.4), (-0.8, -0.2, 0.6)]):
        _add(bpy.ops.mesh.primitive_cube_add, "LogoAnim_IconCube%d" % i,
             mat if i != 1 else ring_mat, parent, loc=loc,
             rot=(0.4 * i, 0.6 * i, 0.3 * i), scale=(0.7,) * 3)


def orbit_spheres(parent, mat, ring_mat):
    _add(bpy.ops.mesh.primitive_uv_sphere_add, "LogoAnim_IconCore",
         mat, parent, scale=(0.6,) * 3)
    for i in range(3):
        a = math.radians(i * 120)
        _add(bpy.ops.mesh.primitive_uv_sphere_add, "LogoAnim_IconOrb%d" % i,
             ring_mat, parent,
             loc=(math.cos(a) * 1.4, math.sin(a) * 1.4, 0.3 * i),
             scale=(0.28,) * 3)


ICON_BUILDERS = {
    "GEM_RINGS": gem_rings,
    "TORUS_KNOT": torus_knot,
    "SHIELD": shield,
    "CUBE_ABSTRACT": cube_abstract,
    "ORBIT_SPHERES": orbit_spheres,
}


class IconFactory:
    def __init__(self, mats):
        self.mats = mats

    def create(self, icon_type, location, accent):
        for o in list(bpy.data.objects):
            if o.name.startswith("LogoAnim_Icon"):
                bpy.data.objects.remove(o, do_unlink=True)
        parent = bpy.data.objects.new("LogoAnim_IconRoot", None)
        link(parent)
        parent.location = location
        parent.scale = (0.7,) * 3
        parent.empty_display_type = "PLAIN_AXES"
        mat = self.mats.principled(
            "LogoAnim_IconMat", base=(0.1, 0.5, 1.0, 1.0), metallic=0.2,
            roughness=0.15, emission=tuple(accent[:3]) + (1.0,),
            emission_strength=3.0)
        ring_mat = self.mats.principled(
            "LogoAnim_RingMat", base=(1.0, 0.75, 0.25, 1.0), metallic=1.0,
            roughness=0.25, emission=(1.0, 0.6, 0.15, 1.0),
            emission_strength=1.2)
        builder = ICON_BUILDERS.get(icon_type, gem_rings)
        builder(parent, mat, ring_mat)
        return parent
