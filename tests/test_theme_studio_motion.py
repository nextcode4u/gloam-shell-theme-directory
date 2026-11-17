# SPDX-License-Identifier: GPL-3.0-or-later
"""Motion demonstrations explain their target, use prepared frames and stop on exit."""

import importlib.util
import io
import os
import unittest
from PIL import Image
from test_theme_studio_user_journeys import editor


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium motion checks",
)
class MotionJourney(unittest.TestCase):
    def test_header_import_play_stop_and_selection_feedback(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=motion]").click()
            expect(page.locator("#section-title")).to_have_text(
                "Header accent & selection feedback"
            )
            expect(page.locator("#inspector-content")).to_contain_text(
                "No header accent imported yet"
            )
            source = root / "two-frame.gif"
            Image.new("RGBA", (32, 32), "red").save(
                source,
                "GIF",
                save_all=True,
                append_images=[Image.new("RGBA", (32, 32), "blue")],
                duration=100,
            )
            with page.expect_file_chooser() as chooser:
                page.get_by_role(
                    "button", name="Import header GIF / PNG…", exact=True
                ).click()
            chooser.value.set_files(str(source))
            expect(page.locator("#inspector-content")).to_contain_text(
                "2 prepared frame(s)"
            )
            with page.expect_response(
                lambda r: (
                    "/api/motion-preview" in r.url
                    and "kind=ambient" in r.url
                    and "play=1" in r.url
                )
            ) as response:
                page.get_by_role(
                    "button", name="Play header accent", exact=True
                ).click()
            with Image.open(io.BytesIO(response.value.body())) as image:
                self.assertEqual(image.n_frames, 2)
            page.get_by_role("button", name="Stop header accent", exact=True).click()
            expect(page.locator('img[data-motion-demo="ambient"]')).to_have_attribute(
                "src", __import__("re").compile("play=0")
            )
            page.get_by_label("Selection feedback", exact=True).select_option("pulse")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            with page.expect_response(
                lambda r: (
                    "/api/motion-preview" in r.url
                    and "kind=focus" in r.url
                    and "play=1" in r.url
                )
            ) as response:
                page.get_by_role(
                    "button", name="Play selection feedback", exact=True
                ).click()
            with Image.open(io.BytesIO(response.value.body())) as image:
                self.assertEqual(image.n_frames, 3)
            page.locator("[data-stage=assets]").click()
            expect(page.locator('img[data-motion-demo="focus"]')).to_have_attribute(
                "src", __import__("re").compile("play=0")
            )
            page.locator("[data-section=layout]").click()
            expect(page.locator("img[data-motion-demo]")).to_have_count(0)
