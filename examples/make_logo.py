"""Create an animated logo through code.

Run inside Blender's Scripting tab, or headless:

    blender --background --python examples/make_logo.py

Pick one of the two config blocks below; `cfg` is what gets built.
"""
import importlib.util
import os
import sys

# Blender's `--python` does not add the script's directory to sys.path, so the
# add-on is loaded explicitly from the repository root (two levels up).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_addon(repo_root):
    init = os.path.join(repo_root, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        "blend_logo_anim_creator", init, submodule_search_locations=[repo_root])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["blend_logo_anim_creator"] = mod
    spec.loader.exec_module(mod)
    return mod


load_addon(REPO_ROOT)

import bpy  # noqa: E402
from blend_logo_anim_creator import output  # noqa: E402
from blend_logo_anim_creator.config import LogoAnimConfig  # noqa: E402
from blend_logo_anim_creator.director import LogoDirector  # noqa: E402

# --- Studio fly-in: 3D text + icon on a lit stage -------------------------
studio = LogoAnimConfig(
    company_name="MY COMPANY",
    style="STUDIO",
    icon="GEM_RINGS",   # GEM_RINGS | TORUS_KNOT | SHIELD | CUBE_ABSTRACT | ORBIT_SPHERES
    engine="EEVEE",
    output="//logo_studio.mp4",
    res_x=1920, res_y=1080, fps=30, frame_end=180,
    font="",            # "" = Blender's built-in font, or a .ttf/.otf path
    accent_color=(1.0, 0.45, 0.05, 1.0),
)

# --- Plug & plant: jack flies in, cord grows into a plant, name blooms ----
plug = LogoAnimConfig(
    company_name="ROSMIC GAMES",
    style="PLUG",
    output="//logo_plug.mp4",
    res_x=1920, res_y=1080, fps=30, frame_end=300,
    hold_seconds=2.0,   # fully settled logo at the end
    brightness=1.0,     # global exposure multiplier
    glow=1.0,           # bloom strength multiplier
    accent_color=(1.0, 0.45, 0.05, 1.0),
    secondary_color=(1.0, 1.0, 1.0, 1.0),
)

cfg = plug
LogoDirector().build(cfg)

# Preview the settled logo (last frame of the hold):
bpy.context.scene.frame_set(cfg.frame_end - 2)

# Render the full video (uncomment):
# output.configure_video_output(bpy.context.scene, cfg.output)
# output.render_animation()

# Fast draft render (50% resolution, heavy FX hidden, settings restored after):
# with output.draft_mode(bpy.context.scene, cfg.output):
#     output.render_animation()
