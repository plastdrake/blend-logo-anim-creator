"""Build configuration.

GRASP Information Expert / Parameter Object: every builder and style takes a
single LogoAnimConfig instead of a dozen loose arguments (DRY).
"""
from dataclasses import dataclass
from typing import Tuple

Color = Tuple[float, float, float, float]


@dataclass
class LogoAnimConfig:
    company_name: str = "MY COMPANY"
    style: str = "STUDIO"          # STUDIO | PLUG (see styles.py)
    icon: str = "GEM_RINGS"        # studio icon preset (see icons.py)
    engine: str = "EEVEE"          # EEVEE | CYCLES
    output: str = "//logo_anim.mp4"
    res_x: int = 1920
    res_y: int = 1080
    resolution_percentage: int = 100
    samples: int = 64              # Eevee render samples (higher = cleaner)
    fps: int = 30
    frame_end: int = 300
    hold_seconds: float = 2.0     # fully settled logo at the end
    brightness: float = 1.0       # exposure multiplier (1.0 = as authored)
    glow: float = 1.0             # compositor glare strength multiplier
    fly_dist: float = 12.0
    font: str = ""                 # path to .ttf/.otf ("" = Blender's default)
    accent_color: Color = (1.0, 0.45, 0.05, 1.0)      # cord/plug/words glow
    secondary_color: Color = (1.0, 1.0, 1.0, 1.0)     # second word colour
    with_volume: bool = True
    with_smoke: bool = True
    with_dust: bool = True
    with_glow: bool = True
    with_light_sweep: bool = True  # light bar passing in front of the logo
    with_metal: bool = True        # metallic highlights on plug + second word

    @classmethod
    def from_scene(cls, props) -> "LogoAnimConfig":
        """Build a config from the UI PropertyGroup (duck-typed, no import)."""
        get = lambda name, default: getattr(props, name, default)
        font = get("font_file", "") or get("font", "")
        return cls(
            company_name=get("company_name", "MY COMPANY"),
            style=get("style", "STUDIO"),
            icon=get("icon", "GEM_RINGS"),
            engine=get("engine", "EEVEE"),
            output=get("output", "//logo_anim.mp4"),
            res_x=get("res_x", 1920),
            res_y=get("res_y", 1080),
            samples=get("samples", 64),
            fps=get("fps", 30),
            frame_end=get("frame_end", 300),
            hold_seconds=get("hold_seconds", 2.0),
            brightness=get("brightness", 1.0),
            glow=get("glow", 1.0),
            fly_dist=get("fly_dist", 12.0),
            font=font,
            accent_color=tuple(get("accent_color", (1.0, 0.45, 0.05, 1.0))),
            with_volume=get("with_volume", True),
            with_smoke=get("with_smoke", True),
            with_dust=get("with_dust", True),
            with_glow=get("with_glow", True),
            with_light_sweep=get("with_light_sweep", True),
            with_metal=get("with_metal", True),
        )
