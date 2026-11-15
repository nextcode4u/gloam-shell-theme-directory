# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the credited BUUF adaptation from pinned, unmodified upstream icons."""

import configparser
import hashlib
import io
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageColor
from collection_surfaces import focus_skin, prepare_materials, tint
from theme_icons import CELLS, native_icon
from theme_typography import prepare_fonts

ROOT = Path(__file__).resolve().parents[1]
COLORS = dict(
    zip(
        ("background", "surface", "line", "text", "muted", "accent", "ink"),
        ("#e7d9b8", "#f1e7cb", "#a38b63", "#332c23", "#66533b", "#50613c", "#fff1d4"),
    )
)
BASE_COMPONENTS = "header footer panel row-selected tab-selected card card-selected row icon-frame artwork-frame battery-empty battery-low battery-half battery-high battery-full battery-charging battery-unknown wireless-idle update-available".split()
CONTROLS = "check-off check-on toggle-off toggle-on arrow-left arrow-right arrow-up arrow-down scroll-track scroll-thumb busy".split()


def sources():
    directory = ROOT / "source/buuf"
    manifest = json.loads((directory / "UPSTREAM.json").read_text())
    for name, record in manifest["files"].items():
        if (
            hashlib.sha256((directory / "icons" / name).read_bytes()).hexdigest()
            != record["sha256"]
        ):
            raise ValueError("BUUF source hash mismatch: " + name)
    if (
        hashlib.sha256((directory / "LICENSE.md").read_bytes()).hexdigest()
        != manifest["license_sha256"]
    ):
        raise ValueError("BUUF license hash mismatch")
    return directory, manifest


def control(name, directory, manifest):
    if name in manifest["controls"]:
        image = native_icon(
            Image.open(directory / "icons" / manifest["controls"][name])
        )
        draw = ImageDraw.Draw(image)
        if name == "check-on":
            draw.line(((9, 16), (14, 21), (24, 10)), fill="#fff5d7", width=3)
        elif name == "wireless-idle":
            draw.ellipse((21, 20, 31, 30), fill="#8f3d30", outline="#f2dfbb")
            draw.line((24, 23, 28, 27), fill="#fff1d4", width=2)
            draw.line((28, 23, 24, 27), fill="#fff1d4", width=2)
        elif name == "battery-unknown":
            draw.line(((12, 11), (18, 11), (19, 14), (15, 18)), fill="#fff4dc", width=2)
            draw.rectangle((14, 21, 16, 23), fill="#fff4dc")
        return image
    if name in ("arrow-up", "arrow-down"):
        return control("arrow-right", directory, manifest).rotate(
            90 if name == "arrow-up" else 270
        )
    # Draw the remaining small controls at 4x, keeping soft inked silhouettes.
    image = Image.new("RGBA", (128, 128))
    draw = ImageDraw.Draw(image)
    if name.startswith("toggle-"):
        on = name.endswith("on")
        draw.rounded_rectangle((4, 29, 123, 99), radius=30, fill="#3b3328")
        draw.rounded_rectangle(
            (9, 34, 118, 94), radius=26, fill="#8eaa65" if on else "#b39a76"
        )
        x = 63 if on else 13
        draw.ellipse((x + 2, 39, x + 46, 89), fill="#6d573a")
        draw.ellipse((x, 35, x + 44, 85), fill="#f0dfb9", outline="#514332", width=4)
        draw.arc((x + 6, 40, x + 38, 77), 190, 285, fill="#fff4db", width=3)
    elif name.startswith("scroll-"):
        thumb = name.endswith("thumb")
        draw.rounded_rectangle(
            (12, 1, 115, 126), radius=12, fill="#53442e" if thumb else "#bca985"
        )
        draw.rounded_rectangle(
            (18, 6, 108, 120), radius=9, fill="#a6b67d" if thumb else "#d7c6a0"
        )
        if thumb:
            for y in (54, 65, 76):
                draw.line((42, y, 84, y - 2), fill="#665b3e", width=3)
    elif name == "busy":
        return native_icon(Image.open(directory / "icons/wheel-buuf.png"))
    return image.resize((32, 32), Image.Resampling.LANCZOS)


def component(name, directory, manifest):
    if name in manifest["controls"] or name in CONTROLS:
        return control(name, directory, manifest)
    if name in ("row-selected", "card-selected", "tab-selected"):
        return focus_skin("buuf", COLORS)
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    if name in ("card", "panel"):
        draw.polygon(
            ((2, 0), (28, 1), (31, 4), (30, 29), (27, 31), (1, 30), (0, 26), (1, 4)),
            fill="#9e805b",
        )
        draw.polygon(
            ((3, 2), (27, 3), (29, 5), (28, 28), (26, 29), (3, 28), (2, 25), (3, 5)),
            fill=(
                *ImageColor.getrgb(COLORS["surface"]),
                170 if name == "card" else 255,
            ),
        )
    elif name in ("icon-frame", "artwork-frame"):
        draw.rounded_rectangle((0, 0, 31, 31), radius=4, outline="#8b6c49", width=2)
        draw.line((4, 2, 26, 2), fill="#f4e8c9")
        draw.line((2, 5, 2, 26), fill="#b9a17b")
    elif name in ("row", "header", "footer"):
        draw.line((1, 30, 30, 30), fill=(120, 98, 68, 85))
    return image


def build_buuf(gloam, font_dir, profile, load_tool, compose_audio, download=False):
    directory, manifest = sources()
    folder = ROOT / "themes/buuf"
    for name in ("icons", "components", "backgrounds", "fonts", "sounds", "motion"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config.read_dict(
        {
            "theme": {"version": "2", "name": "BUUF", "header": "BUUF"},
            "colors": COLORS,
            "fonts": {"ui": "fonts/ui.dsfont", "heading": "fonts/heading.dsfont"},
            "layout": {
                "top_layout": profile["layout"],
                "chrome": "minimal",
                "tab_style": "icons",
                "tabs_position": "bottom",
                "tab_highlight": "skin",
                "tab_visible": "3",
                "tab_gap": "4",
                "view": "extended",
                "icon_size": "large",
                "row_padding": "2",
                "top_content_opacity": "100",
                "bottom_content_opacity": "100",
            },
            "backgrounds": {
                "top": "backgrounds/top.png",
                "bottom": "backgrounds/bottom.png",
                "strength": "100",
                "top_surface": "backgrounds/material-top.png",
                "bottom_surface": "backgrounds/material-bottom.png",
            },
            "icons": {"directory": "icons"},
            "components": {
                "directory": "components",
                "border": "6",
                "alpha": "coverage",
                "controls": "on",
            },
            "audio": {
                name: "sounds/" + file + ".wav"
                for name, file in [
                    ("music", "loop"),
                    ("cursor", "cursor"),
                    ("confirm", "confirm"),
                    ("back", "back"),
                ]
            },
            "motion": {
                "ambient": "motion/ambient.gtm",
                "ambient_ticks": "18",
                "focus": "off",
            },
            "assets": {"prepared": "assets.gfx"},
        }
    )
    with Image.open(ROOT / "source/art/buuf.png") as original:
        backdrop = original.convert("RGB").resize((256, 192), Image.Resampling.LANCZOS)
    for screen in ("top", "bottom"):
        backdrop.save(folder / "backgrounds" / (screen + ".png"), optimize=True)
        # A complete image-backed reading veil; illustration stays visible beneath it.
        paper = tint("buuf", COLORS["background"], amplitude=4).convert("RGBA")
        coverage = Image.new("L", paper.size, 85 if screen == "top" else 100)
        # Minimal chrome omits the footer component. Keep the legend readable
        # through the full-screen reading surface, above the dark leather edge.
        ImageDraw.Draw(coverage).rectangle((0, 174, 255, 191), fill=255)
        paper.putalpha(coverage)
        ImageDraw.Draw(paper).line(
            (8, 174, 247, 174), fill=(*ImageColor.getrgb(COLORS["line"]), 255)
        )
        paper.save(
            folder / "backgrounds" / ("material-" + screen + ".png"), optimize=True
        )
    for kind, cell in CELLS.items():
        icon = native_icon(Image.open(directory / "icons" / manifest["icons"][cell]))
        if kind == "missing":
            draw = ImageDraw.Draw(icon)
            draw.ellipse((20, 20, 31, 31), fill="#984932", outline="#fff1d4")
            draw.line((23, 23, 28, 28), fill="#fff1d4", width=2)
            draw.line((28, 23, 23, 28), fill="#fff1d4", width=2)
        icon.save(folder / "icons" / (kind + ".png"), optimize=True)
    for name in BASE_COMPONENTS + CONTROLS:
        component(name, directory, manifest).save(
            folder / "components" / (name + ".png"), optimize=True
        )
    prepare_materials("buuf", folder, config)
    packer = load_tool(gloam / "tools/pack_theme_font.py", "buuf_font_packer")
    font_notes = prepare_fonts("buuf", folder, packer, profile, font_dir, download)
    compose_audio(dict(name="BUUF", bpm=78, notes=[55, 58, 62, 65]), folder / "sounds")
    packer = load_tool(gloam / "tools/pack_theme_assets.py", "buuf_asset_packer")
    gear = native_icon(Image.open(directory / "icons/wheel-buuf.png"))
    frames = []
    for frame in range(8):
        # Small cached breathing mark, no repeated SD reads and no full-screen animation.
        image = ImageEnhance.Brightness(gear).enhance(
            0.90 + 0.10 * math.cos(frame * math.pi / 4)
        )
        frames.append(packer.sprite(image))
    (folder / "motion/ambient.gtm").write_bytes(
        b"GLMFX001" + bytes([8, 32, 32, 0, 0, 0, 0, 0]) + b"".join(frames)
    )
    (folder / "BUUF-LICENSE.txt").write_bytes((directory / "LICENSE.md").read_bytes())
    (folder / "UPSTREAM.json").write_bytes((directory / "UPSTREAM.json").read_bytes())
    (folder / "CREDITS.md").write_text(
        "# BUUF credits and license\n\n"
        "**Original BUUF icons: [mattahan](https://www.deviantart.com/mattahan).**\n\n"
        "[Upstream icon theme](https://github.com/oxayotl/buuf-icon-theme), pinned at `"
        + manifest["commit"]
        + "`.\n\n"
        "Upstream credit: “" + manifest["upstream_credit"] + "”\n\n"
        "Gloam adaptation: nextcode4u / Gloam Shell NDX contributors. This is an independent adaptation, not an endorsement by the original artists.\n\n"
        "## Artwork terms\n\n"
        "BUUF icons and this adapted theme artwork use **Creative Commons Attribution–NonCommercial–ShareAlike 2.5**. "
        "Keep these credits and `BUUF-LICENSE.txt` with copies. Commercial use is not granted; distribute artwork adaptations under the same terms. "
        "[License description](https://creativecommons.org/licenses/by-nc-sa/2.5/).\n\n"
        "Original source PNGs are retained unchanged in `source/buuf/icons/`; `UPSTREAM.json` records their paths and SHA-256 hashes. "
        "Runtime adaptations trim transparent margins, resize icons, rotate arrows, add checkbox/disconnected/unknown marks and gently vary the ambient gear brightness. "
        "The paper/leather illustration and green paper-label skins are new supporting artwork by the Gloam project (agent-assisted), also offered under CC-BY-NC-SA-2.5 in this pack. "
        "They are not claimed as mattahan’s artwork.\n\n"
        "## Independent components\n\n"
        "Public Sans and Delius retain SIL Open Font License 1.1; full notices are in `fonts/LICENSE.txt`.\n"
        + "\n".join(font_notes)
        + "\n\n"
        "Original synthesized UI cues are CC0-1.0. Background music is separately licensed CC-BY-4.0; see MUSIC.md and MUSIC-LICENSE.txt. "
        "Configuration and build tools use GPL-3.0-or-later. These separate licenses do not relicense BUUF artwork.\n"
    )
    music = json.loads((ROOT / "config/theme-music.json").read_text())["themes"]["buuf"]
    with (folder / "CREDITS.md").open("a") as credits:
        credits.write(
            "\nBackground music: “"
            + music["title"]
            + "” by Kevin MacLeod (incompetech.com), CC-BY-4.0; "
            "[source and adaptations](MUSIC.md).\n"
        )
    output = io.StringIO()
    config.write(output, space_around_delimiters=False)
    (folder / "theme.ini").write_text(output.getvalue().rstrip() + "\n")
    (folder / "assets.gfx").write_bytes(packer.pack(folder))
