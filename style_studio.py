"""Studio style: extruded text + icon fly-in on a lit stage (the original look)."""
import math
import bpy
import mathutils
from .scene_setup import link, frame_perspective
from .text_logo import TextLogoBuilder, UPRIGHT
from .icons import IconFactory
from .animation import Animator
from .fx import LightRig, VolumeBox, SmokeCards, DustEmitter, spark_prototype
from . import compositing

TEXT_TARGET_WIDTH = 5.4
ICON_GAP = 0.7
ICON_Z = 1.4
TEXT_Z = 1.2


def _ground(mats):
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, -1.2))
    g = bpy.context.view_layer.objects.active
    g.name = "LogoAnim_Ground"
    link(g)
    mat = mats.principled("LogoAnim_GroundMat", base=(0.02, 0.025, 0.04, 1.0),
                          metallic=0.4, roughness=0.45,
                          emission=(0, 0, 0, 1), emission_strength=0.0)
    g.data.materials.clear()
    g.data.materials.append(mat)
    return g


def _half_width(obj):
    """World-space half width of an object and its mesh children."""
    xs = []
    for o in [obj] + list(getattr(obj, "children", [])):
        if o.type not in {"MESH", "CURVE"}:
            continue
        try:
            for c in o.bound_box:
                xs.append((o.matrix_world @ mathutils.Vector(c)).x)
        except Exception:
            continue
    return (max(xs) - min(xs)) / 2.0 if xs else 0.7


def _layout(text, icon):
    """Place text left of the icon, both centered on the frame origin."""
    bpy.context.view_layer.update()
    text_w = text.dimensions.x or TEXT_TARGET_WIDTH
    icon_r = _half_width(icon)
    total = text_w + ICON_GAP + 2.0 * icon_r
    return ((-total + text_w) / 2.0,          # text home x
            (total - 2.0 * icon_r) / 2.0)     # icon home x


def _animate(text, icon, rig, frame_end, fly_dist, text_home, icon_home):
    f_hit, f_settle = 32, 55
    # text from the left
    text.animation_data_clear()
    text.location = (text_home - fly_dist, 0, TEXT_Z)
    text.rotation_euler = (UPRIGHT[0], 0, math.radians(-18))
    base_scale = tuple(text.scale)
    Animator.pose(text, 1)
    text.location = (text_home, 0, TEXT_Z)
    text.rotation_euler = UPRIGHT
    Animator.pose(text, f_hit)
    Animator.pop(text, f_hit + 6,
                 tuple(s * 1.12 for s in base_scale), 1.0, f_settle)
    text.scale = base_scale
    text.location = (text_home, 0, TEXT_Z + 0.12)
    text.keyframe_insert(data_path="location", frame=frame_end)
    for dp, interp, ease in (("location", "BACK", "OUT"),
                             ("rotation_euler", "BACK", "OUT"),
                             ("scale", "ELASTIC", "OUT")):
        Animator.ease(text, dp, interp, ease)
    # icon from the right with spin
    icon.animation_data_clear()
    icon.location = (icon_home + fly_dist, -2.0, 5.5)
    icon.rotation_euler = (0, 0, math.radians(200))
    icon.scale = (0.01,) * 3
    Animator.pose(icon, 6)
    icon.location = (icon_home, 0, ICON_Z)
    icon.rotation_euler = (0, 0, 0)
    icon.scale = (0.7,) * 3
    Animator.pose(icon, f_hit + 5)
    icon.rotation_euler = (0, 0, math.radians(720))
    icon.keyframe_insert(data_path="rotation_euler", frame=frame_end)
    for dp in ("location", "rotation_euler", "scale"):
        Animator.ease(icon, dp,
                      "BACK" if dp != "rotation_euler" else "LINEAR")
    for child in icon.children:
        if "Ring" in child.name or "Orb" in child.name:
            try:
                child.rotation_euler = (child.rotation_euler.x,
                                        child.rotation_euler.y, 0)
                child.keyframe_insert(data_path="rotation_euler", frame=f_hit)
                child.rotation_euler = (child.rotation_euler.x,
                                        child.rotation_euler.y,
                                        math.radians(180))
                child.keyframe_insert(data_path="rotation_euler", frame=frame_end)
                Animator.ease(child, "rotation_euler", "LINEAR")
            except Exception:
                pass
    # camera push-in
    if rig is not None:
        rig.animation_data_clear()
        rig.location = (0, -2.5, 0)
        rig.keyframe_insert(data_path="location", frame=1)
        rig.location = (0, 0, 0)
        rig.keyframe_insert(data_path="location", frame=frame_end)
        Animator.ease(rig, "location", "SINE")
    bpy.context.scene.frame_set(1)


class StudioStyle:
    """Classic look: stage, shafts, smoke, dust, glow."""

    @staticmethod
    def apply(ctx):
        cfg, mats = ctx.config, ctx.mats
        _ground(mats)
        text = TextLogoBuilder(mats).build_single(
            cfg, target_width=TEXT_TARGET_WIDTH)
        icon = IconFactory(mats).create(cfg.icon, (0, 0, ICON_Z),
                                        cfg.accent_color)
        text_home, icon_home = _layout(text, icon)
        # frame the camera on the RESTING composition, before animation data
        # exists (keyframes would otherwise report the off-screen start pose)
        text.location = (text_home, 0, TEXT_Z)
        icon.location = (icon_home, 0, ICON_Z)
        bpy.context.view_layer.update()
        frame_perspective(ctx.rig.camera, [text, icon], cfg.res_x, cfg.res_y)
        _animate(text, icon, ctx.rig.rig, cfg.frame_end, cfg.fly_dist,
                 text_home, icon_home)
        LightRig.build()
        if cfg.with_volume:
            VolumeBox.build(mats)
        if cfg.with_smoke:
            SmokeCards.build(mats)
        if cfg.with_dust:
            DustEmitter.build(
                mats, instance=spark_prototype(
                    mats, (0.75, 0.88, 1.0, 1.0), name="LogoAnim_DustMote"))
        if cfg.with_glow:
            compositing.setup_glow()
        return {"text": text.name, "icon": icon.name}
