"""Text logo builders: single extruded block (studio) or per-letter (plug)."""
import bpy
from .scene_setup import link

#: letters stand upright facing a -Y camera
UPRIGHT = (1.57079632679, 0.0, 0.0)

_font_cache = {}


def load_font(path):
    """Load (and cache) a .ttf/.otf; falls back to Blender's font on failure."""
    if not path:
        return None
    if path in _font_cache:
        return _font_cache[path]
    font = None
    try:
        font = bpy.data.fonts.load(path, check_existing=True)
    except Exception:
        font = None
    _font_cache[path] = font
    return font


def _apply_font(text_data, config):
    font = load_font(getattr(config, "font", ""))
    if font is not None:
        try:
            text_data.font = font
        except Exception:
            pass
    return font


class TextLogoBuilder:
    def __init__(self, mats):
        self.mats = mats

    def build_single(self, config, target_width=5.5, max_scale=1.2):
        old = bpy.data.objects.get("LogoAnim_Text")
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        bpy.ops.object.text_add(location=(0, 0, 1.2))
        t = bpy.context.view_layer.objects.active
        t.name = "LogoAnim_Text"
        link(t)
        _apply_font(t.data, config)
        t.data.body = config.company_name
        t.data.align_x = "CENTER"
        t.data.align_y = "CENTER"
        t.data.extrude = 0.22
        t.data.bevel_depth = 0.025
        t.data.bevel_resolution = 4
        t.rotation_euler = UPRIGHT
        # measure at unit scale, then fit the name to a target width so long
        # company names cannot overflow the frame (short ones cap at max_scale)
        t.scale = (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        width = t.dimensions.x or 1.0
        scale = min(max_scale, target_width / max(0.001, width))
        t.scale = (scale, scale, scale)
        bpy.context.view_layer.update()
        mat = self.mats.principled(
            "LogoAnim_TextMat", base=(0.85, 0.88, 1.0, 1.0), metallic=0.85,
            roughness=0.22, emission=(0.2, 0.55, 1.0, 1.0), emission_strength=0.6)
        t.data.materials.clear()
        t.data.materials.append(mat)
        return t

    def build_letters(self, config, mat_first, mat_rest, size=0.95,
                      baseline=1.15, tracking=0.10, mat_provider=None):
        """One object per character; first word uses mat_first.

        mat_provider(word_index, char_index, default_mat) may return a unique
        material per letter (used by the glow sweep). Row is centered on x=0.
        Returns (letters, total_width).
        """
        for o in list(bpy.data.objects):
            if o.name.startswith("LogoAnim_Letter"):
                bpy.data.objects.remove(o, do_unlink=True)
        words = (config.company_name or "MY COMPANY").split(" ") or ["MY"]
        chars = []  # (char, mat, fixed_width, word_index)
        for wi, word in enumerate(words):
            mat = mat_first if wi == 0 else mat_rest
            for ch in word:
                chars.append((ch, mat, None, wi))
            chars.append((" ", None, 0.38 * size, wi))  # gap, no object
        if chars and chars[-1][0] == " ":
            chars.pop()

        # pass 1: create + measure
        made = []
        for i, (ch, mat, fixed, wi) in enumerate(chars):
            if ch == " ":
                made.append((None, fixed))
                continue
            bpy.ops.object.text_add(location=(0, 0, baseline))
            o = bpy.context.view_layer.objects.active
            o.name = "LogoAnim_Letter%02d" % i
            link(o)
            _apply_font(o.data, config)
            o.data.body = ch
            o.data.align_x = "CENTER"
            o.data.align_y = "CENTER"
            o.data.extrude = 0.14
            o.data.bevel_depth = 0.014
            o.data.bevel_resolution = 4
            try:
                o.data.size = size
            except Exception:
                pass
            o.rotation_euler = UPRIGHT
            use_mat = mat_provider(wi, i, mat) if mat_provider else mat
            o.data.materials.clear()
            o.data.materials.append(use_mat)
            made.append((o, None))
        bpy.context.view_layer.update()
        widths = [fixed if o is None else o.dimensions.x for o, fixed in made]

        # pass 2: center the row on x=0 (caller positions the group)
        total = sum(widths) + tracking * (len(widths) - 1)
        cursor = -total / 2.0
        letters = []
        for (o, _), w in zip(made, widths):
            cursor += w / 2.0
            if o is not None:
                o.location.x = cursor
                letters.append(o)
            cursor += w / 2.0 + tracking
        return letters, total
