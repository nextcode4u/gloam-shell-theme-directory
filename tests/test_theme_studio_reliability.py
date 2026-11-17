# SPDX-License-Identifier: GPL-3.0-or-later
"""End-user failure cases: retained notices, layered undo and scoped installation."""

import base64
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_builder import Studio
from theme_media import generate_set, png
from theme_validate import check


class AuthoringReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.studio = Studio(self.temp.name)
        self.p = self.studio.project

    def board(self, color, name, binding=None):
        data = (
            "data:image/png;base64,"
            + base64.b64encode(png(Image.new("RGBA", (32, 32), color))).decode()
        )
        document = dict(
            width=32,
            height=32,
            index=0,
            layers=[
                dict(name=name, visible=True, opacity=1, blend="source-over", data=data)
            ],
        )
        self.studio.action(
            "artboard-save",
            dict(
                path="icons/folder.png", data=data, document=document, binding=binding
            ),
        )

    def test_inherit_top_layout_without_an_explicit_layout_section(self):
        self.p.update(raw="[theme]\nname=Minimal theme\nversion=2\n")
        self.studio.action(
            "field", dict(section="layout", key="top_layout", inherit=True)
        )
        self.assertNotIn("top_layout", self.p.data["config"].get("layout", {}))
        self.studio.action(
            "field", dict(section="layout", key="top_layout", value="spotlight")
        )
        self.assertEqual(self.p.data["config"]["layout"]["top_layout"], "spotlight")

    def test_refresh_updates_both_launchers_after_shared_notice_changes(self):
        import update_theme_manifest as themes
        import update_splash_manifest as splashes

        root = self.p.root / "manifest-fixture"
        for relative in set(themes.FILES) | set(splashes.FILES):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(("Fixture: " + relative).encode())
        with (
            mock.patch.object(themes, "ROOT", root),
            mock.patch.object(splashes, "ROOT", root),
        ):
            themes.refresh()
            (root / "LICENSES.md").write_text("Updated shared notice")
            with self.assertRaises(SystemExit):
                themes.refresh(check=True)
            themes.refresh()
            themes.refresh(check=True)
            import json

            for name in ("theme", "splash"):
                data = json.loads(
                    (root / ("tools/" + name + "-downloads.json")).read_text()
                )
                entry = next(e for e in data["files"] if e["path"] == "LICENSES.md")
                self.assertEqual(entry["size"], len(b"Updated shared notice"))

    def test_prepared_asset_destination_cannot_destroy_a_notice_or_font(self):
        generate_set(self.p, "icons", {})
        for path in ("notices/LICENSE.txt", "LICENSE.gfx", "fonts/ui.dsfont"):
            self.p.write_asset(path, b"KEEP THIS SOURCE")
            self.p.data["config"]["assets"] = {"prepared": path}
            self.p.save()
            with self.assertRaises(ValueError):
                self.p.prepare()
            self.assertEqual((self.p.theme / path).read_bytes(), b"KEEP THIS SOURCE")

    def test_existing_authoring_credits_are_not_replaced_by_export(self):
        self.p.write_asset(
            "AUTHORING-CREDITS.md", b"Original author and full special terms."
        )
        self.p.update(
            metadata=dict(author="New author", license="See original notices")
        )
        with zipfile.ZipFile(self.p.export()) as archive:
            prefix = "_nds/dsi-frontend/themes/my-theme/"
            self.assertEqual(
                archive.read(prefix + "AUTHORING-CREDITS.md"),
                b"Original author and full special terms.",
            )
            self.assertIn(b"New author", archive.read(prefix + "STUDIO-CREDITS-1.md"))
        self.p.export()
        self.assertEqual(len(list(self.p.theme.glob("STUDIO-CREDITS-*.md"))), 1)

    def test_undo_redo_restores_editable_layers_and_assignment(self):
        self.p.data["config"].pop("icons")
        self.board(
            "red", "First", dict(section="icons", key="directory", value="icons")
        )
        self.board("blue", "Second")
        self.p.undo()
        doc = self.studio.action("artboard-load", dict(path="icons/folder.png"))[
            "result"
        ]
        self.assertEqual(doc["layers"][0]["name"], "First")
        self.p.undo(True)
        self.assertEqual(
            self.studio.action("artboard-load", dict(path="icons/folder.png"))[
                "result"
            ]["layers"][0]["name"],
            "Second",
        )
        self.p.undo()
        self.p.undo()
        self.assertNotIn("icons", self.p.data["config"])
        self.assertFalse((self.p.theme / "icons/folder.png").exists())

    def test_imported_studio_generated_credits_keep_the_original_author(self):
        from theme_project import ThemeProject

        source = self.p.root / "other-project"
        source.mkdir()
        other = ThemeProject(source)
        other.update(
            metadata=dict(author="Original contributor", license="Keep credit")
        )
        other.export()
        self.p.import_theme(other.theme)
        self.p.update(
            metadata=dict(author="Adapting contributor", license="Keep original terms")
        )
        with zipfile.ZipFile(self.p.export()) as archive:
            prefix = "_nds/dsi-frontend/themes/theme/"
            self.assertIn(
                b"Original contributor", archive.read(prefix + "AUTHORING-CREDITS.md")
            )
            self.assertIn(
                b"Adapting contributor", archive.read(prefix + "STUDIO-CREDITS-1.md")
            )

    def test_invalid_prepared_font_import_preserves_the_previous_face(self):
        data = (ROOT / "themes/morrow/fonts/ui.dsfont").read_bytes()
        self.p.write_asset("fonts/ui.dsfont", data)
        with self.assertRaises(ValueError):
            self.studio.action(
                "upload",
                dict(
                    path="fonts/ui.dsfont",
                    data=base64.b64encode(b"invalid font").decode(),
                    format="font",
                    binding=dict(section="fonts", key="ui"),
                ),
            )
        self.assertEqual((self.p.theme / "fonts/ui.dsfont").read_bytes(), data)

    def test_recursive_install_is_refused_before_writing_any_export(self):
        with self.assertRaises(ValueError):
            self.p.install(self.p.theme)
        self.assertFalse((self.p.theme / "_nds").exists())
        self.assertFalse((self.p.root / "exports/my-theme.zip").exists())

    def test_saved_drawing_and_assignment_are_one_undoable_edit(self):
        image = png(Image.new("RGB", (256, 192), "orange"))
        self.studio.action(
            "image",
            dict(
                path="backgrounds/top.png",
                data=base64.b64encode(image).decode(),
                options=dict(width=256, height=192),
                binding=dict(section="backgrounds", key="top"),
            ),
        )
        self.assertEqual(
            self.p.data["config"]["backgrounds"]["top"], "backgrounds/top.png"
        )
        self.assertTrue(check(self.p.theme, self.p.data["config"])["valid"])
        self.p.undo()
        self.assertNotIn("top", self.p.data["config"]["backgrounds"])
        self.assertFalse((self.p.theme / "backgrounds/top.png").exists())

    def test_stale_editor_refuses_to_overwrite_newer_settings_or_assets(self):
        from theme_project import ThemeProject

        other = ThemeProject(self.p.root)
        self.p.palette("Paper")
        saved = self.p.file.read_bytes()
        with self.assertRaisesRegex(ValueError, "Reload project"):
            other.update(id="stale-id")
        with self.assertRaisesRegex(ValueError, "Reload project"):
            other.write_asset("icons/game.png", png(Image.new("RGB", (32, 32), "red")))
        self.assertEqual(saved, self.p.file.read_bytes())
        self.assertFalse((self.p.theme / "icons/game.png").exists())

    def test_external_ini_edit_is_retained_until_the_project_is_reloaded(self):
        from theme_project import ThemeProject

        target = self.p.theme / "theme.ini"
        target.write_text(
            target.read_text().replace("name=Untitled theme", "name=Edited outside")
        )
        with self.assertRaisesRegex(ValueError, "Reload project"):
            self.p.update(id="my-change")
        self.assertEqual(
            ThemeProject(self.p.root).data["config"]["theme"]["name"], "Edited outside"
        )

    def test_recovery_preserves_damaged_ini_and_keeps_artwork(self):
        from theme_project import ThemeProject, recover_project

        image = png(Image.new("RGB", (32, 32), "blue"))
        self.p.write_asset("icons/folder.png", image)
        (self.p.theme / "theme.ini").write_text("broken section with no bracket")
        backup = recover_project(self.p.root)
        reopened = ThemeProject(self.p.root)
        self.assertEqual((reopened.theme / "icons/folder.png").read_bytes(), image)
        self.assertEqual(
            (backup / "theme/theme.ini").read_text(), "broken section with no bracket"
        )
        self.assertEqual(reopened.data["id"], "my-theme")

    def test_canceled_preview_connection_is_not_reported_as_a_server_failure(self):
        from theme_builder import Handler

        handler = Handler.__new__(Handler)
        handler.request_version = "HTTP/1.1"
        handler.requestline = "GET /api/preview HTTP/1.1"
        handler.wfile = mock.Mock()
        handler.wfile.write.side_effect = BrokenPipeError()
        handler.send(b"preview", "image/png")


if __name__ == "__main__":
    unittest.main()
