#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build original illustrated themes and refresh the three starter themes.
Artwork comes from source/art; geometry, music and cues are authored here.
"""

import argparse
import configparser
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import wave

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, ImageStat
from theme_finishing import finish, parchment_coverage
from theme_materials import component_skin
from theme_icons import prepare_icons
from theme_typography import prepare_fonts

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "aerial": dict(
        name="Aerial",
        subtitle="Cloud study",
        colors=[
            "#e5ebef",
            "#f6f9fa",
            "#95a8b5",
            "#172d3d",
            "#4a626f",
            "#285a79",
            "#ffffff",
        ],
        layout="scene",
        tabs="icons",
        view="extended",
        opacity=74,
        radius=7,
        bpm=80,
        notes=[62, 66, 69, 73],
        description="Pearl glass, floating clouds and restrained blue enamel. Soft electric-piano chords and rounded glass cues.",
    ),
    "koi": dict(
        name="Koi",
        subtitle="Still water",
        colors=[
            "#101a2a",
            "#18283c",
            "#58657a",
            "#f6eddb",
            "#bbbec7",
            "#f1a18a",
            "#291b21",
        ],
        layout="sidebar_left",
        tabs="labels",
        view="classic",
        opacity=46,
        radius=2,
        bpm=64,
        notes=[57, 60, 64, 67],
        description="Vermilion koi in ink-blue water, lacquer edges and ivory pictograms. A sparse plucked pentatonic phrase with a quiet water-like bed.",
    ),
    "vesper": dict(
        name="Vesper",
        subtitle="The velvet hour",
        colors=[
            "#201723",
            "#342436",
            "#79606d",
            "#f8edda",
            "#c7b4bf",
            "#e7bd7f",
            "#291a22",
        ],
        layout="scene",
        tabs="pager",
        view="shelf",
        opacity=80,
        radius=3,
        bpm=72,
        notes=[53, 56, 60, 63],
        description="Cream moths, burgundy roses and gold on plum velvet. Chamfered brass frames, engraved symbols and a chamber-like harp loop.",
    ),
    "tidal": dict(
        name="Tidal",
        subtitle="Below the surface",
        colors=[
            "#061f2c",
            "#123746",
            "#427785",
            "#e7fcf4",
            "#a2c7cc",
            "#89e2d9",
            "#0a3038",
        ],
        layout="poster",
        tabs="icons",
        view="grid",
        opacity=48,
        radius=9,
        bpm=68,
        notes=[50, 57, 60, 64],
        description="Translucent jellyfish and deep teal water. Fluid oval controls, luminous porcelain symbols and slow bell-and-pad harmonies.",
    ),
    "morrow": dict(
        name="Morrow",
        subtitle="A slower morning",
        colors=[
            "#f3e8d7",
            "#fff6e8",
            "#b6a58d",
            "#3a3029",
            "#776249",
            "#70503a",
            "#fff7e8",
        ],
        layout="scene",
        tabs="numbered",
        view="index",
        opacity=80,
        radius=1,
        bpm=88,
        notes=[60, 64, 67, 71],
        description="Sunlit illustration behind aged ivory parchment, worn paper selections, quiet marimba and warm chord voicings.",
    ),
}
COLOR_KEYS = ("background", "surface", "line", "text", "muted", "accent", "ink")
ICONS = (
    "file folder game application audio video book text image save config archive shortcut system missing settings camera sound pictochat download-play system-menu slot1 tab-home tab-games tab-apps tab-media tab-system tab-files tab-folder"
).split()
COMPONENTS = (
    "header footer panel row-selected tab-selected card card-selected row icon-frame artwork-frame battery-empty battery-low battery-half battery-high battery-full battery-charging battery-unknown wireless-idle update-available"
).split()


def rgb(c):
    return ImageColor.getrgb(c)


def mix(a, b, t):
    return tuple(
        round(x * (1 - t) + y * t)
        for x, y in zip(
            rgb(a) if isinstance(a, str) else a, rgb(b) if isinstance(b, str) else b
        )
    )


def paper_component(name, spec):
    """Aged edges stay in the corner slices; the center stays calm behind labels."""
    colors = dict(zip(COLOR_KEYS, spec["colors"]))
    image = Image.new("RGBA", (32, 32))
    if name in ("header", "footer", "row", "icon-frame"):
        return image
    paper = Image.open(ROOT / "source/materials/morrow-parchment.png").convert("RGBA")
    image = paper.resize((32, 32), Image.Resampling.LANCZOS)
    if name in ("row-selected", "card-selected", "card"):
        parchment_coverage(image, 170, border=3, fade=3)
    d = ImageDraw.Draw(image)
    if name in ("row-selected", "card-selected", "card", "panel"):
        average = tuple(
            round(value)
            for value in ImageStat.Stat(image.crop((8, 8, 24, 24)).convert("RGB")).mean
        )
        pixels = image.load()
        for y in range(6, 26):
            for x in range(6, 26):
                pixels[x, y] = average + (pixels[x, y][3],)
    if name in ("row-selected", "card-selected"):
        d.polygon([(26, 2), (30, 6), (26, 6)], fill="#c6b58a")
    if name == "tab-selected":
        d.rectangle((4, 4, 27, 27), fill=colors["accent"])
    if name == "artwork-frame":
        d.rectangle((4, 4, 27, 27), fill=(0, 0, 0, 0))
    return image


def component(name, spec):
    c = dict(zip(COLOR_KEYS, spec["colors"]))
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    if name.startswith("battery-"):
        d.rounded_rectangle((2, 8, 27, 24), radius=3, outline=c["text"], width=2)
        d.rectangle((28, 13, 30, 19), fill=c["text"])
        bars = {"empty": 0, "low": 1, "half": 2, "high": 3, "full": 4}.get(name[8:], 0)
        for i in range(bars):
            d.rounded_rectangle(
                (5 + i * 5, 11, 8 + i * 5, 21), radius=1, fill=c["accent"]
            )
        if name.endswith("charging"):
            d.polygon(
                [(16, 9), (10, 18), (15, 18), (12, 23), (21, 14), (16, 14)],
                fill=c["accent"],
            )
        if name.endswith("unknown"):
            d.line([(12, 12), (17, 12), (17, 15), (14, 17)], fill=c["muted"], width=2)
            d.point((14, 20), fill=c["muted"])
        return im
    if name == "wireless-idle":
        for inset in (0, 6):
            d.arc(
                (2 + inset, 5 + inset, 30 - inset, 33 - inset),
                220,
                320,
                fill=c["muted"],
                width=2,
            )
        d.ellipse((14, 23, 18, 27), fill=c["muted"])
        return im
    if name == "update-available":
        d.ellipse((3, 3, 29, 29), fill=c["accent"])
        d.line((16, 24, 16, 9), fill=c["ink"], width=3)
        d.line([(10, 15), (16, 9), (22, 15)], fill=c["ink"], width=3)
        return im
    if spec["name"] == "Morrow":
        return paper_component(name, spec)
    return component_skin(spec["name"].lower(), name, c)


def audio(spec, folder):
    rate = 16000
    beat = 60 / spec["bpm"]
    length = 16 * beat
    n = round(length * rate)
    out = np.zeros(n)
    rng = np.random.default_rng(20261114 + spec["bpm"])

    def add_note(midi, start, duration, amp, voice):
        count = round(duration * rate)
        t = np.arange(count) / rate
        f = 440 * 2 ** ((midi - 69) / 12)
        if voice == "pluck":
            s = (
                np.sin(2 * np.pi * f * t)
                + 0.25 * np.sin(2 * np.pi * f * 2 * t)
                + 0.10 * np.sin(2 * np.pi * f * 3 * t)
            )
            env = (1 - np.exp(-t * 180)) * np.exp(-t * 2.4)
        elif voice == "bell":
            s = (
                np.sin(2 * np.pi * f * t)
                + 0.28 * np.sin(2 * np.pi * f * 2.01 * t)
                + 0.08 * np.sin(2 * np.pi * f * 4 * t)
            )
            env = (1 - np.exp(-t * 250)) * np.exp(-t * 1.7)
        else:
            s = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * f * 2 * t)
            env = np.sin(np.pi * np.minimum(t / duration, 1)) ** 2
        wavelet = amp * s * env * np.minimum(1, (duration - t) * 12)
        indices = (round(start * rate) + np.arange(count)) % n
        np.add.at(out, indices, wavelet)
        # Circular delay preserves reverb tails at the loop boundary.
        for delay, gain in ((0.23, 0.18), (0.47, 0.08)):
            np.add.at(out, (indices + round(delay * rate)) % n, wavelet * gain)

    root = spec["notes"][0]
    progressions = {
        "Aerial": [0, 5, 9, 7],
        "Koi": [0, 0, 5, 7],
        "Vesper": [0, 8, 5, 7],
        "Tidal": [0, 3, 8, 5],
        "Morrow": [0, 5, 7, 0],
        "BUUF": [0, 3, 5, 7],
    }
    melody = {
        "Aerial": [0, 2, 3, 1, 2, 1, 3, 2],
        "Koi": [0, 2, 1, 3, 2, 0, 1, 2],
        "Vesper": [3, 2, 1, 0, 2, 3, 1, 0],
        "Tidal": [2, 3, 1, 2, 0, 1, 3, 2],
        "Morrow": [0, 1, 2, 3, 2, 1, 3, 0],
        "BUUF": [0, 2, 1, 3, 2, 1, 0, 2],
    }[spec["name"]]
    for bar, shift in enumerate(progressions[spec["name"]]):
        for interval in (0, 7, 14):
            add_note(
                root - 12 + shift + interval, bar * 4 * beat, 4.6 * beat, 0.055, "pad"
            )
        for j in range(4 if spec["name"] == "Koi" else 8):
            start = (bar * 4 + j * (1 if spec["name"] == "Koi" else 0.5)) * beat
            note = spec["notes"][melody[(j + (2 if bar >= 2 else 0)) % 8]] + (
                12 if spec["name"] in ("Tidal", "Vesper") else 0
            )
            add_note(
                note,
                start,
                2.5 * beat,
                0.13 if j % 2 == 0 else 0.08,
                "bell" if spec["name"] in ("Aerial", "Tidal") else "pluck",
            )
    out *= 0.66 / max(1, np.max(np.abs(out)))

    def write(name, data):
        with wave.open(str(folder / name), "wb") as w:
            w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            w.writeframes(
                np.clip(np.rint(data * 32767), -32767, 32767).astype("<i2").tobytes()
            )

    write("loop.wav", out)
    for name, tones, duration in [
        ("cursor", [root + 24], 0.065),
        ("confirm", [root + 24, root + 31], 0.24),
        ("back", [root + 24, root + 19], 0.18),
    ]:
        t = np.arange(round(rate * duration)) / rate
        cue = np.zeros_like(t)
        for i, note in enumerate(tones):
            v = t - i * 0.065
            active = v >= 0
            f = 440 * 2 ** ((note - 69) / 12)
            cue += np.where(
                active,
                0.18
                * np.sin(2 * np.pi * f * v)
                * np.exp(-np.maximum(v, 0) * 28)
                * np.minimum(np.maximum(v, 0) * 500, 1),
                0,
            )
        cue *= np.minimum(1, (duration - t) * 100)
        write(name + ".wav", cue)
    return round(length, 2)


def build(id):
    spec = SPECS[id]
    p = ROOT / "themes" / id
    for sub in ("backgrounds", "icons", "components", "sounds", "fonts"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    art = ImageOps.fit(
        Image.open(ROOT / "source/art" / f"{id}.png").convert("RGB"),
        (256, 192),
        method=Image.Resampling.LANCZOS,
    )
    art.save(p / "backgrounds/top.png", optimize=True)
    # A cohesive secondary surface, with the image subdued for long browser rows.
    tone = Image.new("RGB", (256, 192), spec["colors"][0])
    bottom = Image.blend(art, tone, 0.18)
    bottom.save(p / "backgrounds/bottom.png", optimize=True)
    for name in COMPONENTS:
        component(name, spec).save(p / "components" / f"{name}.png", optimize=True)
    length = audio(spec, p / "sounds")
    config = configparser.ConfigParser()
    config.optionxform = str
    config["theme"] = {"version": "1", "name": spec["name"], "header": spec["name"]}
    config["colors"] = dict(zip(COLOR_KEYS, spec["colors"]))
    config["fonts"] = {"ui": "fonts/ui.dsfont"}
    config["layout"] = {
        "top_layout": spec["layout"],
        "chrome": "minimal",
        "content_opacity": str(spec["opacity"]),
        "tab_style": spec["tabs"],
        "tab_highlight": "skin" if spec["tabs"] == "labels" else "underline",
        "tab_visible": "5" if spec["tabs"] == "icons" else "3",
        "tab_gap": "4",
        "view": spec["view"],
        "icon_size": "large",
        "row_padding": "2",
        "large_grid_columns": "3",
    }
    if spec["layout"] == "scene":
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
    }
    config["icons"] = {"directory": "icons"}
    config["components"] = {"directory": "components", "border": "6"}
    config["audio"] = {
        "music": "sounds/loop.wav",
        "cursor": "sounds/cursor.wav",
        "confirm": "sounds/confirm.wav",
        "back": "sounds/back.wav",
    }
    with (p / "theme.ini").open("w") as f:
        config.write(f, space_around_delimiters=False)
    return length


# Faces are deliberately different; body line height stays 12 so every browser,
# settings row and touch target retains its geometry. Values are size/baseline/height.
PROFILES = {
    "aerial": dict(
        layout="spotlight",
        tabs="icons",
        position="bottom",
        body=("DejaVuSans", 10, 10, 12),
        heading=("DejaVuSans", 13, 12, 15),
    ),
    "koi": dict(
        layout="gallery",
        tabs="labels",
        position="top",
        body=("DejaVuSans-Bold", 10, 10, 12),
        heading=("DejaVuSerif", 13, 12, 15),
    ),
    "vesper": dict(
        layout="scene",
        tabs="pager",
        body=("DejaVuSerif", 10, 9, 12),
        heading=("DejaVuSerif", 14, 13, 16),
    ),
    "tidal": dict(
        layout="poster",
        tabs="icons",
        body=("DejaVuSans", 10, 10, 12),
        heading=("DejaVuSans", 12, 12, 15),
    ),
    "morrow": dict(
        layout="journal",
        tabs="numbered",
        position="bottom",
        body=("DejaVuSerif", 10, 9, 12),
        heading=("DejaVuSerif-Italic", 12, 12, 15),
    ),
    "slate": dict(
        layout="sidebar_left",
        tabs="icons",
        body=("DejaVuSans", 10, 10, 12),
        heading=("DejaVuSans-Bold", 13, 12, 15),
    ),
    "folio": dict(
        layout="journal",
        tabs="labels",
        position="top",
        body=("DejaVuSerif", 10, 9, 12),
        heading=("DejaVuSerif", 14, 13, 16),
    ),
    "phosphor": dict(
        layout="sidebar",
        tabs="numbered",
        body=("DejaVuSansMono", 10, 9, 12),
        heading=("DejaVuSansMono", 13, 12, 16),
    ),
}


PROFILES["buuf"] = dict(layout="gallery", tabs="icons", position="bottom")

# The manifest keeps immutable OFL source pins and exact native glyph metrics.
_FONT_ROLES = json.loads((ROOT / "config/theme-fonts.json").read_text())["themes"]
for _id, _roles in _FONT_ROLES.items():
    if _id in PROFILES:
        for _role, _spec in _roles.items():
            PROFILES[_id][_role] = (
                _spec["family"],
                _spec["size"],
                _spec["baseline"],
                _spec["height"],
            )


def load_tool(path, name):
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def refresh_style(id, gloam, font_dir, download_fonts=False):
    """Use Gloam's authoritative font packer; do not duplicate its binary format."""
    profile = PROFILES[id]
    folder = ROOT / "themes" / id
    config = configparser.ConfigParser()
    config.read(folder / "theme.ini")
    config["theme"]["version"] = "2"
    layout = config["layout"]
    layout.update(
        top_layout=profile["layout"],
        tab_style=profile["tabs"],
    )
    if "position" in profile:
        layout["tabs_position"] = profile["position"]
    elif "tabs_position" in layout:
        del layout["tabs_position"]
    if id == "phosphor":
        config["theme"]["header"] = "Phosphor"
    if id == "morrow":
        # Library index remains a personal option; start with the illustrated journal.
        layout["view"] = "extended"
    config["components"]["alpha"] = "coverage"
    if id != "morrow":
        # All seven families use local materials; status glyphs share the same
        # clear battery/wireless language as the illustrated packs.
        status_spec = {
            "name": id.title(),
            "colors": [config["colors"][key] for key in COLOR_KEYS],
            "radius": 1,
        }
        for name in COMPONENTS:
            image = component_skin(id, name, config["colors"])
            if image is None:
                image = component(name, status_spec)
            image.save(folder / "components" / f"{name}.png", optimize=True)
        config["components"]["border"] = "6"
        layout.update(chrome="minimal", tab_highlight="skin")
        if id == "slate":
            layout.update(view="extended", icon_size="small", row_padding="2")
        if id == "folio":
            layout.update(view="list", row_padding="2", tab_highlight="underline")
        if id == "phosphor":
            layout.update(view="classic", row_padding="2", tab_highlight="outline")
    packer = load_tool(gloam / "tools/pack_theme_font.py", "gloam_font_packer")
    (folder / "fonts").mkdir(exist_ok=True)
    font_notes = prepare_fonts(id, folder, packer, profile, font_dir, download_fonts)
    for role, filename in (("body", "ui"), ("heading", "heading")):
        config["fonts"][filename] = f"fonts/{filename}.dsfont"
    prepare_icons(id, folder)
    credits = (folder / "CREDITS.md").read_text()
    # Replace the previous generated font paragraph without losing asset provenance.
    start = credits.find("Font: DejaVu")
    if start >= 0:
        end = credits.index("Configuration, tools", start)
        credits = credits[:start] + credits[end:]
    credits = credits.replace(
        "Uses the built-in font, illustrated wallpapers and UI sounds; no background music is included.",
        "Illustrated wallpapers and UI sounds; no background music is included.",
    )
    credits = credits.split("\n## Version 2 treatment")[0].rstrip()
    credits += "\n\n## Version 2 treatment\n\n"
    credits += (
        "Updated layout, material coverage and fonts are generated by "
        "`tools/build_collection.py` and `tools/theme_finishing.py` in this repository. "
        "The latter also authors the controls and ambient accents. Fonts use Gloam's "
        "DSFONT03 converter, four grayscale coverage levels and independent "
        "body/heading faces. Original font notices remain in `fonts/LICENSE.txt`;\n"
        "OFL source pins are in `config/theme-fonts.json`. Morrow retains its DejaVu pairing.\n\n"
    )
    if id != "morrow":
        credits += (
            "Material shapes and control silhouettes: `tools/theme_materials.py`.\n\n"
        )
    credits += (
        "Independent illustrated icon masters: `source/art/" + id + "-icons.png`.\n"
    )
    credits += "Full-image materials and individual focus skins: `tools/collection_surfaces.py`; no repeated patches.\n\n"
    credits += "\n".join(font_notes) + "\n"
    (folder / "CREDITS.md").write_text(credits)
    asset_packer = load_tool(gloam / "tools/pack_theme_assets.py", "gloam_asset_packer")
    finish(id, folder, config, asset_packer)
    out = io.StringIO()
    config.write(out, space_around_delimiters=False)
    (folder / "theme.ini").write_text(out.getvalue().rstrip() + "\n")
    (folder / "assets.gfx").write_bytes(asset_packer.pack(folder))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gloam",
        type=Path,
        required=True,
        help="Matching Gloam checkout, for the authoritative font and sprite packers",
    )
    parser.add_argument(
        "--font-dir", type=Path, required=True, help="DejaVu TTF directory"
    )
    parser.add_argument("--theme", choices=PROFILES)
    parser.add_argument(
        "--download-fonts",
        action="store_true",
        help="Fetch verified OFL authoring inputs",
    )
    args = parser.parse_args()
    for id in ([args.theme] if args.theme else PROFILES):
        if id == "buuf":
            from buuf_theme import build_buuf

            build_buuf(
                args.gloam,
                args.font_dir,
                PROFILES[id],
                load_tool,
                audio,
                args.download_fonts,
            )
            print(id)
            continue
        if id in SPECS:
            build(id)
        refresh_style(id, args.gloam, args.font_dir, args.download_fonts)
        print(id)


if __name__ == "__main__":
    main()
