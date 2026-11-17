# SPDX-License-Identifier: GPL-3.0-or-later
"""A contributor's complete pack must survive conversion, export and installation."""

import base64
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_builder import Studio
from theme_project import ThemeProject
from theme_validate import check
from splash_project import Workspace
import theme_preview


class CompletePackJourney(unittest.TestCase):
    def test_full_pack_reopens_exports_and_installs_with_notices(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            studio = Studio(root)
            p = studio.project
            p.update(metadata=dict(author="Fixture contributor", license="See notices"))
            p.write_asset("notices/LICENSE.txt", b"Fixture artwork: CC0-1.0.")
            for kind in ("icons", "components"):
                studio.action("generate", dict(kind=kind, options={}))
            for role in ("top", "bottom"):
                image = Image.new("RGBA", (256, 192), "#28374b")
                stream = io.BytesIO()
                image.save(stream, "PNG")
                studio.action(
                    "image",
                    dict(
                        path=f"backgrounds/{role}.png",
                        data=base64.b64encode(stream.getvalue()).decode(),
                        options=dict(width=256, height=192),
                        binding=dict(section="backgrounds", key=role),
                    ),
                )
            for role in ("top_surface", "bottom_surface"):
                studio.action(
                    "material",
                    dict(
                        path=f"backgrounds/{role}.png",
                        options=dict(width=256, height=192, opacity=170),
                        binding=dict(section="backgrounds", key=role),
                    ),
                )
            font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
            if font.is_file():
                notice = Path("/usr/share/doc/fonts-dejavu-core/copyright")
                if notice.is_file():
                    p.write_asset("notices/DejaVu-LICENSE.txt", notice.read_bytes())
                for role in ("ui", "heading"):
                    studio.action(
                        "font",
                        dict(
                            role=role,
                            name=font.name,
                            data=base64.b64encode(font.read_bytes()).decode(),
                            options=dict(size=9, baseline=10, height=16),
                        ),
                    )
            sound = io.BytesIO()
            with wave.open(sound, "wb") as audio:
                audio.setparams((1, 2, 16000, 0, "NONE", ""))
                audio.writeframes(struct.pack("<h", 1000) * 16000)
            for role in ("music", "cursor", "confirm", "back"):
                studio.action(
                    "audio",
                    dict(
                        role=role,
                        name="fixture.wav",
                        data=base64.b64encode(sound.getvalue()).decode(),
                        options=dict(seconds=1),
                    ),
                )
            motion = io.BytesIO()
            frames = [Image.new("RGB", (32, 32), color) for color in ("red", "blue")]
            frames[0].save(
                motion, "GIF", save_all=True, append_images=frames[1:], duration=100
            )
            studio.action(
                "ambient",
                dict(
                    name="fixture.gif",
                    count=2,
                    data=base64.b64encode(motion.getvalue()).decode(),
                ),
            )
            splash_folder = root / "splash"
            splash_folder.mkdir()
            workspace = Workspace(splash_folder)
            workspace.state["paths"]["top"] = workspace.reference(
                workspace.import_asset(p.theme / "backgrounds/top.png")
            )
            workspace.state["options"]["duration"] = "1"
            workspace.save(workspace.state)
            studio.action("splash-build", {})
            p = ThemeProject(root)
            self.assertTrue(
                check(p.theme, p.data["config"], p.data["metadata"])["valid"]
            )
            source = os.environ.get("GLOAM_SOURCE")
            if source:
                native = theme_preview.native(p, Path(source) / "build/host/preview")
                self.assertEqual(native.size, (256, 396))
            archive = p.export()
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                for suffix in (
                    "assets.gfx",
                    "splash.gsp",
                    "sounds/loop.wav",
                    "sounds/confirm.wav",
                    "motion/ambient.gtm",
                    "notices/LICENSE.txt",
                ):
                    self.assertTrue(
                        any(n.endswith("/" + suffix) for n in names), suffix
                    )
                self.assertFalse(
                    any("/artboards/" in n or "/sources/" in n for n in names)
                )
            card = root / "card"
            card.mkdir()
            (card / "BOOT.NDS").write_bytes(b"keep boot")
            (card / "game.sav").write_bytes(b"keep save")
            target = p.install(card)
            self.assertTrue((target / "splash.gsp").is_file())
            self.assertEqual((card / "BOOT.NDS").read_bytes(), b"keep boot")
            self.assertEqual((card / "game.sav").read_bytes(), b"keep save")
            imported = root / "reimported"
            imported.mkdir()
            imported = ThemeProject(imported)
            imported.import_theme(archive)
            self.assertEqual(
                (imported.theme / "sounds/loop.wav").read_bytes(),
                (p.theme / "sounds/loop.wav").read_bytes(),
            )
            self.assertEqual(
                (imported.theme / "notices/LICENSE.txt").read_bytes(),
                b"Fixture artwork: CC0-1.0.",
            )
