# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pack_splash
import splash_builder
import splash_motion
import splash_project


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "tile.png"
        image = Image.new("RGBA", (20, 12), (0, 0, 0, 0))
        for y in range(12):
            for x in range(20):
                if (x + y) % 4:
                    image.putpixel(
                        (x, y), (255 if x < 10 else 0, 255 if y < 6 else 0, 255, 255)
                    )
        image.save(self.image)

    def build(self, **options):
        return pack_splash.build(
            top=self.image,
            bottom_logo=self.image,
            fps=20,
            duration=2,
            background="#182838",
            layer_options=options,
        )

    def test_compression_preserves_pixels_and_keeps_small_raw_layers(self):
        large = self.root / "large.png"
        Image.new("RGB", (256, 192), "purple").save(large)
        tiny = self.root / "tiny.png"
        Image.new("RGB", (1, 1), "lime").save(tiny)
        for direct in (False, True):
            options = dict(
                top=large,
                bottom_logo=tiny,
                direct=direct,
                duration=2,
                layer_options={
                    "top": {"preset": "none"},
                    "bottom_logo": {"preset": "none", "fit": "native"},
                },
            )
            raw = pack_splash.build(**options)
            packed = pack_splash.build(**options, compress=True)
            self.assertEqual(packed[:8], b"GLOMSP03")
            self.assertEqual(packed[81], 1)
            self.assertEqual(packed[145], 0)
            self.assertLess(len(packed), len(raw))
            self.assertEqual(
                splash_builder.render(raw, 0).tobytes(),
                splash_builder.render(packed, 0).tobytes(),
            )

    def test_full_screen_sequences_fit_without_dropping_frames(self):
        frames = self.root / "frames"
        frames.mkdir()
        for index in range(64):
            Image.new("RGB", (256, 192), (index * 4, 0, 255 - index * 4)).save(
                frames / f"{index:03}.png"
            )
        options = dict(
            top=frames, bottom=frames, effect="none", fit="native", duration=3.2
        )
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            pack_splash.build(**options)
        data = pack_splash.build(**options, compress=True)
        self.assertEqual(data[:8], b"GLOMSP03")
        self.assertEqual(struct.unpack_from("<H", data, 16)[0], 192)
        for layer in range(2):
            self.assertEqual(
                struct.unpack_from("<4H", data, 36 + layer * 64), (256, 192, 64, 3)
            )

    def test_independent_layers_and_static_scale(self):
        data = self.build(
            top={"preset": "none", "fit": "native", "scale_from": 200, "scale_to": 200},
            bottom_logo={"preset": "fade-zoom", "delay": "0.5", "width": "40"},
        )
        self.assertEqual(data[:8], b"GLOMSP02")
        self.assertEqual(struct.unpack_from("<H", data, 16)[0], 120)
        first = splash_builder.render(data, 0)
        later = splash_builder.render(data, 60)
        self.assertEqual(
            first.crop((0, 0, 256, 192)).tobytes(),
            later.crop((0, 0, 256, 192)).tobytes(),
        )
        self.assertNotEqual(
            first.crop((0, 192, 256, 384)).tobytes(),
            later.crop((0, 192, 256, 384)).tobytes(),
        )
        self.assertLess(
            len(data), 10000
        )  # Motion reuses the image; no baked transition frames.

    def test_fit_modes_and_all_presets(self):
        for fit, size in (
            ("fit", (256, 154)),
            ("crop", (256, 192)),
            ("stretch", (256, 192)),
            ("native", (20, 12)),
        ):
            with self.subTest(fit=fit):
                data = self.build(top={"preset": "none", "fit": fit})
                self.assertEqual(struct.unpack_from("<2H", data, 36), size)
        for name in splash_motion.PRESETS:
            data = self.build(top={"preset": name, "fit": "native"})
            splash_builder.render(data, 17)
            self.assertEqual(
                splash_builder.render(data, 0, True).tobytes(),
                splash_builder.render(data, 90, True).tobytes(),
            )

    def test_invalid_and_unfinished_controls_fail_without_export(self):
        for options in (
            {"scale_from": 401},
            {"start_x": -513},
            {"scale_to": float("nan")},
            {"opacity_to": 101},
            {"transition": "0", "repeat": "loop"},
            {"delay": 2},
            {"easing": "unknown"},
            {"sequence": "unknown"},
            {"fit": "unknown"},
            {"scale_from": "2."},
            {"scale_to": "unfinished"},
        ):
            # A numeric entry like '2.' is valid once parsed; unfinished non-numbers are not.
            if options == {"scale_from": "2."}:
                self.build(top=options)
                continue
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.build(top=options)

    def test_project_migration_preserves_old_motion_and_backup(self):
        legacy = splash_project.default_state()
        legacy["format"] = 1
        del legacy["layers"]
        legacy["options"].update(effect="slide-left", transition="1.2", fit="crop")
        legacy["paths"]["top_logo"] = "tile.png"
        target = self.root / splash_project.PROJECT_FILE
        original = (json.dumps(legacy) + "\n").encode()
        target.write_bytes(original)
        workspace = splash_project.Workspace(self.root)
        self.assertEqual(workspace.state["format"], 2)
        self.assertEqual(workspace.state["layers"]["top"]["preset"], "none")
        self.assertEqual(workspace.state["layers"]["top_logo"]["preset"], "slide-left")
        self.assertEqual(workspace.state["layers"]["top_logo"]["transition"], "1.2")
        self.assertEqual(target.read_bytes(), original)
        workspace.state["layers"]["bottom"]["scale_from"] = "unfinished"
        workspace.save(workspace.state)
        self.assertEqual(target.with_name(target.name + ".bak").read_bytes(), original)
        self.assertEqual(
            splash_project.Workspace(self.root).state["layers"]["bottom"]["scale_from"],
            "unfinished",
        )

    @unittest.skipUnless(
        os.environ.get("GLOAM_SOURCE"),
        "Set GLOAM_SOURCE for native renderer comparison",
    )
    def test_native_and_pc_previews_match(self):
        gloam = Path(os.environ["GLOAM_SOURCE"])
        executable = self.root / "native-preview"
        subprocess.run(
            [
                "cc",
                "-std=c11",
                "-g",
                "-fsanitize=address,undefined",
                "-ffunction-sections",
                "-fdata-sections",
                "-Wl,--gc-sections",
                "-I" + str(gloam / "arm9/include"),
                "-I" + str(gloam / "third_party/stb"),
                "-I" + str(gloam / "third_party/lodepng"),
                str(gloam / "arm9/source/splash.c"),
                str(gloam / "arm9/source/image_decode.c"),
                str(ROOT / "tests/native_splash_preview.c"),
                "-o",
                str(executable),
            ],
            check=True,
        )
        gif = self.root / "colors.gif"
        Image.new("RGB", (7, 5), "red").save(
            gif,
            save_all=True,
            append_images=[
                Image.new("RGB", (7, 5), "lime"),
                Image.new("RGB", (7, 5), "blue"),
            ],
            duration=100,
            loop=0,
        )
        cases = [
            (name, {"preset": name, "fit": "native"}) for name in splash_motion.PRESETS
        ]
        cases += [
            (
                "custom",
                {
                    "preset": "custom",
                    "fit": "native",
                    "start_x": -150,
                    "start_y": 96,
                    "end_x": 130,
                    "end_y": -100,
                    "scale_from": 400,
                    "scale_to": 0,
                    "opacity_from": 40,
                    "opacity_to": 100,
                    "easing": "ease-in",
                    "repeat": "ping-pong",
                },
            )
        ]
        package, output = self.root / "test.gsp", self.root / "pixels.rgb"
        for index, (name, controls) in enumerate(cases):
            data = pack_splash.build(
                top=self.image,
                bottom_logo=gif,
                duration=2,
                background="#182838",
                direct=bool(index % 2),
                compress=bool(index % 3),
                layer_options={
                    "top": controls,
                    "bottom_logo": {
                        "preset": "slide-down",
                        "delay": "0.1",
                        "width": 30,
                        "sequence": splash_motion.REPEAT[index % 3],
                        "repeat": "loop",
                        "end_y": 85,
                    },
                },
            )
            package.write_bytes(data)
            for tick, reduced in (
                (0, False),
                (7, False),
                (17, False),
                (30, False),
                (65, False),
                (119, True),
            ):
                with self.subTest(preset=name, tick=tick, reduced=reduced):
                    subprocess.run(
                        [
                            str(executable),
                            str(package),
                            str(tick),
                            str(int(reduced)),
                            str(output),
                        ],
                        check=True,
                    )
                    self.assertEqual(
                        output.read_bytes(),
                        splash_builder.render(data, tick, reduced).tobytes(),
                    )


if __name__ == "__main__":
    unittest.main()
