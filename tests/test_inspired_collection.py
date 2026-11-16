"""The shipped desktop/device packs remain complete, bounded and attributable."""

import configparser
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

from PIL import Image, ImageColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inspired_assets import SPECS, COMPONENTS
from theme_icons import CELLS
from package_collection import package, INSPIRED_COLLECTION


class InspiredCollectionTests(unittest.TestCase):
    def test_source_masters_and_complete_runtime_inputs(self):
        sources = json.loads(
            (ROOT / "config/inspired-art.json").read_text(encoding="utf-8")
        )["sources"]
        for relative, record in sources.items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                record["sha256"],
            )
        font_pairs, silhouettes = set(), set()
        for name in SPECS:
            with self.subTest(theme=name):
                folder = ROOT / "themes" / name
                config = configparser.ConfigParser()
                config.read(folder / "theme.ini", encoding="utf-8")
                for section in ("fonts", "audio", "backgrounds"):
                    for key, relative in config[section].items():
                        if key == "strength":
                            continue
                        path = folder / relative
                        self.assertTrue(path.resolve().is_relative_to(folder.resolve()))
                        self.assertTrue(path.is_file(), relative)
                for directory, names in (("icons", CELLS), ("components", COMPONENTS)):
                    for kind in names:
                        with Image.open(folder / directory / (kind + ".png")) as image:
                            self.assertEqual(image.size, (32, 32))
                            self.assertEqual(image.mode, "RGBA")
                with Image.open(folder / "icons/folder.png") as icon:
                    silhouettes.add(icon.getchannel("A").tobytes())
                font_pairs.add(
                    tuple(
                        (folder / "fonts" / (role + ".dsfont")).read_bytes()
                        for role in ("ui", "heading")
                    )
                )
                prepared = (folder / "assets.gfx").read_bytes()
                self.assertEqual(prepared[:8], b"GLMART02")
                runtime = sum(
                    p.stat().st_size
                    for p in folder.rglob("*")
                    if p.is_file() and p.suffix != ".md" and "preview" not in p.name
                )
                self.assertLess(runtime, 2 * 1024 * 1024, name)
        self.assertEqual(len(font_pairs), 7)
        self.assertEqual(len(silhouettes), 7)

    def test_neon_theme_text_contrast_on_actual_control_surfaces(self):
        def luminance(rgb):
            # Check the colors the DS can actually display, after RGB555 packing.
            values = [(channel >> 3) / 31 for channel in rgb]
            linear = [
                v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                for v in values
            ]
            return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722)))

        for theme in ("portal-terminal", "synthwave"):
            folder = ROOT / "themes" / theme
            config = configparser.ConfigParser()
            config.read(folder / "theme.ini", encoding="utf-8")
            for component in ("header", "footer", "panel", "row", "row-selected"):
                with Image.open(
                    folder / "components" / (component + ".png")
                ) as surface:
                    background = luminance(surface.getpixel((16, 16))[:3])
                keys = (
                    ("selection_text",)
                    if component == "row-selected"
                    else ("text", "muted", "accent")
                )
                for key in keys:
                    ink = luminance(ImageColor.getrgb(config["colors"][key]))
                    ratio = (max(ink, background) + 0.05) / (
                        min(ink, background) + 0.05
                    )
                    self.assertGreaterEqual(ratio, 4.5, (component, key, ratio))

    def test_intros_use_three_still_layers_not_full_screen_movies(self):
        for name in SPECS:
            with self.subTest(theme=name):
                data = (ROOT / "themes" / name / "splash.gsp").read_bytes()
                self.assertEqual(data[:8], b"GLOMSP03")
                self.assertEqual(
                    struct.unpack_from("<II", data, 8),
                    (len(data), zlib.crc32(data[16:])),
                )
                self.assertEqual(struct.unpack_from("<HHB", data, 16), (72, 66, 3))
                self.assertEqual(struct.unpack_from("<II", data, 24), (0, 0))
                self.assertLess(len(data), 128 * 1024)
                for layer in range(3):
                    self.assertEqual(
                        struct.unpack_from("<H", data, 40 + layer * 64)[0], 1
                    )

    def test_installable_collection_has_notices_and_no_previews(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "collection.zip"
            package(target, INSPIRED_COLLECTION)
            with zipfile.ZipFile(target) as zipped:
                names = zipped.namelist()
                self.assertEqual(len([n for n in names if n.endswith("/theme.ini")]), 7)
                self.assertFalse(
                    any(
                        "preview" in Path(n).name or Path(n).name.startswith(".")
                        for n in names
                    )
                )
                for theme in SPECS:
                    prefix = "_nds/dsi-frontend/themes/" + theme + "/"
                    for name in (
                        "splash.gsp",
                        "assets.gfx",
                        "CREDITS.md",
                        "MUSIC.md",
                        "MUSIC-LICENSE.txt",
                        "fonts/LICENSE.txt",
                    ):
                        self.assertIn(prefix + name, names)
