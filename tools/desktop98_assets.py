#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Original 32px Windows-98-era shell glyphs, drawn on an exact pixel grid."""

import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BLACK, WHITE = "#000000", "#ffffff"
GRAY, SILVER, NAVY, TEAL = "#808080", "#c0c0c0", "#000080", "#008080"
YELLOW, PALE, OLIVE = "#ffff00", "#ffffc0", "#808000"


def sheet(draw):
    draw.polygon(
        [(7, 2), (22, 2), (28, 8), (28, 29), (7, 29)], fill=WHITE, outline=BLACK
    )
    draw.line((22, 2, 22, 8, 28, 8), fill=GRAY)
    draw.line((8, 28, 27, 28, 27, 9), fill=SILVER)


def monitor(draw):
    draw.rectangle((3, 3, 27, 22), fill=SILVER, outline=BLACK)
    draw.line((4, 21, 4, 4, 26, 4), fill=WHITE)
    draw.rectangle((6, 6, 24, 18), fill=NAVY, outline=GRAY)
    draw.rectangle((8, 8, 22, 16), fill=TEAL)
    draw.line((9, 9, 20, 9), fill="#00ffff")
    draw.rectangle((12, 23, 19, 26), fill=GRAY, outline=BLACK)
    draw.polygon([(8, 26), (24, 26), (27, 29), (5, 29)], fill=SILVER, outline=BLACK)
    draw.line((8, 27, 23, 27), fill=WHITE)


def icon(cell):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if cell == 0:
        draw.polygon(
            [(3, 9), (3, 6), (13, 6), (16, 9), (28, 9), (28, 26), (3, 26)],
            fill=YELLOW,
            outline=BLACK,
        )
        draw.line((4, 8, 12, 8, 15, 11, 27, 11), fill=PALE)
        draw.polygon([(6, 14), (30, 14), (25, 27), (2, 27)], fill=YELLOW, outline=BLACK)
        draw.line((6, 15, 28, 15), fill=PALE)
        draw.line((3, 26, 24, 26, 28, 16), fill=OLIVE)
        for y in (22, 24):
            for x in range(5, 25, 4):
                draw.point((x + y % 4, y), fill=OLIVE)
    elif cell == 1:
        draw.polygon(
            [(3, 23), (13, 18), (27, 21), (29, 26), (17, 30), (3, 27)],
            fill=SILVER,
            outline=BLACK,
        )
        draw.line((5, 23, 14, 20, 25, 22), fill=WHITE)
        draw.ellipse((11, 15, 21, 22), fill=GRAY, outline=BLACK)
        draw.rectangle((15, 8, 18, 18), fill=GRAY, outline=BLACK)
        draw.ellipse((11, 2, 23, 12), fill="#ff0000", outline=BLACK)
        draw.line((14, 4, 18, 4), fill=WHITE)
        draw.rectangle((5, 24, 8, 26), fill="#ff0000", outline=BLACK)
    elif cell == 2:
        monitor(draw)
    elif cell == 3:
        draw.ellipse((2, 5, 25, 28), fill=SILVER, outline=BLACK)
        draw.arc((3, 6, 24, 27), 140, 300, fill=WHITE)
        draw.polygon([(13, 16), (4, 10), (5, 8)], fill="#00ffff")
        draw.polygon([(13, 16), (21, 24), (23, 21)], fill="#ff00ff")
        draw.ellipse((10, 13, 16, 19), fill=GRAY, outline=WHITE)
        draw.line((23, 7, 28, 5, 28, 21), fill=BLACK, width=2)
        draw.ellipse((22, 20, 28, 24), fill=NAVY, outline=BLACK)
    elif cell == 4:
        sheet(draw)
        draw.rectangle((9, 8, 24, 25), fill=BLACK)
        for y in range(10, 25, 5):
            draw.rectangle((10, y, 11, y + 2), fill=WHITE)
            draw.rectangle((22, y, 23, y + 2), fill=WHITE)
        draw.polygon([(14, 12), (20, 16), (14, 20)], fill="#00ffff")
    elif cell == 5:
        draw.polygon(
            [(5, 6), (23, 2), (28, 6), (28, 27), (10, 30), (5, 26)],
            fill="#800080",
            outline=BLACK,
        )
        draw.polygon([(7, 6), (23, 3), (25, 5), (9, 9)], fill=WHITE, outline=BLACK)
        draw.line((10, 10, 10, 28), fill="#ff00ff")
        draw.line((13, 12, 23, 10), fill=PALE, width=2)
        draw.line((13, 17, 23, 15), fill=SILVER)
    elif cell == 6:
        sheet(draw)
        for y in (12, 16, 20, 24):
            draw.line((11, y, 23, y), fill=NAVY)
    elif cell == 7:
        draw.rectangle((3, 5, 29, 27), fill=SILVER, outline=BLACK)
        draw.line((4, 26, 4, 6, 28, 6), fill=WHITE)
        draw.rectangle((6, 8, 26, 23), fill="#00ffff", outline=GRAY)
        draw.ellipse((20, 10, 23, 13), fill=YELLOW)
        draw.polygon([(7, 22), (14, 13), (22, 22)], fill=GRAY)
        draw.line((11, 17, 14, 13, 17, 17), fill=WHITE)
        draw.polygon([(7, 23), (11, 19), (18, 23), (24, 19), (26, 23)], fill="#008000")
    elif cell == 8:
        draw.polygon(
            [(4, 3), (25, 3), (28, 6), (28, 29), (4, 29)], fill=NAVY, outline=BLACK
        )
        draw.line((5, 28, 5, 4, 24, 4), fill="#0000ff")
        draw.rectangle((9, 4, 23, 13), fill=SILVER, outline=BLACK)
        draw.rectangle((18, 5, 21, 11), fill=GRAY)
        draw.rectangle((8, 18, 24, 28), fill=WHITE, outline=BLACK)
        draw.line((11, 21, 21, 21), fill=NAVY)
        draw.line((11, 24, 21, 24), fill=SILVER)
    elif cell == 9:
        draw.polygon(
            [
                (4, 27),
                (17, 14),
                (16, 8),
                (21, 3),
                (27, 2),
                (23, 8),
                (25, 12),
                (30, 8),
                (29, 15),
                (23, 19),
                (19, 18),
                (8, 30),
            ],
            fill=SILVER,
            outline=BLACK,
        )
        draw.line((6, 26, 18, 14, 18, 8, 23, 4), fill=WHITE)
        draw.ellipse((5, 26, 7, 28), fill=GRAY)
    elif cell == 10:
        draw.polygon(
            [(3, 10), (15, 5), (29, 10), (29, 25), (16, 30), (3, 25)],
            fill="#c08040",
            outline=BLACK,
        )
        draw.polygon([(3, 10), (15, 5), (29, 10), (16, 15)], fill=PALE, outline=BLACK)
        draw.line((16, 15, 16, 29), fill="#804000")
        draw.line((10, 8, 22, 12, 22, 24), fill=NAVY, width=2)
        for y in range(15, 24, 3):
            draw.point((22, y), fill=WHITE)
    elif cell == 11:
        draw.polygon(
            [
                (2, 25),
                (7, 14),
                (16, 10),
                (16, 5),
                (29, 15),
                (16, 25),
                (16, 19),
                (9, 20),
            ],
            fill=NAVY,
            outline=BLACK,
        )
        draw.line((4, 22, 8, 15, 18, 12, 18, 9, 25, 15), fill=WHITE)
    elif cell == 12:
        draw.rectangle((3, 4, 29, 28), fill=SILVER, outline=BLACK)
        draw.line((4, 27, 4, 5, 28, 5), fill=WHITE)
        draw.rectangle((6, 7, 26, 11), fill=NAVY)
        for y, x, color in (
            (16, 12, "#ff0000"),
            (21, 20, "#008000"),
            (25, 15, "#0000ff"),
        ):
            draw.line((7, y, 25, y), fill=GRAY)
            draw.rectangle((x - 2, y - 2, x + 2, y + 1), fill=color, outline=BLACK)
    elif cell == 13:
        draw.polygon(
            [
                (3, 10),
                (10, 10),
                (12, 6),
                (22, 6),
                (24, 10),
                (29, 10),
                (29, 27),
                (3, 27),
            ],
            fill=SILVER,
            outline=BLACK,
        )
        draw.line((4, 26, 4, 11, 27, 11), fill=WHITE)
        draw.rectangle((5, 8, 10, 10), fill="#ff0000", outline=BLACK)
        draw.rectangle((23, 12, 27, 15), fill=TEAL, outline=BLACK)
        draw.ellipse((10, 12, 24, 26), fill=GRAY, outline=BLACK)
        draw.ellipse((13, 15, 21, 23), fill=NAVY, outline=WHITE)
        draw.rectangle((15, 17, 17, 18), fill="#00ffff")
    elif cell == 14:
        draw.polygon(
            [(11, 11), (29, 11), (29, 24), (25, 24), (25, 29), (20, 24), (11, 24)],
            fill=YELLOW,
            outline=BLACK,
        )
        draw.polygon(
            [(2, 3), (23, 3), (23, 18), (11, 18), (6, 23), (6, 18), (2, 18)],
            fill=WHITE,
            outline=BLACK,
        )
        for x in (6, 12, 18):
            draw.rectangle((x, 9, x + 2, 11), fill=TEAL)
    elif cell == 15:
        draw.polygon(
            [(5, 14), (16, 5), (28, 14), (27, 28), (6, 28)], fill=SILVER, outline=BLACK
        )
        draw.polygon(
            [(2, 14), (16, 2), (30, 14), (27, 16), (16, 6), (5, 16)],
            fill="#800000",
            outline=BLACK,
        )
        draw.line((5, 13, 16, 4, 27, 13), fill="#ff0000")
        draw.rectangle((10, 17, 15, 23), fill="#00ffff", outline=BLACK)
        draw.rectangle((19, 18, 24, 28), fill=OLIVE, outline=BLACK)
    return image


def main():
    atlas = Image.new("RGBA", (128, 128))
    for cell in range(16):
        atlas.paste(icon(cell), ((cell % 4) * 32, (cell // 4) * 32))
    path = ROOT / "source/art/desktop-98-icons.png"
    atlas.resize((512, 512), Image.Resampling.NEAREST).save(path, optimize=True)
    manifest_path = ROOT / "config/inspired-art.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"]["source/art/desktop-98-icons.png"]["sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    manifest["sources"].pop("source/art/desktop-98.png", None)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
