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

    def test_tab_styles_and_highlights_change_both_side_and_horizontal_previews(self):
        layout = self.project.data["config"]["layout"]
        for composition in ("sidebar", "sidebar_left", "gallery", "scene"):
            layout["top_layout"] = composition
            styles = set()
            for style in ("labels", "icons", "numbered", "pager"):
                layout["tab_style"] = style
                highlights = set()
                for highlight in ("skin", "underline", "outline"):
                    layout["tab_highlight"] = highlight
                    pixels = (
                        theme_preview.render(self.project)
                        .crop((0, 24, 256, 173))
                        .tobytes()
                    )
                    highlights.add(hashlib.sha256(pixels).digest())
                    if highlight == "skin":
                        styles.add(hashlib.sha256(pixels).digest())
                self.assertEqual(len(highlights), 3, (composition, style))
            self.assertEqual(len(styles), 4, composition)

    def test_browser_icons_fit_native_row_sizes_with_and_without_skins(self):
        icons = self.project.theme / "icons"
        icons.mkdir()
        Image.new("RGBA", (32, 32), "red").save(icons / "folder.png")
        config = self.project.data["config"]
        config["icons"]["directory"] = "icons"
        components = self.project.theme / "components"
        components.mkdir()
        Image.new("RGBA", (32, 32), "#234555").save(components / "row.png")
        expected = {
            "classic": (18, 28, 36),
            "index": (18, 28, 36),
            "extended": (28, 34, 40),
            "list": (16, 16, 16),
        }
        for framed in (False, True):
            if framed:
                config["components"]["directory"] = "components"
            else:
                config["components"].pop("directory", None)
            for padding in (0, 12):
                config["layout"]["row_padding"] = str(padding)
                for style, heights in expected.items():
                    for size, pixels, base in zip(
                        ("small", "medium", "large"), (16, 24, 32), heights
                    ):
                        with self.subTest(
                            framed=framed, padding=padding, style=style, size=size
                        ):
                            config["layout"].update(view=style, icon_size=size)
                            image = theme_preview.render(self.project).crop(
                                (0, 204, 256, 396)
                            )
                            red = [
                                y
                                for y in range(41, 169)
                                if image.getpixel((14, y))[:3] == (255, 0, 0)
                            ]
                            if style == "list":
                                self.assertEqual(red, [])
                                continue
                            height = (
                                max(
                                    base,
                                    max(26 if style == "extended" else 12, pixels) + 8,
                                )
                                if framed
                                else base
                            )
                            height += padding
                            starts = [y for y in red if y - 1 not in red]
                            self.assertEqual(
                                starts,
                                [
                                    41 + i * height + (height - pixels) // 2
                                    for i in range(min(6, 128 // height))
                                ],
                            )
                            self.assertEqual(len(red), len(starts) * pixels)

    def test_motion_previews_decode_prepared_frames_and_keep_native_timing(self):
        gif = io.BytesIO()
        Image.new("RGBA", (32, 32), "red").save(
            gif,
            "GIF",
            save_all=True,
            append_images=[Image.new("RGBA", (32, 32), "blue")],
            duration=100,
        )
        self.project.write_asset(
            "motion/ambient.gtm",
            ambient(gif.getvalue()),
            binding=dict(section="motion", key="ambient"),
        )
        for play, count in ((False, 1), (True, 2)):
            with Image.open(
                io.BytesIO(theme_preview.motion_preview(self.project, "ambient", play))
            ) as image:
                self.assertEqual(image.n_frames, count)
                self.assertEqual(image.size, (256, 88))
                self.assertEqual(
                    image.convert("RGBA").getpixel((136, 4)), (255, 0, 0, 255)
                )
                if play:
                    self.assertAlmostEqual(image.info["duration"], 200, places=1)
                    image.seek(1)
                    self.assertEqual(
                        image.convert("RGBA").getpixel((136, 4)), (0, 0, 255, 255)
                    )
        self.project.data["config"]["motion"]["focus"] = "pulse"
        with Image.open(
            io.BytesIO(theme_preview.motion_preview(self.project, "focus", True))
        ) as image:
            self.assertEqual(image.n_frames, 3)
        self.project.data["config"]["motion"]["focus"] = "off"
        with Image.open(
            io.BytesIO(theme_preview.motion_preview(self.project, "focus", True))
        ) as image:
            self.assertEqual(image.n_frames, 1)
        with self.assertRaises(ValueError):
            theme_preview.motion_preview(self.project, "unknown", True)
        (self.project.theme / "motion/ambient.gtm").write_bytes(b"bad")
        with self.assertRaises(ValueError):
            theme_preview.motion_preview(self.project, "ambient", True)

    def test_compositions_keep_top_tabs_out_of_headings_and_artwork(self):
        def overlap(a, b):
            return (
                a
                and b
                and a[0] < b[0] + b[2]
                and b[0] < a[0] + a[2]
                and a[1] < b[1] + b[3]
                and b[1] < a[1] + a[3]
            )

        for layout in theme_preview.COMPOSED_LAYOUTS:
            for position in (None, "top", "bottom"):
                for style in ("labels", "icons", "numbered", "pager"):
                    config = dict(top_layout=layout, tab_style=style)
                    if position:
                        config["tabs_position"] = position
                    boxes = theme_preview.composition_boxes(config)
                    art = boxes["artwork"]
                    frame = (art[0] - 2, art[1] - 2, art[2] + 4, art[3] + 4)
                    self.assertGreaterEqual(frame[1], 25)
                    self.assertLessEqual(frame[1] + frame[3], 176)
                    for key in ("title", "information", "tabs"):
                        self.assertFalse(overlap(frame, boxes[key]), (config, key))
                    self.assertFalse(overlap(boxes["title"], boxes["tabs"]))
                    self.assertFalse(overlap(boxes["information"], boxes["tabs"]))
                    if style == "labels" and position == "top":
                        self.project.data["config"]["layout"].update(config)
                        self.assertEqual(
                            theme_preview.render(self.project).size, (256, 396)
                        )

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
            "panorama",
            "dossier",
            "portrait",
        ):
            self.project.data["config"]["layout"]["top_layout"] = composition
            self.assertEqual(theme_preview.render(self.project).size, (256, 396))

    def test_optional_top_content_presets_preview_without_changing_legacy_layouts(self):
        baseline = theme_preview.render(self.project).tobytes()
        for mode in ("context", "neighbors", "folder", "activity", "smart", "layout"):
            for tabs in ("labels", "icons", "numbered", "pager"):
                config = copy.deepcopy(self.project.data["config"])
                config["layout"]["top_content"] = mode
                config["layout"]["tab_style"] = tabs
                self.project.update(config=config)
                self.assertEqual(theme_preview.render(self.project).size, (256, 396))
                self.assertIn("top_content=" + mode, (self.project.theme / "theme.ini").read_text())
        config = copy.deepcopy(self.project.data["config"])
        config["layout"].pop("top_content")
        config["layout"]["tab_style"] = "labels"
        self.project.update(config=config)
        self.assertEqual(theme_preview.render(self.project).tobytes(), baseline)


if __name__ == "__main__":
    unittest.main()
