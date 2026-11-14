"""Keep catalog compatibility and distributed assets consistent with each pack."""

import configparser
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_collection import package
from build_collection import PROFILES


class ThemeCollectionTests(unittest.TestCase):
    def test_catalog_and_pack_requirements_agree(self):
        catalog = json.loads((ROOT / "catalog.json").read_text())
        self.assertEqual({entry["id"] for entry in catalog["themes"]}, set(PROFILES))
        for entry in catalog["themes"]:
            with self.subTest(theme=entry["id"]):
                folder = ROOT / entry["path"]
                config = configparser.ConfigParser()
                config.read(folder / "theme.ini")
                self.assertEqual(
                    config.getint("theme", "version"), entry["theme_format"]
                )
                self.assertNotEqual(entry.get("minimum_gloam_version"), "1.0.0")
                self.assertIn("theme format 2", entry["requires_gloam"])
                self.assertEqual(config.get("components", "alpha"), "coverage")
                for role in ("ui", "heading"):
                    data = (folder / config.get("fonts", role)).read_bytes()
                    self.assertEqual(data[:8], b"DSFONT03")
                    self.assertEqual(
                        data[9],
                        12 if role == "ui" else PROFILES[entry["id"]]["heading"][3],
                    )
                for section in ("backgrounds", "audio"):
                    for key, path in (
                        config.items(section) if config.has_section(section) else []
                    ):
                        if key != "strength":
                            self.assertTrue((folder / path).is_file(), path)

    def test_install_archives_keep_notices_and_exclude_preview_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "themes.zip"
            package(archive, list(PROFILES))
            with zipfile.ZipFile(archive) as zipped:
                names = set(zipped.namelist())
                self.assertIn("licenses/GPL-3.0.txt", names)
                self.assertIn("licenses/README.md", names)
                for theme in PROFILES:
                    prefix = f"_nds/dsi-frontend/themes/{theme}/"
                    for required in (
                        "theme.ini",
                        "CREDITS.md",
                        "fonts/LICENSE.txt",
                        "fonts/ui.dsfont",
                        "fonts/heading.dsfont",
                    ):
                        self.assertIn(prefix + required, names)
                    for excluded in (
                        "README.md",
                        "preview.png",
                        "settings-preview.png",
                    ):
                        self.assertNotIn(prefix + excluded, names)
                self.assertFalse(
                    any(
                        name.startswith(("source/", "build/", "tools/"))
                        for name in names
                    )
                )


if __name__ == "__main__":
    unittest.main()
