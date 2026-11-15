# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, reproducible UI materials. Geometry stays inside Gloam's slice bounds.

These are authored surfaces, not runtime effects: all texture and shading is
baked into PNGs. Cards use four coverage levels; modal panels remain opaque.
"""

from PIL import Image, ImageColor, ImageDraw
from collection_surfaces import focus_skin

# Reading-surface alpha is independent of the 2-bit sprite coverage. A quieter
# browser supports small labels; the upper illustration gets more open space.
STYLES = {
    "aerial": dict(radius=6, top=58, bottom=163, ticks=18),
    "koi": dict(radius=1, top=116, bottom=178, ticks=20),
    "vesper": dict(radius=3, top=172, bottom=170, ticks=24),
    "tidal": dict(radius=9, top=74, bottom=157, ticks=16),
    "slate": dict(radius=0, top=128, bottom=186, ticks=14),
    "folio": dict(radius=0, top=138, bottom=188, ticks=22),
    "phosphor": dict(radius=0, top=150, bottom=194, ticks=12),
}


def rgba(color, alpha=255):
    return (*ImageColor.getrgb(color), alpha)


def chamfer(bounds, cut=3):
    x, y, right, bottom = bounds
    return [
        (x + cut, y),
        (right - cut, y),
        (right, y + cut),
        (right, bottom - cut),
        (right - cut, bottom),
        (x + cut, bottom),
        (x, bottom - cut),
        (x, y + cut),
    ]


def corners(draw, bounds, color, length=5):
    x, y, right, bottom = bounds
    for left, top, sx, sy in (
        (x, y, 1, 1),
        (right, y, -1, 1),
        (x, bottom, 1, -1),
        (right, bottom, -1, -1),
    ):
        draw.line(
            [(left, top + sy * length), (left, top), (left + sx * length, top)],
            fill=color,
        )


def component_skin(theme, name, colors):
    """Return a nine-slice material, or None for a shared status pictogram."""
    if name in ("row-selected", "card-selected"):
        return focus_skin(theme, colors)
    if name.startswith("battery-") or name in ("wireless-idle", "update-available"):
        return None
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    selected = name in ("row-selected", "card-selected", "tab-selected")
    edge = colors["accent"] if selected else colors["line"]
    if name == "icon-frame":
        # Native banners keep their own pixels and don't acquire a second box.
        return image
    if name in ("header", "footer", "row"):
        if theme in ("folio", "slate", "phosphor"):
            y = 31 if name != "footer" else 0
            draw.line((5, y, 26, y), fill=rgba(colors["line"], 85))
        return image
    tab = name == "tab-selected"
    panel = name == "panel"
    frame = name == "artwork-frame"
    alpha = 255 if tab or panel else (170 if selected else 85)
    fill = rgba(colors["accent"] if tab else colors["surface"], alpha)
    if theme == "vesper":
        draw.polygon(chamfer((1, 1, 30, 30)), fill=fill, outline=edge)
        corners(draw, (3, 3, 28, 28), rgba(colors["accent"], 170), 3)
        for x, y in ((4, 4), (27, 4), (4, 27), (27, 27)):
            draw.point((x, y), fill=colors["text"])
    elif theme == "koi":
        draw.rectangle((1, 1, 30, 30), fill=fill)
        draw.line((2, 1, 29, 1), fill=rgba(edge, 170))
        draw.line((2, 30, 29, 30), fill=colors["line"])
        if selected:
            # A lacquer seal, not a full enclosing selection rectangle.
            draw.rectangle((1, 3, 3, 28), fill=colors["accent"])
            draw.rectangle((28, 3, 30, 5), fill=colors["text"])
        else:
            corners(draw, (1, 1, 30, 30), edge, 3)
    elif theme == "slate":
        draw.polygon([(1, 1), (26, 1), (30, 5), (30, 30), (1, 30)], fill=fill)
        draw.line([(1, 30), (1, 1), (26, 1), (30, 5)], fill=edge)
        draw.line((4, 30, 30, 30), fill=rgba(edge, 170))
        if selected:
            draw.rectangle((1, 1, 3, 30), fill=colors["accent"])
            draw.line((26, 1, 26, 5, 30, 5), fill=colors["text"])
    elif theme == "folio":
        draw.rectangle((2, 1, 29, 29), fill=fill)
        draw.line((3, 30, 30, 30), fill=rgba(colors["background"], 170))
        draw.line((30, 3, 30, 30), fill=rgba(colors["line"], 85))
        draw.line((2, 1, 29, 1), fill=rgba(edge, 170))
        draw.line((2, 29, 29, 29), fill=rgba(edge, 170))
        if selected:
            # A folded slip with a small green binding line, distinct from Morrow.
            draw.line((3, 3, 3, 27), fill=colors["accent"])
            draw.polygon([(25, 1), (29, 5), (25, 5)], fill=colors["line"])
    elif theme == "phosphor":
        draw.rectangle((2, 2, 29, 29), fill=fill)
        corners(draw, (1, 1, 30, 30), edge, 5)
        if selected:
            draw.line((8, 1, 23, 1), fill=rgba(edge, 170))
            draw.line((8, 30, 23, 30), fill=rgba(edge, 170))
            draw.rectangle((1, 4, 2, 6), fill=colors["text"])
    else:
        radius = STYLES[theme]["radius"]
        draw.rounded_rectangle(
            (2, 2, 31, 31), radius=radius, fill=rgba(colors["background"], 85)
        )
        draw.rounded_rectangle(
            (1, 1, 30, 30), radius=radius, fill=fill, outline=rgba(edge, 170)
        )
        if theme == "aerial":
            draw.line(
                (7, 2, 24, 2), fill=rgba(colors["text"] if tab else "#ffffff", 170)
            )
            draw.arc((2, 2, 15, 15), 180, 270, fill=rgba("#ffffff", 170))
        else:
            draw.arc((1, 1, 19, 19), 180, 270, fill=colors["accent"], width=1)
            draw.arc((12, 12, 30, 30), 0, 90, fill=rgba(colors["text"], 85))
            if selected:
                draw.ellipse((25, 3, 27, 5), fill=colors["text"])
    if frame:
        # Never wash over real artwork. The four-pixel safe rim is all we need.
        draw.rectangle((4, 4, 27, 27), fill=(0, 0, 0, 0))
    if panel:
        # Modal bodies redraw over the browser; their text area must fully cover it.
        draw.rectangle((4, 4, 27, 27), fill=rgba(colors["surface"]))
    return image


def reading_surface_skin(theme, colors, bottom):
    image = Image.new("RGBA", (256, 192))
    pixels = image.load()
    alpha = STYLES[theme]["bottom" if bottom else "top"]
    base = ImageColor.getrgb(colors["background"])
    # A fixed, very quiet texture avoids both a flat wash and noisy small text.
    for y in range(4, 188):
        for x in range(6, 250):
            grain = ((x * 37 + y * 19 + (x * y) % 23) % 5) - 2
            shade = grain if theme in ("folio", "slate", "vesper") else 0
            coverage = alpha
            if theme in ("aerial", "tidal"):
                coverage += round(22 * (1 - y / 192))
            pixels[x, y] = (*[max(0, min(255, c + shade)) for c in base], coverage)
    draw = ImageDraw.Draw(image)
    line, accent = colors["line"], colors["accent"]
    if theme == "aerial":
        corners(draw, (5, 4, 250, 187), rgba("#ffffff", 170), 13)
        draw.line((20, 4, 234, 4), fill=rgba("#ffffff", 100))
        draw.line((20, 188, 234, 188), fill=rgba(line, 100))
    elif theme == "tidal":
        # Two offset arcs evoke an optical lens without another rectangular mat.
        draw.arc((4, 3, 48, 47), 180, 270, fill=rgba(accent, 170))
        draw.arc((208, 143, 252, 187), 0, 90, fill=rgba(accent, 170))
        draw.arc((211, 146, 249, 184), 0, 90, fill=rgba(colors["text"], 85))
        for y in (8, 14, 20):
            draw.line((249, y, 251, y), fill=rgba(line, 170))
    elif theme == "koi":
        draw.line((6, 4, 249, 4), fill=rgba(accent, 170))
        draw.line((6, 187, 249, 187), fill=rgba(line, 170))
        for y in (6, 10, 14):
            draw.rectangle((3, y, 4, y + 2), fill=rgba(accent, 170))
        draw.rectangle((248, 181, 251, 184), fill=rgba(accent, 170))
    elif theme == "vesper":
        corners(draw, (4, 3, 251, 189), rgba(accent, 170), 14)
        for x, y in ((4, 3), (248, 3), (4, 186), (248, 186)):
            draw.polygon(
                [(x, y + 1), (x + 1, y), (x + 3, y + 1), (x + 1, y + 3)], fill=accent
            )
    elif theme == "slate":
        draw.line((4, 4, 4, 187), fill=rgba(line, 170))
        draw.line((251, 4, 251, 187), fill=rgba(line, 170))
        for y in range(10, 185, 8):
            draw.line((4, y, 6 if y % 16 else 8, y), fill=rgba(accent, 170))
        corners(draw, (4, 3, 251, 189), rgba(accent, 170), 5)
    elif theme == "folio":
        draw.line((5, 5, 5, 187), fill=rgba(accent, 170))
        draw.line((8, 5, 8, 187), fill=rgba(line, 85))
        for y in range(12, 184, 16):
            draw.ellipse((3, y, 5, y + 2), fill=rgba(line, 170))
        draw.line((9, 188, 249, 188), fill=rgba(line, 170))
        draw.polygon([(243, 4), (249, 10), (243, 10)], fill=rgba(line, 100))
    else:
        corners(draw, (4, 3, 251, 189), rgba(accent, 170), 10)
        for x in range(16, 244, 12):
            draw.line((x, 189, x, 188 if x % 24 else 186), fill=rgba(line, 170))
    return image


def control_skin(theme, name, colors):
    """Use simple, different silhouettes that still read at 8–18 pixels."""
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    accent, face, line = colors["accent"], colors["surface"], colors["line"]
    round_control = theme in ("aerial", "tidal")
    if name.startswith("arrow-"):
        if theme == "tidal":
            draw.polygon([(10, 4), (25, 16), (10, 28), (13, 16)], fill=accent)
        elif theme in ("koi", "vesper"):
            draw.line([(10, 5), (23, 16), (10, 27)], fill=accent, width=4)
            draw.line((4, 16, 22, 16), fill=accent, width=3)
        elif theme in ("slate", "phosphor"):
            draw.polygon([(8, 5), (24, 16), (8, 27)], fill=accent)
            if theme == "phosphor":
                draw.rectangle((2, 6, 4, 26), fill=line)
        else:
            draw.line([(10, 5), (23, 16), (10, 27)], fill=accent, width=4)
        return image.rotate({"right": 0, "up": 90, "left": 180, "down": 270}[name[6:]])
    if name.startswith("scroll-"):
        draw.rectangle(
            (0, 0, 31, 31),
            fill=rgba(
                accent if name.endswith("thumb") else line,
                255 if name.endswith("thumb") else 85,
            ),
        )
        if name.endswith("thumb") and theme in ("slate", "folio", "phosphor"):
            for y in (9, 16, 23):
                draw.line((0, y, 31, y), fill=face, width=2)
    elif name.startswith("check-"):
        if theme == "tidal":
            draw.ellipse((2, 2, 29, 29), fill=face, outline=accent, width=3)
        elif theme == "vesper":
            draw.polygon(chamfer((2, 2, 29, 29), 5), fill=face, outline=accent)
            corners(draw, (4, 4, 27, 27), accent, 4)
        elif theme == "phosphor":
            corners(draw, (2, 2, 29, 29), accent, 7)
        else:
            draw.rounded_rectangle(
                (3, 3, 28, 28),
                radius=6 if round_control else 0,
                fill=face,
                outline=accent,
                width=3,
            )
        if name.endswith("on"):
            if theme in ("koi", "phosphor"):
                draw.polygon([(16, 8), (24, 16), (16, 24), (8, 16)], fill=accent)
            else:
                draw.line([(8, 16), (14, 22), (24, 10)], fill=accent, width=4)
    elif name.startswith("toggle-"):
        on = name.endswith("on")
        draw.rounded_rectangle(
            (1, 5, 30, 26),
            radius=10 if round_control else 2,
            fill=accent if on else face,
            outline=accent,
            width=2,
        )
        x = 18 if on else 3
        bounds = (x, 8, x + 10, 23)
        ink = colors["ink"] if on else line
        if round_control:
            draw.ellipse(bounds, fill=ink)
        else:
            draw.rectangle(bounds, fill=ink)
            if theme in ("slate", "phosphor"):
                draw.line((x + 5, 10, x + 5, 21), fill=face, width=2)
    elif theme in ("aerial", "tidal", "koi"):
        draw.arc((4, 4, 28, 28), 25, 305, fill=accent, width=3)
        draw.ellipse((22, 3, 27, 8), fill=accent)
    elif theme == "phosphor":
        for i in range(3):
            draw.rectangle(
                (4 + i * 9, 8, 9 + i * 9, 25), fill=rgba(accent, 85 * (i + 1))
            )
    else:
        draw.line([(7, 4), (25, 4), (9, 27), (25, 27), (7, 4)], fill=accent, width=3)
    return image
