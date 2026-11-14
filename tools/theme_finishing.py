"""Small material surfaces, control artwork and bounded ambient marks."""

import math
from pathlib import Path
from PIL import Image, ImageColor, ImageDraw

CONTROLS = "check-off check-on toggle-off toggle-on arrow-left arrow-right arrow-up arrow-down scroll-track scroll-thumb busy".split()


def rgba(color, alpha=255):
    return (*ImageColor.getrgb(color), alpha)


def parchment_coverage(image, center, border, fade):
    """Thin the paper interior while retaining the authored, worn perimeter."""
    width, height = image.size
    original = image.getchannel("A").tobytes()
    coverage = bytearray(len(original))
    for y in range(height):
        for x in range(width):
            distance = min(x, y, width - 1 - x, height - 1 - y)
            rim = max(0, min(fade, border + fade - distance))
            opacity = center + (255 - center) * rim // fade
            index = y * width + x
            coverage[index] = original[index] * opacity // 255
    image.putalpha(Image.frombytes("L", image.size, bytes(coverage)))


def control(name, colors, theme):
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    ink, face, line = colors["accent"], colors["surface"], colors["line"]
    rounded = theme in ("aerial", "tidal", "koi")
    if name.startswith("arrow-"):
        d.line([(10, 6), (22, 16), (10, 26)], fill=ink, width=5 if rounded else 4)
        turns = {"right": 0, "up": 90, "left": 180, "down": 270}
        return image.rotate(turns[name[6:]])
    if name.startswith("scroll-"):
        d.rectangle(
            (0, 0, 31, 31),
            fill=rgba(
                ink if name.endswith("thumb") else line,
                255 if name.endswith("thumb") else 85,
            ),
        )
    elif name.startswith("check-"):
        d.rounded_rectangle(
            (3, 3, 28, 28), radius=6 if rounded else 1, fill=face, outline=ink, width=3
        )
        if name.endswith("on"):
            d.line([(8, 16), (14, 22), (25, 10)], fill=ink, width=4)
    elif name.startswith("toggle-"):
        on = name.endswith("on")
        d.rounded_rectangle(
            (1, 4, 30, 27),
            radius=11 if rounded else 4,
            fill=ink if on else face,
            outline=ink,
            width=2,
        )
        x = 17 if on else 4
        d.rounded_rectangle(
            (x, 8, x + 10, 23),
            radius=4 if rounded else 1,
            fill=colors["ink"] if on else line,
        )
    else:
        d.line([(7, 3), (25, 3), (9, 27), (25, 27), (7, 3)], fill=ink, width=3)
        d.line((7, 29, 25, 29), fill=line, width=2)
    if theme == "vesper" and name.startswith(("check", "toggle")):
        for x, y in ((2, 2), (29, 29)):
            d.point((x, y), fill=colors["text"])
    return image


def reading_surface(theme, colors, opacity, bottom, materials):
    image = Image.new("RGBA", (256, 192))
    if theme == "morrow":
        # Transparency is baked once; the console still blends only on loading.
        sheet = Image.open(materials / "morrow-parchment.png").convert("RGBA")
        sheet = sheet.resize((250, 190), Image.Resampling.LANCZOS)
        parchment_coverage(sheet, 158 if bottom else 107, border=7, fade=9)
        image.alpha_composite(sheet, (3, 1))
        return image
    if theme == "folio":
        paper = Image.open(materials / "morrow-paper.png").convert("RGBA")
        paper = paper.resize((244, 184), Image.Resampling.LANCZOS)
        paper.putalpha(240 if bottom else 225)
        image.alpha_composite(paper, (6, 4))
        d = ImageDraw.Draw(image)
        d.line((6, 5, 6, 186), fill=rgba(colors["accent"], 170))
        return image
    d = ImageDraw.Draw(image)
    radius = {"aerial": 12, "tidal": 16, "koi": 3, "vesper": 2}.get(theme, 0)
    d.rounded_rectangle((7, 5, 251, 189), radius=radius, fill=(0, 0, 0, 65))
    d.rounded_rectangle(
        (6, 4, 249, 187),
        radius=radius,
        fill=rgba(colors["background"], round(opacity * 2.55)),
    )
    # Keep material details on the perimeter, outside live text.
    if theme in ("aerial", "tidal"):
        d.arc((6, 4, 46, 44), 180, 270, fill=rgba(colors["text"], 170), width=1)
        d.line((26, 4, 225, 4), fill=rgba(colors["text"], 120))
        d.arc((209, 147, 249, 187), 0, 90, fill=rgba(colors["accent"], 170))
    elif theme == "vesper":
        for x, y in ((6, 4), (245, 4), (6, 183), (245, 183)):
            d.polygon(
                [(x + 2, y), (x + 4, y + 2), (x + 2, y + 4), (x, y + 2)],
                fill=colors["accent"],
            )
        d.line((16, 4, 239, 4), fill=rgba(colors["accent"], 100))
    elif theme == "koi":
        d.line((7, 5, 248, 5), fill=rgba(colors["accent"], 170))
        d.line((7, 186, 248, 186), fill=rgba(colors["line"], 200))
    elif theme == "slate":
        d.line((6, 4, 249, 4), fill=rgba(colors["text"], 85))
        for y in range(12, 183, 12):
            d.line((6, y, 7, y), fill=rgba(colors["line"], 170))
    else:
        d.line((6, 4, 249, 4), fill=rgba(colors["accent"], 100))
        for x in range(12, 245, 12):
            d.point((x, 187), fill=rgba(colors["accent"], 170))
    return image


def ambient_frame(theme, colors, frame):
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    ink, muted = colors["accent"], colors["line"]
    phase = 2 * math.pi * frame / 8
    if theme == "tidal":
        for x, offset in ((11, 0), (22, 4)):
            y = 24 - ((frame + offset) % 8) * 2
            d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=rgba(ink, 170), width=2)
    elif theme == "phosphor":
        d.ellipse((3, 3, 29, 29), outline=muted, width=2)
        d.line(
            (
                16,
                16,
                16 + round(math.cos(phase) * 12),
                16 + round(math.sin(phase) * 12),
            ),
            fill=ink,
            width=2,
        )
    elif theme == "koi":
        for radius in (5 + frame % 4, 11 + frame % 4):
            d.arc(
                (16 - radius, 16 - radius, 16 + radius, 16 + radius),
                20,
                290,
                fill=rgba(ink, 170),
            )
    elif theme in ("morrow", "folio"):
        shift = round(math.sin(phase))
        d.line((10, 27, 20 + shift, 5), fill=muted, width=2)
        d.ellipse((13 + shift, 7, 24 + shift, 14), fill=rgba(ink, 170))
        d.ellipse((7 + shift, 16, 18 + shift, 22), fill=rgba(ink, 170))
    elif theme == "slate":
        d.line((5, 26, 26, 26), fill=muted, width=2)
        for x, offset in ((9, 0), (17, 3), (25, 6)):
            y = 5 + (frame + offset) % 8 * 2
            d.line((x, y, x - 2, y + 5), fill=rgba(ink, 170), width=2)
    else:
        radius = 3 + round((math.sin(phase) + 1) * 2)
        d.line((16 - radius, 16, 16 + radius, 16), fill=ink, width=2)
        d.line((16, 16 - radius, 16, 16 + radius), fill=ink, width=2)
        if theme == "vesper":
            d.polygon(
                [(16, 16), (5, 8), (8, 22), (16, 18), (24, 22), (27, 8)], outline=muted
            )
    return image


def finish(theme, folder, config, profiles, packer):
    colors = config["colors"]
    config["components"]["controls"] = "on"
    for name in CONTROLS:
        control(name, colors, theme).save(
            folder / "components" / f"{name}.png", optimize=True
        )
    for screen in ("top", "bottom"):
        image = reading_surface(
            theme,
            colors,
            profiles[theme][screen],
            screen == "bottom",
            folder.parents[1] / "source/materials",
        )
        name = f"material-{screen}.png"
        image.save(folder / "backgrounds" / name, optimize=True)
        config["backgrounds"][screen + "_surface"] = "backgrounds/" + name
        config["layout"][screen + "_content_opacity"] = "100"
    (folder / "motion").mkdir(exist_ok=True)
    frames = [packer.sprite(ambient_frame(theme, colors, frame)) for frame in range(8)]
    (folder / "motion/ambient.gtm").write_bytes(
        b"GLMFX001" + bytes([8, 32, 32, 0, 0, 0, 0, 0]) + b"".join(frames)
    )
    config["motion"] = {
        "ambient": "motion/ambient.gtm",
        "ambient_ticks": "12",
        "focus": "pulse",
    }
    config["assets"] = {"prepared": "assets.gfx"}
