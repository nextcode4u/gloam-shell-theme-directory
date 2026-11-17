# SPDX-License-Identifier: GPL-3.0-or-later
"""Preview navigation zooms the image without clamping it or editing the theme."""

import importlib.util
import json
import os
import unittest
from test_theme_studio_user_journeys import editor


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium zoom checks",
)
class PreviewZoomJourneys(unittest.TestCase):
    def test_zoom_pan_back_and_fit_preserve_the_theme(self):
        with editor() as (page, root, expect):
            expect(page.locator("#preview")).to_have_js_property("naturalWidth", 256)
            saved = (root / "theme-project.json").read_bytes()
            original = page.locator("#preview").bounding_box()["width"]
            page.get_by_role("button", name="Zoom in", exact=True).click()
            self.assertGreater(
                page.locator("#preview").bounding_box()["width"], original
            )
            page.locator("#zoom").select_option("8")
            self.assertEqual(page.locator("#preview").bounding_box()["width"], 2048)
            viewport = page.locator("#preview-viewport")
            before = viewport.evaluate("(e) => ({left:e.scrollLeft, top:e.scrollTop})")
            box = viewport.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 - 80,
                box["y"] + box["height"] / 2 - 55,
                steps=5,
            )
            page.mouse.up()
            after = viewport.evaluate("(e) => ({left:e.scrollLeft, top:e.scrollTop})")
            self.assertAlmostEqual(after["left"] - before["left"], 80, delta=2)
            self.assertAlmostEqual(after["top"] - before["top"], 55, delta=2)
            page.locator("[data-stage=assets]").click()
            page.locator("#view-back").click()
            expect(page.locator("#zoom")).to_have_value("8")
            restored = viewport.evaluate(
                "(e) => ({left:e.scrollLeft, top:e.scrollTop})"
            )
            self.assertAlmostEqual(restored["left"], after["left"], delta=2)
            self.assertAlmostEqual(restored["top"], after["top"], delta=2)
            page.get_by_role("button", name="Fit", exact=True).click()
            expect(page.locator("#zoom")).to_have_value("fit")
            self.assertLessEqual(viewport.evaluate("(e) => e.scrollTop"), 2)
            self.assertLessEqual(viewport.evaluate("(e) => e.scrollLeft"), 2)
            viewport.focus()
            viewport.press("+")
            expect(page.locator("#zoom")).not_to_have_value("fit")
            viewport.press("0")
            expect(page.locator("#zoom")).to_have_value("fit")
            self.assertEqual((root / "theme-project.json").read_bytes(), saved)

    def test_scene_artwork_drag_is_separate_from_alt_drag_panning(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=layout]").click()
            page.get_by_label("top layout", exact=True).select_option("scene")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            page.locator("#guides").check()
            page.locator("#zoom").select_option("2")
            viewport = page.locator("#preview-viewport")
            viewport.evaluate("(e) => {e.scrollTop=0;e.scrollLeft=0}")
            box = page.locator("#preview").bounding_box()
            x, y = box["x"] + 38 * 2, box["y"] + 54 * 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 20, y + 20, steps=5)
            page.mouse.up()
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            layout = json.loads((root / "theme-project.json").read_text())["config"][
                "layout"
            ]
            self.assertEqual(
                (layout["scene_cover_x"], layout["scene_cover_y"]), ("28", "44")
            )
            self.assertEqual(viewport.evaluate("(e) => e.scrollTop"), 0)
            saved = (root / "theme-project.json").read_bytes()
            box = page.locator("#preview").bounding_box()
            x, y = box["x"] + 48 * 2, box["y"] + 64 * 2
            page.keyboard.down("Alt")
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x - 40, y - 40, steps=5)
            page.mouse.up()
            page.keyboard.up("Alt")
            self.assertGreater(viewport.evaluate("(e) => e.scrollTop"), 0)
            self.assertEqual((root / "theme-project.json").read_bytes(), saved)
