# SPDX-License-Identifier: GPL-3.0-or-later
"""Slow operations and rapid input must preserve a contributor's newest drawing."""

import importlib.util
import os
import threading
import time
import unittest
from unittest import mock
from test_theme_studio_user_journeys import editor, draw
from theme_builder import Studio


@unittest.skipUnless(
    os.environ.get("GLOAM_STUDIO_BROWSER") and importlib.util.find_spec("playwright"),
    "Optional Chromium authoring race checks",
)
class AuthoringEdges(unittest.TestCase):
    def test_typing_during_slow_manifest_save_preserves_the_newer_draft(self):
        original_action = Studio.action
        started = threading.Event()

        def action(studio, name, request):
            if name == "save" and "raw" in request:
                started.set()
                time.sleep(0.7)
            return original_action(studio, name, request)

        with (
            mock.patch.object(Studio, "action", action),
            editor() as (page, root, expect),
        ):
            page.locator("[data-section=manifest]").click()
            raw = page.locator("textarea.raw")
            first = raw.input_value().replace("Untitled theme", "First draft")
            with page.expect_response(
                lambda r: "/api/action" in r.url and "raw" in r.request.post_data_json
            ):
                raw.fill(first)
                page.get_by_role("button", name="Apply INI", exact=True).click()
                self.assertTrue(started.wait(3))
                raw.fill(first.replace("First draft", "Second draft"))
            expect(page.locator("#save-state")).to_have_text("Unsaved manifest")
            self.assertIn("Second draft", raw.input_value())
            page.get_by_role("button", name="Apply INI", exact=True).click()
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            expect(page.locator("#project-name")).to_have_text("Second draft")

    def test_export_does_not_publish_an_older_drawing_when_new_edits_arrive(self):
        original_action = Studio.action
        started = threading.Event()

        def action(studio, name, request):
            if name == "artboard-save":
                started.set()
                time.sleep(0.7)
            return original_action(studio, name, request)

        with (
            mock.patch.object(Studio, "action", action),
            editor() as (page, root, expect),
        ):
            page.get_by_label("Author", exact=True).fill("Audit fixture")
            page.get_by_label("Asset terms", exact=True).fill("CC0-1.0")
            page.get_by_role("button", name="Save project details", exact=True).click()
            page.locator("[data-section=icons]").click()
            page.locator('.slot[title="icons/folder.png"]').click()
            draw(page)
            with page.expect_response(
                lambda r: (
                    "/api/action" in r.url
                    and r.request.post_data_json.get("action") == "artboard-save"
                )
            ):
                page.locator("#export").click()
                self.assertTrue(started.wait(3))
                page.locator("#paint-color").fill("#00ff00")
                draw(page)
            expect(page.locator("#activity")).to_contain_text(
                "Newer edits arrived during save"
            )
            expect(page.locator("#artboard-name")).to_contain_text("unsaved")
            self.assertFalse((root / "exports/my-theme.zip").exists())

    def test_drawing_during_a_slow_save_stays_unsaved_until_its_own_save(self):
        original_action = Studio.action
        started = threading.Event()

        def action(studio, name, request):
            if name == "artboard-save":
                started.set()
                time.sleep(0.7)
            return original_action(studio, name, request)

        with (
            mock.patch.object(Studio, "action", action),
            editor() as (page, root, expect),
        ):
            page.locator("[data-section=icons]").click()
            page.locator('.slot[title="icons/folder.png"]').click()
            draw(page)
            with page.expect_response(
                lambda r: (
                    "/api/action" in r.url
                    and r.request.post_data_json.get("action") == "artboard-save"
                )
            ):
                page.get_by_role("button", name="Save artwork", exact=True).click()
                self.assertTrue(started.wait(3))
                page.locator("#paint-color").fill("#00ff00")
                draw(page)
            expect(page.locator("#save-state")).to_have_text("Unsaved artwork")
            expect(page.locator("#artboard-name")).to_contain_text("unsaved")
            newest = page.locator("#paint").evaluate("c => c.toDataURL()")
            page.get_by_role("button", name="Save artwork", exact=True).click()
            expect(page.locator("#save-state")).to_have_text("Saved locally")
            expect(page.locator("#artboard-name")).not_to_contain_text("unsaved")
            self.assertEqual(
                page.locator("#paint").evaluate("c => c.toDataURL()"), newest
            )
