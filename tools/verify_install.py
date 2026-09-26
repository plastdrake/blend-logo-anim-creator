"""Verify the INSTALLED extension loads and works (not the source folder).

Run by tools/deploy.py after --install::

    blender --background --python tools/verify_install.py -- \
        --module bl_ext.user_default.blend_logo_anim_creator --out-dir dist/verify

Fails loudly if the installed copy is missing modules, the manifest is
invalid, or the operators did not register.
"""
import argparse
import os
import sys
import traceback


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser(description="verify installed extension")
    p.add_argument("--module", required=True,
                   help="e.g. bl_ext.user_default.blend_logo_anim_creator")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--frames", type=int, default=40)
    return p.parse_args(argv)


def check(cond, label):
    print(("PASS" if cond else "FAIL") + ": " + label)
    if not cond:
        raise AssertionError(label)


def main():
    args = parse_args()
    import addon_utils
    import bpy

    ok = addon_utils.enable(args.module, default_set=True, persistent=True)
    check(bool(ok), "installed extension enabled: " + args.module)

    check(hasattr(bpy.ops, "logoanim"), "ops.logoanim registered")
    for op in ("create", "render_video", "render_draft", "render_still"):
        check(op in dir(bpy.ops.logoanim), "operator logoanim." + op)
    check(hasattr(bpy.context.scene, "logoanim"), "Scene.logoanim properties")

    # build with the installed package (import errors surface here)
    props = bpy.context.scene.logoanim
    props.style = "PLUG"
    props.company_name = "VERIFY"
    props.frame_end = args.frames
    props.with_glow = False
    result = bpy.ops.logoanim.create()
    check("FINISHED" in result, "logoanim.create via installed package")

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        from bl_ext.user_default.blend_logo_anim_creator import output as om
        om.configure_image_output(bpy.context.scene,
                                  os.path.join(args.out_dir, "verify.png"),
                                  "PNG")
        bpy.context.scene.frame_set(int(args.frames * 0.6))
        bpy.ops.render.render(write_still=True)
        check(os.path.isfile(os.path.join(args.out_dir, "verify.png")),
              "still rendered from installed package")

    print("INSTALL VERIFY PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("INSTALL VERIFY FAILED")
        raise SystemExit(1)
