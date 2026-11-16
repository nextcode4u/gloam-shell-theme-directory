# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable end-to-end authoring fixtures; no physical SD or network access."""

import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_project import ThemeProject
from theme_validate import check, inside, parse_ini, font_info, audio_info
from theme_media import (
    generate_set,
    material,
    png,
    convert_audio,
    ambient,
    atlas_import,
)
import theme_preview


class ThemeStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = ThemeProject(self.root)

    def test_project_reopen_atomic_metadata_and_undo(self):
        p = self.project
        p.update(id="my-paper", metadata=dict(author="Someone", license="CC0-1.0"))
        config = copy.deepcopy(p.data["config"])
        config["theme"]["header"] = "Paper"
        p.update(config=config)
        self.assertEqual(
            ThemeProject(self.root).data["config"]["theme"]["header"], "Paper"
        )
        p.undo()
        self.assertNotIn("header", p.data["config"]["theme"])
        p.undo(True)
        self.assertEqual(p.data["config"]["theme"]["header"], "Paper")
        previous = p.file.read_bytes()
        with self.assertRaises(ValueError):
            p.update(id="../outside")
        self.assertEqual(p.file.read_bytes(), previous)
        self.assertTrue((self.root / "theme-project.previous.json").is_file())

    def test_asset_source_master_bounds_transform_and_undo(self):
        p = self.project
        source = png(Image.new("RGBA", (100, 60), (200, 50, 80, 180)))
        p.image_asset(
            "icons/folder.png",
            source,
            dict(width=32, height=32, fit="contain", source_name="master.png"),
        )
        file = p.theme / "icons/folder.png"
        first = file.read_bytes()
        with Image.open(file) as image:
            self.assertEqual(image.size, (32, 32))
        self.assertEqual(len(p.data["provenance"]), 1)
        self.assertTrue((self.root / p.data["provenance"][0]["path"]).is_file())
        p.write_asset("icons/folder.png", png(Image.new("RGBA", (32, 32), "blue")))
        p.undo()
        self.assertEqual(file.read_bytes(), first)
        for path in (
            "theme.ini",
            "../outside.png",
            "/outside.png",
            "sd:/file",
            "x/../../file",
            "folder\\file",
        ):
            with self.assertRaises(ValueError):
                p.write_asset(path, b"no")

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.project.theme / "linked").symlink_to(
                outside, target_is_directory=True
            )
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            inside(self.project.theme, "linked/file.png")

    def test_complete_asset_export_and_scoped_install(self):
        p = self.project
        generate_set(p, "icons", {})
        generate_set(p, "components", dict(style="paper"))
        p.write_asset("LICENSE.txt", b"Keep this notice.")
        p.write_asset("draft.png", png(Image.new("RGB", (16, 16))))
        p.update(
            metadata=dict(
                author="Test author", license="CC0-1.0", credits="Original shapes."
            )
        )
        archive = p.export()
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            prefix = "_nds/dsi-frontend/themes/my-theme/"
            self.assertIn(prefix + "assets.gfx", names)
            self.assertIn(prefix + "LICENSE.txt", names)
            self.assertIn(prefix + "AUTHORING-CREDITS.md", names)
            self.assertNotIn(prefix + "draft.png", names)
            self.assertFalse(
                any(
                    "theme-project" in n or "sources/" in n or "artboards/" in n
                    for n in names
                )
            )
        self.assertTrue((p.theme / "assets.gfx").read_bytes().startswith(b"GLMART02"))
        card = self.root / "sd"
        card.mkdir()
        (card / "BOOT.NDS").write_bytes(b"unchanged")
        target = p.install(card)
        with self.assertRaises(ValueError):
            p.install(card)
        p.install(card, replace=True)
        self.assertEqual((card / "BOOT.NDS").read_bytes(), b"unchanged")
        self.assertTrue((target / "theme.ini").is_file())
        self.assertEqual(len(list((self.root / "exports/backups").iterdir())), 1)

    def test_blank_theme_exports_without_sprite_bundle(self):
        p = self.project
        p.update(metadata=dict(author="Author", license="Own assets"))
        with zipfile.ZipFile(p.export()) as z:
            self.assertTrue(any(n.endswith("theme.ini") for n in z.namelist()))
            self.assertFalse(any(n.endswith("assets.gfx") for n in z.namelist()))

        p.write_asset(
            "fonts/ui.dsfont", (ROOT / "themes/morrow/fonts/ui.dsfont").read_bytes()
        )
        config = copy.deepcopy(p.data["config"])
        config["fonts"]["ui"] = "fonts/ui.dsfont"
        p.update(config=config)
        with zipfile.ZipFile(p.export()) as z:
            self.assertTrue(any(n.endswith("fonts/ui.dsfont") for n in z.namelist()))
            self.assertFalse(any(n.endswith("assets.gfx") for n in z.namelist()))

    def test_import_preserves_notices_and_rejects_zip_traversal(self):
        folder = self.root / "input"
        folder.mkdir()
        (folder / "theme.ini").write_text("[theme]\nversion=2\nname=Imported\n")
        (folder / "LICENSE.txt").write_text("Third party terms")
        self.project.import_theme(folder)
        self.assertFalse(self.project.data["metadata"]["license"])
        self.assertEqual(
            (self.project.theme / "LICENSE.txt").read_text(), "Third party terms"
        )
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("../outside", "bad")
            z.writestr("theme.ini", "[theme]\nversion=2\n")
        before = (self.project.theme / "theme.ini").read_bytes()
        with self.assertRaises(ValueError):
            self.project.import_theme(archive)
        self.assertEqual((self.project.theme / "theme.ini").read_bytes(), before)

    def test_all_existing_manifests_and_schema_constraints(self):
        for folder in (ROOT / "themes").iterdir():
            if not (folder / "theme.ini").exists():
                continue
            with self.subTest(theme=folder.name):
                report = check(folder, parse_ini((folder / "theme.ini").read_text()))
                self.assertTrue(report["valid"], report["errors"])
        config = copy.deepcopy(self.project.data["config"])
        config["layout"].update(
            top_layout="scene", tabs_position="top", scene_cover_x="240"
        )
        config["colors"]["text"] = config["colors"]["background"]
        self.assertGreaterEqual(len(check(self.project.theme, config)["errors"]), 3)
        with self.assertRaises(ValueError):
            parse_ini("x" * 4097)

    def test_material_atlas_audio_and_motion_conversion(self):
        image = material(dict(width=256, height=192, style="paper", opacity=170))
        self.assertEqual(image.size, (256, 192))
        self.assertTrue(set(image.getchannel("A").getdata()) <= {0, 85, 170, 255})
        atlas = png(Image.new("RGBA", (128, 128), "red"))
        self.assertEqual(atlas_import(self.project, atlas, "icons", 4, 4), 16)
        with Image.open(self.project.theme / "icons/folder.png") as image:
            self.assertEqual(image.size, (32, 32))
        gif = io.BytesIO()
        Image.new("RGBA", (20, 20), "red").save(
            gif,
            "GIF",
            save_all=True,
            append_images=[Image.new("RGBA", (20, 20), "blue")],
            duration=100,
            loop=0,
        )
        packed = ambient(gif.getvalue())
        self.assertEqual(packed[:11], b"GLMFX001\x02  ")
        self.assertEqual(len(packed), 16 + 2 * 2304)
        source = self.root / "stereo.wav"
        with wave.open(str(source), "wb") as w:
            w.setparams((2, 2, 8000, 8000, "NONE", ""))
            w.writeframes(struct.pack("<hh", 10000, -2000) * 8000)
        converted = convert_audio(source, rate=16000, seconds=0.5, fade=0, music=False)
        info = audio_info(converted)
        self.assertEqual(info["pcm_bytes"], 16000)
        with wave.open(io.BytesIO(converted)) as w:
            self.assertEqual(struct.unpack("<h", w.readframes(1))[0], 4000)
        with self.assertRaises(ValueError):
            convert_audio(source, rate=48000, seconds=2, music=False)

    def test_font_packer_preview_and_exact_source_provenance(self):
        folder = ROOT / "tools/theme_native"
        upstream = json.loads((folder / "UPSTREAM.json").read_text())
        for name, digest in upstream["files"].items():
            self.assertEqual(
                hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest
            )
        data = (ROOT / "themes/morrow/fonts/ui.dsfont").read_bytes()
        self.assertEqual(font_info(data)["height"], 12)
        with self.assertRaises(ValueError):
            font_info(data + b"\0")
        for composition in (
            "sidebar",
            "sidebar_left",
            "scene",
            "poster",
            "spotlight",
            "gallery",
            "journal",
        ):
            self.project.data["config"]["layout"]["top_layout"] = composition
            self.assertEqual(theme_preview.render(self.project).size, (256, 396))


if __name__ == "__main__":
    unittest.main()
