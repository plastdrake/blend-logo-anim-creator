"""FX builders: light rig, volume shafts, smoke cards, dust, ember bursts.

Each class owns one effect (Single Responsibility) and shares MaterialFactory.
"""
import math
import bpy
from .scene_setup import link, look_at


def _light(name, ltype, energy, loc, rot, color=(1, 1, 1, 1)):
    data = bpy.data.lights.get(name) or bpy.data.lights.new(name, ltype)
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, data)
        link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    try:
        data.energy = energy
        data.color = color[:3]
    except Exception:
        pass
    return obj


def apply_settings(ps, spec):
    """Set particle settings one by one.

    Crucially, a single unsupported property must not abort the rest:
    if render_type/instance_object were skipped, Eevee would draw nothing.
    """
    failures = []
    for attr, value in spec:
        try:
            setattr(ps, attr, value)
        except Exception:
            failures.append(attr)
    return failures


def burst_emitter(name, pos, spread):
    """A cube emitter: particles fill a volume instead of a flat plane.

    A plane seen edge-on collapses every particle into a straight line.
    """
    bpy.ops.mesh.primitive_cube_add(size=max(0.05, spread), location=pos)
    em = bpy.context.view_layer.objects.active
    em.name = name
    link(em)
    try:
        em.display_type = "WIRE"
    except Exception:
        pass
    return em


def make_invisible(em, mats, mat_name):
    """Emitter shells must never be drawn (nor occlude the logo)."""
    em.data.materials.clear()
    em.data.materials.append(mats.transparent(mat_name))
    for psys in em.particle_systems:
        try:  # render particles, never the shell
            psys.settings.use_render_emitter = False
        except Exception:
            pass


class LightRig:
    @staticmethod
    def build():
        key = _light("LogoAnim_KeySpot", "SPOT", 2500,
                     (0, -7, 7), (math.radians(55), 0, 0))
        try:
            key.data.spot_size = math.radians(38)
            key.data.spot_blend = 0.4
            key.data.shadow_soft_size = 0.5
        except Exception:
            pass
        _light("LogoAnim_Rim", "AREA", 1800, (5, 4, 4),
               (math.radians(70), 0, math.radians(130)), (0.25, 0.5, 1.0, 1.0))
        _light("LogoAnim_Fill", "AREA", 500, (-5, -3, 3),
               (math.radians(65), 0, math.radians(-60)), (1.0, 0.7, 0.45, 1.0))
        try:  # energy pulse at the impact frame
            key.data.animation_data_clear()
            for frame, energy in ((1, 800), (32, 3500), (60, 2500)):
                key.data.energy = energy
                key.data.keyframe_insert(data_path="energy", frame=frame)
        except Exception:
            pass


class MetalLightRig:
    """Frontal area lights so metallic surfaces catch highlights.

    The plug style is otherwise unlit (emission only), which would leave any
    PBR metal black - these give it a studio-lit sheen.
    """

    SPECS = (
        ("LogoAnim_MetalKey", 330.0, (-3.4, -6.5, 4.2), 2.0,
         (1.00, 0.96, 0.90, 1.0)),
        ("LogoAnim_MetalRim", 235.0, (3.4, -5.5, 0.2), 1.6,
         (0.70, 0.84, 1.00, 1.0)),
        ("LogoAnim_MetalFill", 95.0, (-5.0, -6.0, -0.8), 3.0,
         (1.00, 0.76, 0.50, 1.0)),
    )

    @classmethod
    def build(cls, aim=(0.6, 0.0, 1.3)):
        made = []
        for name, energy, loc, size, color in cls.SPECS:
            lo = _light(name, "AREA", energy, loc, (0.0, 0.0, 0.0), color)
            try:
                lo.data.size = size
                lo.data.shape = "SQUARE"
            except Exception:
                pass
            look_at(lo, aim)
            made.append(lo)
        return made


class SweepingLight:
    """A light that travels past the logo, lighting it as it goes.

    Deliberately invisible: nothing renders, but the metallic surfaces catch a
    moving highlight, so the logo appears to be lit by a passing torch.
    """

    @staticmethod
    def build(name="LogoAnim_SweepLight", energy=200.0, size=2.0,
              front_y=-4.0, z=1.4, color=(1.0, 0.96, 0.90, 1.0), aim=None):
        lo = _light(name, "AREA", energy, (0.0, front_y, z), (0.0, 0.0, 0.0),
                    color)
        try:
            lo.data.size = size
            lo.data.shape = "SQUARE"
        except Exception:
            pass
        look_at(lo, aim or (0.0, 0.0, z))
        return lo

    @staticmethod
    def animate(obj, f_start, f_end, x_from=-6.0, x_to=6.5, fade_out=10):
        """Travel across, then switch off so the settled hold is clean."""
        obj.animation_data_clear()
        base = (obj.location.y, obj.location.z)
        obj.location = (x_from, base[0], base[1])
        obj.keyframe_insert(data_path="location", frame=f_start)
        obj.location = (x_to, base[0], base[1])
        obj.keyframe_insert(data_path="location", frame=f_end)

        energy = obj.data.energy
        for frame, value in ((f_start, 0.0), (f_start + 4, energy),
                             (f_end, energy), (f_end + fade_out, 0.0)):
            obj.data.energy = value
            obj.data.keyframe_insert(data_path="energy", frame=frame)

        from .animation import Animator
        Animator.set_key_interpolation(obj, "location", f_start, "SINE", "IN")
        return obj


class VolumeBox:
    @staticmethod
    def build(mats):
        old = bpy.data.objects.get("LogoAnim_Volume")
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        bpy.ops.mesh.primitive_cube_add(size=24, location=(0, -3, 3))
        vol = bpy.context.view_layer.objects.active
        vol.name = "LogoAnim_Volume"
        link(vol)
        try:
            vol.display_type = "WIRE"
        except Exception:
            pass
        vol.data.materials.clear()
        vol.data.materials.append(mats.volume("LogoAnim_VolumeMat"))


class SmokeCards:
    @staticmethod
    def build(mats):
        for i, x in enumerate([-5.0, 5.0]):
            name = "LogoAnim_Smoke%d" % i
            old = bpy.data.objects.get(name)
            if old:
                bpy.data.objects.remove(old, do_unlink=True)
            bpy.ops.mesh.primitive_plane_add(size=9, location=(x * 0.6, 3.5, 2.0))
            p = bpy.context.view_layer.objects.active
            p.name = name
            link(p)
            p.rotation_euler = (math.radians(90), 0, math.radians(15 if i == 0 else -15))
            p.data.materials.clear()
            p.data.materials.append(mats.smoke_card(name + "Mat"))


class DustEmitter:
    @staticmethod
    def build(mats, name="LogoAnim_Dust", size=16, loc=(0, 0, 2), count=400,
              instance=None):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        em = burst_emitter(name, loc, size)
        bpy.ops.object.particle_system_add()
        ps = em.particle_systems.active.settings
        ps.name = "LogoAnimDust"
        apply_settings(ps, (
            ("type", "EMITTER"),
            ("count", count),
            ("frame_start", 1),
            ("frame_end", 120),
            ("lifetime", 120),
            ("emit_from", "VOLUME"),
            ("physics_type", "NEWTON"),
            ("particle_size", 0.6),
            ("size_randomness", 0.9),
            ("display_size", 0.03),
            ("display_method", "CIRCLE"),
            ("brownian_factor", 0.6),
            ("drag_factor", 0.1),
            # Eevee cannot draw the default halo type: instance a tiny mote
            ("render_type", "OBJECT" if instance else "NONE"),
            ("instance_object", instance),
        ))
        try:
            ps.effector_weights.gravity = 0.0
        except Exception:
            pass
        return em


_spark_cache = {}


def spark_prototype(mats, color, name="LogoAnim_Spark", radius=0.018,
                    strength=1.1):
    """Tiny emission sphere instanced by ember particles.

    Kept render-visible but parked far below the stage: hiding it would also
    hide its particle instances.
    """
    if name in _spark_cache and bpy.data.objects.get(name):
        return bpy.data.objects[name]
    mat = mats.emission(name + "_Mat", tuple(color), strength)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, -80),
                                         segments=8, ring_count=6)
    s = bpy.context.view_layer.objects.active
    s.name = name
    link(s)
    s.data.materials.clear()
    s.data.materials.append(mat)
    try:
        s.hide_render = False
    except Exception:
        pass
    _spark_cache[name] = s
    return s


def spark_palette(mats, colors, radius=0.018):
    """One small prototype per colour, so bursts can be multi-coloured."""
    return [spark_prototype(mats, tuple(c), name="LogoAnim_Spark%d" % i,
                            radius=radius)
            for i, c in enumerate(colors)]


class EmberBurst:
    """Object-instanced spark burst (works in Eevee, headless-safe)."""

    _n = 0

    @classmethod
    def build(cls, mats, pos, f_start, color, count=220, lifetime=30,
              speed=1.6, duration=1, spread=0.4, parent=None, name=None,
              instance=None, size=1.0):
        cls._n += 1
        name = name or "LogoAnim_Embers%d" % cls._n
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        em = burst_emitter(name, pos, spread)
        if parent is not None:
            em.parent = parent
        bpy.ops.object.particle_system_add()
        ps = em.particle_systems.active.settings
        apply_settings(ps, (
            ("type", "EMITTER"),
            ("count", count),
            ("frame_start", f_start),
            ("frame_end", f_start + max(0, duration - 1)),
            ("lifetime", lifetime),
            ("lifetime_randomness", 0.5),
            ("emit_from", "VOLUME"),
            ("distribution", "RAND"),
            ("physics_type", "NEWTON"),
            ("normal_factor", speed),
            ("factor_random", 0.9),
            ("brownian_factor", 1.2),
            ("drag_factor", 0.15),
            ("particle_size", size),
            ("size_randomness", 0.7),
            # these two must never be skipped: Eevee cannot draw the default
            ("render_type", "OBJECT"),
            ("instance_object", instance or spark_prototype(mats, tuple(color))),
        ))
        try:
            ps.effector_weights.gravity = 0.35
        except Exception:
            pass
        make_invisible(em, mats, name + "GhostMat")
        return em
