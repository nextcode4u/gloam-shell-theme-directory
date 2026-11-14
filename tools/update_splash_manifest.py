#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh or check the small set of files fetched by splash.ps1."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "tools/pack_splash.py",
    "tools/splash_builder.py",
    "tools/splash_project.py",
    "tools/splash_motion.py",
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "tools/splash-downloads.json"
    data = (json.dumps(manifest(), indent=2) + "\n").encode()
    if args.check:
        if not path.is_file() or path.read_bytes() != data:
            raise SystemExit(
                "Refresh tools/splash-downloads.json with tools/update_splash_manifest.py"
            )
        print("Splash download manifest matches the authoring files.")
    else:
        path.write_bytes(data)


if __name__ == "__main__":
    main()
