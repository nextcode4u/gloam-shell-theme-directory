# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from splash_project import Workspace, PROJECT_FILE, default_state


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()

    def test_import_resume_and_move_workspace(self):
        source = self.root / "artwork.png"
        source.write_bytes(b"synthetic asset")
        workspace = Workspace(self.project)
        imported = workspace.import_asset(source)
        self.assertEqual(workspace.import_asset(source), imported)
        state = default_state()
        state["paths"]["top"] = workspace.reference(imported)
        state["options"].update(effect="reveal", duration="2.", fps="15")
        state["export_path"] = "splash.gsp"
        workspace.save(state)
        source.unlink()
        moved = self.root / "moved"
        shutil.move(self.project, moved)
        reopened = Workspace(moved)
        self.assertEqual(reopened.state, state)
        self.assertEqual(
            Path(reopened.resolve(state["paths"]["top"])).read_bytes(),
            b"synthetic asset",
        )
        self.assertEqual(
            reopened.resolve(state["export_path"]), str(moved / "splash.gsp")
        )

    def test_numbered_frames_are_copied_without_unrelated_files(self):
        frames = self.root / "frames"
        frames.mkdir()
        for name in ("frame01.png", "frame02.png", "notes.txt"):
            (frames / name).write_bytes(name.encode())
        workspace = Workspace(self.project)
        imported = workspace.import_asset(frames)
        self.assertEqual(
            {p.name for p in imported.iterdir()}, {"frame01.png", "frame02.png"}
        )
        self.assertEqual(workspace.import_asset(frames), imported)

    def test_backup_and_conflicting_editor(self):
        first = Workspace(self.project)
        first.save(default_state())
        second = Workspace(self.project)
        state = default_state()
        state["direct"] = True
        first.save(state)
        self.assertEqual(
            json.loads((self.project / (PROJECT_FILE + ".bak")).read_text()),
            default_state(),
        )
        with self.assertRaisesRegex(ValueError, "another window"):
            second.save(default_state())
        self.assertTrue(Workspace(self.project).state["direct"])

    def test_failed_atomic_write_preserves_project(self):
        workspace = Workspace(self.project)
        workspace.save(default_state())
        before = workspace.path.read_bytes()
        state = default_state()
        state["reduced"] = True
        replace = os.replace

        def failure(source, target):
            if Path(target) == workspace.path:
                raise OSError("disk full")
            return replace(source, target)

        with mock.patch(
            "splash_project.os.replace", side_effect=failure
        ), self.assertRaises(OSError):
            workspace.save(state)
        self.assertEqual(workspace.path.read_bytes(), before)
        self.assertFalse(list(self.project.glob(".splash-*.tmp")))

    def test_invalid_project_is_not_replaced(self):
        target = self.project / PROJECT_FILE
        for data in (b"broken", b'{"format":2}', b"x" * (128 * 1024 + 1)):
            target.write_bytes(data)
            with self.assertRaises(ValueError):
                Workspace(self.project)
            self.assertEqual(target.read_bytes(), data)

    def test_escaping_relative_reference_is_rejected(self):
        workspace = Workspace(self.project)
        state = default_state()
        state["paths"]["top"] = "../outside.png"
        with self.assertRaises(ValueError):
            workspace.save(state)
        self.assertFalse(workspace.path.exists())


if __name__ == "__main__":
    unittest.main()
