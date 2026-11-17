# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional browser journeys which actually draw, cancel, convert and install."""

from contextlib import contextmanager
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_builder import Server


@contextmanager
def editor():
    from playwright.sync_api import sync_playwright, expect

    with tempfile.TemporaryDirectory() as folder, Server(folder) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    executable_path=os.environ["GLOAM_STUDIO_BROWSER"],
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(viewport=dict(width=1366, height=768))
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                expect(page.locator("#project-name")).to_have_text("Untitled theme")
                yield page, Path(folder), expect
                if errors:
                    raise AssertionError(errors)
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=3)


def draw(page):
    page.locator("#paint").wait_for(state="visible")
    box = page.locator("#paint").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.6, steps=6
    )
    page.mouse.up()


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium / Playwright journeys",
)
class EndUserJourneys(unittest.TestCase):
    def test_labeled_artwork_undo_and_redo_restore_pixels_and_button_states(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=icons]").click()
            page.locator('.slot[title="icons/folder.png"]').click()
            undo = page.get_by_role("button", name="↶ Undo", exact=True)
            redo = page.get_by_role("button", name="↷ Redo", exact=True)
            expect(undo).to_be_disabled()
            expect(redo).to_be_disabled()
            original = page.locator("#paint").evaluate("c => c.toDataURL()")
            draw(page)
            expect(undo).to_be_enabled()
            painted = page.locator("#paint").evaluate("c => c.toDataURL()")
            self.assertNotEqual(painted, original)
            undo.click()
            expect(undo).to_be_disabled()
            expect(redo).to_be_enabled()
            self.assertEqual(
                page.locator("#paint").evaluate("c => c.toDataURL()"), original
            )
            redo.click()
            expect(redo).to_be_disabled()
            expect(undo).to_be_enabled()
            self.assertEqual(
                page.locator("#paint").evaluate("c => c.toDataURL()"), painted
            )
            page.keyboard.press("Control+z")
            expect(undo).to_be_disabled()
            self.assertEqual(
                page.locator("#paint").evaluate("c => c.toDataURL()"), original
            )
            draw(page)
            expect(redo).to_be_disabled()
            self.assertFalse((root / "theme/icons/folder.png").exists())

    def test_cancel_switch_and_change_inspector_do_not_redirect_the_drawing(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=icons]").click()
            page.locator('.slot[title="icons/folder.png"]').click()
            expect(page.locator("#canvas-stage")).to_be_visible()
            draw(page)
            page.locator('.slot[title="icons/game.png"]').click()
            page.get_by_role("button", name="Cancel", exact=True).click()
            expect(page.locator("#artboard-name")).to_contain_text("icons/folder.png")
            page.locator("[data-section=components]").click()
            page.get_by_role("button", name="Save artwork", exact=True).click()
            expect(page.locator("#artboard-name")).not_to_contain_text("unsaved")
            self.assertTrue((root / "theme/icons/folder.png").exists())
            self.assertFalse((root / "theme/icons/game.png").exists())
            self.assertFalse((root / "theme/components/header.png").exists())

    def test_new_wallpaper_is_assigned_and_save_reopens_layers(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=backgrounds]").click()
            page.get_by_role("button", name="Edit / draw", exact=True).first.click()
            expect(page.locator("#canvas-stage")).to_be_visible()
            draw(page)
            page.get_by_role("button", name="Save artwork", exact=True).click()
            expect(page.locator("#artboard-name")).not_to_contain_text("unsaved")
            state = json.loads((root / "theme-project.json").read_text())
            self.assertEqual(
                state["config"]["backgrounds"]["top"], "backgrounds/top.png"
            )
            page.reload()
            page.locator("[data-section=backgrounds]").click()
            page.get_by_role("button", name="Edit / draw", exact=True).first.click()
            expect(page.locator("#layer-list .layer")).to_have_count(1)
            self.assertEqual(len(list((root / "artboards").glob("*.json"))), 1)

    def test_unsaved_manifest_navigation_and_inheritance_status(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=manifest]").click()
            raw = page.locator("textarea.raw")
            raw.fill(
                raw.input_value().replace(
                    "name=Untitled theme", "name=Saved on navigation"
                )
            )
            page.locator("[data-section=colors]").click()
            page.get_by_role("button", name="Cancel", exact=True).click()
            expect(page.locator("textarea.raw")).to_be_visible()
            self.assertIn("name=Saved on navigation", raw.input_value())
            page.locator("[data-section=colors]").click()
            page.get_by_role("button", name="Save and continue", exact=True).click()
            expect(page.locator("#project-name")).to_have_text("Saved on navigation")
            entry = page.locator(".field").filter(
                has=page.get_by_label("header text", exact=True)
            )
            expect(entry.locator(".inherit input")).to_be_checked()
            page.get_by_label("header text", exact=True).fill("#ffffff")
            page.get_by_label("header text", exact=True).press("Tab")
            expect(entry.locator(".inherit input")).not_to_be_checked()

    def test_audio_cue_conversion_works_with_role_defaults(self):
        with editor() as (page, root, expect):
            source = root / "cue.wav"
            with wave.open(str(source), "wb") as stream:
                stream.setparams((2, 2, 44100, 44100, "NONE", ""))
                stream.writeframes(
                    b"".join(
                        struct.pack(
                            "<hh",
                            *(int(math.sin(i * 2 * math.pi * 440 / 44100) * 8000),) * 2,
                        )
                        for i in range(44100)
                    )
                )
            page.locator("[data-section=audio]").click()
            page.get_by_label("Role", exact=True).select_option("cursor")
            self.assertLessEqual(
                float(page.get_by_label("Length seconds", exact=True).input_value()), 2
            )
            with page.expect_file_chooser() as chooser:
                page.get_by_role(
                    "button", name="Choose audio and convert…", exact=True
                ).click()
            chooser.value.set_files(str(source))
            expect(page.locator("audio")).to_have_count(1)
            with wave.open(str(root / "theme/sounds/cursor.wav")) as stream:
                self.assertEqual(stream.getnchannels(), 1)
                self.assertEqual(stream.getsampwidth(), 2)
                self.assertLessEqual(stream.getnframes() * 2, 65536)

    def test_generic_canvas_assignment_exports_and_installs_without_touching_other_files(
        self,
    ):
        with editor() as (page, root, expect):
            page.get_by_label("Author", exact=True).fill("Fixture contributor")
            page.get_by_label("Asset terms", exact=True).fill("CC0-1.0")
            page.get_by_role("button", name="Save project details", exact=True).click()
            answers = iter(["artwork/new.png", "256 x 192"])

            def answer(dialog):
                dialog.accept(next(answers))

            page.on("dialog", answer)
            page.locator("[data-stage=canvas]").click()
            page.get_by_role("button", name="New canvas", exact=True).click()
            expect(page.locator("#artboard-name")).to_contain_text("artwork/new.png")
            page.remove_listener("dialog", answer)
            draw(page)
            page.get_by_label("Artwork assignment", exact=True).select_option(
                label="Background / top"
            )
            page.get_by_role("button", name="Save artwork", exact=True).click()
            expect(page.locator("#artboard-name")).not_to_contain_text("unsaved")
            card = root / "card"
            card.mkdir()
            (card / "BOOT.NDS").write_bytes(b"keep loader")
            (card / "game.sav").write_bytes(b"keep save")
            page.on("dialog", lambda dialog: dialog.accept())
            page.locator("[data-section=publish]").click()
            install = page.locator("section.group").filter(
                has=page.get_by_role("heading", name="Install theme on SD", exact=True)
            )
            install.locator("input[type=text],input:not([type])").fill(str(card))
            page.get_by_role("button", name="Install this theme", exact=True).click()
            expect(page.locator("#toast")).to_contain_text("Installed")
            self.assertTrue(
                (
                    card / "_nds/dsi-frontend/themes/my-theme/backgrounds/top.png"
                ).is_file()
            )
            self.assertEqual((card / "BOOT.NDS").read_bytes(), b"keep loader")
            self.assertEqual((card / "game.sav").read_bytes(), b"keep save")
            expect(install.locator("input[type=text],input:not([type])")).to_have_value(
                str(card)
            )


if __name__ == "__main__":
    unittest.main()
