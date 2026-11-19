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
    def test_reading_surface_opacity_controls_share_layout_values_and_persist(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=layout]").click()
            page.get_by_label("content opacity", exact=True).fill("37")
            page.get_by_label("content opacity", exact=True).press("Tab")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            page.locator("[data-section=backgrounds]").click()
            top = page.get_by_role(
                "heading", name="Top reading surface", exact=True
            ).locator("..")
            bottom = page.get_by_role(
                "heading", name="Bottom reading surface", exact=True
            ).locator("..")
            expect(top.get_by_role("checkbox")).to_be_checked()
            expect(
                page.get_by_label("Top reading surface opacity percent")
            ).to_have_value("37")
            slider = page.get_by_label("Top reading surface opacity slider")
            slider.focus()
            slider.press("Home")
            bottom_value = page.get_by_label("Bottom reading surface opacity percent")
            bottom_value.fill("65")
            bottom_value.press("Tab")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            expect(top.get_by_role("checkbox")).not_to_be_checked()
            expect(bottom.get_by_role("checkbox")).not_to_be_checked()
            config = json.loads((root / "theme-project.json").read_text())["config"][
                "layout"
            ]
            self.assertEqual(
                (
                    config["content_opacity"],
                    config["top_content_opacity"],
                    config["bottom_content_opacity"],
                ),
                ("37", "0", "65"),
            )
            top.get_by_role("checkbox").check()
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            page.reload()
            page.locator("[data-section=backgrounds]").click()
            expect(
                page.get_by_label("Top reading surface opacity percent")
            ).to_have_value("37")
            expect(
                page.get_by_label("Bottom reading surface opacity percent")
            ).to_have_value("65")
            config = json.loads((root / "theme-project.json").read_text())["config"][
                "layout"
            ]
            self.assertNotIn("top_content_opacity", config)
            self.assertEqual(config["bottom_content_opacity"], "65")

    def test_fixed_rail_controls_and_inherited_dock_defaults_stay_in_sync(self):
        with editor() as (page, root, expect):
            page.locator("[data-section=layout]").click()
            position = page.get_by_label("tabs position", exact=True)
            position.select_option("bottom")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            page.get_by_label("top layout", exact=True).select_option("sidebar_left")
            expect(position).to_be_disabled()
            expect(position).to_have_text("Fixed side rail")
            expect(page.get_by_label("tab gap", exact=True)).to_be_disabled()
            expect(page.get_by_label("tab visible", exact=True)).to_be_disabled()
            config = json.loads((root / "theme-project.json").read_text())["config"][
                "layout"
            ]
            self.assertNotIn("tabs_position", config)
            page.locator("#undo").click()
            expect(position).to_be_enabled()
            expect(position).to_have_value("bottom")
            page.locator("#redo").click()
            expect(position).to_be_disabled()
            page.get_by_label("tab style", exact=True).select_option("numbered")
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            config = json.loads((root / "theme-project.json").read_text())["config"][
                "layout"
            ]
            self.assertEqual(config["tab_style"], "numbered")
            page.get_by_label("top layout", exact=True).select_option("gallery")
            expect(position).to_be_enabled()
            expect(position).to_have_value("top")
            page.get_by_label("top layout", exact=True).select_option("portrait")
            expect(position).to_have_value("bottom")

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

    def test_existing_theme_content_preset_survives_an_unrelated_edit(self):
        with editor() as (page, root, expect):
            result = page.evaluate("""async () => {
                const response = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json',
                              'X-Studio-Token': document.body.dataset.token},
                    body: JSON.stringify({action: 'save',
                        raw: '[theme]\\nversion=2\\n[layout]\\ntop_content=context\\nicon_size=large\\n'})
                });
                return {ok: response.ok, body: await response.json()};
            }""")
            self.assertTrue(result['ok'], result['body'])
            page.reload()
            page.locator('[data-section=layout]').click()
            picker = page.get_by_label('top content', exact=True)
            expect(picker).to_have_value('context')
            expect(picker.locator('option')).to_have_count(4)
            page.get_by_label('icon size', exact=True).select_option('medium')
            expect(page.locator('#save-state')).to_have_text('Saved locally')
            self.assertIn('top_content=context', (root / 'theme/theme.ini').read_text())

    def test_top_content_presets_save_preview_and_leave_a_return_to_layout(self):
        with editor() as (page, root, expect):
            page.locator('[data-section=layout]').click()
            picker = page.get_by_label('top content', exact=True)
            picker.select_option('neighbors')
            expect(page.locator('#save-state')).to_have_text('Saved locally')
            expect(page.get_by_label('tabs position', exact=True)).to_be_disabled()
            config = json.loads((root / 'theme-project.json').read_text())['config']['layout']
            self.assertEqual(config['top_content'], 'neighbors')
            picker = page.get_by_label('top content', exact=True)
            picker.select_option('smart')
            expect(page.locator('#save-state')).to_have_text('Saved locally')
            picker = page.get_by_label('top content', exact=True)
            picker.select_option('theme')
            expect(page.locator('#save-state')).to_have_text('Saved locally')
            expect(page.get_by_label('tabs position', exact=True)).to_be_enabled()
            page.locator('[data-section=backgrounds]').click()
            page.locator('[data-section=layout]').click()
            expect(page.get_by_label('top content', exact=True)).to_have_value('theme')
