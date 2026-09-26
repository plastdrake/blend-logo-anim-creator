"""Publish this repository to GitHub.

Fills the real repository URL into README.md and blender_manifest.toml, commits
that, then creates the remote and pushes. Requires the GitHub CLI to be
authenticated once:

    gh auth login
    python tools/publish.py                 # public repo
    python tools/publish.py --private       # private repo
    python tools/publish.py --dry-run       # show what would change, write nothing

The owner is taken from the authenticated gh account; override with --owner.
"""
import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NAME = "blend-logo-anim-creator"
PLACEHOLDER = "<owner>"


def run(cmd, capture=True):
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=capture,
                            text=True)
    if result.returncode != 0:
        raise SystemExit("command failed: %s\n%s"
                         % (" ".join(cmd), (result.stderr or "").strip()))
    return (result.stdout or "").strip()


def gh_login():
    try:
        return run(["gh", "api", "user", "--jq", ".login"])
    except SystemExit:
        raise SystemExit(
            "GitHub CLI is not authenticated.\n"
            "Run `gh auth login` once, then re-run this script.")


def substitute(path, replacements, dry_run):
    full = os.path.join(REPO_ROOT, path)
    text = open(full, encoding="utf-8").read()
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text == original:
        print("  %-28s already up to date" % path)
        return False
    print("  %-28s %d change(s)" % (path, sum(
        1 for old, _ in replacements if old in original)))
    if dry_run:
        for old, new in replacements:
            if old in original:
                print("      - %s" % old[:90])
                print("      + %s" % new[:90])
    else:
        open(full, "w", encoding="utf-8", newline="\n").write(text)
    return True


def main(argv=None):
    p = argparse.ArgumentParser(description="Publish to GitHub")
    p.add_argument("--name", default=DEFAULT_NAME)
    p.add_argument("--owner", default=None,
                   help="GitHub user/org (default: the authenticated account)")
    p.add_argument("--private", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    owner = args.owner or gh_login()
    url = "https://github.com/%s/%s" % (owner, args.name)
    print("Repository: %s (%s)" % (url, "private" if args.private else "public"))
    if args.dry_run:
        print("DRY RUN - no files written, no repo created")

    # 1. real URLs in the docs and manifest
    print("==> Update repository URLs")
    changed = substitute("README.md", [
        ("https://github.com/%s/%s.git" % (PLACEHOLDER, DEFAULT_NAME), url + ".git"),
        ("https://github.com/%s/%s" % (PLACEHOLDER, DEFAULT_NAME), url),
    ], args.dry_run)
    manifest = os.path.join(REPO_ROOT, "blender_manifest.toml")
    text = open(manifest, encoding="utf-8").read()
    if "website" not in text:
        new = re.sub(r'(?m)^(maintainer\s*=.*)$',
                     r'\1\nwebsite = "%s"' % url, text, count=1)
        if new != text:
            changed = True
            print("  %-28s add website" % "blender_manifest.toml")
            if not args.dry_run:
                open(manifest, "w", encoding="utf-8", newline="\n").write(new)

    # 2. validate before publishing
    if not args.dry_run:
        print("==> Validate manifest")
        run([sys.executable, os.path.join(REPO_ROOT, "tools",
                                          "check_manifest.py")], capture=False)

    # 3. commit the URL updates
    if changed and not args.dry_run:
        print("==> Commit repository URLs")
        run(["git", "add", "README.md", "blender_manifest.toml"])
        run(["git", "commit", "-m",
             "Add repository URL to README and manifest"])

    # 4. create the remote and push
    visibility = "--private" if args.private else "--public"
    cmd = ["gh", "repo", "create", "%s/%s" % (owner, args.name), visibility,
           "--source", REPO_ROOT, "--remote", "origin", "--push",
           "--description",
           "Procedural animated logo intros for Blender: text, plant, light "
           "and particles, rendered to video."]
    if args.dry_run:
        print("==> Would run:\n    " + " ".join(cmd))
        print("DRY RUN COMPLETE")
        return 0

    print("==> Create repository and push")
    run(cmd)
    print("Published: %s" % url)
    print("Add topics/releases on GitHub to finish the listing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
