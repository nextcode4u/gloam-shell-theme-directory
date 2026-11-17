#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local Theme Studio: browser workspace, Python converters and shared splash editor."""

from __future__ import annotations

import argparse
import base64
import copy
import io
import hashlib
import html as html_text
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from PIL import Image
from splash_project import atomic_write
from theme_project import ThemeProject, MAX_FILE, recover_project
from theme_schema import SCHEMA, PALETTES, ICONS, COMPONENTS
from theme_validate import inside
import theme_media
import theme_preview

ROOT = Path(__file__).resolve().parent


def choose(kind="directory", title="Choose a folder"):
    import splash_builder
    import tkinter as tk
    from tkinter import filedialog

    splash_builder.tk = tk
    root = splash_builder.create_root()
    try:
        if kind == "recover":
            from tkinter import messagebox

            return messagebox.askyesno(
                "Recover Theme Studio project?",
                title
                + "\n\nRestore saved project metadata? Current metadata is backed up under imports/recovery-*. Artwork files are kept.",
                parent=root,
            )
        if kind == "file":
            return filedialog.askopenfilename(title=title, parent=root)
        return filedialog.askdirectory(title=title, parent=root)
    finally:
        root.destroy()


def dialog(kind, title):
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--dialog",
            kind,
            "--title",
            title,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode:
        raise ValueError(
            result.stderr.strip()[-1000:]
            or "Folder picker could not open. You can type the path instead."
        )
    return json.loads(result.stdout)


def decode(value):
    if not isinstance(value, str) or len(value) > MAX_FILE * 4 // 3 + 1024:
        raise ValueError("Upload exceeds 32 MiB.")
    if "," in value:
        value = value.partition(",")[2]
    try:
        data = base64.b64decode(value, validate=True)
    except ValueError:
        raise ValueError("Invalid uploaded data.") from None
    if len(data) > MAX_FILE:
        raise ValueError("Upload exceeds 32 MiB.")
    return data


class Studio:
    def __init__(self, workspace):
        self.project = ThemeProject(workspace)
        self.lock = threading.RLock()
        self.splash_process = None

    def state(self):
        return self.project.state() | dict(
            schema=SCHEMA,
            palettes=PALETTES,
            icons=ICONS,
            components=COMPONENTS,
            ffmpeg=bool(shutil.which("ffmpeg")),
            splash_running=self.splash_process is not None
            and self.splash_process.poll() is None,
        )

    def action(self, action, request):
        p = self.project
        result = None
        if action == "state":
            pass
        elif action == "field":
            config = copy.deepcopy(p.data["config"])
            section, key = request["section"], request["key"]
            if section not in SCHEMA or key not in SCHEMA[section]:
                raise ValueError("Unknown theme field.")
            if request.get("inherit"):
                config.get(section, {}).pop(key, None)
            else:
                config.setdefault(section, {})[key] = str(request.get("value", ""))
            if (
                section == "layout"
                and key == "top_layout"
                and config.get(section, {}).get(key, "sidebar")
                not in theme_preview.COMPOSED_LAYOUTS
            ):
                config.get(section, {}).pop("tabs_position", None)
            p.update(config=config)
        elif action == "save":
            p.update(
                **{
                    k: request[k]
                    for k in ("config", "raw", "metadata", "id")
                    if k in request
                }
            )
        elif action == "undo":
            p.undo()
        elif action == "redo":
            p.undo(True)
        elif action == "palette":
            p.palette(request["name"])
        elif action == "choose":
            result = dialog(
                request.get("kind", "directory"),
                request.get("title", "Choose a folder"),
            )
        elif action == "workspace":
            folder = Path(request["path"]).expanduser()
            if request.get("create"):
                folder.mkdir(parents=True, exist_ok=True)
            self.project = ThemeProject(folder)
        elif action == "import":
            p.import_theme(request["path"])
        elif action == "upload":
            data = decode(request["data"])
            if request.get("format") == "font":
                from theme_validate import font_info

                font_info(data, request.get("heading", False))
            p.write_asset(
                request["path"], data, request.get("name"), request.get("binding")
            )
        elif action == "image":
            p.image_asset(
                request["path"],
                decode(request["data"]),
                request.get("options", {}),
                request.get("binding"),
            )
        elif action == "artboard-load":
            inside(p.theme, request["path"])
            name = hashlib.sha256(request["path"].encode()).hexdigest() + ".json"
            file = inside(p.root, "artboards/" + name)
            result = (
                json.loads(file.read_text("utf-8"))
                if file.is_file() and file.stat().st_size <= MAX_FILE
                else None
            )
        elif action == "artboard-save":
            if not request["path"].lower().endswith(".png"):
                raise ValueError("Artwork needs a .png destination.")
            document = request["document"]
            width, height = int(document["width"]), int(document["height"])
            if (
                not 1 <= width <= 512
                or not 1 <= height <= 512
                or not isinstance(document.get("layers"), list)
                or not 1 <= len(document["layers"]) <= 16
            ):
                raise ValueError("An artboard needs 1–16 layers at up to 512×512.")
            for layer in document["layers"]:
                if (
                    not isinstance(layer.get("name"), str)
                    or len(layer["name"]) > 128
                    or layer.get("blend")
                    not in ("source-over", "multiply", "screen", "overlay")
                    or not 0 <= float(layer["opacity"]) <= 1
                ):
                    raise ValueError("Invalid artboard layer.")
                with Image.open(io.BytesIO(decode(layer["data"]))) as image:
                    if image.size != (width, height):
                        raise ValueError(
                            "Artboard layers must match the canvas dimensions."
                        )
            data = decode(request["data"])
            with Image.open(io.BytesIO(data)) as image:
                if image.size != (width, height) or image.format != "PNG":
                    raise ValueError("Artboard output must be a matching PNG.")
            encoded = json.dumps(document).encode()
            if len(encoded) > MAX_FILE:
                raise ValueError("Artboard project is oversized.")
            name = hashlib.sha256(request["path"].encode()).hexdigest() + ".json"
            p.write_asset(request["path"], data, binding=request.get("binding"))
            atomic_write(inside(p.root, "artboards/" + name), encoded)
        elif action == "remove":
            p.remove_asset(request["path"])
        elif action == "copy":
            data = inside(p.theme, request["source"]).read_bytes()
            targets = request["targets"]
            if not isinstance(targets, list) or len(targets) > 64:
                raise ValueError("Copy to at most 64 asset slots.")
            for name in targets:
                inside(p.theme, name)
            p.checkpoint(targets)
            for name in targets:
                p.clear_artboard(name)
                atomic_write(inside(p.theme, name), data)
            p.save()
        elif action == "material":
            p.write_asset(
                request["path"],
                theme_media.png(theme_media.material(request["options"])),
                binding=request.get("binding"),
            )
        elif action == "generate":
            result = theme_media.generate_set(
                p, request["kind"], request.get("options", {})
            )
        elif action == "atlas":
            result = theme_media.atlas_import(
                p,
                decode(request["data"]),
                request["kind"],
                int(request["columns"]),
                int(request["rows"]),
            )
        elif action == "font":
            from theme_native.pack_theme_font import pack_font

            data = decode(request["data"])
            role = request.get("role", "ui")
            if role not in ("ui", "heading"):
                raise ValueError("Unknown font role.")
            options = request.get("options", {})
            height = 12 if role == "ui" else int(options.get("height", 16))
            source = p.record_source(request.get("name", "font.ttf"), data)
            converted = pack_font(
                source,
                int(options.get("size", 10)),
                int(options.get("baseline", 10)),
                latin1=bool(options.get("latin1", True)),
                proportional=True,
                height=height,
                edge_shift=int(options.get("edge_shift", 0)),
                weight=float(options["weight"]) if options.get("weight") else None,
            )
            relative = "fonts/" + role + ".dsfont"
            p.write_asset(relative, converted, binding=dict(section="fonts", key=role))
        elif action == "audio":
            role = request.get("role", "music")
            if role not in ("music", "cursor", "confirm", "back"):
                raise ValueError("Unknown audio role.")
            source = p.record_source(
                request.get("name", "audio.wav"), decode(request["data"])
            )
            data = theme_media.convert_audio(
                source, music=role == "music", **request.get("options", {})
            )
            relative = "sounds/" + ("loop" if role == "music" else role) + ".wav"
            p.write_asset(relative, data, binding=dict(section="audio", key=role))
        elif action == "ambient":
            data = decode(request["data"])
            converted = theme_media.ambient(data, int(request.get("count", 8)))
            p.record_source(request.get("name", "accent.gif"), data)
            p.write_asset(
                "motion/ambient.gtm",
                converted,
                binding=dict(section="motion", key="ambient"),
            )
        elif action == "splash-open":
            if self.splash_process is None or self.splash_process.poll() is not None:
                folder = inside(p.root, "splash")
                folder.mkdir(exist_ok=True)
                self.splash_process = subprocess.Popen(
                    [
                        sys.executable,
                        str(ROOT / "splash_builder.py"),
                        "--workspace",
                        str(folder),
                    ]
                )
        elif action == "splash-build":
            import splash_project, pack_splash

            workspace = splash_project.Workspace(inside(p.root, "splash"))
            state = workspace.state
            values = {
                key: workspace.resolve(value) or None
                for key, value in state["paths"].items()
            }
            values.update(state["options"])
            for key in ("duration", "poster"):
                values[key] = float(values[key]) if values[key] else None
            for key in ("fps", "logo_width"):
                values[key] = int(values[key])
            values["transition"] = float(values["transition"])
            values.update(
                direct=state["direct"], compress=True, layer_options=state["layers"]
            )
            data = pack_splash.build(**values)
            p.write_asset("splash.gsp", data)
            result = len(data)
        elif action == "prepare":
            result = p.prepare()
        elif action == "export":
            result = str(p.export(request.get("prepare", True)))
        elif action == "install":
            result = str(p.install(request["path"], bool(request.get("replace"))))
        elif action == "native":
            p.prepare()
            image = theme_preview.native(
                p, request["executable"], request.get("sample", "browser")
            )
            atomic_write(
                inside(p.root, "exports/native-preview.png"), theme_media.png(image)
            )
            result = "native-preview.png"
        elif action == "open-folder":
            relative = request.get("path", "exports")
            folder = p.root if relative == "." else inside(p.root, relative)
            folder.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(
                    ["xdg-open", str(folder)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        else:
            raise ValueError("Unknown editor action.")
        return dict(state=self.state(), result=result)


class ProjectOpenError(ValueError):
    pass


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace, port=0):
        try:
            self.studio = Studio(workspace)
        except Exception as error:
            raise ProjectOpenError(str(error)) from error
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, data, kind="application/json", status=200):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'",
        )
        try:
            self.end_headers()
            self.wfile.write(data)
        except ConnectionError:
            # Navigation cancels obsolete preview requests; this is not a save failure.
            pass

    def allowed(self, api=False):
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != origin.removeprefix("http://"):
            return False
        if self.headers.get("Origin") not in (None, origin):
            return False
        if api:
            token = (
                self.headers.get("X-Studio-Token", "")
                or parse_qs(urlsplit(self.path).query).get("token", [""])[0]
            )
            return secrets.compare_digest(token, self.server.token)
        return True

    def do_GET(self):
        try:
            route = urlsplit(self.path)
            name = unquote(route.path)
            if not self.allowed():
                self.send({"error": "Invalid local origin."}, status=403)
                return
            if name == "/":
                html = (
                    (ROOT / "theme_studio/index.html")
                    .read_text("utf-8")
                    .replace("__TOKEN__", self.server.token)
                )
                self.send(html.encode(), "text/html; charset=utf-8")
                return
            if name == "/guide":
                guide = ROOT.parent / "docs/THEME_STUDIO.md"
                text = guide.read_text("utf-8")
                page = (
                    '<html lang="en"><meta charset="utf-8"><title>Theme Studio guide</title><body style="max-width:90ch;margin:40px auto;padding:20px;background:#181b20;color:#eceef4"><nav><button id="help-close">Close help / return to editor</button> <a href="/" style="color:#c2b0f3">Open editor</a></nav><p>Your original editor stays open in its tab.</p><pre style="white-space:pre-wrap;font:14px/1.7 system-ui">'
                    + html_text.escape(text)
                    + '</pre><script src="/guide-actions.js"></script></body></html>'
                )
                self.send(page.encode(), "text/html; charset=utf-8")
                return
            if name == "/guide-actions.js":
                self.send(
                    b'document.getElementById("help-close").onclick=()=>window.close();',
                    "text/javascript",
                )
                return
            if name == "/gloam-icon.png":
                self.send(
                    (ROOT / "theme_studio/gloam-icon.png").read_bytes(), "image/png"
                )
                return
            if name in ("/studio.js", "/studio.css"):
                self.send(
                    (ROOT / "theme_studio" / name[1:]).read_bytes(),
                    "text/javascript" if name.endswith(".js") else "text/css",
                )
                return
            if not self.allowed(True):
                self.send({"error": "Editor token required."}, status=403)
                return
            query = parse_qs(route.query)
            with self.server.studio.lock:
                p = self.server.studio.project
                if name == "/api/state":
                    self.send(self.server.studio.state())
                elif name == "/api/preview":
                    image = theme_preview.render(
                        p,
                        query.get("sample", ["browser"])[0],
                        query.get("view", [None])[0],
                        int(query.get("selected", ["1"])[0]),
                        query.get("guides", ["0"])[0] == "1",
                    )
                    self.send(theme_media.png(image), "image/png")
                elif name == "/api/motion-preview":
                    self.send(
                        theme_preview.motion_preview(
                            p,
                            query.get("kind", ["ambient"])[0],
                            query.get("play", ["0"])[0] == "1",
                        ),
                        "image/png",
                    )
                elif name in ("/api/asset", "/api/export-file"):
                    root = (
                        p.theme if name == "/api/asset" else inside(p.root, "exports")
                    )
                    file = inside(root, query.get("path", [""])[0])
                    if not file.is_file() or file.stat().st_size > MAX_FILE:
                        raise ValueError("Missing or oversized asset.")
                    kind = (
                        mimetypes.guess_type(str(file))[0] or "application/octet-stream"
                    )
                    if file.suffix.lower() not in (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".wav",
                        ".zip",
                    ):
                        kind = "application/octet-stream"
                    self.send(file.read_bytes(), kind)
                else:
                    self.send({"error": "Not found."}, status=404)
        except (ValueError, OSError, KeyError) as exc:
            self.send({"error": str(exc)}, status=400)

    def do_POST(self):
        if not self.allowed(True):
            self.send({"error": "Editor token / origin rejected."}, status=403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_FILE * 4 // 3 + 32768:
                raise ValueError("Request exceeds upload limit.")
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict):
                raise ValueError("Expected an editor request.")
            if urlsplit(self.path).path == "/api/close":
                self.send({"result": "Closed"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if urlsplit(self.path).path != "/api/action":
                raise ValueError("Unknown endpoint.")
            with self.server.studio.lock:
                self.send(self.server.studio.action(request.pop("action", ""), request))
        except Exception as exc:
            # User input/converter errors stay visible; saved projects remain reopenable.
            self.send({"error": str(exc)[:3000]}, status=400)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--recover",
        action="store_true",
        help="Restore saved project metadata, retaining the damaged originals",
    )
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--dialog", choices=("file", "directory", "recover"))
    parser.add_argument("--title", default="Choose a folder")
    args = parser.parse_args(argv)
    if args.dialog:
        print(json.dumps(choose(args.dialog, args.title)))
        return
    folder = args.workspace or dialog(
        "directory", "Create or reopen a Theme Studio working folder"
    )
    if not folder:
        return
    Path(folder).mkdir(parents=True, exist_ok=True)
    try:
        if args.recover:
            recover_project(folder)
        server = Server(folder, args.port)
    except (ProjectOpenError, ValueError) as error:
        if args.no_browser or args.recover:
            parser.exit(
                1,
                "Project not opened: "
                + str(error)
                + "\nUse --recover with this working folder if saved metadata is available.\n",
            )
        if not dialog("recover", "The project could not open: " + str(error)):
            return
        try:
            recover_project(folder)
            server = Server(folder, args.port)
        except Exception as retry_error:
            parser.exit(1, "Recovery could not complete: " + str(retry_error) + "\n")
    except (OSError, OverflowError) as error:
        parser.exit(1, "Could not start the local editor: " + str(error) + "\n")
    with server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print("Gloam Theme Studio: " + url, flush=True)
        print("Working folder: " + str(server.studio.project.root), flush=True)
        print("Keep this window open. Ctrl+C stops the local editor.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
