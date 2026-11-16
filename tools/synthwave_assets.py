# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared plum surfaces and pink/cyan controls for Synthwave."""

from PIL import Image, ImageDraw


def skin(name):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name == "icon-frame":
        return image
    selected = name in ("row-selected", "card-selected", "tab-selected")
    if selected:
        # Neon goes into the surface; dark labels retain contrast at RGB555.
        for y in range(32):
            t = y / 31
            rgb = tuple(
                round(a * (1 - t) + b * t)
                for a, b in zip((255, 126, 219), (249, 42, 173))
            )
            draw.line((0, y, 31, y), fill=rgb + (255,))
        draw.rounded_rectangle((0, 0, 31, 31), radius=3, outline="#ffb9e9")
        draw.line((6, 29, 25, 29), fill="#9d167b")
        draw.line((25, 30, 30, 30, 30, 25), fill="#36f9f6")
        return image
    fill = (52, 41, 79, 190) if name == "card" else "#34294f"
    if name in ("header", "footer", "panel"):
        fill = "#2a2139"
    draw.rounded_rectangle((0, 0, 31, 31), radius=3, fill=fill, outline="#675581")
    if name in ("header", "footer"):
        draw.line((3, 30, 18, 30), fill="#f92aad")
        draw.line((19, 30, 28, 30), fill="#36f9f6")
    elif name in ("card", "artwork-frame", "panel"):
        draw.line((3, 1, 18, 1), fill="#9f508e")
        draw.line((26, 29, 30, 29, 30, 24), fill="#36f9f6")
    if name == "artwork-frame":
        draw.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
    return image
