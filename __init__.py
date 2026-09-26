# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright 2026 Sebastian Svensson
# Licensed under the PolyForm Noncommercial License 1.0.0 - free for
# noncommercial use; commercial use and resale are not permitted.
# https://polyformproject.org/licenses/noncommercial/1.0.0
"""Blend Logo Anim Creator: procedural animated logo intros.

Architecture (GRASP/SOLID):
  config.py       Parameter Object shared by every builder (DRY)
  materials.py    MaterialFactory (Creator): cached shader builders
  scene_setup.py  SceneBuilder: render/engine/world/camera
  text_logo.py    TextLogoBuilder: single block or per-letter text
  icons.py        IconFactory + strategy registry (Open/Closed)
  curves.py       light-trail tube builders
  animation.py    Animator keyframing helpers
  fx.py           one small class per effect (SRP)
  compositing.py  glow setup, 4.x/5.x compatible
  output.py       video/image output + draft mode
  style_studio.py StudioStyle (lit stage fly-in)
  style_comet.py  CometStyle (black-stage energy reveal)
  styles.py       style registry (Open/Closed)
  director.py     LogoDirector Facade/Controller + create_animated_logo API
  properties/operators/panels: UI layer (thin, delegates to director)
"""
bl_info = {
    "name": "Blend Logo Anim Creator",
    "author": "BlendLogoAnimCreator",
    "version": (1, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Logo Anim",
    "description": ("Animated logos: studio fly-in or comet-trail reveal, "
                    "procedural icons, FX, one-click video render"),
    "category": "Animation",
}

import bpy
from .properties import LogoAnimProps
from .operators import (LOGOANIM_OT_create, LOGOANIM_OT_render,
                        LOGOANIM_OT_draft, LOGOANIM_OT_still)
from .panels import LOGOANIM_PT_panel
from .director import create_animated_logo, LogoDirector  # noqa: F401 (public API)

__all__ = ["create_animated_logo", "LogoDirector"]

classes = (LogoAnimProps, LOGOANIM_OT_create, LOGOANIM_OT_render,
           LOGOANIM_OT_draft, LOGOANIM_OT_still, LOGOANIM_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.logoanim = bpy.props.PointerProperty(type=LogoAnimProps)


def unregister():
    del bpy.types.Scene.logoanim
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
