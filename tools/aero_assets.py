# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista-era smoky window glass around neutral Explorer reading surfaces."""

from PIL import Image, ImageDraw


def glass(image, footer=False):
    draw = ImageDraw.Draw(image)
    stops = (
        (0, (81, 113, 105)),
        (0.38, (43, 68, 61)),
        (0.5, (23, 44, 39)),
        (1, (40, 74, 64)),
    )
    if footer:
        stops = (
            (0, (63, 83, 76)),
            (0.38, (35, 50, 44)),
            (0.5, (14, 24, 22)),
            (1, (24, 43, 35)),
        )
    for y in range(32):
        t = y / 31
        for index in range(1, len(stops)):
            if t <= stops[index][0]:
                break
        a, first = stops[index - 1]
        b, second = stops[index]
        u = (t - a) / (b - a)
        rgb = tuple(round(x * (1 - u) + z * u) for x, z in zip(first, second))
        draw.line((0, y, 31, y), fill=rgb + (235,))
    draw.line((0, 0, 31, 0), fill=(190, 221, 204, 210))
    draw.line((0, 31, 31, 31), fill="#182c24")


def skin(name):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name == "icon-frame":
        return image
    if name == "row":
        draw.line((4, 31, 27, 31), fill=(117, 147, 145, 65))
        return image
    if name in ("header", "footer", "tab-selected"):
        glass(image, name == "footer")
        if name == "tab-selected":
            draw.rounded_rectangle((0, 0, 31, 31), radius=4, outline="#b6e4d7")
            draw.line((4, 28, 27, 28), fill="#69b391", width=2)
        return image
    if name in ("row-selected", "card-selected"):
        for y in range(32):
            t = y / 31
            rgb = tuple(
                round(a * (1 - t) + b * t)
                for a, b in zip((232, 248, 255), (183, 221, 236))
            )
            draw.line((0, y, 31, y), fill=rgb + (255,))
        draw.rounded_rectangle((0, 0, 31, 31), radius=3, outline="#5799b5")
        draw.line((4, 2, 27, 2), fill="#ffffff")
        return image
    draw.rounded_rectangle(
        (0, 0, 31, 31),
        radius=3,
        fill=(247, 251, 250, 170) if name == "card" else (247, 251, 250, 246),
        outline=(90, 122, 116, 210),
    )
    draw.line((2, 27, 2, 2, 27, 2), fill=(255, 255, 255, 220))
    draw.line((3, 29, 29, 29, 29, 3), fill=(143, 167, 160, 170))
    if name == "artwork-frame":
        draw.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
    return image


def reading_surface(screen):
    image = Image.new("RGBA", (256, 192))
    draw = ImageDraw.Draw(image)
    # Keep the desktop at the edges, with a bounded Explorer content window.
    draw.rounded_rectangle(
        (5, 25, 250, 175),
        radius=4,
        fill=(83, 113, 102, 190),
        outline=(184, 217, 203, 220),
    )
    draw.rectangle((8, 28, 247, 172), fill="#f7fbfa")
    if screen == "top":
        # The Welcome-style upper pane shows the Aurora through prepared glass;
        # the lower toolbar remains a neutral Explorer reading surface.
        draw.rectangle((8, 28, 247, 112), fill=(247, 251, 250, 180))
    return image
