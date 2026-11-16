# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable, non-executable theme projects and explicit runtime exports."""

from __future__ import annotations

import copy
import configparser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from PIL import Image, ImageOps
from splash_project import atomic_write
from theme_schema import defaults, PALETTES, ICONS, COMPONENTS
from theme_validate import inside, parse_ini, to_ini, check

PROJECT = "theme-project.json"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,63}\Z")


def safe_tree(folder):
    result, total = [], 0
    seen = set()
    for file in sorted(Path(folder).rglob("*")):
        if file.is_symlink():
            raise ValueError("Linked files are not supported.")
        if not file.is_file():
            continue
        relative = file.relative_to(folder).as_posix()
        inside(folder, relative)
        if relative.casefold() in seen:
            raise ValueError("Case-colliding files are not portable to an SD card.")
        seen.add(relative.casefold())
        size = file.stat().st_size
        total += size
        if size > MAX_FILE or total > MAX_TOTAL or len(result) >= 4096:
            raise ValueError("Theme exceeds the authoring import limit.")
        result.append((relative, file))
    return result


class ThemeProject:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Choose a working folder.")
        self.file = inside(self.root, PROJECT)
        self.theme = inside(self.root, "theme")
        self.undo_stack, self.redo_stack = [], []
        if self.file.exists():
            if self.file.stat().st_size > 262144:
                raise ValueError("Oversized project file.")
            self.data = json.loads(self.file.read_text("utf-8"))
            self.validate_state(self.data)
            # INI is deliberately editable outside the app; preserve it on reopen.
            if (self.theme / "theme.ini").is_file():
                self.data["config"] = parse_ini(
                    (self.theme / "theme.ini").read_text("utf-8-sig")
                )
        else:
            if self.theme.exists() and any(self.theme.iterdir()):
                raise ValueError(
                    "This folder has theme files but no project. Choose a new folder and import them."
                )
            self.data = dict(
                format=1,
                id="my-theme",
                metadata=dict(author="", license="", description="", credits=""),
                config=defaults(),
                provenance=[],
            )
            self.save()

    @staticmethod
    def validate_state(data):
        if (
            not isinstance(data, dict)
            or type(data.get("format")) is not int
            or data["format"] != 1
            or not ID.fullmatch(str(data.get("id", "")))
        ):
            raise ValueError("Unsupported or invalid theme project.")
        if not isinstance(data.get("metadata"), dict) or any(
            not isinstance(v, str) or len(v) > 32768 or "\0" in v
            for v in data["metadata"].values()
        ):
            raise ValueError("Invalid project metadata.")
        if not isinstance(data.get("config"), dict) or any(
            not isinstance(v, dict) for v in data["config"].values()
        ):
            raise ValueError("Invalid project settings.")
        if any(
            not isinstance(s, str) or not isinstance(k, str) or not isinstance(v, str)
            for s, fields in data["config"].items()
            for k, v in fields.items()
        ):
            raise ValueError("Project values must be strings.")
        parse_ini(to_ini(data["config"]))
        if (
            not isinstance(data.get("provenance"), list)
            or len(data["provenance"]) > 512
        ):
            raise ValueError("Invalid project source inventory.")

    def save(self):
        self.validate_state(self.data)
        self.theme.mkdir(parents=True, exist_ok=True)
        if self.file.exists():
            atomic_write(
                inside(self.root, "theme-project.previous.json"), self.file.read_bytes()
            )
        atomic_write(
            inside(self.theme, "theme.ini"), to_ini(self.data["config"]).encode()
        )
        atomic_write(
            self.file,
            (json.dumps(self.data, indent=2, ensure_ascii=False) + "\n").encode(),
        )

    def checkpoint(self, paths=()):
        snapshot = dict(state=copy.deepcopy(self.data), files={})
        for relative in paths:
            file = inside(self.theme, relative)
            snapshot["files"][relative] = file.read_bytes() if file.is_file() else None
        self.undo_stack.append(snapshot)
        # Bound retained undo bytes as well as count; source masters stay on disk.
        while len(self.undo_stack) > 30 or (
            len(self.undo_stack) > 1
            and sum(
                sum(len(v or b"") for v in item["files"].values())
                for item in self.undo_stack
            )
            > 64 * 1024 * 1024
        ):
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, redo=False):
        source, destination = (
            (self.redo_stack, self.undo_stack)
            if redo
            else (self.undo_stack, self.redo_stack)
        )
        if not source:
            return
        previous = source.pop()
        current = dict(state=copy.deepcopy(self.data), files={})
        for relative, value in previous["files"].items():
            self.clear_artboard(relative)
            target = inside(self.theme, relative)
            current["files"][relative] = (
                target.read_bytes() if target.is_file() else None
            )
            if value is None:
                target.unlink(missing_ok=True)
            else:
                atomic_write(target, value)
        destination.append(current)
        self.data = previous["state"]
        self.save()

    def update(self, config=None, raw=None, metadata=None, id=None):
        candidate = copy.deepcopy(self.data)
        if config is not None:
            candidate["config"] = config
        if raw is not None:
            candidate["config"] = parse_ini(raw)
        if metadata is not None:
            candidate["metadata"] = metadata
        if id is not None:
            candidate["id"] = id
        self.validate_state(candidate)
        self.checkpoint()
        self.data = candidate
        self.save()

    def palette(self, name):
        if name not in PALETTES:
            raise ValueError("Unknown palette.")
        config = copy.deepcopy(self.data["config"])
        config.setdefault("colors", {}).update(PALETTES[name])
        config["colors"].update(
            selection_text=PALETTES[name]["ink"], tab_text=PALETTES[name]["ink"]
        )
        self.update(config=config)

    def record_source(self, name, data):
        suffix = Path(name).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
            suffix = ".bin"
        digest = hashlib.sha256(data).hexdigest()
        target = inside(self.root, "sources/" + digest + suffix)
        if not target.exists():
            atomic_write(target, data)
        if not any(p.get("sha256") == digest for p in self.data["provenance"]):
            if len(self.data["provenance"]) >= 512:
                raise ValueError("Source inventory is full.")
            self.data["provenance"].append(
                dict(
                    name=Path(name).name,
                    sha256=digest,
                    path=target.relative_to(self.root).as_posix(),
                )
            )
        return target

    def write_asset(self, relative, data, source_name=None):
        if relative.casefold() == "theme.ini":
            raise ValueError("Use the manifest editor to change theme.ini.")
        if len(data) > MAX_FILE:
            raise ValueError("Asset exceeds 32 MiB.")
        target = inside(self.theme, relative)
        self.checkpoint([relative])
        if source_name:
            self.record_source(source_name, data)
        self.clear_artboard(relative)
        atomic_write(target, data)
        self.save()

    def clear_artboard(self, relative):
        name = hashlib.sha256(relative.encode()).hexdigest() + ".json"
        inside(self.root, "artboards/" + name).unlink(missing_ok=True)

    def remove_asset(self, relative):
        target = inside(self.theme, relative)
        if relative == "theme.ini":
            raise ValueError("Use the manifest editor to edit theme.ini.")
        self.clear_artboard(relative)
        self.checkpoint([relative])
        target.unlink(missing_ok=True)
        self.save()

    def image_asset(self, relative, data, options):
        if not relative.lower().endswith(".png"):
            raise ValueError("Converted artwork needs a .png destination.")
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 16777216:
                raise ValueError("Source image exceeds 16 megapixels.")
            image = ImageOps.exif_transpose(source).convert("RGBA")
        width, height = (
            int(options.get(k, v)) for k, v in (("width", 32), ("height", 32))
        )
        if not 1 <= width <= 512 or not 1 <= height <= 512:
            raise ValueError("Output dimensions must be 1–512.")
        mode = options.get("fit", "contain")
        if mode not in ("contain", "cover", "stretch", "native"):
            raise ValueError("Unsupported fit mode.")
        resample = (
            Image.Resampling.NEAREST
            if options.get("sampling") == "nearest"
            else Image.Resampling.LANCZOS
        )
        if options.get("flip_x"):
            image = ImageOps.mirror(image)
        if options.get("flip_y"):
            image = ImageOps.flip(image)
        angle = int(options.get("rotate", 0))
        if angle not in (0, 90, 180, 270):
            raise ValueError("Rotation must be 0, 90, 180 or 270.")
        if angle:
            image = image.rotate(angle, expand=True)
        if mode == "cover":
            image = ImageOps.fit(
                image,
                (width, height),
                method=resample,
                centering=(
                    float(options.get("anchor_x", 0.5)),
                    float(options.get("anchor_y", 0.5)),
                ),
            )
        elif mode == "stretch":
            image = image.resize((width, height), resample)
        else:
            if mode == "contain":
                image.thumbnail((width, height), resample)
            canvas = Image.new("RGBA", (width, height))
            canvas.alpha_composite(
                image, ((width - image.width) // 2, (height - image.height) // 2)
            )
            image = canvas
        opacity = max(0, min(100, int(options.get("opacity", 100))))
        image.putalpha(image.getchannel("A").point(lambda a: a * opacity // 100))
        output = io.BytesIO()
        image.save(output, "PNG", optimize=True)
        self.checkpoint([relative])
        self.record_source(options.get("source_name", "artwork.png"), data)
        self.clear_artboard(relative)
        atomic_write(inside(self.theme, relative), output.getvalue())
        self.save()

    def import_theme(self, source):
        source = Path(source).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="gloam-import-") as temp:
            stage = Path(temp) / "theme"
            stage.mkdir()
            if source.is_dir():
                entries = safe_tree(source)
                for relative, file in entries:
                    target = inside(stage, relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, target)
            else:
                with zipfile.ZipFile(source) as archive:
                    total = 0
                    seen = set()
                    for item in archive.infolist():
                        if item.is_dir():
                            continue
                        key = item.filename.casefold()
                        total += item.file_size
                        if (
                            key in seen
                            or item.file_size > MAX_FILE
                            or total > MAX_TOTAL
                            or len(seen) > 4096
                            or ((item.external_attr >> 16) & 0o170000) == 0o120000
                        ):
                            raise ValueError(
                                "Unsafe, duplicate or oversized theme ZIP."
                            )
                        seen.add(key)
                        target = inside(stage, item.filename)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(item) as stream:
                            data = stream.read(MAX_FILE + 1)
                        if len(data) != item.file_size:
                            raise ValueError("Truncated ZIP member.")
                        target.write_bytes(data)
                manifests = list(stage.rglob("theme.ini"))
                if len(manifests) != 1:
                    raise ValueError(
                        "Import a single theme ZIP, not a theme collection."
                    )
                stage = manifests[0].parent
            manifest = stage / "theme.ini"
            if not manifest.is_file():
                raise ValueError("Choose the folder containing theme.ini.")
            config = parse_ini(manifest.read_text("utf-8-sig"))
            # Keep the original package and all notices together. Imports cannot run code.
            for relative, file in safe_tree(stage):
                if file.suffix.lower() in (
                    ".exe",
                    ".dll",
                    ".nds",
                    ".dsi",
                    ".ps1",
                    ".py",
                    ".bat",
                    ".cmd",
                    ".sh",
                ):
                    raise ValueError("A theme may not contain executable files.")
            backup = inside(
                self.root,
                "imports/previous-theme-"
                + hashlib.sha256(to_ini(self.data["config"]).encode()).hexdigest()[:12],
            )
            backup = backup.with_name(backup.name + "-" + os.urandom(4).hex())
            if self.theme.exists():
                backup.parent.mkdir(exist_ok=True)
                shutil.copytree(self.theme, backup)
            replacement = Path(tempfile.mkdtemp(prefix=".theme-import-", dir=self.root))
            old = self.theme.with_name(".previous-theme-" + os.urandom(6).hex())
            try:
                shutil.copytree(stage, replacement, dirs_exist_ok=True)
                self.theme.rename(old)
                try:
                    replacement.rename(self.theme)
                except OSError:
                    old.rename(self.theme)
                    raise
                shutil.rmtree(old)
            finally:
                if replacement.exists():
                    shutil.rmtree(replacement)
            artboards = inside(self.root, "artboards")
            if artboards.exists():
                safe_tree(artboards)
                shutil.move(
                    str(artboards), str(backup.with_name(backup.name + "-layers"))
                )
            self.data["config"] = config
            source_id = source.stem if source.is_file() else source.name
            if ID.fullmatch(source_id):
                self.data["id"] = source_id
            self.data["metadata"] = dict(
                author="", license="", credits="Retain and review the imported notices."
            )
            self.data["metadata"]["description"] = (
                "Adapted from "
                + source.name
                + ". Retain and review the imported credits."
            )
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.save()

    def assets(self):
        result = []
        for relative, file in safe_tree(self.theme):
            entry = dict(path=relative, bytes=file.stat().st_size)
            if file.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
                try:
                    with Image.open(file) as image:
                        entry.update(width=image.width, height=image.height)
                except OSError:
                    pass
            result.append(entry)
        return result

    def state(self):
        return copy.deepcopy(self.data) | dict(
            workspace=str(self.root),
            raw=to_ini(self.data["config"]),
            assets=self.assets(),
            undo=bool(self.undo_stack),
            redo=bool(self.redo_stack),
            report=check(self.theme, self.data["config"], self.data["metadata"]),
        )

    def runtime_files(self):
        config = self.data["config"]
        names = {"theme.ini"}
        for section, fields in config.items():
            from theme_schema import SCHEMA

            for key, value in fields.items():
                if (
                    SCHEMA.get(section, {}).get(key, {}).get("type") != "path"
                    or value == "builtin"
                ):
                    continue
                if key == "directory":
                    directory = inside(self.theme, value)
                    for file in directory.glob("*.png") if directory.is_dir() else []:
                        if file.stem in (ICONS if section == "icons" else COMPONENTS):
                            names.add(file.relative_to(self.theme).as_posix())
                elif inside(self.theme, value).is_file():
                    names.add(value)
        if (self.theme / "splash.gsp").is_file():
            names.add("splash.gsp")
        # Licenses are never stripped from a theme distribution.
        for relative, file in safe_tree(self.theme):
            if file.suffix.lower() in (".md", ".txt", ".license") or re.search(
                "license|copying|notice|credits|ofl", file.name, re.I
            ):
                names.add(relative)
        return sorted(names)

    def prepare(self):
        from theme_native.pack_theme_assets import pack

        report = check(self.theme, self.data["config"], self.data["metadata"])
        if not report["valid"]:
            raise ValueError("\n".join(report["errors"]))
        try:
            data = pack(self.theme)
        except ValueError as exc:
            if str(exc) != "Prepared asset set is empty or exceeds 512 KiB":
                raise
            from theme_native.pack_theme_assets import screens, materials

            parser = configparser.ConfigParser(interpolation=None)
            parser.read_dict(self.data["config"])
            sprites = any(
                inside(self.theme, values["directory"] + "/" + name + ".png").is_file()
                for section, names in (("icons", ICONS), ("components", COMPONENTS))
                if (values := self.data["config"].get(section, {})).get("directory")
                for name in names
            )
            if (
                sprites
                or list(screens(self.theme, parser, inside))
                or list(materials(self.theme, parser, inside))
            ):
                raise
            self.data["config"].get("assets", {}).pop("prepared", None)
            self.save()
            return 0
        relative = self.data["config"].get("assets", {}).get("prepared", "assets.gfx")
        atomic_write(inside(self.theme, relative), data)
        self.data["config"].setdefault("assets", {})["prepared"] = relative
        self.data["config"]["theme"]["version"] = "2"
        self.save()
        return len(data)

    def export(self, prepare=True):
        if prepare:
            self.prepare()
        report = check(self.theme, self.data["config"], self.data["metadata"])
        if not report["valid"]:
            raise ValueError("\n".join(report["errors"]))
        metadata = self.data["metadata"]
        if (
            not metadata.get("author", "").strip()
            or not metadata.get("license", "").strip()
        ):
            raise ValueError(
                "Enter the author and license/attribution before exporting."
            )
        credit = (
            "\n".join(
                (
                    "# "
                    + self.data["config"].get("theme", {}).get("name", self.data["id"]),
                    "",
                    "Author: " + metadata["author"],
                    "Asset terms: " + metadata["license"],
                    "",
                    metadata.get("credits", ""),
                )
            )
            + "\n"
        )
        atomic_write(inside(self.theme, "AUTHORING-CREDITS.md"), credit.encode())
        out = inside(self.root, "exports/" + self.data["id"] + ".zip")
        out.parent.mkdir(exist_ok=True)
        handle, temp = tempfile.mkstemp(prefix=".theme-", suffix=".zip", dir=out.parent)
        os.close(handle)
        try:
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
                for relative in self.runtime_files():
                    archive.write(
                        inside(self.theme, relative),
                        "_nds/dsi-frontend/themes/" + self.data["id"] + "/" + relative,
                    )
            os.replace(temp, out)
        finally:
            Path(temp).unlink(missing_ok=True)
        return out

    def install(self, root, replace=False):
        archive = self.export()
        root = Path(root).resolve(strict=True)
        target = inside(root, "_nds/dsi-frontend/themes/" + self.data["id"])
        if target.exists() and not replace:
            raise ValueError("Theme already exists. Enable replacement to install it.")
        if target.exists():
            backup = inside(
                self.root,
                "exports/backups/" + self.data["id"] + "-" + os.urandom(4).hex(),
            )
            safe_tree(target)
            shutil.copytree(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".gloam-theme-", dir=target.parent))
        old = None
        try:
            with zipfile.ZipFile(archive) as package:
                prefix = "_nds/dsi-frontend/themes/" + self.data["id"] + "/"
                for name in package.namelist():
                    dest = inside(stage, name.removeprefix(prefix))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(package.read(name))
            if target.exists():
                old = target.with_name(".previous-" + os.urandom(6).hex())
                target.rename(old)
            try:
                stage.rename(target)
            except OSError:
                if old is not None:
                    old.rename(target)
                raise
            if old is not None:
                shutil.rmtree(old)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return target
