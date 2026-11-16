# SPDX-License-Identifier: GPL-3.0-or-later
"""Open control frames that let the illustrated Pokédex casing form the UI."""

from PIL import Image, ImageDraw


def skin(name):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name in ("header", "footer", "panel", "icon-frame"):
        return image
    selected = name in ("row-selected", "card-selected", "tab-selected")
    if selected:
        draw.rounded_rectangle(
            (0, 0, 31, 31), radius=3, fill="#277c8c", outline="#163f4e"
        )
        draw.line((4, 3, 27, 3), fill="#72d7ed", width=2)
        draw.line((4, 28, 27, 28), fill="#194f5c", width=2)
    else:
        # The interior is fully transparent. Only the soft green frame remains.
        draw.rounded_rectangle((0, 0, 31, 31), radius=3, outline=(58, 100, 80, 170))
    if name == "tab-selected":
        draw.ellipse((3, 12, 8, 17), fill="#72d7ed", outline="#163f4e")
    return image
