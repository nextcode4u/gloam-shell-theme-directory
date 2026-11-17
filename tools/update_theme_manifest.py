#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh/check the exact files fetched by theme.ps1; no collection artwork is downloaded."""

import argparse
import hashlib
import json
from pathlib import Path
from update_splash_manifest import manifest as splash_manifest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "tools/theme_builder.py",
    "tools/theme_project.py",
    "tools/theme_schema.py",
    "tools/theme_validate.py",
    "tools/theme_media.py",
    "tools/theme_preview.py",
    "tools/theme_studio/index.html",
    "tools/theme_studio/gloam-icon.png",
    "tools/theme_studio/studio.css",
    "tools/theme_studio/studio.js",
    "tools/theme_native/__init__.py",
    "tools/theme_native/UPSTREAM.json",
    "tools/theme_native/pack_theme_assets.py",
    "tools/theme_native/theme_prepared_surfaces.py",
    "tools/theme_native/pack_theme_font.py",
    "tools/pack_splash.py",
    "tools/splash_builder.py",
    "tools/splash_project.py",
    "tools/splash_motion.py",
    "docs/THEME_STUDIO.md",
    "LICENSE",
    "LICENSES.md",
)


def manifest():
    return {
        "format": 1,
        "pillow": "11.3.0",
        "files": [
            {
                "path": name,
                "size": (ROOT / name).stat().st_size,
                "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
            }
            for name in FILES
        ],
    }


def refresh(check=False):
    # The launchers share converters and license notices. Refresh them together.
    snapshots = {
        "tools/theme-downloads.json": manifest(),
        "tools/splash-downloads.json": splash_manifest(),
    }
    for name, snapshot in snapshots.items():
        path = ROOT / name
        data = (json.dumps(snapshot, indent=2) + "\n").encode()
        if check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit("Run python tools/update_theme_manifest.py")
        else:
            path.write_bytes(data)
    if check:
        print("Theme Studio and Splash Builder manifests match their authoring files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    refresh(args.check)


if __name__ == "__main__":
    main()
