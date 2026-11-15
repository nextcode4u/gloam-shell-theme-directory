#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate packs with an existing Gloam host build and capture real UI previews."""

import argparse
from pathlib import Path
import shutil
import subprocess
import os
from PIL import Image, ImageDraw, ImageFont
from build_collection import ROOT, SPECS, PROFILES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gloam", type=Path, required=True)
    args = parser.parse_args()
    build = ROOT / "build"
    sd = build / "preview-sd"
    renders = build / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    objects = list((args.gloam / "build/host/check-objects").glob("*.o"))
    if not objects:
        raise SystemExit("Run tools/host-check.sh in Gloam first.")
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-D_DEFAULT_SOURCE",
            "-DHOST_PREVIEW",
            "-DFRONTEND_DECODE_PROGRESS",
            "-g",
            "-fsanitize=address,undefined",
            "-I" + str(args.gloam / "arm9/include"),
            str(ROOT / "tools/check_gloam.c"),
            *map(str, objects),
            "-o",
            str(build / "check-gloam"),
        ],
        check=True,
    )
    shutil.copytree(
        ROOT / "themes", sd / "_nds/dsi-frontend/themes", dirs_exist_ok=True
    )
    roms = sd / "roms"
    roms.mkdir(exist_ok=True)
    media = sd / "media"
    media.mkdir(exist_ok=True)
    # A valid picker fixture exercises selection skins and image previews.
    shutil.copyfile(ROOT / "themes/morrow/backgrounds/top.png", media / "Morning.png")
    for name in ["Adventure", "Homebrew", "Nintendo DS", "Puzzle"]:
        (roms / name).mkdir(exist_ok=True)
    for name in [
        "A book for a quiet afternoon.epub",
        "Coastal photographs.png",
        "Evening playlist.mp3",
        "Field notes.txt",
        "The longest title in this sample collection.nds",
    ]:
        (roms / name).touch()
    gallery = Image.new("RGB", (256 * 5, 428), "#12171d")
    draw = ImageDraw.Draw(gallery)
    starters = Image.new("RGB", (256 * 3, 428), "#12171d")
    starter_draw = ImageDraw.Draw(starters)
    for i, id in enumerate(PROFILES):
        # Each process starts clean: no preference state leaks between themes.
        for state in (sd / "_nds/dsi-frontend").glob("state.*"):
            state.unlink()
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
        subprocess.run(
            [str(build / "check-gloam"), str(sd), id, str(renders)], env=env, check=True
        )
        combined = Image.new("RGB", (256, 396), "#12171d")
        for screen, y in [("top", 0), ("bottom", 204)]:
            combined.paste(Image.open(renders / f"{id}-{screen}.ppm"), (0, y))
        combined.save(ROOT / "themes" / id / "preview.png", optimize=True)
        Image.open(renders / f"{id}-settings.ppm").save(
            ROOT / "themes" / id / "settings-preview.png", optimize=True
        )
        if id in SPECS:
            draw.text((i * 256 + 10, 8), SPECS[id]["name"], fill="white")
            gallery.paste(combined, (i * 256, 32))
        elif id in ("slate", "folio", "phosphor"):
            column = ("slate", "folio", "phosphor").index(id)
            starter_draw.text((column * 256 + 10, 8), id.title(), fill="white")
            starters.paste(combined, (column * 256, 32))
    gallery.save(ROOT / "docs/collection-preview.png", optimize=True)
    starters.save(ROOT / "docs/starter-preview.png", optimize=True)


if __name__ == "__main__":
    main()
