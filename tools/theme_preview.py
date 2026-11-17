# SPDX-License-Identifier: GPL-3.0-or-later
"""Fast authoring composition; optional native renderer uses an isolated SD fixture."""

from __future__ import annotations

import configparser
from pathlib import Path
import os
import shutil
import struct
import subprocess
import tempfile
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageColor
from theme_schema import COLORS
from theme_validate import inside, font_info


COMPOSED_LAYOUTS = (
    "spotlight",
    "gallery",
    "journal",
    "panorama",
    "dossier",
    "portrait",
)


def composition_boxes(layout):
    """Mirror Gloam's bounded composition geometry, including icon-tab captions."""
    kind = layout.get("top_layout", "gallery")
    above = layout.get("tabs_position") == "top" or (
        not layout.get("tabs_position") and kind == "gallery"
    )
    tabs_height = 32 if layout.get("tab_style") == "icons" else 20
    tabs_y = 26 if above else 176 - tabs_height
    top = tabs_y + tabs_height + 6 if above else 27
    bottom = 173 if above else tabs_y - 6
    height = bottom - top - 24
    title, info = (12, top, 232, 16), None
    if kind == "spotlight":
        art = (76, top + 24, 104, min(height, 104))
    elif kind == "gallery":
        art, info = (14, top + 24, 92, height), (120, top + 24, 124, height)
    elif kind == "panorama":
        art, title = (48, top + 4, 160, bottom - top - 30), (12, bottom - 18, 232, 16)
    elif kind == "dossier":
        art, info = (154, top + 24, 88, height), (12, top + 24, 128, height)
    elif kind == "portrait":
        art = (14, top + 4, 96, bottom - top - 8)
        title, info = (124, top + 2, 120, 16), (124, top + 26, 120, bottom - top - 26)
    else:
        art = (14, top + 4, 60, min(bottom - top - 8, 84))
        title, info = (86, top + 2, 158, 16), (86, top + 26, 158, bottom - top - 26)
    return dict(
        artwork=art, title=title, information=info, tabs=(0, tabs_y, 256, tabs_height)
    )


def text(draw, xy, value, fill, width=236, size=11):
    packs = getattr(draw, "theme_fonts", {})
    pack = packs.get("heading" if size >= 13 else "ui")
    if pack:
        glyphs, height = pack
        x, y = xy
        rgb = ImageColor.getrgb(fill)
        for character in value:
            glyph = glyphs.get(ord(character), glyphs.get(63))
            if glyph is None:
                continue
            advance, mask = glyph
            if x + advance > xy[0] + width:
                break
            ink = Image.new("RGBA", mask.size, rgb + (255,))
            ink.putalpha(mask)
            draw.theme_image.alpha_composite(ink, (int(x), int(y)))
            x += advance
        return
    font = ImageFont.load_default(size=size)
    while value and draw.textlength(value, font=font) > width:
        value = value[:-1]
    draw.text(xy, value, font=font, fill=fill)


@lru_cache(maxsize=16)
def glyph_pack(data):
    info = font_info(data, True)
    height = info["height"]
    glyphs = {}
    proportional = data[:8] == b"DSFONT03"
    count = info["glyphs"]
    stride = 2 + height * 4 if proportional else 24
    for index in range(count):
        start = 16 + index * stride
        advance = data[start] if proportional else 7
        rows = struct.unpack_from(
            "<" + ("I" if proportional else "H") * height,
            data,
            start + 2 if proportional else start,
        )
        mask = Image.new("L", (advance, height))
        mask.putdata(
            [
                ((rows[y] >> (2 * x)) & 3) * 85
                for y in range(height)
                for x in range(advance)
            ]
        )
        cp = index + 32 if index < 95 else index - 95 + 160
        glyphs[cp] = (advance, mask)
    return glyphs, height


def theme_draw(project, image):
    draw = ImageDraw.Draw(image)
    draw.theme_fonts = {}
    draw.theme_image = image
    for role in ("ui", "heading"):
        relative = project.data["config"].get("fonts", {}).get(role, "builtin")
        if relative == "builtin":
            continue
        try:
            draw.theme_fonts[role] = glyph_pack(
                inside(project.theme, relative).read_bytes()
            )
        except (ValueError, OSError):
            pass
    if "heading" not in draw.theme_fonts and "heading" not in project.data[
        "config"
    ].get("fonts", {}):
        draw.theme_fonts["heading"] = draw.theme_fonts.get("ui")
    return draw


def skin(project, screen, name, box, fallback):
    config = project.data["config"]
    directory = config.get("components", {}).get("directory", "")
    relative = directory + "/" + name + ".png"
    path = inside(project.theme, relative) if directory else None
    if not path or not path.is_file():
        if fallback is not None:
            ImageDraw.Draw(screen).rectangle(box, fill=fallback)
        return
    with Image.open(path) as source:
        source = source.convert("RGBA")
    if source.size != (32, 32):
        return
    b = int(config.get("components", {}).get("border", "6"))
    x, y, right, bottom = box
    w, h = right - x, bottom - y
    b = min(b, w // 2, h // 2)
    if config.get("components", {}).get("alpha") == "coverage":
        source.putalpha(source.getchannel("A").point(lambda a: round(a / 85) * 85))
    else:
        source.putalpha(source.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
    if not b:
        screen.alpha_composite(source.resize((w, h)), (x, y))
        return
    for sy, sh, dy, dh in (
        (0, b, 0, b),
        (b, 32 - 2 * b, b, h - 2 * b),
        (32 - b, b, h - b, b),
    ):
        for sx, sw, dx, dw in (
            (0, b, 0, b),
            (b, 32 - 2 * b, b, w - 2 * b),
            (32 - b, b, w - b, b),
        ):
            if dw <= 0 or dh <= 0:
                continue
            piece = source.crop((sx, sy, sx + sw, sy + sh)).resize(
                (dw, dh), Image.Resampling.NEAREST
            )
            screen.alpha_composite(piece, (x + dx, y + dy))


def icon(project, name, size=32):
    directory = project.data["config"].get("icons", {}).get("directory", "icons")
    path = inside(project.theme, directory + "/" + name + ".png")
    if path.is_file():
        with Image.open(path) as image:
            return image.convert("RGBA").resize((size, size), Image.Resampling.NEAREST)
    from theme_media import starter_icon

    return starter_icon(name, COLORS | project.data["config"].get("colors", {})).resize(
        (size, size), Image.Resampling.NEAREST
    )


def render(project, sample="browser", view=None, selected=1, guides=False):
    config = project.data["config"]
    p = COLORS | config.get("colors", {})
    layout = config.get("layout", {})
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_dict(config)
    from theme_native.theme_prepared_surfaces import screens

    output = [Image.new("RGBA", (256, 192), p["background"]) for _ in range(2)]
    try:
        for _, index, data in screens(project.theme, parser, inside):
            values = struct.unpack_from("<49152H", data, 8)
            image = Image.new("RGBA", (256, 192))
            image.putdata(
                [
                    (
                        (v & 31) * 255 // 31,
                        ((v >> 5) & 31) * 255 // 31,
                        ((v >> 10) & 31) * 255 // 31,
                        255,
                    )
                    for v in values
                ]
            )
            output[index] = image
            if struct.unpack_from("<I", data, 4)[0] & 4:
                values = struct.unpack_from("<24064H", data, 8 + 98304)
                strip = Image.new("RGBA", (256, 94))
                strip.putdata(
                    [
                        (
                            (v & 31) * 255 // 31,
                            ((v >> 5) & 31) * 255 // 31,
                            ((v >> 10) & 31) * 255 // 31,
                            255,
                        )
                        for v in values
                    ]
                )
                image.paste(strip, (0, 24))
    except (OSError, ValueError):
        pass
    top, bottom = output
    for screen in output:
        if layout.get("chrome", "full") == "full":
            skin(project, screen, "header", (5, 4, 251, 26), None)
            skin(project, screen, "footer", (5, 173, 251, 190), None)
    d = theme_draw(project, top)
    header = config.get("theme", {}).get(
        "header", config.get("theme", {}).get("name", "Gloam")
    )
    text(d, (10, 7), header, p.get("header_text", p["text"]), width=132)
    text(d, (201, 7), "2 / 6", p.get("header_text", p["muted"]), width=48, size=10)
    cd = config.get("components", {}).get("directory", "components")
    for name, x in (("battery-high", 164), ("wireless-idle", 182)):
        file = inside(project.theme, cd + "/" + name + ".png")
        if file.is_file():
            with Image.open(file) as image:
                top.alpha_composite(image.convert("RGBA").resize((14, 14)), (x, 6))
    composition = layout.get("top_layout", "sidebar")
    if composition in ("sidebar", "sidebar_left"):
        rail = 7 if composition == "sidebar_left" else 184
        art_x = 80 if rail == 7 else 14
        skin(project, top, "card", (art_x, 48, art_x + 76, 143), p["surface"])
        top.alpha_composite(icon(project, "folder", 48), (art_x + 14, 64))
        text(d, (art_x, 30), "Adventure", p["text"], 100)
        for i, label in enumerate(
            ("Home", "Games", "Apps", "Media", "System", "Files")
        ):
            y = 40 + i * 20
            if i == 1:
                skin(
                    project,
                    top,
                    "tab-selected",
                    (rail - 2, y - 2, rail + 65, y + 16),
                    p["accent"],
                )
            text(
                d,
                (rail + 2, y),
                label,
                p.get("tab_text", p["ink"]) if i == 1 else p["text"],
                60,
                size=10,
            )
    else:
        boxes = composition_boxes(layout) if composition in COMPOSED_LAYOUTS else None
        art = (
            boxes["artwork"]
            if boxes
            else {
                "scene": (
                    int(layout.get("scene_cover_x", "18")),
                    int(layout.get("scene_cover_y", "34")),
                    int(layout.get("scene_cover_width", "48")),
                    int(layout.get("scene_cover_height", "72")),
                ),
                "poster": (18, 45, 86, 95),
            }[composition]
        )
        x, y, w, h = art
        skin(project, top, "card", (x, y, x + w, y + h), p["surface"])
        size = min(w - 12, h - 12, 80)
        top.alpha_composite(
            icon(project, "folder", size), (x + (w - size) // 2, y + (h - size) // 2)
        )
        if composition == "scene":
            skin(project, top, "panel", (7, 121, 249, 151), p["surface"])
            text(d, (11, 123), "Adventure", p["text"], 232, size=13)
            if layout.get("tab_style") != "icons":
                text(d, (11, 138), "FOLDER / Y: details", p["muted"], 232, size=9)
        elif boxes:
            tx, ty, tw, _ = boxes["title"]
            text(d, (tx, ty + 2), "Adventure", p["text"], tw, size=13)
            if boxes["information"]:
                ix, iy, iw, ih = boxes["information"]
                text(d, (ix, iy), "FOLDER", p["accent"], iw)
                if ih >= 60:
                    text(d, (ix, iy + 48), "SD card", p["muted"], iw)
                if ih >= 78:
                    text(d, (ix, iy + 66), "Y: details", p["muted"], iw)
        else:
            text(d, (12, 29), "Adventure", p["text"], 228, size=13)
        nav_y = (
            boxes["tabs"][1]
            if boxes
            else (144 if layout.get("tab_style") == "icons" else 155)
        )
        count = int(layout.get("tab_visible", "3"))
        gap = int(layout.get("tab_gap", "4"))
        cell = (240 - gap * (count - 1)) // count
        for i, label in enumerate(("Home", "Games", "Apps", "Media", "Files")[:count]):
            x = 8 + i * (cell + gap)
            highlight = layout.get("tab_highlight", "skin")
            if i == 1:
                if highlight == "skin":
                    skin(
                        project,
                        top,
                        "tab-selected",
                        (x, nav_y, x + cell, nav_y + 18),
                        p["accent"],
                    )
                elif highlight == "underline":
                    d.rectangle(
                        (x, nav_y + 16, x + cell - 1, nav_y + 17), fill=p["accent"]
                    )
                else:
                    d.rectangle(
                        (x, nav_y, x + cell - 1, nav_y + 17), outline=p["accent"]
                    )
            style = layout.get("tab_style", "labels")
            if style == "icons":
                top.alpha_composite(
                    icon(project, "tab-" + label.lower(), 14),
                    (x + cell // 2 - 7, nav_y + 1),
                )
            else:
                text(
                    d,
                    (x + 3, nav_y + 2),
                    str(i + 1) + " " + label if style == "numbered" else label,
                    p.get("tab_text", p["ink"])
                    if i == 1 and highlight == "skin"
                    else p["text"],
                    cell - 6,
                    size=9,
                )
        if layout.get("tab_style") == "icons":
            text(d, (12, nav_y + 20), "Games", p["text"], 232)
    text(d, (10, 178), "20:30  L/R tabs", p.get("footer_text", p["muted"]), 164, size=9)
    text(d, (202, 178), "SD OK", p.get("footer_text", p["accent"]), 48, size=9)
    d = theme_draw(project, bottom)
    text(
        d,
        (10, 7),
        "Appearance" if sample == "settings" else "Games",
        p.get("header_text", p["text"]),
        170,
    )
    text(d, (202, 7), "Settings", p.get("header_link_text", p["accent"]), 48, size=9)
    text(d, (10, 23), "sd:/roms", p.get("header_text", p["muted"]), 225, size=9)
    style = view or layout.get("view", "extended")
    icon_size = layout.get("icon_size", "large")
    large = icon_size == "large"
    medium = icon_size == "medium"
    names = [
        "Adventure",
        "Homebrew",
        "Nintendo DS",
        "Puzzle",
        "A long title to check clipping",
        "Music collection",
    ]
    if sample == "settings":
        for i, (label, value) in enumerate(
            (
                ("Theme", "My theme"),
                ("Icon size", "Large"),
                ("Browser view", style),
                ("Reduced motion", "Off"),
                ("Background music", "Theme"),
            )
        ):
            y = 46 + i * 23
            skin(
                project,
                bottom,
                "row-selected" if i == selected else "row",
                (8, y - 2, 248, y + 21),
                p["accent"] if i == selected else None,
            )
            text(
                d,
                (14, y + 3),
                label,
                p.get("selection_text", p["text"]) if i == selected else p["text"],
                140,
                size=10,
            )
            text(d, (162, y + 3), value, p["accent"], 80, size=10)
    elif style in ("grid", "shelf"):
        columns = (
            3
            if style == "shelf" or medium
            else (2 if not large else int(layout.get("large_grid_columns", "3")))
        )
        rows = 1 if style == "shelf" else 2
        w = 240 // columns
        h = 120 // rows
        for i in range(columns * rows):
            x = 8 + (i % columns) * w
            y = 43 + (i // columns) * h
            skin(
                project,
                bottom,
                "card-selected" if i == selected else "card",
                (x + 1, y, x + w - 3, y + h - 4),
                p["accent"] if i == selected else p["surface"],
            )
            size = (
                (48 if large else 40 if medium else 32)
                if style == "shelf"
                else (32 if large else 24 if medium else 16)
            )
            bottom.alpha_composite(
                icon(project, "folder", size), (x + (w - size) // 2, y + 7)
            )
            text(
                d,
                (x + 5, y + h - 18),
                names[i % len(names)],
                p.get("selection_text", p["text"]) if i == selected else p["text"],
                w - 12,
                size=9,
            )
    else:
        height = (
            (36 if style == "extended" or (style == "index" and large) else 24)
            + (4 if medium and style not in ("list", "extended") else 0)
            + int(layout.get("row_padding", "0"))
        )
        for i, label in enumerate(names[: max(1, 126 // height)]):
            y = 42 + i * height
            skin(
                project,
                bottom,
                "row-selected" if i == selected else "row",
                (8, y, 248, y + height - 2),
                p["accent"] if i == selected else None,
            )
            if style != "list":
                bottom.alpha_composite(
                    icon(project, "folder", 32 if large else 24 if medium else 16),
                    (13, y + 4),
                )
            x = 13 if style == "list" else 51 if large else 43 if medium else 35
            text(
                d,
                (x, y + 4),
                label,
                p.get("selection_text", p["text"]) if i == selected else p["text"],
                238 - x,
                size=11,
            )
            if style == "extended":
                text(d, (x, y + 21), "FOLDER", p["muted"], 236 - x, size=9)
    text(
        d,
        (10, 178),
        "A Open  B Back  X Tabs  Y Info  SEL",
        p.get("footer_text", p["muted"]),
        236,
        size=9,
    )
    if guides:
        for screen in output:
            guide = ImageDraw.Draw(screen)
            guide.rectangle((6, 4, 249, 187), outline="#ee53a4")
            guide.line((0, 173, 255, 173), fill="#ee53a4")
    result = Image.new("RGB", (256, 396), "#11151c")
    result.paste(top.convert("RGB"), (0, 0))
    result.paste(bottom.convert("RGB"), (0, 204))
    return result


def native(project, executable, sample="browser"):
    executable = Path(executable).resolve(strict=True)
    if not executable.is_file():
        raise ValueError("Choose a trusted local Gloam host preview executable.")
    with tempfile.TemporaryDirectory(prefix="gloam-native-preview-") as temp:
        root = Path(temp)
        sd = root / "sd"
        folder = sd / "_nds/dsi-frontend/themes" / project.data["id"]
        folder.parent.mkdir(parents=True)
        shutil.copytree(project.theme, folder)
        for name in ("Adventure", "Homebrew", "Nintendo DS", "Puzzle"):
            (sd / "roms" / name).mkdir(parents=True)
        (sd / "_nds/dsi-frontend/state.ini").write_text(
            "version=1\ntheme_id=" + project.data["id"] + "\ncategory=1\n"
        )
        args = [str(executable), str(sd), str(root / "preview"), "1"]
        if sample == "settings":
            args.append("settings")
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=60,
            env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"),
        )
        if result.returncode:
            raise ValueError(
                result.stderr.decode(errors="replace")[:2000]
                or "Native preview rejected the package."
            )
        image = Image.new("RGB", (256, 396), "#11151c")
        for name, y in (("top", 0), ("bottom", 204)):
            with Image.open(root / f"preview-{name}.ppm") as source:
                image.paste(source, (0, y))
        return image
