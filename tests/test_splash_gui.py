# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import splash_builder
from splash_project import Workspace


@unittest.skipUnless(
    os.name == "nt" or os.environ.get("DISPLAY"), "Needs a graphical display (or xvfb)"
)
class SplashGuiTests(unittest.TestCase):
    def test_escape_stops_animation_and_visible_close_returns_without_losing_the_project(
        self,
    ):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        from PIL import ImageTk

        for key, value in dict(
            tk=tk,
            ttk=ttk,
            filedialog=filedialog,
            messagebox=messagebox,
            ImageTk=ImageTk,
        ).items():
            setattr(splash_builder, key, value)
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder).resolve()
            source = project / "source.png"
            Image.new("RGB", (32, 32), "blue").save(source)
            root = splash_builder.create_root()
            builder = splash_builder.Builder(root, Workspace(project))
            closed = False
            try:
                builder.selected_asset(source, builder.paths["top"])
                root.deiconify()
                root.update()
                root.focus_force()
                builder.preview()
                self.assertIsNotNone(builder.timer)
                root.event_generate("<Escape>")
                root.update()
                self.assertIsNone(builder.timer)
                self.assertTrue(root.winfo_exists())
                builder.preview()
                builder.stop_button.invoke()
                self.assertIsNone(builder.timer)
                builder.close_button.invoke()
                closed = True
                self.assertTrue((project / "splash-project.json").is_file())
                self.assertTrue(
                    Workspace(project).resolve(Workspace(project).state["paths"]["top"])
                )
            finally:
                if not closed:
                    builder.close()

    def test_autosave_reopen_and_export_keep_editable_project(self):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        from PIL import ImageTk

        for key, value in dict(
            tk=tk,
            ttk=ttk,
            filedialog=filedialog,
            messagebox=messagebox,
            ImageTk=ImageTk,
        ).items():
            setattr(splash_builder, key, value)
        with tempfile.TemporaryDirectory() as temporary:
            # Windows CI can expose TEMP through an 8.3 alias such as RUNNER~1.
            base = Path(temporary).resolve()
            project = base / "working folder"
            project.mkdir()
            source = base / "source.png"
            Image.new("RGB", (256, 192), "purple").save(source)
            root = splash_builder.create_root()
            builder = splash_builder.Builder(root, Workspace(project))
            builder.selected_asset(source, builder.paths["top"])
            builder.layer_values["top"]["preset"].set("fade-zoom")
            builder.apply_preset("top")
            builder.layer_values["top"]["scale_from"].set("45")
            builder.layer_values["bottom"]["delay"].set("0.7")
            builder.values["duration"].set("2.5")
            root.after(850, root.quit)
            root.mainloop()
            self.assertIn("project saved", builder.workspace_status.get())
            data = builder.build()
            with mock.patch.object(
                filedialog, "asksaveasfilename", return_value=str(project / "intro.gsp")
            ):
                builder.export()
            self.assertEqual((project / "intro.gsp").read_bytes(), data)
            builder.close()
            source.unlink()
            root = splash_builder.create_root()
            reopened = splash_builder.Builder(root, Workspace(project))
            try:
                self.assertEqual(reopened.values["duration"].get(), "2.5")
                self.assertEqual(reopened.layer_values["top"]["scale_from"].get(), "45")
                self.assertEqual(reopened.layer_values["bottom"]["delay"].get(), "0.7")
                self.assertEqual(reopened.export_path, str(project / "intro.gsp"))
                self.assertEqual(reopened.build(), data)
                reopened.preview()
                self.assertIsNotNone(reopened.timer)
                reopened.stop()
                self.assertIsNone(reopened.timer)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
