"""Keep catalog compatibility and distributed assets consistent with each pack."""

import configparser
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import struct
import wave
import zlib

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_collection import package, ART_COLLECTION, STARTER_COLLECTION
from build_collection import PROFILES
from inspired_assets import SPECS as INSPIRED_SPECS


class ThemeCollectionTests(unittest.TestCase):
    def test_prepared_assets_motion_and_audio_stay_bounded(self):
        for name in PROFILES:
            with self.subTest(theme=name):
                folder = ROOT / "themes" / name
                config = configparser.ConfigParser()
                config.read(folder / "theme.ini")
                self.assertEqual(config.get("components", "controls"), "on")
                self.assertEqual(config.get("components", "fill"), "stretch")
                for key in ("material", "focus_material"):
                    with Image.open(folder / config.get("components", key)) as material:
                        self.assertEqual(material.size, (256, 192))
                        self.assertFalse(material.info.get("transparency"))
                data = (folder / config.get("assets", "prepared")).read_bytes()
                self.assertEqual(data[:8], b"GLMART02")
                raw_size, count = struct.unpack_from("<II", data, 8)
                raw = zlib.decompress(data[16:])
                self.assertEqual(len(raw), raw_size)
                self.assertLessEqual(raw_size, 512 * 1024)
                self.assertLessEqual(len(data), 256 * 1024)
                seen, offset = set(), 0
                for _ in range(count):
                    group, reserved, index, length = struct.unpack_from(
                        "<BBHI", raw, offset
                    )
                    self.assertEqual(reserved, 0)
                    self.assertIn(group, (0, 1, 2, 3))
                    self.assertLess(index, {0: 29, 1: 30, 2: 2, 3: 2}[group])
                    if group < 2:
                        self.assertEqual(length, 2304 if group else 2048)
                    elif group == 2:
                        flags = struct.unpack_from("<I", raw, offset + 12)[0]
                        self.assertEqual(flags & ~7, 0)
                        self.assertEqual(
                            length,
                            8 + 256 * 192 * 2 + (256 * 94 * 2 if flags & 4 else 0),
                        )
                    else:
                        self.assertEqual(length, 4 + 256 * 192 // 2)
                    self.assertNotIn((group, index), seen)
                    seen.add((group, index))
                    offset += 8 + length
                self.assertEqual(offset, len(raw))
                # Every new control has a prepared record, including busy.
                self.assertTrue(all((1, index) in seen for index in range(19, 30)))
                data = (folder / config.get("motion", "ambient")).read_bytes()
                self.assertEqual(data[:8], b"GLMFX001")
                self.assertTrue(1 <= data[8] <= 8)
                self.assertEqual(data[9:16], bytes([32, 32, 0, 0, 0, 0, 0]))
                self.assertEqual(len(data), 16 + data[8] * 2304)
                frames = [
                    data[16 + i * 2304 : 16 + (i + 1) * 2304] for i in range(data[8])
                ]
                self.assertGreater(len(set(frames)), 1)
                for screen in ("top", "bottom"):
                    with Image.open(
                        folder / config.get("backgrounds", screen + "_surface")
                    ) as image:
                        self.assertEqual(image.size, (256, 192))
                        self.assertEqual(image.mode, "RGBA")
                if config.has_option("audio", "music"):
                    with wave.open(
                        str(folder / config.get("audio", "music")), "rb"
                    ) as audio:
                        self.assertEqual(
                            (audio.getnchannels(), audio.getsampwidth()), (1, 2)
                        )
                        self.assertLessEqual(audio.getnframes() * 2, 1024 * 1024)

    def test_icon_silhouettes_and_font_pairs_are_independent(self):
        silhouettes = set()
        for theme in PROFILES:
            with Image.open(ROOT / "themes" / theme / "icons/folder.png") as icon:
                self.assertEqual(icon.size, (32, 32))
                silhouettes.add(icon.getchannel("A").tobytes())
        self.assertEqual(len(silhouettes), len(PROFILES))
        for face in ("ui", "heading"):
            packs = {
                (ROOT / "themes" / theme / "fonts" / (face + ".dsfont")).read_bytes()
                for theme in PROFILES
            }
            self.assertEqual(len(packs), len(PROFILES))

    def test_material_fields_are_full_images_not_repeated_patches(self):
        for theme in PROFILES:
            with Image.open(
                ROOT / "themes" / theme / "components/material.png"
            ) as image:
                self.assertEqual(image.size, (256, 192))
                original = image.tobytes()
                repeat = Image.new(image.mode, image.size)
                patch = image.crop((0, 0, 16, 16))
                for y in range(0, 192, 16):
                    for x in range(0, 256, 16):
                        repeat.paste(patch, (x, y))
                self.assertNotEqual(original, repeat.tobytes(), theme)

    def test_catalog_and_pack_requirements_agree(self):
        catalog = json.loads((ROOT / "catalog.json").read_text())
        self.assertEqual(
            {entry["id"] for entry in catalog["themes"]},
            set(PROFILES) | set(INSPIRED_SPECS),
        )
        for entry in catalog["themes"]:
            with self.subTest(theme=entry["id"]):
                folder = ROOT / entry["path"]
                config = configparser.ConfigParser()
                config.read(folder / "theme.ini")
                self.assertEqual(
                    config.getint("theme", "version"), entry["theme_format"]
                )
                self.assertNotEqual(entry.get("minimum_gloam_version"), "1.0.0")
                self.assertIn("theme format 2", entry["requires_gloam"])
                self.assertEqual(config.get("components", "alpha"), "coverage")
                for role in ("ui", "heading"):
                    data = (folder / config.get("fonts", role)).read_bytes()
                    self.assertEqual(data[:8], b"DSFONT03")
                    self.assertEqual(
                        data[9],
                        (
                            12
                            if role == "ui"
                            else (
                                PROFILES[entry["id"]]["heading"][3]
                                if entry["id"] in PROFILES
                                else 16
                            )
                        ),
                    )
                for section in ("backgrounds", "audio"):
                    for key, path in (
                        config.items(section) if config.has_section(section) else []
                    ):
                        if key != "strength":
                            self.assertTrue((folder / path).is_file(), path)

    def test_buuf_sources_and_archive_preserve_noncommercial_notices(self):
        source = ROOT / "source/buuf"
        manifest = json.loads((source / "UPSTREAM.json").read_text())
        self.assertEqual(manifest["license"], "CC-BY-NC-SA-2.5")
        self.assertEqual(manifest["creator"], "mattahan")
        for name, record in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((source / "icons" / name).read_bytes()).hexdigest(),
                record["sha256"],
                name,
            )
        license_bytes = (source / "LICENSE.md").read_bytes()
        self.assertEqual(
            hashlib.sha256(license_bytes).hexdigest(), manifest["license_sha256"]
        )
        self.assertNotIn("buuf", ART_COLLECTION)
        self.assertNotIn("buuf", STARTER_COLLECTION)
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "buuf.zip"
            package(archive, ["buuf"])
            with zipfile.ZipFile(archive) as zipped:
                prefix = "_nds/dsi-frontend/themes/buuf/"
                self.assertEqual(
                    zipped.read(prefix + "BUUF-LICENSE.txt"), license_bytes
                )
                credits = zipped.read(prefix + "CREDITS.md").decode()
                for credit in (
                    "mattahan",
                    "fana-m",
                    "Hybrid Son Of Oxayotl",
                    "NonCommercial",
                    manifest["commit"],
                ):
                    self.assertIn(credit, credits)
                self.assertEqual(
                    json.loads(zipped.read(prefix + "UPSTREAM.json")), manifest
                )
                self.assertIn(prefix + "fonts/LICENSE.txt", zipped.namelist())

    def test_install_archives_keep_notices_and_exclude_preview_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "themes.zip"
            package(archive, list(PROFILES))
            with zipfile.ZipFile(archive) as zipped:
                names = set(zipped.namelist())
                self.assertIn("licenses/GPL-3.0.txt", names)
                self.assertIn("licenses/README.md", names)
                for theme in PROFILES:
                    prefix = f"_nds/dsi-frontend/themes/{theme}/"
                    for required in (
                        "theme.ini",
                        "CREDITS.md",
                        "fonts/LICENSE.txt",
                        "fonts/ui.dsfont",
                        "fonts/heading.dsfont",
                        "assets.gfx",
                        "motion/ambient.gtm",
                        "components/toggle-on.png",
                        "backgrounds/material-top.png",
                    ):
                        self.assertIn(prefix + required, names)
                    for excluded in (
                        "README.md",
                        "preview.png",
                        "settings-preview.png",
                    ):
                        self.assertNotIn(prefix + excluded, names)
                self.assertFalse(
                    any(
                        name.startswith(("source/", "build/", "tools/"))
                        for name in names
                    )
                )


if __name__ == "__main__":
    unittest.main()
