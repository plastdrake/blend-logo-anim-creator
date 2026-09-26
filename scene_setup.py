"""Scene setup: collection registry, render/engine config, world, camera.

Single home for Blender scene-graph plumbing every builder reuses (DRY).
"""
import math
import bpy
import mathutils
from dataclasses import dataclass, field
from typing import Optional


# -- collection registry --------------------------------------------------
COLLECTION_NAME = "LogoAnim"


def get_collection():
    coll = bpy.data.collections.get(COLLECTION_NAME)
    if coll is None:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_collection():
    coll = bpy.data.collections.get(COLLECTION_NAME)
    if coll:
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)


def link(obj):
    coll = get_collection()
    try:
        for c in list(obj.users_collection):
            if c != coll:
                c.objects.unlink(obj)
        if obj.name not in coll.objects:
            coll.objects.link(obj)
    except Exception:
        pass


def look_at(obj, target):
    """Bake a -Z track rotation (constraints are unreliable headless)."""
    try:
        direction = mathutils.Vector(target) - mathutils.Vector(obj.location)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
    except Exception:
        pass


def content_bounds(objects):
    """(center, size) of the geometry of `objects` in world space.

    Empty parents are ignored; mesh/curve/font children are measured.
    """
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    found = False
    for obj in objects:
        stack = [obj] + list(getattr(obj, "children", []))
        for o in stack:
            if o.type not in {"MESH", "CURVE", "FONT", "SURFACE"}:
                continue
            try:
                mat = o.matrix_world
                for corner in o.bound_box:
                    w = mat @ mathutils.Vector(corner)
                    for i in range(3):
                        lo[i] = min(lo[i], w[i])
                        hi[i] = max(hi[i], w[i])
                    found = True
            except Exception:
                continue
    if not found:
        return mathutils.Vector((0, 0, 0)), mathutils.Vector((1, 1, 1))
    center = mathutils.Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2,
                               (lo[2] + hi[2]) / 2))
    size = mathutils.Vector((hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    return center, size


def frame_perspective(cam, objects, res_x, res_y, margin=0.86,
                      direction=(0.10, -1.0, 0.12)):
    """Move a perspective camera so `objects` fill the frame with margin.

    Keeps the film fit independent of the company-name length.
    """
    center, size = content_bounds(objects)
    lens = cam.data.lens or 50.0
    sensor = cam.data.sensor_width or 36.0
    sensor_h = sensor * (res_y / float(res_x or 1))
    hfov = 2.0 * math.atan(sensor / (2.0 * lens))
    vfov = 2.0 * math.atan(sensor_h / (2.0 * lens))
    need_w = max(1e-3, size.x) / margin
    need_h = max(1e-3, size.z) / margin
    dist = max(need_w / (2.0 * math.tan(hfov / 2.0)),
               need_h / (2.0 * math.tan(vfov / 2.0)))
    d = mathutils.Vector(direction).normalized()
    cam.location = center + d * dist
    look_at(cam, center)


# -- render / world / camera ----------------------------------------------
@dataclass
class SceneRig:
    camera: bpy.types.Object
    rig: Optional[bpy.types.Object] = None
    extras: dict = field(default_factory=dict)


class SceneBuilder:
    """Builds render settings, engine, world and camera from config."""

    def __init__(self, config):
        self.cfg = config

    def build(self) -> SceneRig:
        sc = bpy.context.scene
        sc.render.resolution_x = self.cfg.res_x
        sc.render.resolution_y = self.cfg.res_y
        sc.render.resolution_percentage = self.cfg.resolution_percentage
        sc.render.film_transparent = False
        sc.frame_start = 1
        sc.frame_end = self.cfg.frame_end
        sc.render.fps = self.cfg.fps
        self._exposure(sc)
        self._engine(sc)
        self._world(sc)
        if self.cfg.style == "PLUG":
            return self._ortho_camera(sc)
        return self._perspective_rig(sc)

    def _exposure(self, sc):
        """Global brightness control (in stops, so it scales everything)."""
        brightness = max(0.05, float(getattr(self.cfg, "brightness", 1.0)))
        try:
            sc.view_settings.exposure = math.log(brightness, 2.0)
        except Exception:
            pass

    def _engine(self, sc):
        if self.cfg.engine == "CYCLES":
            sc.render.engine = "CYCLES"
            try:
                sc.cycles.device = "GPU"
            except Exception:
                pass
            return
        try:
            sc.render.engine = "BLENDER_EEVEE_NEXT"
        except Exception:
            try:
                sc.render.engine = "BLENDER_EEVEE"
            except Exception:
                pass
        eevee = getattr(sc, "eevee", None)
        if eevee is not None:
            for attr, val in (("use_bloom", True),
                              ("use_volumetric_lights", True),
                              ("volumetric_tile_size", "2"),
                              ("taa_render_samples", max(16, int(
                                  getattr(self.cfg, "samples", 64)))),
                              ("use_shadows", True)):
                try:
                    setattr(eevee, attr, val)
                except Exception:
                    pass
            if getattr(self.cfg, "with_metal", False):
                # metallic surfaces need reflections to read as metal
                try:
                    eevee.use_raytracing = True
                except Exception:
                    pass
                rto = getattr(eevee, "ray_tracing_options", None)
                if rto is not None:
                    for attr, val in (("use_denoise", True),
                                      ("screen_trace_quality", 0.5),
                                      ("trace_max_roughness", 0.7)):
                        try:
                            setattr(rto, attr, val)
                        except Exception:
                            pass
        try:  # fast fly-ins streak with motion blur; keep it off
            sc.render.use_motion_blur = False
        except Exception:
            pass
        if getattr(self.cfg, "style", "") == "PLUG":
            # flat logo look: AgX desaturates bright emission heavily
            try:
                sc.view_settings.view_transform = "Standard"
                sc.view_settings.look = "None"
            except Exception:
                pass
    def _world(self, sc):
        world = sc.world or bpy.data.worlds.new("LogoAnimWorld")
        sc.world = world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputWorld")
        bg = nodes.new("ShaderNodeBackground")
        if self.cfg.style == "PLUG":
            bg.inputs["Color"].default_value = (0, 0, 0, 1)
            bg.inputs["Strength"].default_value = 0.0
        else:
            from .materials import set_socket
            set_socket(bg.inputs["Color"], (0.008, 0.01, 0.02, 1.0))
            bg.inputs["Strength"].default_value = 0.6
        links.new(bg.outputs["Background"], out.inputs["Surface"])

    def _camera_object(self, name, lens=None, cam_type=None, ortho_scale=None):
        data = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
        if lens:
            data.lens = lens
        if cam_type:
            try:
                data.type = cam_type
            except Exception:
                pass
        if ortho_scale:
            try:
                data.ortho_scale = ortho_scale
            except Exception:
                pass
        cam = bpy.data.objects.get(name)
        if cam is None:
            cam = bpy.data.objects.new(name, data)
            link(cam)
        return cam

    def _perspective_rig(self, sc):
        rig = bpy.data.objects.get("LogoAnim_CamRig")
        if rig is None:
            rig = bpy.data.objects.new("LogoAnim_CamRig", None)
            link(rig)
        rig.location = (0, 0, 0)
        rig.rotation_euler = (0, 0, 0)
        cam = self._camera_object("LogoAnim_Cam", lens=50)
        cam.parent = rig
        cam.location = (1.0, -12.5, 2.8)
        target = bpy.data.objects.get("LogoAnim_CamTarget")
        if target is None:
            target = bpy.data.objects.new("LogoAnim_CamTarget", None)
            link(target)
        target.location = (0.9, 0.0, 1.0)
        look_at(cam, target.location)
        for c in list(cam.constraints):
            if c.type == "TRACK_TO":
                try:
                    cam.constraints.remove(c)
                except Exception:
                    pass
        sc.camera = cam
        return SceneRig(camera=cam, rig=rig)

    def _ortho_camera(self, sc):
        """Flat front view for the 2D plug look (static, no dolly)."""
        cam = self._camera_object("LogoAnim_Cam", cam_type="ORTHO",
                                  ortho_scale=10.0)
        cam.parent = None
        cam.location = (0.0, -20.0, 2.15)
        look_at(cam, (0.0, 0.0, 2.15))
        sc.camera = cam
        return SceneRig(camera=cam)
