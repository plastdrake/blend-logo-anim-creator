"""Headless smoke test for BlendLogoAnimCreator.

Run by tools/deploy.py (or manually)::

    blender --background --python tools/smoke_test.py -- --source-dir D:\\BlendLogoAnimCreator --style COMET

Builds the logo for the given style, renders stills at key beats and asserts
the expected objects, operators and output files exist. Exits 0 on success.
"""
import argparse
import math
import os
import re
import sys
import traceback


def load_addon(source_dir):
    """Import the repo as package 'blend_logo_anim_creator' (relative imports)."""
    import importlib.util
    init = os.path.join(source_dir, "__init__.py")
    if not os.path.isfile(init):
        raise AssertionError("addon __init__.py not found at " + init)
    spec = importlib.util.spec_from_file_location(
        "blend_logo_anim_creator", init, submodule_search_locations=[source_dir])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["blend_logo_anim_creator"] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser(description="BlendLogoAnimCreator smoke test")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--style", default="STUDIO")
    p.add_argument("--company", default="ACME GAMES")
    p.add_argument("--frames", type=int, default=0,
                   help="0 = style default (studio 60, comet 200)")
    p.add_argument("--res-x", type=int, default=960)
    p.add_argument("--res-y", type=int, default=540)
    return p.parse_args(argv)


def check(cond, label):
    print(("PASS" if cond else "FAIL") + ": " + label)
    if not cond:
        raise AssertionError(label)


def main():
    args = parse_args()
    out_dir = args.out_dir or os.path.join(args.source_dir, "dist",
                                           "smoke_" + args.style.lower())
    os.makedirs(out_dir, exist_ok=True)

    mod = load_addon(args.source_dir)
    mod.register()
    print("PASS: addon registered (%s)" % args.style)

    import bpy
    from blend_logo_anim_creator.config import LogoAnimConfig
    from blend_logo_anim_creator.director import LogoDirector
    from blend_logo_anim_creator import output as output_mod

    check(hasattr(bpy.ops, "logoanim"), "ops.logoanim category registered")
    for op in ("create", "render_video", "render_draft", "render_still"):
        check(op in dir(bpy.ops.logoanim), "operator logoanim." + op)
    check(hasattr(bpy.context.scene, "logoanim"), "Scene.logoanim properties")
    check(bpy.context.scene.logoanim.style in ("STUDIO", "COMET"),
          "style property present")

    frames = args.frames or (220 if args.style == "PLUG" else 60)
    cfg = LogoAnimConfig(
        company_name=args.company, style=args.style, icon="GEM_RINGS",
        engine="EEVEE", output=os.path.join(out_dir, "logo_anim.mp4"),
        res_x=args.res_x, res_y=args.res_y, fps=30, frame_end=frames)
    res = LogoDirector().build(cfg)
    print("BUILT: style=%s camera=%s" % (res.style, res.camera))

    check(bpy.data.objects.get("LogoAnim_Cam") is not None, "camera exists")
    check(bpy.context.scene.camera is not None, "scene camera assigned")
    if args.style == "STUDIO":
        for name in ("LogoAnim_Text", "LogoAnim_IconRoot", "LogoAnim_KeySpot",
                     "LogoAnim_Ground"):
            check(bpy.data.objects.get(name) is not None, "object: " + name)
        beats = (32, 70)
    else:
        for name in ("LogoAnim_Plug", "LogoAnim_Plug_Tip",
                     "LogoAnim_Stem", "LogoAnim_Words",
                     "LogoAnim_Branch0", "LogoAnim_Branch1",
                     "LogoAnim_Leaf0", "LogoAnim_Leaf1", "LogoAnim_Leaf2",
                     "LogoAnim_SweepLight"):
            check(bpy.data.objects.get(name) is not None, "object: " + name)
        check(bpy.data.objects["LogoAnim_Stem"].data.taper_object
              is not None, "stem taper object assigned")
        # the cord root must sit on the jack's cable end (no visible step)
        stem_pt = bpy.data.objects["LogoAnim_Stem"].data.splines[0].points[0].co
        root = (-3.09, 0.0, 1.15)
        check(abs(stem_pt[0] - root[0]) < 0.02 and abs(stem_pt[2] - root[2]) < 0.02,
              "cord root aligned to the cable end")
        # the cord must leave along the jack's axis (no elbow at the joint)
        pts = bpy.data.objects["LogoAnim_Stem"].data.splines[0].points
        dz = abs(pts[3].co[2] - pts[0].co[2])
        dx = abs(pts[3].co[0] - pts[0].co[0])
        check(dz < dx * 0.35, "cord leaves along the plug axis (dz=%.3f dx=%.3f)"
              % (dz, dx))
        # cord root radius must match the boot's tip radius (flush junction)
        relief = bpy.data.objects["LogoAnim_Plug_Relief"].data
        tip_r = max(math.hypot(v.co.x, v.co.y) for v in relief.vertices
                    if v.co.z > 0.05)
        check(abs(0.152 - tip_r) < 0.02,
              "cord radius matches boot tip (cord 0.152 vs boot %.3f)" % tip_r)
        # the light sweep must be a light, not a visible object
        sweep = bpy.data.objects.get("LogoAnim_SweepLight")
        check(sweep is not None and sweep.type == "LIGHT",
              "sweep is an invisible light source")
        check(bpy.data.objects.get("LogoAnim_LightSweep") is None,
              "no visible sweep band object")
        # glare must actually be configured (5.x uses input sockets)
        tree = bpy.context.scene.compositing_node_group
        glares = [n for n in tree.nodes if n.bl_idname == "CompositorNodeGlare"]
        check(len(glares) >= 2, "glow glare nodes present (%d)" % len(glares))
        check(all(str(n.inputs["Type"].default_value) for n in glares),
              "glare type configured")
        # three leaves: two on branches and one continuing the stem tip
        leaves = [o for o in bpy.data.objects
                  if re.match(r"^LogoAnim_Leaf\d+$", o.name)]
        check(len(leaves) == 3, "three leaves (%d)" % len(leaves))
        check(bpy.data.objects.get("LogoAnim_Branch2") is None,
              "no third branch (top leaf grows off the stem)")
        # each branch tip must be covered by its leaf, not left poking out
        for i in range(2):
            branch = bpy.data.objects["LogoAnim_Branch%d" % i]
            leaf = bpy.data.objects["LogoAnim_Leaf%d" % i]
            tip = branch.data.splines[0].points[-1].co
            gap = math.hypot(tip[0] - leaf.location.x, tip[2] - leaf.location.z)
            check(gap < 0.16,
                  "leaf %d covers its branch tip (gap %.3f)" % (i, gap))
        check(len(res.letters) > 5, "letters built (%d)" % len(res.letters))
        # leaves must render in front of the vine, and carry the unroll key
        for leaf in leaves:
            check(leaf.location.y < -0.15,
                  "%s sits in front of the vines (y=%.2f)"
                  % (leaf.name, leaf.location.y))
            keys = leaf.data.shape_keys
            check(keys is not None and keys.key_blocks.get("Furled") is not None,
                  "%s has an unroll shape key" % leaf.name)
            check(len(leaf.data.materials) == 2,
                  "%s has blade + vein materials" % leaf.name)
        # particle systems must be object-instanced or Eevee draws nothing
        instanced = 0
        for obj in bpy.data.objects:
            for psys in obj.particle_systems:
                if psys.settings.render_type == "OBJECT" \
                        and psys.settings.instance_object is not None:
                    instanced += 1
        check(instanced >= 3, "ember emitters object-instanced (%d)" % instanced)
        beats = (int(.14 * frames), int(.36 * frames), int(.50 * frames),
                 int(.80 * frames), int(.98 * frames))

    sc = bpy.context.scene
    for i, f in enumerate(beats):
        sc.frame_set(f)
        still = os.path.join(out_dir, "still_%02d.png" % f)
        output_mod.configure_image_output(sc, still, "PNG")
        bpy.ops.render.render(write_still=True)
        check(os.path.isfile(still) and os.path.getsize(still) > 0,
              "still rendered f=%d" % f)

    print("SMOKE TEST PASSED (%s)" % args.style)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("SMOKE TEST FAILED")
        raise SystemExit(1)
