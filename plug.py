"""3.5mm audio plug (TRS jack) built from primitives.

Local frame: origin at the grip/barrel junction (the "seat" point).
  +X = tip direction, -X = back where the vine grows from.
"""
import math
import bpy
from .scene_setup import link


class PlugBuilder:
    """Builds one reusable jack model as children of a single root empty."""

    def __init__(self, mats):
        self.mats = mats

    def build(self, accent, location=(0, 0, 0), name="LogoAnim_Plug",
              with_metal=True, secondary=(1.0, 1.0, 1.0, 1.0)):
        mats = self.mats
        if with_metal:
            # painted-metal housing and polished contact parts
            body_mat = mats.principled(
                "LogoAnim_PlugBody", base=tuple(accent), metallic=0.75,
                roughness=0.30, emission=tuple(accent), emission_strength=0.38)
            metal_mat = mats.principled(
                "LogoAnim_PlugMetal", base=(0.92, 0.94, 0.98, 1.0),
                metallic=1.0, roughness=0.22,
                emission=(0.85, 0.90, 1.0, 1.0), emission_strength=0.16)
        else:
            body_mat = mats.emission("LogoAnim_PlugBody", tuple(accent), 1.0)
            metal_mat = mats.emission("LogoAnim_PlugMetal",
                                      (0.88, 0.90, 0.98, 1.0), 1.3)
        dark_mat = mats.emission("LogoAnim_PlugDark", (0.03, 0.03, 0.03, 1.0), 1.0)

        root = bpy.data.objects.new(name, None)
        link(root)
        root.empty_display_type = "PLAIN_AXES"
        root.location = location

        def cyl(radius, depth, x, mat, suffix, verts=32):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=verts, radius=radius, depth=depth, location=(x, 0, 0))
            o = bpy.context.view_layer.objects.active
            o.name = "%s_%s" % (name, suffix)
            link(o)
            o.rotation_euler = (0, math.radians(90), 0)  # align axis to X
            o.parent = root
            o.data.materials.clear()
            o.data.materials.append(mat)
            return o

        # grip / housing
        cyl(0.19, 0.54, -0.27, body_mat, "Grip", verts=64)
        # strain relief boot: tapers from the housing down to EXACTLY the cord
        # radius, so the cord continues its silhouette with no lip or step
        bpy.ops.mesh.primitive_cone_add(radius1=0.19, radius2=0.15, depth=0.22,
                                        vertices=64, location=(-0.65, 0, 0))
        relief = bpy.context.view_layer.objects.active
        relief.name = name + "_Relief"
        link(relief)
        relief.rotation_euler = (0, math.radians(-90), 0)
        relief.parent = root
        relief.data.materials.clear()
        relief.data.materials.append(body_mat)
        # collar
        cyl(0.13, 0.06, 0.03, body_mat, "Collar", verts=64)
        # sleeve (the long barrel)
        cyl(0.105, 0.40, 0.26, metal_mat, "Sleeve", verts=64)
        # insulator gap
        cyl(0.075, 0.04, 0.48, dark_mat, "Gap1", verts=64)
        # ring contact
        cyl(0.105, 0.11, 0.555, metal_mat, "Ring", verts=64)
        # insulator gap
        cyl(0.075, 0.04, 0.63, dark_mat, "Gap2", verts=64)
        # tip: pointed cone
        bpy.ops.mesh.primitive_cone_add(radius1=0.10, radius2=0.015, depth=0.18,
                                        vertices=64, location=(0.74, 0, 0))
        tip = bpy.context.view_layer.objects.active
        tip.name = name + "_Tip"
        link(tip)
        tip.rotation_euler = (0, math.radians(90), 0)
        tip.parent = root
        tip.data.materials.clear()
        tip.data.materials.append(metal_mat)
        return root
