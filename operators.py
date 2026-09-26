"""UI operators (thin: they delegate everything to director/output)."""
import bpy
from .config import LogoAnimConfig
from .director import LogoDirector
from . import output


def _impact_frame(props):
    if getattr(props, "style", "STUDIO") == "PLUG":
        return int(getattr(props, "frame_end", 120) * 0.95)
    return 32


class LOGOANIM_OT_create(bpy.types.Operator):
    bl_idname = "logoanim.create"
    bl_label = "Create Animated Logo"
    bl_description = "Build the logo scene for the selected style"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.logoanim
        res = LogoDirector().build(LogoAnimConfig.from_scene(props))
        self.report({"INFO"}, "%s logo built (%d frames)"
                    % (res.style, props.frame_end))
        return {"FINISHED"}


class LOGOANIM_OT_render(bpy.types.Operator):
    bl_idname = "logoanim.render_video"
    bl_label = "Render to Video"
    bl_description = "Render full-quality animation to MP4"

    def execute(self, context):
        props = context.scene.logoanim
        output.configure_video_output(context.scene, props.output)
        output.render_animation()
        self.report({"INFO"}, "Rendered: %s" % props.output)
        return {"FINISHED"}


class LOGOANIM_OT_draft(bpy.types.Operator):
    bl_idname = "logoanim.render_draft"
    bl_label = "Draft Render (fast)"
    bl_description = ("Render animation at 50% with heavy FX hidden; "
                      "settings are restored afterwards")

    def execute(self, context):
        props = context.scene.logoanim
        with output.draft_mode(context.scene, props.output) as path:
            output.render_animation()
        self.report({"INFO"}, "Draft rendered: %s" % path)
        return {"FINISHED"}


class LOGOANIM_OT_still(bpy.types.Operator):
    bl_idname = "logoanim.render_still"
    bl_label = "Render Still"
    bl_description = "Render the impact frame as a preview image"

    def execute(self, context):
        context.scene.frame_set(_impact_frame(context.scene.logoanim))
        bpy.ops.render.render()
        return {"FINISHED"}
