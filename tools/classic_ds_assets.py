#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Original code-authored grid and flat glyphs inspired by the classic DS menu."""

import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INK = "#272d30"
PAPER = "#f3f4f1"
MID = "#9da5a8"


def wallpaper():
    image = Image.new("RGB", (256, 192), "#f6f6f3")
    draw = ImageDraw.Draw(image)
    for y in range(0, 192, 3):
        draw.line((0, y, 255, y), fill="#dddddc")
    for x in range(0, 256, 16):
        draw.line((x, 0, x, 191), fill="#d4d6d5")
        draw.line((x + 2, 0, x + 2, 191), fill="#e5e6e3")
    return image


def icon(cell):
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    if cell == 0:
        d.polygon(
            [(3, 9), (3, 6), (12, 6), (15, 9), (28, 9), (28, 26), (3, 26)],
            fill=PAPER,
            outline=INK,
        )
        d.polygon([(5, 14), (29, 14), (25, 26), (2, 26)], fill="#e5e7e4", outline=INK)
        d.line((6, 17, 25, 17), fill=MID)
    elif cell == 1:
        d.rectangle((6, 4, 25, 28), fill=PAPER, outline=INK, width=2)
        d.rectangle((9, 7, 22, 18), fill=MID, outline=INK)
        for x in range(9, 24, 4):
            d.rectangle((x, 24, x + 1, 28), fill=INK)
    elif cell == 2:
        for y in (3, 18):
            d.rectangle((3, y, 28, y + 11), fill=PAPER, outline=INK, width=2)
            d.rectangle((7, y + 3, 24, y + 8), outline=MID)
        d.line((8, 16, 23, 16), fill=INK, width=2)
    elif cell == 3:
        d.polygon(
            [(3, 12), (9, 12), (17, 6), (17, 26), (9, 20), (3, 20)],
            fill=PAPER,
            outline=INK,
        )
        for x in (21, 25):
            d.arc((x - 7, 7, x + 5, 25), 300, 60, fill=INK, width=2)
    elif cell == 4:
        d.rectangle((3, 6, 29, 26), fill=PAPER, outline=INK, width=2)
        for x in (4, 25):
            for y in (9, 15, 21):
                d.rectangle((x, y, x + 2, y + 2), fill=INK)
        d.polygon([(13, 11), (21, 16), (13, 21)], fill=INK)
    elif cell == 5:
        d.polygon(
            [
                (3, 7),
                (13, 5),
                (16, 7),
                (19, 5),
                (29, 7),
                (29, 26),
                (18, 24),
                (16, 27),
                (13, 24),
                (3, 26),
            ],
            fill=PAPER,
            outline=INK,
        )
        d.line((16, 7, 16, 25), fill=INK)
        for y in (11, 15, 19):
            d.line((6, y, 12, y - 1), fill=MID)
            d.line((20, y - 1, 26, y), fill=MID)
    elif cell == 6:
        d.polygon(
            [(6, 3), (21, 3), (27, 9), (27, 29), (6, 29)], fill=PAPER, outline=INK
        )
        d.line((21, 3, 21, 9, 27, 9), fill=INK)
        for y in (13, 17, 21, 25):
            d.line((10, y, 23, y), fill=INK)
    elif cell == 7:
        d.rectangle((3, 6, 29, 26), fill=PAPER, outline=INK, width=2)
        d.ellipse((20, 10, 24, 14), fill=MID)
        d.line([(5, 23), (12, 15), (19, 22), (24, 18), (27, 23)], fill=INK, width=2)
    elif cell == 8:
        d.rectangle((5, 4, 27, 28), fill=PAPER, outline=INK, width=2)
        d.rectangle((9, 5, 22, 13), fill=MID, outline=INK)
        d.rectangle((9, 18, 23, 28), outline=INK)
        d.rectangle((18, 6, 20, 11), fill=PAPER)
    elif cell == 9:
        for y, x in ((8, 10), (16, 22), (24, 14)):
            d.line((4, y, 29, y), fill=INK, width=2)
            d.rectangle((x - 2, y - 3, x + 2, y + 3), fill=PAPER, outline=INK)
    elif cell == 10:
        d.rectangle((4, 8, 28, 27), fill=PAPER, outline=INK, width=2)
        d.line((4, 13, 28, 13), fill=INK)
        d.rectangle((13, 8, 18, 27), fill=MID, outline=INK)
        for y in (12, 18, 24):
            d.point((15, y), fill=PAPER)
    elif cell == 11:
        d.line([(4, 26), (4, 19), (11, 12), (23, 12)], fill=INK, width=3)
        d.polygon([(18, 5), (28, 12), (18, 20)], fill=PAPER, outline=INK)
    elif cell == 12:
        for x, y in ((14, 3), (14, 25), (3, 14), (25, 14)):
            d.rectangle((x, y, x + 4, y + 4), fill=INK)
        d.ellipse((6, 6, 26, 26), fill=PAPER, outline=INK, width=2)
        d.ellipse((12, 12, 20, 20), fill=MID, outline=INK)
    elif cell == 13:
        d.rectangle((3, 10, 29, 25), fill=PAPER, outline=INK, width=2)
        d.rectangle((8, 6, 17, 10), fill=PAPER, outline=INK)
        d.ellipse((12, 12, 23, 23), fill=MID, outline=INK, width=2)
        d.point((7, 14), fill=INK)
    elif cell == 14:
        d.polygon(
            [(3, 4), (23, 4), (23, 18), (10, 18), (5, 23), (5, 18), (3, 18)],
            fill=PAPER,
            outline=INK,
        )
        d.polygon(
            [(13, 16), (29, 16), (29, 27), (27, 27), (27, 31), (22, 27), (13, 27)],
            fill="#e1e4e1",
            outline=INK,
        )
        for x in (7, 12, 17):
            d.point((x, 11), fill=INK)
    else:
        d.rectangle((4, 3, 27, 29), fill=PAPER, outline=INK, width=2)
        for y in (7, 14, 21):
            for x in (8, 16):
                d.rectangle((x, y, x + 4, y + 4), fill=MID, outline=INK)
    return im


def main():
    folder = ROOT / "source/art"
    wallpaper().save(folder / "classic-ds.png", optimize=True)
    atlas = Image.new("RGBA", (512, 512))
    for cell in range(16):
        atlas.paste(
            icon(cell).resize((128, 128), Image.Resampling.NEAREST),
            (cell % 4 * 128, cell // 4 * 128),
        )
    atlas.save(folder / "classic-ds-icons.png", optimize=True)
    path = ROOT / "config/inspired-art.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name in ("classic-ds.png", "classic-ds-icons.png"):
        relative = "source/art/" + name
        manifest["sources"][relative] = {
            "sha256": hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
            "authoring": "tools/classic_ds_assets.py",
        }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
