"""Render output setup (Single Responsibility: only output configuration).

Handles the Blender 4.x / 5.x video-output API split (media_type) internally.
"""
import os
from contextlib import contextmanager
import bpy

#: objects hidden during draft renders (expensive FX)
DRAFT_HIDE_PREFIXES = ("LogoAnim_Volume", "LogoAnim_Smoke", "LogoAnim_Dust")


def configure_video_output(scene, filepath=None):
    if filepath is not None:
        scene.render.filepath = filepath
    try:  # Blender 5.x requires VIDEO media type before FFMPEG exists
        scene.render.image_settings.media_type = "VIDEO"
    except Exception:
        pass
    try:  # 4.x needs the explicit set; 5.x derives it automatically
        scene.render.image_settings.file_format = "FFMPEG"
    except Exception:
        pass
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    for attr, val in (("constant_rate_factor", "HIGH"),
                      ("ffmpeg_preset", "GOOD"),
                      ("video_bitrate", 8000),
                      ("use_max_size", False)):
        try:
            setattr(scene.render.ffmpeg, attr, val)
        except Exception:
            pass


def configure_image_output(scene, filepath=None, fmt="PNG"):
    if filepath is not None:
        scene.render.filepath = filepath
    try:
        scene.render.image_settings.media_type = "IMAGE"
    except Exception:
        pass
    scene.render.image_settings.file_format = fmt


def draft_filepath(path):
    base, ext = os.path.splitext(path)
    return base + "_draft" + (ext or ".mp4")


@contextmanager
def draft_mode(scene, output_path):
    """Temporarily: 50% resolution, FX hidden, draft file. Always restores."""
    render = scene.render
    saved = (render.resolution_percentage, render.filepath)
    hidden = []
    for obj in bpy.data.objects:
        if obj.name.startswith(DRAFT_HIDE_PREFIXES) and not obj.hide_render:
            obj.hide_render = True
            hidden.append(obj)
    render.resolution_percentage = 50
    render.filepath = draft_filepath(bpy.path.abspath(output_path) or output_path)
    try:
        yield render.filepath
    finally:
        render.resolution_percentage, render.filepath = saved
        for obj in hidden:
            try:
                obj.hide_render = False
            except Exception:
                pass


def render_animation():
    bpy.ops.render.render(animation=True)
