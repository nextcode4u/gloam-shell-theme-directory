# SPDX-License-Identifier: GPL-3.0-or-later
"""Every preview/editor route has an exit and respects a user's newer navigation."""

import importlib.util
import os
import threading
import time
import unittest
import wave
from unittest import mock
from PIL import Image
from test_theme_studio_user_journeys import editor, draw


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium navigation checks",
)
class NavigationTests(unittest.TestCase):
    def test_delayed_material_result_does_not_reopen_an_editor_after_back(self):
        import theme_media

        original = theme_media.material
        started = threading.Event()

        def material(options):
            started.set()
            time.sleep(0.7)
            return original(options)

        with (
            mock.patch("theme_media.material", side_effect=material),
            editor() as (page, root, expect),
        ):
            page.locator("[data-section=icons]").click()
            page.get_by_role("button", name="Fill missing slots", exact=True).click()
            expect(page.locator(".slot img")).to_have_count(29)
            page.locator("[data-stage=assets]").click()
            page.locator(".asset-tile").filter(has_text="icons/folder.png").click()
            expect(page.locator("#canvas-stage")).to_be_visible()
            page.get_by_role("button", name="Generate texture…", exact=True).click()
            page.get_by_role("button", name="Generate 32×32", exact=True).click()
            self.assertTrue(started.wait(5))
            page.locator("#view-back").click()
            page.locator("#view-back").click()
            expect(page.locator("#assets-stage")).to_be_visible()
            expect(page.locator("#activity")).to_contain_text(
                "Artwork saved; current view kept."
            )
            expect(page.locator("#canvas-stage")).to_be_hidden()

    def test_back_stops_audio_without_closing_the_project(self):
        with editor() as (page, root, expect):
            source = root / "music.wav"
            with wave.open(str(source), "wb") as out:
                out.setparams((1, 2, 16000, 160000, "NONE", ""))
                out.writeframes(b"\0\0" * 160000)
            page.locator("[data-section=audio]").click()
            with page.expect_file_chooser() as chooser:
                page.get_by_role(
                    "button", name="Choose audio and convert…", exact=True
                ).click()
            chooser.value.set_files(str(source))
            expect(page.locator("audio")).to_have_count(1)
            player = page.locator("audio")
            player.click(position=dict(x=23, y=27))
            expect(player).to_have_js_property("paused", False)
            handle = player.element_handle()
            page.locator("#view-back").click()
            expect(page.locator("#section-title")).to_have_text(
                "Start, import or resume"
            )
            self.assertTrue(handle.get_property("paused").json_value())

    def test_back_returns_to_asset_library_and_cancel_keeps_unsaved_work(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=icons]").click()
            page.get_by_role("button", name="Fill missing slots", exact=True).click()
            expect(page.locator(".slot img")).to_have_count(29)
            page.locator("[data-stage=assets]").click()
            page.locator(".asset-tile").filter(has_text="icons/folder.png").click()
            expect(page.locator("#canvas-stage")).to_be_visible()
            draw(page)
            page.locator("#view-back").click()
            page.get_by_role("button", name="Cancel", exact=True).click()
            expect(page.locator("#canvas-stage")).to_be_visible()
            expect(page.locator("#artboard-name")).to_contain_text("unsaved")
            page.locator("#view-back").click()
            page.get_by_role("button", name="Save and continue", exact=True).click()
            expect(page.locator("#assets-stage")).to_be_visible()
            self.assertTrue((root / "theme/icons/folder.png").is_file())
            page.keyboard.press("Escape")
            expect(page.locator("#preview-stage")).to_be_visible()
            page.keyboard.press("Alt+ArrowLeft")
            expect(page.locator("#section-title")).to_have_text(
                "Start, import or resume"
            )
            expect(page.locator("#view-back")).to_be_enabled()

    def test_temporary_tools_close_without_leaving_their_parent_section(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=icons]").click()
            page.get_by_role("button", name="Generate texture…", exact=True).click()
            expect(page.locator("[data-transient-tool]")).to_have_count(1)
            page.keyboard.press("Escape")
            expect(page.locator("[data-transient-tool]")).to_have_count(0)
            expect(page.locator("#section-title")).to_have_text("File & tab icons")
            page.get_by_role("button", name="Import atlas…", exact=True).click()
            page.get_by_role(
                "button", name="Close import sprite sheet", exact=True
            ).click()
            expect(page.locator("[data-transient-tool]")).to_have_count(0)
            self.assertFalse((root / "theme/icons/folder.png").exists())

    def test_native_preview_has_back_and_a_late_result_does_not_steal_the_view(self):
        started = threading.Event()
        calls = 0

        def native(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                started.set()
                time.sleep(0.7)
            return Image.new("RGB", (256, 396), "navy")

        with (
            mock.patch("theme_preview.native", side_effect=native),
            editor() as (page, root, expect),
        ):
            page.locator("[data-section=publish]").click()
            page.get_by_placeholder("File path…").fill("/mock-preview")
            page.get_by_role(
                "button", name="Render with local Gloam host tool", exact=True
            ).click()
            self.assertTrue(started.wait(5))
            page.locator("#view-back").click()
            expect(page.locator("#section-title")).to_have_text(
                "Start, import or resume"
            )
            expect(page.locator("#activity")).to_contain_text(
                "Native preview saved in exports; current view kept."
            )
            page.locator("[data-section=publish]").click()
            page.get_by_role(
                "button", name="Render with local Gloam host tool", exact=True
            ).click()
            expect(page.locator("#native-preview-back")).to_be_visible()
            page.locator("#native-preview-back").click()
            expect(page.locator("#native-preview-back")).to_be_hidden()
            expect(page.locator("#section-title")).to_have_text("Check & export")

    def test_help_returns_to_original_editor_and_atlas_export_is_not_a_dead_end(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=icons]").click()
            with page.expect_popup() as popup:
                page.locator("#help").click()
            help_page = popup.value
            with help_page.expect_event("close"):
                help_page.get_by_role(
                    "button", name="Close help / return to editor", exact=True
                ).click()
            expect(page.locator("#section-title")).to_have_text("File & tab icons")
            page.get_by_role("button", name="Fill missing slots", exact=True).click()
            expect(page.locator(".slot img")).to_have_count(29)
            with page.expect_download() as download:
                page.get_by_role("button", name="Export atlas", exact=True).click()
            with Image.open(download.value.path()) as atlas:
                self.assertEqual(atlas.size, (256, 128))
            expect(page.locator("#view-back")).to_be_visible()


if __name__ == "__main__":
    unittest.main()
