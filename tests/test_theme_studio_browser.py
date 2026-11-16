# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional real-browser authoring workflow; set GLOAM_STUDIO_BROWSER to Chromium."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_builder import Server


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium / Playwright smoke test",
)
class ThemeBrowserTests(unittest.TestCase):
    def test_authoring_layers_reopen_and_export(self):
        from playwright.sync_api import sync_playwright, expect

        with tempfile.TemporaryDirectory() as folder, Server(folder) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with sync_playwright() as driver:
                    browser = driver.chromium.launch(
                        executable_path=os.environ["GLOAM_STUDIO_BROWSER"],
                        headless=True,
                        args=["--no-sandbox"],
                    )
                    page = browser.new_page(viewport=dict(width=1500, height=1000))
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("dialog", lambda dialog: dialog.accept())
                    page.goto("http://127.0.0.1:" + str(server.server_port))
                    expect(page.locator("#project-name")).to_have_text("Untitled theme")
                    page.get_by_label("Author", exact=True).fill("Fixture author")
                    page.get_by_label("Asset terms", exact=True).fill("CC0-1.0")
                    page.get_by_role(
                        "button", name="Save project details", exact=True
                    ).click()
                    expect(page.locator("#save-state")).to_have_text("Saved locally")
                    for kind in ("icons", "components"):
                        page.locator("[data-section=" + kind + "]").click()
                        page.get_by_role(
                            "button", name="Fill missing slots", exact=True
                        ).click()
                        expect(page.locator(".slot img")).to_have_count(
                            29 if kind == "icons" else 30
                        )
                    page.locator("[data-section=icons]").click()
                    page.locator('.slot[title="icons/folder.png"]').click()
                    expect(page.locator("#canvas-stage")).to_be_visible()
                    page.get_by_role("button", name="Duplicate", exact=True).click()
                    expect(page.locator("#layer-list .layer")).to_have_count(2)
                    page.get_by_role("button", name="Save artwork", exact=True).click()
                    expect(page.locator("#artboard-name")).not_to_contain_text(
                        "unsaved"
                    )
                    page.locator('.slot[title="icons/game.png"]').click()
                    expect(page.locator("#layer-list .layer")).to_have_count(1)
                    page.locator('.slot[title="icons/folder.png"]').click()
                    expect(page.locator("#layer-list .layer")).to_have_count(2)
                    for name in (
                        "colors",
                        "layout",
                        "backgrounds",
                        "fonts",
                        "audio",
                        "motion",
                        "splash",
                        "manifest",
                        "publish",
                    ):
                        page.locator("[data-section=" + name + "]").click()
                    page.locator("[data-section=manifest]").click()
                    raw = page.locator("textarea.raw")
                    raw.fill(
                        raw.input_value().replace(
                            "name=Untitled theme", "name=Browser authored"
                        )
                    )
                    page.keyboard.press("Control+s")
                    expect(page.locator("#project-name")).to_have_text(
                        "Browser authored"
                    )
                    page.locator("[data-section=publish]").click()
                    with page.expect_download() as download:
                        page.locator("#export").click()
                    self.assertEqual(download.value.suggested_filename, "my-theme.zip")
                    self.assertEqual(errors, [])
                    document = json.loads(
                        (Path(folder) / "theme-project.json").read_text()
                    )
                    self.assertEqual(document["metadata"]["author"], "Fixture author")
                    self.assertTrue((Path(folder) / "exports/my-theme.zip").is_file())
                    page.reload()
                    expect(page.locator("#project-name")).to_have_text(
                        "Browser authored"
                    )
                    browser.close()
            finally:
                server.shutdown()
                worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
