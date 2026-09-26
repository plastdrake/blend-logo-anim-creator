"""Plug style: the jack + growing plant + blooming name intro.

Story beats (fractions of frame_end, so any duration works):
  0.02-0.20  the 3.5mm jack flies in from the left and settles
  0.20-0.24  it seats with a jolt, flash and spark burst at the tip
  0.24-0.50  a cord grows from the cable end and unfurls three leaves
  0.48-0.54  spark burst around the plant
  0.52-0.78  the company name grows out of the plant, letter by letter
  0.80-0.92  a light sweeps across, in front of the logo, and a glow runs
             through the text
  0.90-1.00  particles fade out, logo holds
"""
import math
import bpy
from .scene_setup import link
from .text_logo import TextLogoBuilder, UPRIGHT
from .animation import Animator
from .plug import PlugBuilder
from .plant import PlantBuilder
from . import curves
from .fx import (EmberBurst, MetalLightRig, SweepingLight, spark_palette)
from .particles import fade_prototypes
from . import compositing

# layout (world units, orthographic front view)
PLUG_POS = (-2.35, 0.0, 1.15)
TEXT_LEFT = -1.05
TEXT_BASELINE = 1.15
TEXT_SIZE = 0.62
TEXT_MAX_RIGHT = 5.2

#: cord root: just inside the strain relief, whose tip radius (0.15 at
#: x = -3.11) matches the cord exactly - so the cord continues the boot's
#: silhouette with no lip, step or seam
CORD_ROOT = (-3.09, 0.0, 1.15)
CORD_ROOT_RADIUS = 0.152
#: cubic bezier: leaves the jack ALONG ITS AXIS first (tangent continuous),
#: then curves up and over
STEM_CONTROL = (
    CORD_ROOT,
    (-3.34, 0.0, 1.16),
    (-3.72, 0.0, 1.85),
    (-3.14, 0.0, 2.76),
)
#: stem thickness: straight out of the boot, then tapering to the tip
STEM_PROFILE = (
    (0.00, CORD_ROOT_RADIUS),
    (0.12, 0.148),
    (0.34, 0.122),
    (0.58, 0.096),
    (0.80, 0.062),
    (1.00, 0.032),
)
#: branches sprout off the stem; each carries a leaf that opens while it grows.
#: `at`/`span` are fractions of the growth window (speedlapse timing).
#: `offset` 0 puts the branch's root on the stem's centreline, so its capped end
#: is buried inside the stem instead of poking out as a stub.
BRANCHES = (
    {"t": 0.30, "angle": 148.0, "length": 0.74, "curve": -30.0, "side": 1,
     "at": 0.26, "span": 0.20, "offset": 0.0,
     "leaf": {"angle": 122.0, "length": 0.92, "width": 0.40, "bend": 0.16,
              "sweep": 0.60, "at": 0.40, "span": 0.20, "back": 0.10}},
    {"t": 0.58, "angle": 30.0, "length": 0.66, "curve": 26.0, "side": -1,
     "at": 0.42, "span": 0.20, "offset": 0.0,
     "leaf": {"angle": 66.0, "length": 0.88, "width": 0.38, "bend": 0.15,
              "sweep": 0.55, "at": 0.56, "span": 0.20, "back": 0.10}},
)
#: the leader leaf continues the stem itself (no extra twig / visible stub)
TIP_LEAF = {"length": 0.86, "width": 0.37, "bend": 0.13, "sweep": 0.50,
            "at": 0.52, "span": 0.26, "back": 0.11}


def _var(index, salt, lo, hi):
    """Deterministic pseudo-variation in [lo, hi] (reproducible every run)."""
    h = ((index * 73856093) ^ (salt * 19349663)) % 997
    return lo + (hi - lo) * (h / 996.0)


def _lighten(color, amount):
    """Blend a colour toward white (keeps the hue for veins/highlights)."""
    return tuple(c + (1.0 - c) * amount for c in color[:3]) + (1.0,)


def _palette(accent, secondary):
    """Particle colours: keep the logo hues, add warm + cool sparks."""
    return (
        tuple(accent),
        (1.00, 0.72, 0.28, 1.0),   # amber
        (1.00, 0.97, 0.88, 1.0),   # warm white
        tuple(secondary),
        (0.55, 0.82, 1.00, 1.0),   # cool blue spark
    )


def _letter_materials(ctx, with_metal):
    """Per-letter emissive materials, optionally with a metallic sheen."""
    cfg, mats = ctx.config, ctx.mats
    accent = tuple(cfg.accent_color)
    secondary = tuple(cfg.secondary_color)
    made = []

    def provider(wi, ci, default):
        if wi == 0:
            base, strength = accent, 0.74
            metallic, rough = 0.55, 0.36
        else:
            base, strength = secondary, 0.22
            metallic, rough = 0.95, 0.42
        idx = len(made)
        if with_metal:
            mat = mats.principled("LogoAnim_LetterMat%02d" % idx, base=base,
                                  metallic=metallic, roughness=rough,
                                  emission=base, emission_strength=strength)
        else:
            mat = mats.emission("LogoAnim_LetterMat%02d" % idx, base,
                                1.15 if wi == 0 else 1.0)
        made.append((mat, 1.15 if wi == 0 else 1.0))
        return mat

    return provider, made


def _build_text(ctx, f_let0, f_let1, f_sweep0, f_sweep1, with_metal):
    """Measured letter row; each letter grows out of the plant."""
    cfg = ctx.config
    provider, made = _letter_materials(ctx, with_metal)

    builder = TextLogoBuilder(ctx.mats)
    size = TEXT_SIZE
    letters, total = [], 0.0
    for _ in range(3):  # shrink until the row fits the frame
        letters, total = builder.build_letters(
            cfg, None, None, size=size, baseline=TEXT_BASELINE,
            mat_provider=provider)
        if TEXT_LEFT + total <= TEXT_MAX_RIGHT or not letters:
            break
        size *= 0.9
        made.clear()

    words = bpy.data.objects.get("LogoAnim_Words")
    if words is None:
        words = bpy.data.objects.new("LogoAnim_Words", None)
        link(words)
    for letter in letters:
        letter.parent = words
    words.location.x = TEXT_LEFT + total / 2.0

    # The name unfurls from the plant: the first letter sprouts from the stem's
    # tip, each next one from where the previous landed, with per-letter timing
    # / swivel / scale / curve variation so the growth reads as organic.
    n_letters = max(1, len(letters))
    step = (f_let1 - f_let0) / n_letters
    stem_tip = STEM_CONTROL[3]
    for i, letter in enumerate(letters):
        f0 = int(f_let0 + i * step)
        end_local = (letter.location.x, 0.0, letter.location.z)
        if i == 0:
            start_local = (stem_tip[0] - words.location.x, 0.0,
                           stem_tip[2] - 0.15)
            duration = int(round(step * _var(i, 3, 1.6, 2.2)))
            scale0, arc = 0.10, _var(i, 4, 0.10, 0.20)
        else:
            prev = letters[i - 1].location.x
            start_local = (prev + _var(i, 1, 0.02, 0.18), 0.0,
                           TEXT_BASELINE + _var(i, 2, 0.02, 0.16))
            duration = int(round(step * _var(i, 3, 1.15, 1.85)))
            scale0 = _var(i, 5, 0.14, 0.32)
            arc = _var(i, 4, 0.02, 0.09)
        Animator.grow_from(letter, f0, f0 + max(6, duration),
                           start_local, end_local, UPRIGHT,
                           start_scale=scale0,
                           spin=math.radians(_var(i, 6, -15.0, 15.0)),
                           arc=arc)

    # glow run: each letter brightens in turn as the passing light reaches it
    n = max(1, len(made))
    for i, (mat, base) in enumerate(made):
        f = f_sweep0 + (f_sweep1 - f_sweep0) * i / max(1, n - 1)
        ctx.mats.flash(mat, int(f), peak=base * 2.1, base=base * 0.5,
                       width=8)
    return words, letters, total


class PlugStyle:
    @staticmethod
    def apply(ctx):
        cfg, mats = ctx.config, ctx.mats
        F = cfg.frame_end
        accent = tuple(cfg.accent_color)
        metal = getattr(cfg, "with_metal", True)
        # Beats are fractions of the ACTION window; the last `hold_seconds`
        # are left completely still so the finished logo can settle on screen.
        hold = int(round(max(0.0, getattr(cfg, "hold_seconds", 2.0)) *
                         max(1, cfg.fps)))
        A = max(30, F - hold)
        f_fly = int(.02 * A)
        f_land = int(.20 * A)
        f_grow0 = int(.24 * A)
        f_grow1 = int(.50 * A)
        f_burst = int(.51 * A)
        f_let0 = int(.52 * A)
        f_let1 = int(.74 * A)
        f_sweep0 = int(.74 * A)
        f_sweep1 = int(.94 * A)     # travels the full width, then settles
        f_fade0 = int(.90 * A)
        f_fade1 = int(.97 * A)

        sparks = spark_palette(mats, _palette(accent, tuple(cfg.secondary_color)),
                               radius=0.016)

        # -- the jack flies in and seats ----------------------------------
        plug = PlugBuilder(mats).build(accent, location=PLUG_POS,
                                       with_metal=metal)
        plug.animation_data_clear()
        plug.location = (PLUG_POS[0] - 7.5, PLUG_POS[1], PLUG_POS[2] + 0.9)
        plug.rotation_euler = (0, 0, math.radians(-28))
        Animator.pose(plug, f_fly)
        plug.location = PLUG_POS
        plug.rotation_euler = (0, 0, 0)
        Animator.pose(plug, f_land)
        Animator.ease(plug, "location", "QUAD", "OUT")
        Animator.ease(plug, "rotation_euler", "QUAD", "OUT")
        plug.location = (PLUG_POS[0] + 0.05, PLUG_POS[1], PLUG_POS[2])
        plug.keyframe_insert(data_path="location", frame=f_land + 2)
        plug.location = PLUG_POS
        plug.keyframe_insert(data_path="location", frame=f_land + 8)

        EmberBurst.build(mats, (PLUG_POS[0] + 0.8, 0, PLUG_POS[2]), f_land,
                         accent, count=45, lifetime=18, speed=1.1, spread=0.4,
                         duration=2, name="LogoAnim_SeatBurst",
                         instance=sparks[1], size=0.8)

        # -- the cord grows into a branching plant -------------------------
        plant = PlantBuilder(mats)
        vein_mat = None
        if metal:
            stem_mat = mats.principled("LogoAnim_Stem", base=accent,
                                       metallic=0.28, roughness=0.45,
                                       emission=accent, emission_strength=0.78)
            leaf_mat = mats.principled("LogoAnim_Leaf", base=accent,
                                       metallic=0.15, roughness=0.52,
                                       emission=accent, emission_strength=0.82)
            vein_mat = mats.principled(
                "LogoAnim_Vein", base=tuple(_lighten(accent, 0.35)),
                metallic=0.20, roughness=0.5,
                emission=tuple(_lighten(accent, 0.35)), emission_strength=0.85)
        else:
            stem_mat = mats.trail("LogoAnim_Stem", accent, 0.85)
            leaf_mat = mats.emission("LogoAnim_Leaf", accent, 0.85)
            vein_mat = mats.emission("LogoAnim_Vein",
                                     tuple(_lighten(accent, 0.35)), 0.85)
        plant_objs = plant.build(stem_mat, leaf_mat, CORD_ROOT,
                                 STEM_CONTROL, STEM_PROFILE, BRANCHES,
                                 f_grow0, int(f_grow1 * 0.94), vein_mat,
                                 tip_leaf=TIP_LEAF)
        stem = plant_objs["stem"]
        mats.flash(leaf_mat, f_burst, peak=2.0, base=0.82, width=6)

        # -- particle life around the plant --------------------------------
        centre = (-3.35, 0.0, 2.10)
        for i, colour in enumerate(_palette(accent, tuple(cfg.secondary_color))[:4]):
            EmberBurst.build(mats, centre, f_grow0 + i * 3, colour,
                             count=26, lifetime=34, speed=0.32,
                             duration=max(1, f_grow1 - f_grow0),
                             spread=1.5, name="LogoAnim_Grow%d" % i,
                             instance=sparks[i], size=_var(i, 9, 0.55, 1.05))
        EmberBurst.build(mats, centre, f_burst, accent, count=70,
                         lifetime=26, speed=1.5, duration=2, spread=0.6,
                         name="LogoAnim_CurlBurst", instance=sparks[2],
                         size=1.0)

        # -- the name grows out --------------------------------------------
        words, letters, total = _build_text(ctx, f_let0, f_let1,
                                            f_sweep0, f_sweep1, metal)
        for i, colour in enumerate(_palette(accent, tuple(cfg.secondary_color))[:4]):
            EmberBurst.build(mats, (words.location.x, 0, TEXT_BASELINE),
                             f_let0 + i * 2, colour, count=22, lifetime=26,
                             speed=0.40, duration=max(1, f_let1 - f_let0),
                             spread=max(1.0, total),
                             name="LogoAnim_Name%d" % i,
                             instance=sparks[i],
                             size=_var(i, 8, 0.5, 0.95))

        # -- a light passes by, lighting the metal as it goes --------------
        # nothing visible renders: the logo simply brightens as it sweeps
        if getattr(cfg, "with_light_sweep", True):
            sweep_light = SweepingLight.build(front_y=-4.0, z=1.4)
            SweepingLight.animate(sweep_light, f_sweep0, f_sweep1,
                                  x_from=-6.0, x_to=6.5)

        # -- studio lights so the metal reads as metal ---------------------
        if metal:
            MetalLightRig.build(aim=(0.2, 0.0, 1.4))

        fade_prototypes(sparks, f_fade0, f_fade1)

        if cfg.with_glow:
            compositing.setup_glow(
                intensity=0.9 * max(0.0, float(getattr(cfg, "glow", 1.0))))
        bpy.context.scene.frame_set(1)
        return {"icon": stem.name, "plug": plug.name,
                "letters": [o.name for o in letters]}
