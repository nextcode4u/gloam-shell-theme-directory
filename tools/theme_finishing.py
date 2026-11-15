"""Small material surfaces, control artwork and bounded ambient marks."""

import math
from PIL import Image, ImageColor, ImageDraw
from theme_materials import STYLES, control_skin, reading_surface_skin
from collection_surfaces import prepare_materials, reading_material

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
    if theme != "morrow":
        return control_skin(theme, name, colors)
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


def reading_surface(theme, colors, bottom, materials):
    image = Image.new("RGBA", (256, 192))
    if theme == "morrow":
        # Transparency is baked once; the console still blends only on loading.
        sheet = Image.open(materials / "morrow-parchment.png").convert("RGBA")
        sheet = sheet.resize((250, 190), Image.Resampling.LANCZOS)
        parchment_coverage(sheet, 158 if bottom else 107, border=7, fade=9)
        image.alpha_composite(sheet, (3, 1))
        return image
    return reading_surface_skin(theme, colors, bottom)


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


def finish(theme, folder, config, packer):
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
            screen == "bottom",
            folder.parents[1] / "source/materials",
        )
        image = reading_material(theme, image, colors)
        name = f"material-{screen}.png"
        image.save(folder / "backgrounds" / name, optimize=True)
        config["backgrounds"][screen + "_surface"] = "backgrounds/" + name
        config["layout"][screen + "_content_opacity"] = "100"
    prepare_materials(theme, folder, config)
    (folder / "motion").mkdir(exist_ok=True)
    frames = [packer.sprite(ambient_frame(theme, colors, frame)) for frame in range(8)]
    (folder / "motion/ambient.gtm").write_bytes(
        b"GLMFX001" + bytes([8, 32, 32, 0, 0, 0, 0, 0]) + b"".join(frames)
    )
    config["motion"] = {
        "ambient": "motion/ambient.gtm",
        "ambient_ticks": str(STYLES[theme]["ticks"]) if theme in STYLES else "12",
        "focus": "off",
    }
    config["assets"] = {"prepared": "assets.gfx"}
