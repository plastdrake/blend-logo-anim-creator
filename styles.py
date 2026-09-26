"""Style registry (Open/Closed: new looks plug in here, core stays untouched)."""
from dataclasses import dataclass, field
from .config import LogoAnimConfig
from .materials import MaterialFactory
from .scene_setup import SceneRig
from .style_studio import StudioStyle
from .style_plug import PlugStyle


@dataclass
class BuildContext:
    """Everything a style needs (GRASP: information hiding for styles)."""
    config: LogoAnimConfig
    mats: MaterialFactory
    rig: SceneRig
    extras: dict = field(default_factory=dict)


STYLES = {
    "STUDIO": StudioStyle,
    "PLUG": PlugStyle,
}


def get_style(style_id):
    try:
        return STYLES[style_id]
    except KeyError:
        raise ValueError("Unknown style %r (expected one of %s)"
                         % (style_id, sorted(STYLES)))
