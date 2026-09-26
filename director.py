"""LogoDirector (GRASP Controller + Facade): one entry point for every build.

UI operators, scripts and tests all go through here; styles own the look.
"""
from dataclasses import dataclass, field
import bpy
from .config import LogoAnimConfig
from .materials import MaterialFactory
from .scene_setup import SceneBuilder, clear_collection
from .styles import BuildContext, get_style
from . import output


@dataclass
class BuildResult:
    style: str
    camera: str
    output: str
    text: str = ""
    icon: str = ""
    letters: tuple = ()
    extras: dict = field(default_factory=dict)


class LogoDirector:
    def build(self, config: LogoAnimConfig) -> BuildResult:
        clear_collection()
        rig = SceneBuilder(config).build()
        ctx = BuildContext(config=config, mats=MaterialFactory(), rig=rig)
        style = get_style(config.style)
        names = style.apply(ctx) or {}
        bpy.context.scene.render.filepath = config.output
        output.configure_video_output(bpy.context.scene)
        return BuildResult(
            style=config.style,
            camera=rig.camera.name,
            output=config.output,
            text=names.get("text", ""),
            icon=names.get("icon", ""),
            letters=tuple(names.get("letters", ())),
            extras=names,
        )


def create_animated_logo(company_name="MY COMPANY", style="STUDIO",
                         icon="GEM_RINGS", engine="EEVEE",
                         output="//logo_anim.mp4", res_x=1920, res_y=1080,
                         fps=30, frame_end=120, fly_dist=12.0,
                         accent_color=(1.0, 0.45, 0.05, 1.0),
                         with_volume=True, with_smoke=True, with_dust=True,
                         with_glow=True):
    """Backwards-compatible functional API (delegates to LogoDirector)."""
    cfg = LogoAnimConfig(
        company_name=company_name, style=style, icon=icon, engine=engine,
        output=output, res_x=res_x, res_y=res_y, fps=fps, frame_end=frame_end,
        fly_dist=fly_dist, accent_color=tuple(accent_color),
        with_volume=with_volume, with_smoke=with_smoke, with_dust=with_dust,
        with_glow=with_glow)
    res = LogoDirector().build(cfg)
    return {"text": res.text, "icon": res.icon, "camera": res.camera,
            "output": res.output, "style": res.style,
            "letters": list(res.letters)}
