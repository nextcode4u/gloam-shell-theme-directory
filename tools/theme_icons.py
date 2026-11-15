# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare independent illustrated icon sets at Gloam's native 32px size."""

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CELLS = {
    "file": 6,
    "folder": 0,
    "game": 1,
    "application": 2,
    "audio": 3,
    "video": 4,
    "book": 5,
    "text": 6,
    "image": 7,
    "save": 8,
    "config": 9,
    "archive": 10,
    "shortcut": 11,
    "system": 12,
    "missing": 6,
    "settings": 12,
    "camera": 13,
    "sound": 3,
    "pictochat": 14,
    "download-play": 4,
    "system-menu": 15,
    "slot1": 1,
    "tab-home": 15,
    "tab-games": 1,
    "tab-apps": 2,
    "tab-media": 3,
    "tab-system": 12,
    "tab-files": 0,
    "tab-folder": 0,
}


def native_icon(image):
    image = image.convert("RGBA")
    bounds = image.getchannel("A").point(lambda a: 255 if a >= 16 else 0).getbbox()
    if bounds is None:
        raise ValueError("Icon artwork is empty")
    image = image.crop(bounds)
    image.thumbnail((28, 28), Image.Resampling.LANCZOS)
    image.putalpha(
        image.getchannel("A").point(lambda a: 0 if a < 16 else 255 if a > 239 else a)
    )
    result = Image.new("RGBA", (32, 32))
    result.paste(image, ((32 - image.width) // 2, (32 - image.height) // 2))
    return result


def prepare_icons(theme, folder):
    with Image.open(ROOT / "source/art" / (theme + "-icons.png")) as atlas:
        if atlas.size != (512, 512):
            raise ValueError("Icon atlases use a 4x4 grid of 128px cells")
        for kind, cell in CELLS.items():
            x, y = (cell % 4) * 128, (cell // 4) * 128
            icon = native_icon(atlas.crop((x, y, x + 128, y + 128)))
            if kind == "missing":
                draw = ImageDraw.Draw(icon)
                draw.ellipse((20, 20, 30, 30), fill="#a23b41", outline="#fff2dc")
                draw.line((23, 23, 27, 27), fill="#fff2dc", width=2)
                draw.line((27, 23, 23, 27), fill="#fff2dc", width=2)
            icon.save(folder / "icons" / (kind + ".png"), optimize=True)
