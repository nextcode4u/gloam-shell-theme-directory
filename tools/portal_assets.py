# SPDX-License-Identifier: GPL-3.0-or-later
"""Flat inked cartoon props and quiet label surfaces for Portal Terminal."""

from PIL import Image, ImageDraw

INK = "#252838"
PAPER = "#fff4d6"
LIME = "#c8ef65"


def skin(name):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name == "icon-frame":
        return image
    fill = PAPER
    if name == "header":
        fill = "#d1c4ed"
    elif name == "footer":
        fill = "#f6ce9b"
    elif name in ("row-selected", "card-selected", "tab-selected"):
        fill = LIME
    elif name == "card":
        fill = (255, 244, 214, 190)
    # Broad flat surfaces and an uneven silhouette, without grime, bevels or
    # fine instrument lines. Prepared once; no extra work in the frame loop.
    outline = [(2, 1), (28, 0), (31, 3), (30, 29), (27, 31), (1, 30), (0, 27), (1, 4)]
    draw.polygon(outline, fill=fill, outline=INK, width=2)
    if name in ("row-selected", "card-selected", "tab-selected"):
        draw.line([(5, 4), (26, 3)], fill="#f1ffb9", width=2)
        draw.line([(5, 27), (26, 28)], fill="#95b843", width=2)
    elif name == "header":
        draw.line((5, 28, 27, 28), fill="#b497d4", width=2)
    elif name == "footer":
        draw.line((4, 3, 27, 3), fill="#ffe8bc", width=2)
    if name == "artwork-frame":
        draw.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
    return image
