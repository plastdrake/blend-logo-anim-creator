#!/usr/bin/env python3
"""Deploy BlendLogoAnimCreator: clean, test, package, install.

Just run it and open Blender afterwards::

    python tools/deploy.py

With no arguments it does everything: clean + headless smoke test + package +
install into every detected Blender version. Once the extension has been
enabled once in Blender, redeploys stay enabled automatically.

Individual steps:
    python tools/deploy.py --package
    python tools/deploy.py --install
    python tools/deploy.py --test --blender-exe "D:\\path\\to\\blender.exe"
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_ID = "blend_logo_anim_creator"
EXTRA_FILES = ("blender_manifest.toml", "README.md", "LICENSE")


def package_files():
    """Every top-level .py module plus the manifest/README.

    The add-on is multi-module, so shipping only __init__.py would install a
    broken extension - this derives the file list from the repo instead.
    """
    files = [f for f in EXTRA_FILES
             if os.path.isfile(os.path.join(REPO_ROOT, f))]
    files += sorted(
        name for name in os.listdir(REPO_ROOT)
        if name.endswith(".py") and os.path.isfile(os.path.join(REPO_ROOT, name))
        and name != "setup.py")
    return tuple(files)
FOUNDATION_DIR = r"C:\Program Files\Blender Foundation"


def get_version():
    with open(os.path.join(REPO_ROOT, "blender_manifest.toml"), encoding="utf-8") as f:
        manifest = f.read()
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', manifest)
    if not m:
        raise SystemExit("version not found in blender_manifest.toml")
    manifest_ver = m.group(1)
    with open(os.path.join(REPO_ROOT, "__init__.py"), encoding="utf-8") as f:
        init = f.read()
    m = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', init)
    if m:
        bl_ver = "%s.%s.%s" % (m.group(1), m.group(2), m.group(3))
        if bl_ver != manifest_ver:
            print("WARNING: bl_info %s != manifest %s (using manifest)" % (bl_ver, manifest_ver))
    return manifest_ver


def blender_user_root():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise SystemExit("APPDATA not set; cannot locate Blender user folders")
    return os.path.join(appdata, "Blender Foundation", "Blender")


def detect_versions():
    """Blender versions with an existing user extensions folder, newest first."""
    root = blender_user_root()
    found = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            if re.fullmatch(r"\d+\.\d+", name) and os.path.isdir(
                    os.path.join(root, name, "extensions", "user_default")):
                found.append(name)
    found.sort(key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True)
    return found


def find_blender_exe(preferred=None):
    """Auto-detect blender.exe; optional version pins e.g. '5.2'."""
    candidates = []
    if os.path.isdir(FOUNDATION_DIR):
        for name in os.listdir(FOUNDATION_DIR):
            if not name.startswith("Blender"):
                continue
            exe = os.path.join(FOUNDATION_DIR, name, "blender.exe")
            if os.path.isfile(exe):
                m = re.search(r"(\d+)\.(\d+)", name)
                key = tuple(int(x) for x in m.groups()) if m else (0, 0)
                candidates.append((key, exe))
    if preferred:
        for key, exe in candidates:
            if "%d.%d" % key == preferred:
                return exe
        raise SystemExit("Blender %s not found under %s" % (preferred, FOUNDATION_DIR))
    if not candidates:
        raise SystemExit("No Blender found under %s (use --blender-exe)" % FOUNDATION_DIR)
    candidates.sort(reverse=True)
    return candidates[0][1]


def do_clean():
    print("==> Clean")
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        if "__pycache__" in dirnames:
            shutil.rmtree(os.path.join(dirpath, "__pycache__"), ignore_errors=True)
            dirnames.remove("__pycache__")
        for fn in filenames:
            if fn.endswith(".pyc"):
                os.remove(os.path.join(dirpath, fn))


def do_test(exe):
    print("==> Smoke test (headless Blender: %s)" % exe)
    smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_test.py")
    for style in ("STUDIO", "PLUG"):
        cmd = [exe, "--background", "--python", smoke, "--",
               "--source-dir", REPO_ROOT, "--style", style]
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            raise SystemExit("smoke test %s failed (exit %d)" % (style, rc))
    print("Smoke test OK (STUDIO + PLUG)")


def do_validate(exe):
    """Blender's own extension validator (manifest schema, ids, licences)."""
    print("==> Validate extension manifest")
    rc = subprocess.run([exe, "--command", "extension", "validate",
                         REPO_ROOT]).returncode
    if rc != 0:
        raise SystemExit("extension validation failed (exit %d)" % rc)
    print("Manifest OK")


def do_package(version):
    print("==> Package v%s" % version)
    files = package_files()
    for fn in files:
        if not os.path.isfile(os.path.join(REPO_ROOT, fn)):
            raise SystemExit("missing required file: %s" % fn)
    dist = os.path.join(REPO_ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    stage = tempfile.mkdtemp(prefix="bldeploy_")
    try:
        mod_dir = os.path.join(stage, MODULE_ID)
        os.makedirs(mod_dir)
        for fn in files:
            shutil.copy2(os.path.join(REPO_ROOT, fn), mod_dir)
        zip_path = os.path.join(dist, "%s-v%s.zip" % (MODULE_ID, version))
        if os.path.exists(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in files:
                z.write(os.path.join(mod_dir, fn), os.path.join(MODULE_ID, fn))
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    print("Wrote %s (%d files)" % (zip_path, len(files)))
    return zip_path


def do_install(versions):
    root = blender_user_root()
    files = package_files()
    installed = []
    for ver in versions:
        dest = os.path.join(root, ver, "extensions", "user_default", MODULE_ID)
        # A legacy add-on copy under the same module name conflicts with the
        # extension; remove it so a single copy is loaded.
        legacy = os.path.join(root, ver, "scripts", "addons", MODULE_ID)
        if os.path.isdir(legacy):
            shutil.rmtree(legacy)
            print("Removed duplicate legacy add-on: %s" % legacy)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        for fn in files:
            shutil.copy2(os.path.join(REPO_ROOT, fn), dest)
        installed.append((ver, dest))
        print("Installed: %s (%d files)" % (dest, len(files)))
    return installed


def verify_install(exe, version):
    """Enable the INSTALLED extension in Blender and build a logo.

    Catches the class of bug where the installed copy is missing modules even
    though the source-directory smoke test passes.
    """
    print("==> Verify installed extension (Blender %s)" % version)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "verify_install.py")
    cmd = [exe, "--background", "--python", script, "--",
           "--module", "bl_ext.user_default." + MODULE_ID,
           "--out-dir", os.path.join(REPO_ROOT, "dist", "verify")]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        raise SystemExit("installed-extension verification failed (exit %d)" % rc)


def main(argv=None):
    p = argparse.ArgumentParser(description="Deploy BlendLogoAnimCreator")
    p.add_argument("--blender-version", default=None,
                   help="pin a version, e.g. 5.2 (default: newest found)")
    p.add_argument("--blender-exe", default=None)
    p.add_argument("--clean", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--package", action="store_true")
    p.add_argument("--install", action="store_true")
    p.add_argument("--all", action="store_true")
    args = p.parse_args(argv)

    if not (args.clean or args.test or args.validate or args.package
            or args.install or args.all):
        args.all = True  # just run it: everything, then open Blender

    version = get_version()
    print("BlendLogoAnimCreator v%s" % version)

    if args.clean or args.all:
        do_clean()
    if args.validate or args.all:
        do_validate(args.blender_exe or find_blender_exe(args.blender_version))
    if args.test or args.all:
        exe = args.blender_exe or find_blender_exe(args.blender_version)
        do_test(exe)
    if args.package or args.all:
        do_package(version)
    if args.install or args.all:
        versions = ([args.blender_version] if args.blender_version
                    else detect_versions())
        if not versions:
            print("WARNING: no Blender user folders found; skipping install")
        else:
            do_install(versions)
            if args.test or args.all:
                # only the newest target, to keep the run quick
                verify_install(args.blender_exe or find_blender_exe(versions[0]),
                               versions[0])
    print("Done. Open Blender - the extension is ready (enable it once under "
          "Preferences > Extensions; it stays enabled on redeploy).")


if __name__ == "__main__":
    main()
