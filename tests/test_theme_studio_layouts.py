# SPDX-License-Identifier: GPL-3.0-or-later
"""Layout controls expose usable artwork workflows, not just INI choices."""

import importlib.util
import json
import os
import unittest
from PIL import Image
from test_theme_studio_user_journeys import editor, draw


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium layout checks",
)
class LayoutJourneys(unittest.TestCase):
    def test_medium_and_new_compositions_are_selectable_and_persist(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=layout]").click()
            page.get_by_label("icon size", exact=True).select_option("medium")
            page.get_by_label("tabs position", exact=True).select_option("top")
            page.get_by_label("tab style", exact=True).select_option("icons")
            for name in ("panorama", "dossier", "portrait"):
                with page.expect_response(
                    lambda r: (
                        "/api/action" in r.url
                        and r.request.post_data_json.get("key") == "top_layout"
                        and r.request.post_data_json.get("value") == name
                    )
                ):
                    page.get_by_label("top layout", exact=True).select_option(name)
                expect(page.get_by_label("top layout", exact=True)).to_have_value(name)
            expect(page.get_by_label("Interface framing", exact=True)).to_be_visible()
            expect(page.locator("#inspector-content")).to_contain_text(
                "Interface framing: Full"
            )
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            page.reload()
            page.locator("[data-section=layout]").click()
            expect(page.get_by_label("icon size", exact=True)).to_have_value("medium")
            expect(page.get_by_label("top layout", exact=True)).to_have_value(
                "portrait"
            )
            config = json.loads((root / "theme-project.json").read_text())["config"]
            self.assertEqual(config["layout"]["tabs_position"], "top")

    def test_tab_skin_design_and_upload_target_the_configured_component_slot(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=components]").click()
            page.get_by_label("directory", exact=True).fill("skins")
            page.get_by_label("directory", exact=True).press("Tab")
            page.locator("[data-section=layout]").click()
            expect(page.locator("#inspector-content")).to_contain_text(
                "skins/tab-selected.png"
            )
            page.get_by_role("button", name="Design tab highlight…", exact=True).click()
            expect(page.locator("#artboard-name")).to_contain_text(
                "skins/tab-selected.png"
            )
            draw(page)
            page.get_by_role("button", name="Save artwork", exact=True).click()
            expect(page.locator("#artboard-name")).not_to_contain_text("unsaved")
            self.assertTrue((root / "theme/skins/tab-selected.png").is_file())
            page.locator("[data-section=layout]").click()
            image = root / "tab-source.png"
            Image.new("RGBA", (64, 32), "#b958e1").save(image)
            with page.expect_file_chooser() as chooser:
                page.get_by_role(
                    "button", name="Import tab highlight…", exact=True
                ).click()
            chooser.value.set_files(str(image))
            with page.expect_response(
                lambda r: (
                    "/api/action" in r.url
                    and r.request.post_data_json.get("action") == "image"
                )
            ):
                page.get_by_role(
                    "button", name="Convert and assign", exact=True
                ).click()
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            expect(page.locator("#artboard-name")).to_contain_text(
                "skins/tab-selected.png"
            )
            with Image.open(root / "theme/skins/tab-selected.png") as result:
                self.assertEqual(result.size, (32, 32))
                self.assertEqual(result.getpixel((16, 16)), (185, 88, 225, 255))
