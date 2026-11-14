# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable splash workspaces; project data never contains executable instructions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

PROJECT_FILE = "splash-project.json"
PATH_KEYS = ("top", "bottom", "top_logo", "bottom_logo", "sound")
DEFAULT_OPTIONS = {
    "effect": "fade",
    "fps": "20",
    "fit": "fit",
    "transition": "0.5",
    "duration": "",
    "poster": "",
    "logo_width": "128",
    "background": "#080e18",
}


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".splash-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def default_state():
    return {
        "format": 1,
        "paths": dict.fromkeys(PATH_KEYS, ""),
        "options": DEFAULT_OPTIONS.copy(),
        "direct": False,
        "reduced": False,
        "export_path": "",
    }


def validate(state):
    if (
        not isinstance(state, dict)
        or type(state.get("format")) is not int
        or state["format"] != 1
    ):
        raise ValueError(
            "Unsupported splash project version; the project was left unchanged."
        )
    for key, required in (("paths", PATH_KEYS), ("options", DEFAULT_OPTIONS)):
        values = state.get(key)
        if not isinstance(values, dict) or set(values) != set(required):
            raise ValueError(f"Invalid project {key}; the project was left unchanged.")
        if any(
            not isinstance(value, str) or len(value) > 4096 or "\0" in value
            for value in values.values()
        ):
            raise ValueError(f"Invalid project {key} value.")
    if any(type(state.get(key)) is not bool for key in ("direct", "reduced")):
        raise ValueError("Invalid project display options.")
    if (
        not isinstance(state.get("export_path"), str)
        or len(state["export_path"]) > 4096
    ):
        raise ValueError("Invalid project export path.")
    return state


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Choose a working folder.")
        self.path = self.root / PROJECT_FILE
        if self.path.is_symlink():
            raise ValueError(
                "The project file must be stored inside its working folder."
            )
        self.original = self._read()
        self.state = (
            validate(json.loads(self.original))
            if self.original is not None
            else default_state()
        )

    def _read(self):
        if not self.path.exists():
            return None
        if self.path.stat().st_size > 128 * 1024:
            raise ValueError("The project file exceeds 128 KiB.")
        return self.path.read_bytes()

    def reference(self, value):
        if not value:
            return ""
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.root / path
        path = path.resolve()
        return (
            path.relative_to(self.root).as_posix()
            if path.is_relative_to(self.root)
            else str(path)
        )

    def resolve(self, value):
        if not value:
            return ""
        path = Path(value)
        if path.is_absolute():
            return str(path)
        result = (self.root / path).resolve()
        if not result.is_relative_to(self.root):
            raise ValueError("A relative project path escapes its working folder.")
        return str(result)

    def save(self, state):
        validate(state)
        if self.path.is_symlink() or self._read() != self.original:
            raise ValueError(
                "This project changed in another window. Reopen it before saving."
            )
        for value in (*state["paths"].values(), state["export_path"]):
            self.resolve(value)
        data = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if data == self.original:
            return
        backup = self.root / (PROJECT_FILE + ".bak")
        if backup.is_symlink():
            raise ValueError("The project backup must be inside its working folder.")
        if self.original is not None:
            atomic_write(backup, self.original)
        atomic_write(self.path, data)
        self.original, self.state = data, state

    def import_asset(self, source):
        source = Path(source).resolve(strict=True)
        if source.is_relative_to(self.root):
            return source
        files = sorted(source.glob("*.png")) if source.is_dir() else [source]
        if not files or len(files) > 120 or any(not p.is_file() for p in files):
            raise ValueError(
                "Choose an image/audio file or a folder of 1–120 PNG frames."
            )
        if (
            any(p.stat().st_size > 64 * 1024 * 1024 for p in files)
            or sum(p.stat().st_size for p in files) > 256 * 1024 * 1024
        ):
            raise ValueError("Use files below 64 MiB and frame folders below 256 MiB.")
        assets = self.root / "assets"
        if assets.is_symlink() or not assets.resolve().is_relative_to(self.root):
            raise ValueError("The assets folder must remain inside the working folder.")
        assets.mkdir(exist_ok=True)
        # Hash the staged copy, so edits to the original cannot mislabel a copied asset.
        staging = Path(tempfile.mkdtemp(prefix=".import-", dir=assets))
        try:
            digest = hashlib.sha256()
            for file in files:
                copy = staging / file.name
                shutil.copyfile(file, copy)
                digest.update(file.name.encode("utf-8") + b"\0")
                with copy.open("rb") as stream:
                    for block in iter(lambda: stream.read(65536), b""):
                        digest.update(block)
            label = re.sub(r"[^\w. -]", "_", source.name)[:80] or "asset"
            target = assets / (digest.hexdigest()[:16] + "-" + label)
            if target.is_symlink():
                raise ValueError("An imported asset cannot be a symbolic link.")
            if target.exists():
                for file in files:
                    old = target / file.name if source.is_dir() else target
                    if (
                        not old.is_file()
                        or old.read_bytes() != (staging / file.name).read_bytes()
                    ):
                        raise ValueError(
                            "A cached asset was edited. Keep it and choose a new source name."
                        )
            elif source.is_dir():
                staging.replace(target)
            else:
                (staging / source.name).replace(target)
            return target
        finally:
            if staging.exists():
                shutil.rmtree(staging)


def recent_file():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
    return base / "Gloam" / "SplashBuilder" / "last-workspace.json"


def last_workspace():
    try:
        path = recent_file()
        if path.stat().st_size > 16384:
            return ""
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, str) and Path(value).is_dir() else ""
    except (OSError, ValueError):
        return ""


def remember_workspace(root):
    atomic_write(
        recent_file(), json.dumps(str(root), ensure_ascii=False).encode("utf-8")
    )
