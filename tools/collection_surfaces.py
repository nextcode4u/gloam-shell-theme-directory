# SPDX-License-Identifier: GPL-3.0-or-later
"""Full-image materials and independent focus skins for the collection."""

from functools import lru_cache
from pathlib import Path
import math
from PIL import Image, ImageColor, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
CELLS = {
    "aerial": 0,
    "koi": 1,
    "vesper": 2,
    "tidal": 3,
    "slate": 4,
    "folio": 5,
    "phosphor": 6,
    "buuf": 7,
}
FOCUS = {
    "aerial": "#dcebf4",
    "koi": "#28443f",
    "vesper": "#593747",
    "tidal": "#285d6b",
    "slate": "#38515d",
    "folio": "#f6f0db",
    "phosphor": "#294b35",
    "buuf": "#b6c49d",
}


@lru_cache(maxsize=18)
def material_image(theme, selected=False):
    if theme == "morrow":
        with Image.open(ROOT / "source/materials/morrow-parchment.png") as paper:
            return paper.convert("RGB").resize((256, 192), Image.Resampling.LANCZOS)
    cell = CELLS[theme]
    with Image.open(ROOT / "source/materials/collection.png") as atlas:
        x, y = cell % 4 * 256, cell // 4 * 256 + (64 if selected else 32)
        image = atlas.crop((x, y, x + 256, y + 192)).convert("RGB")
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if selected else image


def tint(theme, color, selected=False, amplitude=6):
    source = material_image(theme, selected)
    stats = ImageStat.Stat(source)
    deviation = max(1, math.sqrt(sum(stats.var) / 3))
    base = ImageColor.getrgb(color) if isinstance(color, str) else color[:3]
    result = Image.new("RGB", source.size)
    result.putdata(
        [
            tuple(
                max(0, min(255, round(b + (c - m) / deviation * amplitude)))
                for b, c, m in zip(base, pixel, stats.mean)
            )
            for pixel in source.getdata()
        ]
    )
    return result


def prepare_materials(theme, folder, config):
    for selected, name in ((False, "material"), (True, "focus-material")):
        if theme == "morrow" and selected:
            continue
        source = tint(theme, (128, 128, 128), selected).convert("L")
        field = Image.new("P", source.size)
        field.putpalette(
            [channel for i in range(256) for channel in (min(i, 15) * 17,) * 3]
        )
        field.putdata(
            [
                max(0, min(15, round((value - 128) / 8) + 8))
                for value in source.getdata()
            ]
        )
        field.save(folder / "components" / (name + ".png"), bits=4, optimize=True)
    if theme == "morrow":
        (folder / "components/focus-material.png").unlink(missing_ok=True)
    config["components"].update(
        fill="stretch",
        material="components/material.png",
        focus_material=(
            "components/material.png"
            if theme == "morrow"
            else "components/focus-material.png"
        ),
    )


def reading_material(theme, image, colors):
    if theme == "morrow":
        return image  # Already a complete translucent aged-parchment composition.
    texture = tint(theme, colors["background"])
    base = ImageColor.getrgb(colors["background"])
    result = image.copy()
    pixels = result.load()
    sample = texture.load()
    for y in range(192):
        for x in range(256):
            r, g, b, a = pixels[x, y]
            if a and max(abs(c - ref) for c, ref in zip((r, g, b), base)) <= 3:
                pixels[x, y] = sample[x, y] + (a,)
    return result


def focus_skin(theme, colors):
    """Each pack uses a full focused surface; trim fits inside the six-pixel border."""
    if theme == "morrow":
        return None  # Keep the existing authored, worn parchment outline.
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    fill = (*ImageColor.getrgb(FOCUS[theme]), 170)
    if theme == "aerial":
        d.rounded_rectangle((0, 1, 31, 31), radius=6, fill=(91, 128, 150, 85))
        d.rounded_rectangle((0, 0, 30, 29), radius=6, fill="#fbffff")
        d.rounded_rectangle((1, 2, 29, 28), radius=5, fill=fill)
        d.arc((1, 1, 11, 11), 180, 270, fill="#ffffff", width=2)
    elif theme == "koi":
        d.rectangle((0, 0, 31, 31), fill="#a67252")
        d.rectangle((1, 2, 30, 29), fill=fill)
        for x, y in ((2, 2), (27, 27)):
            d.polygon([(x, y), (x + 3, y), (x + 3, y + 3), (x, y + 3)], fill="#c36a52")
        d.line((6, 0, 25, 0), fill="#e7c996")
    elif theme == "vesper":
        d.polygon(
            [(4, 0), (27, 0), (31, 4), (31, 27), (27, 31), (4, 31), (0, 27), (0, 4)],
            fill="#cba66e",
        )
        d.polygon(
            [(5, 2), (26, 2), (29, 5), (29, 26), (26, 29), (5, 29), (2, 26), (2, 5)],
            fill=fill,
        )
        for x, y in ((3, 3), (28, 3), (3, 28), (28, 28)):
            d.polygon([(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)], fill="#fff0ce")
    elif theme == "tidal":
        d.rounded_rectangle((0, 0, 31, 31), radius=6, fill="#b0e9dd")
        d.rounded_rectangle((1, 2, 30, 29), radius=5, fill=fill)
        d.arc((1, 1, 12, 12), 180, 270, fill="#e8fff6", width=2)
        d.ellipse((27, 25, 29, 27), fill="#b2d1ed")
    elif theme == "slate":
        d.polygon([(0, 0), (26, 0), (31, 5), (31, 31), (0, 31)], fill="#c4bca8")
        d.polygon([(1, 1), (25, 1), (30, 6), (30, 30), (1, 30)], fill=fill)
        d.polygon([(26, 0), (26, 5), (31, 5)], fill="#d58f71")
    elif theme == "folio":
        d.polygon(
            [
                (1, 1),
                (7, 0),
                (15, 1),
                (24, 0),
                (30, 2),
                (31, 10),
                (30, 21),
                (31, 29),
                (24, 31),
                (16, 30),
                (7, 31),
                (1, 29),
                (0, 20),
                (1, 12),
                (0, 5),
            ],
            fill="#ac9e7c",
        )
        d.rectangle((2, 2, 29, 28), fill=fill)
        d.polygon([(25, 0), (31, 6), (25, 6)], fill="#cbd0b2")
        for x in (2, 25):
            d.rectangle((x, 0, x + 4, 2), fill="#e4d4b3")
    elif theme == "phosphor":
        d.polygon(
            [(0, 0), (26, 0), (31, 5), (31, 31), (5, 31), (0, 26)], fill="#a9c39d"
        )
        d.polygon([(1, 1), (25, 1), (30, 6), (30, 30), (6, 30), (1, 25)], fill=fill)
        for x, y in ((1, 1), (27, 27)):
            d.rectangle((x, y, x + 3, y + 3), fill="#c99765")
    elif theme == "buuf":
        # Inked, slightly crooked paper label with moss-green cloth and worn corners.
        d.polygon(
            [(2, 0), (29, 1), (31, 4), (30, 29), (27, 31), (1, 30), (0, 26), (1, 4)],
            fill="#3b3328",
        )
        d.polygon(
            [(3, 2), (28, 3), (29, 5), (28, 28), (26, 29), (3, 28), (2, 25), (3, 5)],
            fill=fill,
        )
        for x, y in ((3, 3), (26, 26)):
            d.line((x, y, x + 2, y + 1), fill="#e6d5b3", width=1)
    else:
        raise ValueError(theme)
    return image
