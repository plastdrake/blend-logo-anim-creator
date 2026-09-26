"""Validate blender_manifest.toml without needing Blender installed.

Used by CI and by humans. Checks the schema rules that are easy to break:
required keys, tagline length, id rules, version format, and that bl_info in
__init__.py agrees with the manifest version.

    python tools/check_manifest.py
"""
import os
import re
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    tomllib = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = ("schema_version", "id", "version", "name", "tagline", "maintainer",
            "type", "blender_version_min", "license")
MAX_TAGLINE = 64


def fail(msg):
    print("FAIL: " + msg)
    return 1


def main():
    errors = 0
    manifest_path = os.path.join(REPO_ROOT, "blender_manifest.toml")
    if not os.path.isfile(manifest_path):
        return fail("blender_manifest.toml not found")
    raw = open(manifest_path, encoding="utf-8").read()

    if tomllib is None:
        print("WARNING: tomllib unavailable (Python < 3.11); using a "
              "regex fallback parser")
        data = {}
        for m in re.finditer(r'(?ms)^([A-Za-z_]\w*)\s*=\s*'
                             r'("([^"]*)"|\[(.*?)\])', raw):
            key = m.group(1)
            if m.group(3) is not None:
                data[key] = m.group(3)
            else:
                data[key] = re.findall(r'"([^"]*)"', m.group(4) or "")
    else:
        try:
            data = tomllib.loads(raw)
        except Exception as exc:
            return fail("manifest is not valid TOML: %s" % exc)

    for key in REQUIRED:
        if key not in data:
            errors += fail("manifest is missing required key: %s" % key)

    tagline = data.get("tagline", "")
    if len(tagline) > MAX_TAGLINE:
        errors += fail("tagline is %d chars (max %d): %r"
                       % (len(tagline), MAX_TAGLINE, tagline))
    else:
        print("PASS: tagline length %d <= %d" % (len(tagline), MAX_TAGLINE))

    ident = data.get("id", "")
    if not re.fullmatch(r"[a-z0-9_]+", ident):
        errors += fail("id must be lowercase letters, digits and underscores: %r"
                       % ident)
    else:
        print("PASS: id %r" % ident)

    version = data.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors += fail("version must be MAJOR.MINOR.PATCH: %r" % version)
    else:
        print("PASS: version %s" % version)

    if data.get("type") not in ("add-on", "theme"):
        errors += fail("type must be 'add-on' or 'theme': %r" % data.get("type"))
    else:
        print("PASS: type %r" % data.get("type"))

    licences = data.get("license")
    if not isinstance(licences, list) or not licences:
        errors += fail("license must be a non-empty list")
    else:
        print("PASS: license %s" % licences)

    # bl_info version must agree with the manifest
    init_path = os.path.join(REPO_ROOT, "__init__.py")
    init = open(init_path, encoding="utf-8").read()
    m = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', init)
    if not m:
        errors += fail("bl_info version not found in __init__.py")
    else:
        bl = "%s.%s.%s" % m.groups()
        if bl != version:
            errors += fail("bl_info %s != manifest %s" % (bl, version))
        else:
            print("PASS: bl_info matches manifest (%s)" % bl)

    if errors:
        print("MANIFEST CHECK FAILED (%d problem(s))" % errors)
        return 1
    print("MANIFEST CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
