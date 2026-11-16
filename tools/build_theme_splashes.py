#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Author short theme intros from existing, credited artwork and pinned fonts.

Only splash.gsp is installed. Intermediate images stay in a temporary directory.
The player animates three single-frame layers, rather than decoding a movie.
"""

from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path
import tempfile

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

import pack_splash
from theme_font_sources import verified_source

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "luna": ("fade", "slide-up", "#e5effa", "#2157b5"),
    "desktop-98": ("none", "reveal", "#c0c0c0", "#000080"),
    "classic-ds": ("fade", "fade", "#f0f2f1", "#35434d"),
    "portal-terminal": ("reveal", "fade-zoom", "#182e2c", "#c8f970"),
    "aero-glass": ("fade", "zoom-out", "#d6e9ef", "#285873"),
    "pokedex": ("reveal-down", "slide-left", "#e8f2dd", "#245d60"),
    "synthwave": ("fade", "slide-up", "#272540", "#ffb99f"),
    "aerial": ("fade", "slide-up", "#eaf1f4", "#263a55"),
    "buuf": ("fade", "zoom-out", "#ede0bc", "#603c25"),
    "copper": ("fade", "reveal", "#172b2b", "#f5d39b"),
    "eclipse": ("fade", "fade-zoom", "#211d37", "#e8d4f3"),
    "ember": ("fade", "slide-up", "#372322", "#ffdfae"),
    "folio": ("fade", "reveal", "#e9e3c9", "#3d573b"),
    "garnet": ("reveal-down", "fade", "#2e1927", "#f7ddbd"),
    "glacier": ("fade", "zoom-out", "#deedf0", "#244c60"),
    "koi": ("fade", "slide-right", "#152e3e", "#f6d6b5"),
    "morrow": ("fade", "reveal", "#efe4cb", "#68482d"),
    "nocturne": ("fade", "fade-zoom", "#262741", "#ffe3b6"),
    "phosphor": ("reveal-down", "reveal", "#0e2821", "#b9efb3"),
    "prism": ("reveal", "slide-left", "#f6efdf", "#a21459"),
    "slate": ("fade", "slide-up", "#25323d", "#d6e7ec"),
    "tidal": ("fade", "slide-up", "#0a343c", "#cef4ec"),
    "tide": ("fade", "slide-right", "#f0e4ce", "#29596b"),
    "vesper": ("reveal-down", "fade", "#301e33", "#eed5b0"),
}


def font_source(repo: Path, theme: str, download: bool, font_dir: Path, role="heading"):
    if theme == "morrow":
        # The approved Morrow heading already uses this face and ships its notice.
        return (
            font_dir
            / ("DejaVuSerif-Italic.ttf" if role == "heading" else "DejaVuSans.ttf"),
            None,
        )
    manifest = json.loads(
        (repo / "config/theme-fonts.json").read_text(encoding="utf-8")
    )
    spec = manifest["themes"][theme][role]
    family = spec["family"]
    path = verified_source(
        family,
        "font",
        manifest["faces"][family]["font"],
        download=download,
        cache=repo / "build/theme-font-sources",
    )
    return path, spec.get("weight")


def face(path: Path, size: int, weight=None):
    result = ImageFont.truetype(str(path), size)
    if weight is not None:
        try:
            axes = result.get_variation_axes()
        except OSError:  # Fixed-weight OFL faces have no variation axes.
            axes = []
        if axes:
            result.set_variation_by_axes(
                [
                    (
                        min(axis["maximum"], max(axis["minimum"], weight))
                        if axis["name"] == b"Weight"
                        else axis["default"]
                    )
                    for axis in axes
                ]
            )
    return result


def title_layer(
    name: str, source: Path, weight, body_source: Path, body_weight, ink: str
) -> Image.Image:
    # Render large type directly from the source face, never enlarge DS glyphs.
    image = Image.new("RGBA", (224, 96))
    draw = ImageDraw.Draw(image)
    size = 32
    while True:
        font = face(source, size, weight)
        if draw.textbbox((0, 0), name, font=font)[2] <= 208 or size <= 18:
            break
        size -= 1
    draw.text((112, 36), name, font=font, anchor="mm", fill=ink, stroke_width=0)
    small = face(body_source, 11, body_weight)
    subtitle = "GLOAM SHELL NDX"
    width = draw.textlength(subtitle, font=small)
    draw.text(((224 - width) / 2, 66), subtitle, font=small, fill=ink)
    return image


def build_theme(repo: Path, folder: Path, *, download=False, font_dir: Path):
    config = configparser.ConfigParser(interpolation=None)
    config.read(folder / "theme.ini", encoding="utf-8")
    theme = folder.name
    intro, motion, paper, ink = PROFILES[theme]
    source, weight = font_source(repo, theme, download, font_dir)
    body_source, body_weight = font_source(repo, theme, download, font_dir, "body")
    duration = 1.2
    with tempfile.TemporaryDirectory(prefix="gloam-theme-splash-") as temporary:
        temporary = Path(temporary)
        # Whole artwork, without browser panels. The lower wash protects the title.
        for screen in ("top", "bottom"):
            with Image.open(folder / config["backgrounds"][screen]) as original:
                image = original.convert("RGB")
                if image.size != (256, 192):
                    raise ValueError(f"{folder.name}: {screen} artwork must be 256x192")
                if screen == "bottom":
                    image = Image.blend(
                        image.filter(ImageFilter.GaussianBlur(1.2)),
                        Image.new("RGB", image.size, ImageColor.getrgb(paper)),
                        0.76,
                    )
                image.save(temporary / f"{screen}.png")
        title_layer(
            config["theme"]["name"], source, weight, body_source, body_weight, ink
        ).save(temporary / "title.png")
        layers = {
            "top": {"preset": intro, "transition": "0.45", "easing": "smooth"},
            "bottom": {"preset": "none"},
            "bottom_logo": {
                "preset": motion,
                "width": "224",
                "fit": "native",
                "delay": "0.08",
                "transition": "0.55",
                "easing": "smooth",
            },
        }
        # Short, gentle transforms avoid oversized logos and repeated pulsing.
        if motion in ("zoom-out", "fade-zoom"):
            layers["bottom_logo"]["scale_from"] = (
                "106" if motion == "zoom-out" else "94"
            )
        if intro == "fade":
            layers["top"]["opacity_from"] = "35"
        data = pack_splash.build(
            top=temporary / "top.png",
            bottom=temporary / "bottom.png",
            bottom_logo=temporary / "title.png",
            duration=duration,
            poster=1.1,
            background=paper,
            layer_options=layers,
            compress=True,
        )
    if len(data) > 128 * 1024:
        raise ValueError(f"{theme}: intro exceeds the 128 KiB collection budget")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gloam", type=Path, help="Also prepare Gloam's bundled themes"
    )
    parser.add_argument("--download-fonts", action="store_true")
    parser.add_argument(
        "--font-dir", type=Path, default=Path("/usr/share/fonts/truetype/dejavu")
    )
    parser.add_argument(
        "--check", action="store_true", help="Compare rebuilt packages without writing"
    )
    args = parser.parse_args()
    repositories = [(ROOT, ROOT / "themes")]
    if args.gloam:
        repositories.append(
            (args.gloam, args.gloam / "sdroot/_nds/dsi-frontend/themes")
        )
    failed = []
    for repo, themes in repositories:
        for ini in sorted(themes.glob("*/theme.ini")):
            data = build_theme(
                repo, ini.parent, download=args.download_fonts, font_dir=args.font_dir
            )
            target = ini.parent / "splash.gsp"
            if args.check:
                if not target.exists() or target.read_bytes() != data:
                    failed.append(str(target))
            else:
                pack_splash.write_package(target, data, replace=True)
            print(f"{repo.name}/{ini.parent.name}: {len(data):,} bytes")
    if failed:
        parser.exit(
            1,
            "Splash differs; rebuild with the same Pillow version:\n"
            + "\n".join(failed)
            + "\n",
        )


if __name__ == "__main__":
    main()
