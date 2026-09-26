"""UI properties (only data, no behavior)."""
import os
import sys
import bpy
from bpy.props import (StringProperty, EnumProperty, IntProperty,
                       FloatProperty, BoolProperty, FloatVectorProperty)

_font_cache_list = None


def font_items(self, context):
    """Dynamic dropdown of fonts installed on this machine."""
    items = [("", "Default (Blender)", "Blender's built-in font")]
    for path in _installed_fonts():
        items.append((path, os.path.basename(path), path))
    return items


def _installed_fonts():
    global _font_cache_list
    if _font_cache_list is None:
        found = []
        for folder in _font_dirs():
            for root, _dirs, files in os.walk(folder):
                for name in files:
                    if name.lower().endswith((".ttf", ".otf")):
                        found.append(os.path.join(root, name))
        found = sorted(set(found), key=lambda p: os.path.basename(p).lower())
        _font_cache_list = found
    return _font_cache_list


def _font_dirs():
    dirs = []
    if sys.platform.startswith("win"):
        win = os.environ.get("WINDIR", r"C:\Windows")
        dirs += [os.path.join(win, "Fonts"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""),
                              "Microsoft", "Windows", "Fonts")]
    elif sys.platform == "darwin":
        dirs += ["/System/Library/Fonts", "/Library/Fonts",
                 os.path.expanduser("~/Library/Fonts")]
    else:
        dirs += ["/usr/share/fonts", "/usr/local/share/fonts",
                 os.path.expanduser("~/.fonts"),
                 os.path.expanduser("~/.local/share/fonts")]
    return [d for d in dirs if d and os.path.isdir(d)]


class LogoAnimProps(bpy.types.PropertyGroup):
    company_name: StringProperty(name="Company", default="MY COMPANY", maxlen=64)
    font: EnumProperty(
        name="Font", items=font_items,
        description="Typeface for the company name (optional)")
    font_file: StringProperty(
        name="Custom font", default="", subtype="FILE_PATH",
        description="Use a specific .ttf/.otf instead of the list above")
    style: EnumProperty(name="Style", default="STUDIO", items=[
        ("STUDIO", "Studio Fly-in", "3D text + icon on a lit stage"),
        ("PLUG", "Plug & Vine", "Jack flies in, grows a vine, name blooms (reference look)"),
    ])
    icon: EnumProperty(name="Icon", default="GEM_RINGS", items=[
        ("GEM_RINGS", "Gem + Rings", "Glowing gem with gold orbit rings"),
        ("TORUS_KNOT", "Torus Knot", "Smooth abstract knot"),
        ("SHIELD", "Shield", "Beveled emblem block"),
        ("CUBE_ABSTRACT", "Cube Abstract", "Floating cubes cluster"),
        ("ORBIT_SPHERES", "Orbit Spheres", "Core with orbiting spheres"),
    ])
    accent_color: FloatVectorProperty(
        name="Accent", subtype="COLOR", size=4, min=0.0, max=1.0,
        default=(1.0, 0.45, 0.05, 1.0),
        description="Glow color: comet/trails/embers, and the studio icon")
    engine: EnumProperty(name="Engine", default="EEVEE", items=[
        ("EEVEE", "Eevee (fast)", "Fast preview-friendly render"),
        ("CYCLES", "Cycles", "Photorealistic, slower"),
    ])
    output: StringProperty(name="Output", default="//logo_anim.mp4",
                           subtype="FILE_PATH")
    res_x: IntProperty(name="X", default=1920, min=320, max=7680)
    res_y: IntProperty(name="Y", default=1080, min=240, max=4320)
    samples: IntProperty(
        name="Samples", default=64, min=8, max=512,
        description="Eevee render samples: higher is cleaner but slower")
    fps: IntProperty(name="FPS", default=30, min=12, max=120)
    frame_end: IntProperty(name="Frames", default=300, min=30, max=900)
    hold_seconds: FloatProperty(
        name="Settle hold", default=2.0, min=0.0, max=10.0, step=10,
        description="Seconds of fully settled logo at the end (Plug style)")
    brightness: FloatProperty(
        name="Brightness", default=1.0, min=0.2, max=3.0, step=5,
        description="Overall exposure multiplier")
    glow: FloatProperty(
        name="Glow", default=1.0, min=0.0, max=3.0, step=5,
        description="Bloom/glare strength multiplier")
    fly_dist: FloatProperty(name="Fly distance", default=12.0, min=3.0, max=30.0)
    with_volume: BoolProperty(name="Light shafts (volume)", default=True)
    with_smoke: BoolProperty(name="Smoke cards", default=True)
    with_dust: BoolProperty(name="Dust particles", default=True)
    with_glow: BoolProperty(name="Glow (compositor)", default=True)
    with_light_sweep: BoolProperty(
        name="Light sweep", default=True,
        description="A soft bar of light travels in front of the logo")
    with_metal: BoolProperty(
        name="Metallic shine", default=True,
        description="Metallic highlights on the plug and the second word")
