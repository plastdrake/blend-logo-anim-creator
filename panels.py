"""Sidebar panel (only layout, no logic)."""
import bpy


class LOGOANIM_PT_panel(bpy.types.Panel):
    bl_label = "Logo Anim"
    bl_idname = "LOGOANIM_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Logo Anim"

    def draw(self, context):
        p = context.scene.logoanim
        layout = self.layout
        layout.prop(p, "company_name")
        layout.prop(p, "font")
        layout.prop(p, "font_file")
        layout.prop(p, "style")
        if p.style == "STUDIO":
            layout.prop(p, "icon")
        layout.prop(p, "accent_color")
        layout.prop(p, "engine")
        row = layout.row(align=True)
        row.prop(p, "res_x")
        row.prop(p, "res_y")
        row.prop(p, "samples")
        row = layout.row(align=True)
        row.prop(p, "fps")
        row.prop(p, "frame_end")
        layout.prop(p, "brightness")
        layout.prop(p, "glow")
        if p.style == "STUDIO":
            layout.prop(p, "fly_dist")
        else:
            layout.prop(p, "hold_seconds")
        layout.prop(p, "output")
        layout.separator()
        if p.style == "STUDIO":
            layout.prop(p, "with_volume")
            layout.prop(p, "with_smoke")
            layout.prop(p, "with_dust")
        else:
            layout.prop(p, "with_light_sweep")
            layout.prop(p, "with_metal")
        layout.prop(p, "with_glow")
        layout.separator()
        layout.operator("logoanim.create", icon="PLAY")
        layout.operator("logoanim.render_still", icon="IMAGE_DATA")
        layout.operator("logoanim.render_draft", icon="SEQUENCE")
        layout.operator("logoanim.render_video", icon="FILE_MOVIE")
