# SPDX-License-Identifier: GPL-3.0-or-later
"""Celadon LCD reading surfaces inside the illustrated red device casing."""

from PIL import Image, ImageDraw

LCD = "#dcead5"
TEAL = "#185460"


def reading_surface(screen):
    if screen not in ("top", "bottom"):
        raise ValueError("Unknown screen")
    image = Image.new("RGBA", (256, 192))
    draw = ImageDraw.Draw(image)
    # Preblended once at theme load. Keep the outer casing visible, with a
    # lightly translucent LCD beneath every layout's text and navigation.
    draw.rounded_rectangle(
        (6, 26, 249, 174), radius=6,
        fill=(220, 234, 213, 190), outline=(84, 116, 96, 160)
    )
    return image


def skin(name):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name == "icon-frame":
        return image
    if name in ("header", "footer"):
        # White chrome text needs a matte red strip, not bright casing reflections.
        draw.rounded_rectangle((0, 0, 31, 31), radius=2,
                               fill="#82252d", outline="#571c25")
        return image
    selected = name in ("row-selected", "card-selected", "tab-selected")
    if selected:
        draw.rounded_rectangle((0, 0, 31, 31), radius=3,
                               fill=TEAL, outline="#123d48")
        draw.line((5, 1, 26, 1), fill="#45858e")
    else:
        # Menus and settings need a reliable surface even outside the pictured LCD.
        draw.rounded_rectangle((0, 0, 31, 31), radius=3,
                               fill=LCD, outline=(84, 116, 96, 170))
    if name == "artwork-frame":
        draw.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
    if name == "tab-selected":
        draw.ellipse((3, 12, 7, 16), fill="#90c8cd", outline="#123d48")
    return image
