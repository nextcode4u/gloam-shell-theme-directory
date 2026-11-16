#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare seven original desktop/device themes using Gloam's native packers.

Artwork masters live in source/art; recipes in config/inspired-themes.json.
Recorded music is pinned and rebuilt separately by prepare_theme_music.py.
"""

import argparse
import configparser
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from build_collection import load_tool
from theme_icons import CELLS, native_icon
from theme_typography import prepare_fonts
from build_theme_splashes import build_theme
from inspired_assets import (
    ROOT,
    SPECS,
    KEYS,
    COMPONENTS,
    color,
    material,
    skin,
    control,
    ambient,
    cues,
)


def update_font_manifest(gloam):
    path = ROOT / "config/theme-fonts.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    upstream = json.loads(
        (gloam / "config/theme-fonts.json").read_text(encoding="utf-8")
    )
    for theme, s in SPECS.items():
        roles = {}
        for role in ("body", "heading"):
            family = s[role]
            if family not in m["faces"]:
                m["faces"][family] = upstream["faces"][family]
            existing = next(
                (
                    dict(settings)
                    for theme_roles in m["themes"].values()
                    for settings in theme_roles.values()
                    if settings["family"] == family
                ),
                {"family": family},
            )
            existing.update(
                size=11 if role == "body" else 14,
                baseline=10 if role == "body" else 14,
                height=12 if role == "body" else 16,
                edge_shift=2,
            )
            roles[role] = existing
        m["themes"][theme] = roles
    path.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")


def build(theme, gloam, font_dir, download):
    s = SPECS[theme]
    sources = json.loads(
        (ROOT / "config/inspired-art.json").read_text(encoding="utf-8")
    )["sources"]
    for name in (theme + ".png", theme + "-icons.png"):
        relative = "source/art/" + name
        if (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            != sources[relative]["sha256"]
        ):
            raise ValueError(
                "Artwork changed; review its source manifest before rebuilding: "
                + relative
            )
    folder = ROOT / "themes" / theme
    for part in ("backgrounds", "components", "icons", "fonts", "sounds", "motion"):
        (folder / part).mkdir(parents=True, exist_ok=True)
    with Image.open(ROOT / "source/art" / (theme + ".png")) as source:
        art = ImageOps.fit(
            source.convert("RGB"), (256, 192), method=Image.Resampling.LANCZOS
        )
    art.save(folder / "backgrounds/top.png", optimize=True)
    bottom = Image.blend(art, Image.new("RGB", art.size, s["colors"][0]), 0.14)
    bottom.save(folder / "backgrounds/bottom.png", optimize=True)
    with Image.open(ROOT / "source/art" / (theme + "-icons.png")) as source:
        if source.width < 256 or source.height < 256:
            raise ValueError("The 4x4 source atlas needs at least 64px per cell")
        # Transparent exports can trim a few outer pixels. Partition each axis
        # independently so no icon is stretched or clipped to a square atlas.
        for name, index in CELLS.items():
            column, row = index % 4, index // 4
            bounds = (
                round(column * source.width / 4),
                round(row * source.height / 4),
                round((column + 1) * source.width / 4),
                round((row + 1) * source.height / 4),
            )
            icon = native_icon(source.crop(bounds))
            if name == "missing":
                ImageDraw.Draw(icon).line((21, 21, 29, 29), fill="#bd3b40", width=3)
            icon.save(folder / "icons" / (name + ".png"), optimize=True)
    colors = dict(zip(KEYS, s["colors"]))
    for name in COMPONENTS:
        image = skin(theme, name) if name in COMPONENTS[:10] else control(theme, name)
        image.save(folder / "components" / (name + ".png"), optimize=True)
    for index, screen in enumerate(("top", "bottom")):
        surface = Image.new(
            "RGBA", (256, 192), color(colors["surface"], s["opacity"][index])
        )
        surface.save(
            folder / "backgrounds" / ("material-" + screen + ".png"), optimize=True
        )
    for focused, name in ((False, "material"), (True, "focus-material")):
        material(theme, focused).save(
            folder / "components" / (name + ".png"), optimize=True
        )
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config["theme"] = {"version": "2", "name": s["name"], "header": s["name"]}
    config["colors"] = colors | {
        "selection_text": colors["ink"],
        "tab_text": colors["ink"],
    }
    config["fonts"] = {"ui": "fonts/ui.dsfont", "heading": "fonts/heading.dsfont"}
    config["layout"] = {
        "top_layout": s["layout"],
        "chrome": s.get("chrome", "full"),
        "content_opacity": "100",
        "top_content_opacity": "100",
        "bottom_content_opacity": "100",
        "tab_style": s["tabs"],
        "tab_highlight": "skin",
        "tab_visible": "5" if s["tabs"] == "icons" else "3",
        "tab_gap": "4",
        "view": s["view"],
        "icon_size": s["size"],
        "row_padding": "2",
        "large_grid_columns": "3",
    }
    if "position" in s:
        config["layout"]["tabs_position"] = s["position"]
    if s["layout"] == "scene":
        config["layout"].update(
            scene_cover_x="18",
            scene_cover_y="38",
            scene_cover_width="44",
            scene_cover_height="66",
        )
    config["backgrounds"] = {
        "top": "backgrounds/top.png",
        "bottom": "backgrounds/bottom.png",
        "strength": "100",
        "top_surface": "backgrounds/material-top.png",
        "bottom_surface": "backgrounds/material-bottom.png",
    }
    config["icons"] = {"directory": "icons"}
    config["components"] = {
        "directory": "components",
        "border": "4" if theme == "desktop-98" else "6",
        "alpha": "coverage",
        "controls": "on",
        "fill": "stretch",
        "material": "components/material.png",
        "focus_material": "components/focus-material.png",
    }
    config["audio"] = {
        "music": "sounds/loop.wav",
        "cursor": "sounds/cursor.wav",
        "confirm": "sounds/confirm.wav",
        "back": "sounds/back.wav",
    }
    font_packer = load_tool(gloam / "tools/pack_theme_font.py", "inspired_font_packer")
    notes = prepare_fonts(theme, folder, font_packer, {}, font_dir, download)
    packer = load_tool(gloam / "tools/pack_theme_assets.py", "inspired_asset_packer")
    frames = [packer.sprite(ambient(theme, frame)) for frame in range(8)]
    (folder / "motion/ambient.gtm").write_bytes(
        b"GLMFX001" + bytes([8, 32, 32, 0, 0, 0, 0, 0]) + b"".join(frames)
    )
    config["motion"] = {
        "ambient": "motion/ambient.gtm",
        "ambient_ticks": "18" if theme == "aero-glass" else "12",
        "focus": "off",
    }
    config["assets"] = {"prepared": "assets.gfx"}
    with (folder / "theme.ini").open("w", encoding="utf-8") as file:
        config.write(file, space_around_delimiters=False)
    cues(theme, folder / "sounds")
    (folder / "assets.gfx").write_bytes(packer.pack(folder))
    (folder / "splash.gsp").write_bytes(
        build_theme(ROOT, folder, font_dir=font_dir, download=download)
    )
    credit = (
        f"""# {s['name']} — credits

Original Gloam interpretation of {s['inspiration']}, by nextcode4u / Gloam project
(agent-assisted). {s['description']}

## Artwork and controls

Wallpaper and icon masters in `source/art/{theme}.png` and
`source/art/{theme}-icons.png` are original agent-assisted illustrations.
Frames, material maps, status/control assets, ambient animation, UI cues and the
startup splash are prepared by `tools/build_inspired_collection.py` and the
shared splash converter. Project-held rights in this original artwork and
original UI audio are dedicated under CC0-1.0:
https://creativecommons.org/publicdomain/zero/1.0/

This is an unofficial fan-inspired design. Windows/Microsoft, Nintendo,
Pokémon and Rick and Morty names and marks remain with their respective owners;
no affiliation or endorsement is implied. No extracted wallpapers, official
icons, character sprites, television clips, startup sounds or franchise music
are included. The CC0 dedication covers project-held rights only.

## Fonts

"""
        + "\n".join(notes)
        + """

Full original font notices are in `fonts/LICENSE.txt`. Font source revisions and
hashes are pinned in `config/theme-fonts.json`; font licenses are separate from
project artwork. Configuration and authoring tools use GPL-3.0-or-later.

## Recorded music

See MUSIC.md for the credited Kevin MacLeod track, source and loop adaptations.
Music uses CC-BY-4.0; the full license is in MUSIC-LICENSE.txt. Music is never
replaced by the original UI-cue generator.

## Startup splash

The short two-screen `splash.gsp` uses this pack's artwork and typefaces with
bounded motion; choose Startup splash → Theme in Gloam. Any button skips;
Reduced motion uses a still frame. The pack adds no splash audio.
"""
    )
    (folder / "CREDITS.md").write_text(credit, encoding="utf-8")
    (folder / "README.md").write_text(
        f"""# {s['name']}

{s['description']}

![Two-screen renderer preview](preview.png)

[Home preview](home-preview.png) · [Settings preview](settings-preview.png)

## Install

Requires **Gloam 1.1.0 or later**. Copy this whole folder to
`/_nds/dsi-frontend/themes/{theme}/`. Open START → Appearance → Theme:
Up/Down selects, X previews and A applies when ready. Existing personal view,
wallpaper or accent overrides can alter the supplied defaults.

Defaults: {s['layout'].title()} top composition, {s['view'].title()} browser,
{s['size']} icons and {s['tabs']} tabs. Native DS/DSi banner icons keep priority;
theme file/system/category icons cover other entries. Both reading surfaces,
all control skins, eight ambient frames, body/heading fonts, three UI cues,
recorded music and a startup splash are included. Reduced motion is respected.

See [credits](CREDITS.md), [music attribution](MUSIC.md) and original notices.
Illustrations interpret {s['inspiration']}; this is not an official theme.
Previews use the current Gloam source with selection-ink fixes for menus and
settings. The original 1.1.0 binary accepts the pack format but lacks those fixes.
These are renderer captures, not photographs of a DSi LCD.
""",
        encoding="utf-8",
    )
    print(
        theme,
        "prepared",
        len((folder / "assets.gfx").read_bytes()),
        "graphics bytes",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gloam", type=Path, required=True)
    parser.add_argument("--download-fonts", action="store_true")
    parser.add_argument(
        "--font-dir", type=Path, default=Path("/usr/share/fonts/truetype/dejavu")
    )
    parser.add_argument("--only", choices=tuple(SPECS), nargs="+")
    args = parser.parse_args()
    update_font_manifest(args.gloam)
    for theme in args.only or SPECS:
        build(theme, args.gloam, args.font_dir, args.download_fonts)


if __name__ == "__main__":
    main()
