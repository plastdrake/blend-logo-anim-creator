# Architecture

Blend Logo Anim Creator turns a short config object into a finished animated
logo. The code is organised so that **styles** (the creative part) are separate
from the **machinery** (materials, geometry, animation, output), and so that
Blender-version differences are confined to a few small places.

```
                    LogoAnimConfig                 (config.py, a dataclass)
                            │
                    LogoDirector.build()           (director.py - facade)
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
  SceneBuilder         MaterialFactory      Style.apply(ctx)
 (scene_setup.py)       (materials.py)     (styles.py registry)
  render/engine/         cached shader      → style_studio.py
  world/camera           builders           → style_plug.py
                                                  │
                       ┌──────────────┬───────────┼──────────────┐
                       │              │           │              │
                TextLogoBuilder  IconFactory  PlantBuilder   fx / particles
                (text_logo.py)    (icons.py)   (plant.py)     (fx.py)
                       │              │           │              │
                       └──────────────┴─────┬─────┴──────────────┘
                                            │
                             curves.py · animation.py · compositing.py
                                            │
                                      output.py (video / draft)
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | `LogoAnimConfig` parameter object. Every builder takes one config instead of loose arguments. |
| `director.py` | `LogoDirector` facade: clears the scene, builds the rig, delegates to the style, applies output settings. Also exposes `create_animated_logo()`. |
| `styles.py` | Style registry + `BuildContext` (the bundle of config, materials and camera a style receives). |
| `style_studio.py` / `style_plug.py` | The two looks. Each `apply(ctx)` builds and animates everything it needs. |
| `scene_setup.py` | Collection registry, render engine/sampling/exposure, world, camera, and content-based framing. |
| `materials.py` | `MaterialFactory`: cached builders for principled / emission / transparent / volume / smoke / trail shaders. |
| `text_logo.py` | Text logos: font loading, single extruded block, or measured per-letter row. |
| `icons.py` | `IconFactory` plus `ICON_BUILDERS`, a strategy registry of procedural icons. |
| `plug.py` | Procedural 3.5 mm TRS jack. |
| `plant.py` | `LeafBuilder` (bmesh blade + vein, with an unroll shape key) and `PlantBuilder` (cord-stem, arcing branches, leaf timing). |
| `curves.py` | Bezier sampling, profiled tubes, draw-on animation. |
| `animation.py` | `Animator`: transforms, easing, `grow_from`, `pop`, version-proof f-curve access. |
| `fx.py` | Independent effect classes: light rigs, volumes, smoke, dust, ember bursts, sweeping light. |
| `particles.py` | Shared particle fade helper (fades every colour in sync). |
| `compositing.py` | Glow: two chained glare passes, configured through the 4.x property API or the 5.x socket API. |
| `output.py` | Video/image output configuration and `draft_mode` (50%, FX hidden, settings restored). |
| `properties.py` / `operators.py` / `panels.py` | Thin UI layer. Operators only read UI properties and call the director. |

## Data flow

1. The UI (or a script) fills a `LogoAnimConfig`.
2. `LogoDirector.build()` clears the `LogoAnim` collection, builds the scene
   rig, and hands a `BuildContext` to the selected style.
3. The style creates geometry through the builders above and animates it with
   `Animator`.
4. `output.configure_video_output()` sets the FFmpeg/MP4 settings (handling the
   Blender 5 `media_type` requirement) and the renderer writes the file.

## Timing model

Styles express beats as **fractions of an action window**, not absolute frames:

```
action = frame_end - round(hold_seconds * fps)
```

so the animation keeps its pacing at any duration, and the last
`hold_seconds` are always a completely settled logo. The plug style's default
300 frames at 30 fps is ~8 s of animation plus a 2 s hold.

## Adding things

**A style.** Create `style_mine.py` with an `apply(ctx) -> dict`, add it to
`STYLES` in `styles.py`, and add an enum entry in `properties.py`. Nothing else
changes.

**An icon.** Write a builder taking `(parent, mat_icon, mat_ring)` and register
it in `ICON_BUILDERS` (`icons.py`).

**An effect.** Follow the existing pattern in `fx.py`: a small class with a
`build()` (and optionally `animate()`), using `MaterialFactory` for shaders and
`scene_setup.link()` for collections.

## Blender version compatibility

The add-on targets Blender 4.2 LTS through 5.x. Differences are isolated:

| Concern | Where | Approach |
|---|---|---|
| Video output | `output.py` | 5.x needs `image_settings.media_type = "VIDEO"` before `FFMPEG` is accepted. |
| Compositor tree | `compositing.py` | 4.x uses `scene.node_tree`; 5.x uses `scene.compositing_node_group` + a Group Output. |
| Glare settings | `compositing.py` | 4.x exposes node *properties*; 5.x exposes *input sockets*; both are set, and the working one wins. |
| F-curves | `animation.py` | 4.x has `action.fcurves`; 5.x nests them in `layers → strips → channelbags`. |
| Particles | `fx.py` | Eevee cannot draw halo particles, so every system is object-instanced. |

## Testing

| Command | What it does |
|---|---|
| `python tools/check_manifest.py` | Manifest schema + `bl_info` version check (no Blender needed). |
| `python tools/deploy.py` | Clean → manifest validate → headless smoke tests → package → install → verify the *installed* copy. |
| `python tools/deploy.py --test` | Just the smoke tests. |
| `python tools/deploy.py --package` | Just the distributable zip. |
| `python tools/publish.py [--private] [--dry-run]` | Fill the real repo URL into README/manifest, commit, create the GitHub repo and push. |

`tools/smoke_test.py` builds both styles in headless Blender and asserts the
structural invariants that have actually broken before, for example:

- the cord root radius matches the strain-relief tip (no lip at the joint)
- the cord leaves the plug along its axis (no elbow)
- leaves sit in front of the vines and carry the unroll shape key
- each branch tip is covered by its leaf
- every particle system is object-instanced (or Eevee draws nothing)
- glow glare nodes exist and are configured

`tools/verify_install.py` repeats a build using the **installed** extension, so
a package that is missing modules cannot ship silently.

Continuous integration on GitHub runs the Blender-free checks (byte-compile and
manifest validation). The full suite needs Blender and a GPU for Eevee, so it
runs locally through `tools/deploy.py`.
