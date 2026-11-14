#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small contributor UI for splash packages; independent of the future theme builder."""

from __future__ import annotations

import hashlib
import argparse
import os
from pathlib import Path
import struct
import sys
import time

from PIL import Image

import pack_splash
import splash_project


def create_root():
    """Keep older Windows Python installs usable inside the private environment."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        # CPython #125235: Python 3.13.0 looks in the venv for base Tcl data.
        if (
            os.name != "nt"
            or sys.prefix == sys.base_prefix
            or "init.tcl" not in str(error)
        ):
            raise
        base = Path(sys.base_prefix) / "tcl"
        libraries = {
            "TCL_LIBRARY": base / f"tcl{tk.TclVersion}",
            "TK_LIBRARY": base / f"tk{tk.TkVersion}",
        }
        if (
            not (libraries["TCL_LIBRARY"] / "init.tcl").is_file()
            or not (libraries["TK_LIBRARY"] / "tk.tcl").is_file()
        ):
            raise
        previous = {name: os.environ.get(name) for name in libraries}
        try:
            os.environ.update({name: str(path) for name, path in libraries.items()})
            root = tk.Tk()
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
    root.withdraw()
    return root


def render(data: bytes, tick: int, reduced=False) -> Image.Image:
    """PC preview of builder-owned output, using the same prepared pixels/timing."""
    if reduced:
        tick = struct.unpack_from("<H", data, 18)[0]
    screens = Image.new("RGB", (256, 384), "black")
    for i in range(data[20]):
        (
            screen,
            fmt,
            effect,
            _,
            w,
            h,
            count,
            hold,
            x,
            y,
            delay,
            transition,
            offset,
            size,
            _,
        ) = struct.unpack_from("<4B4H2h2H3I", data, 32 + i * 32)
        if tick < delay and not reduced:
            continue
        elapsed = max(0, tick - delay)
        frame = min(count - 1, elapsed // hold)
        progress = (
            32
            if reduced or not effect or elapsed >= transition
            else elapsed * 32 // transition
        )
        if fmt:
            palette = struct.unpack_from("<256H", data, offset)
            start = offset + 512 + frame * w * h
            words = [palette[index] for index in data[start : start + w * h]]
        else:
            words = struct.unpack_from(f"<{w * h}H", data, offset + frame * w * h * 2)
        image = Image.new("RGBA", (w, h))
        image.putdata(
            [
                (
                    (word & 31) * 255 // 31,
                    ((word >> 5) & 31) * 255 // 31,
                    ((word >> 10) & 31) * 255 // 31,
                    (
                        (progress * 255 // 32 if effect == 1 else 255)
                        if word & 0x8000
                        else 0
                    ),
                )
                for word in words
            ]
        )
        if effect == 2:
            y += (32 - progress) * 24 // 32
        if effect == 3:
            x += (32 - progress) * 24 // 32
        if effect == 4:
            image = image.crop((0, 0, w * progress // 32, h))
        # A moving lower-screen layer cannot spill into the other screen.
        image = image.crop(
            (0, 0, min(image.width, 256 - x), min(image.height, 192 - y))
        )
        screens.paste(image, (x, screen * 192 + y), image)
    return screens


def install_custom(root: Path, data: bytes) -> Path:
    """Use content-addressed assets; an interrupted settings write keeps the old splash."""
    root = root.resolve(strict=True)
    folder = root / "_nds/dsi-frontend"
    if not (folder / "splashes").resolve().is_relative_to(root):
        raise ValueError("The splash folder must remain inside the selected SD root.")
    state = folder / "state.ini"
    if state.is_symlink() or (folder / "state.bak").is_symlink():
        raise ValueError("Settings must be regular files on the selected SD root.")
    if state.exists() and state.stat().st_size > 128 * 1024:
        raise ValueError("Settings exceed the 128 KiB limit.")
    previous = state.read_bytes() if state.exists() else b"version=1\n"
    text = previous.decode("utf-8")
    lines = text.splitlines()
    if (
        len(previous) > 128 * 1024
        or not lines
        or lines[0] != "version=1"
        or "\0" in text
        or any(len(line.encode()) >= 1024 for line in lines)
    ):
        raise ValueError(
            "Settings are invalid or too large. Restore a valid state.ini before installing."
        )
    name = "custom-" + hashlib.sha256(data).hexdigest()[:12] + ".gsp"
    target = folder / "splashes" / name
    if target.is_symlink():
        raise ValueError("The splash must be a regular file inside the SD root.")
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError(
                "The destination contains a different package. Keep the original file."
            )
    else:
        pack_splash.write_package(target, data)
    updates = {
        "splash_mode": "2",
        "splash_path": "sd:/_nds/dsi-frontend/splashes/" + name,
    }
    retained = [line for line in lines if line.partition("=")[0] not in updates]
    updated = (
        "\n".join(retained + [f"{key}={value}" for key, value in updates.items()])
        + "\n"
    ).encode()
    if state.exists():
        pack_splash.write_package(folder / "state.bak", previous, replace=True)
    pack_splash.write_package(state, updated, replace=state.exists())
    return target


class Builder:
    def __init__(self, root, workspace=None):
        self.root = root
        self.workspace = workspace
        self.autosave_timer = None
        self.restoring = True
        self.export_path = ""
        self.data = None
        self.timer = None
        root.title("Gloam Splash Builder")
        root.minsize(980, 690)
        workspace_bar = ttk.Frame(root, padding=(18, 10, 18, 0))
        workspace_bar.pack(fill="x")
        self.workspace_status = tk.StringVar(
            value="Choose a working folder to save your project."
        )
        ttk.Label(
            workspace_bar, textvariable=self.workspace_status, wraplength=700
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            workspace_bar, text="Open working folder…", command=self.open_workspace
        ).pack(side="left", padx=6)
        ttk.Button(workspace_bar, text="Save project", command=self.save_project).pack(
            side="left"
        )
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        left = ttk.Frame(frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        frame.columnconfigure(0, weight=1)
        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="n")
        ttk.Label(
            left, text="Create a startup splash", font=("TkDefaultFont", 17, "bold")
        ).pack(anchor="w")
        ttk.Label(
            left,
            text="Import images or animations. Gloam plays the prepared package.",
            wraplength=580,
        ).pack(anchor="w", pady=(6, 14))
        self.paths = {}
        for key, label in (
            ("top", "Top screen"),
            ("bottom", "Bottom screen"),
            ("top_logo", "Top overlay / logo"),
            ("bottom_logo", "Bottom overlay / logo"),
        ):
            ttk.Label(left, text=label).pack(anchor="w")
            row = ttk.Frame(left)
            row.pack(fill="x", pady=(3, 9))
            variable = tk.StringVar()
            self.paths[key] = variable
            ttk.Entry(row, textvariable=variable).pack(
                side="left", fill="x", expand=True
            )
            ttk.Button(
                row, text="File…", command=lambda v=variable: self.choose_file(v)
            ).pack(side="left", padx=4)
            ttk.Button(
                row, text="Frames…", command=lambda v=variable: self.choose_frames(v)
            ).pack(side="left")
        options = ttk.Frame(left)
        options.pack(fill="x", pady=8)
        self.values = {}
        for i, (key, label, default, choices) in enumerate(
            (
                ("effect", "Effect", "fade", pack_splash.EFFECTS),
                ("fps", "Frame rate", "20", pack_splash.FPS),
                ("fit", "Image fitting", "fit", ("fit", "crop")),
                ("transition", "Effect seconds", "0.5", None),
                ("duration", "Duration (blank = automatic)", "", None),
                ("poster", "Still-frame time (blank = end)", "", None),
                ("logo_width", "Overlay width", "128", None),
                ("background", "Letterbox colour", "#080e18", None),
            )
        ):
            variable = self.values[key] = tk.StringVar(value=default)
            row, col = i // 2, (i % 2) * 2
            ttk.Label(options, text=label).grid(
                row=row, column=col, sticky="w", padx=(0, 6), pady=4
            )
            control = (
                ttk.Combobox(
                    options,
                    textvariable=variable,
                    values=choices,
                    state="readonly",
                    width=12,
                )
                if choices
                else ttk.Entry(options, textvariable=variable, width=12)
            )
            control.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=4)
        self.direct = tk.BooleanVar()
        ttk.Checkbutton(
            left, text="Direct colour (larger files)", variable=self.direct
        ).pack(anchor="w")
        sound_row = ttk.Frame(left)
        sound_row.pack(fill="x", pady=10)
        self.sound = tk.StringVar()
        ttk.Label(sound_row, text="Optional WAV").pack(side="left", padx=(0, 8))
        ttk.Entry(sound_row, textvariable=self.sound).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            sound_row,
            text="Choose…",
            command=lambda: self.choose_file(self.sound, True),
        ).pack(side="left", padx=4)
        ttk.Label(
            left,
            text="Effects animate the overlay when supplied; otherwise they affect the screen image. Unused screens stay black. Sound is packaged; the PC preview is silent.",
            wraplength=570,
        ).pack(anchor="w", pady=8)

        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Build & preview", command=self.preview).pack(
            side="left"
        )
        ttk.Button(buttons, text="Save .gsp…", command=self.export).pack(
            side="left", padx=6
        )
        ttk.Button(
            buttons, text="Add to theme…", command=lambda: self.export(theme=True)
        ).pack(side="left")
        ttk.Button(
            left, text="Install as custom splash on an SD folder…", command=self.install
        ).pack(anchor="w", pady=4)
        self.status = tk.StringVar(
            value="Choose artwork to begin. A splash can contain up to 2 MiB and 10 seconds."
        )
        ttk.Label(left, textvariable=self.status, wraplength=570).pack(
            anchor="w", pady=8
        )
        ttk.Label(right, text="Two-screen preview").pack(anchor="w", pady=(0, 6))
        self.canvas = tk.Canvas(
            right, width=320, height=480, highlightthickness=0, background="black"
        )
        self.canvas.pack()
        self.reduced = tk.BooleanVar()
        ttk.Checkbutton(
            right,
            text="Reduced motion / still frame",
            variable=self.reduced,
            command=self.preview,
        ).pack(anchor="w", pady=8)
        ttk.Button(right, text="Skip animation", command=self.stop).pack(
            fill="x", pady=3
        )
        ttk.Button(
            right,
            text="Simulate startup ready after 0.5 s",
            command=lambda: self.preview(0.5),
        ).pack(fill="x", pady=3)
        ttk.Label(
            right,
            text="While loading ends immediately when browsing is ready, even mid-animation.",
            wraplength=320,
        ).pack(anchor="w", pady=8)

        for variable in [
            *self.paths.values(),
            *self.values.values(),
            self.sound,
            self.direct,
            self.reduced,
        ]:
            variable.trace_add("write", self.changed)
        if workspace:
            self.restore_project()
        self.restoring = False
        root.protocol("WM_DELETE_WINDOW", self.close)

    def changed(self, *_):
        if self.restoring or not self.workspace:
            return
        self.workspace_status.set(f"{self.workspace.root} — unsaved changes")
        if self.autosave_timer is not None:
            self.root.after_cancel(self.autosave_timer)
        self.autosave_timer = self.root.after(
            600, lambda: self.save_project(quiet=True)
        )

    def save_project(self, quiet=False):
        if self.autosave_timer is not None:
            self.root.after_cancel(self.autosave_timer)
            self.autosave_timer = None
        if not self.workspace:
            return self.open_workspace()
        try:
            state = dict(self.workspace.state)
            state.update(
                paths={
                    key: self.workspace.reference(value.get())
                    for key, value in self.paths.items()
                },
                options={key: value.get() for key, value in self.values.items()},
                direct=self.direct.get(),
                reduced=self.reduced.get(),
                export_path=self.workspace.reference(self.export_path),
            )
            state["paths"]["sound"] = self.workspace.reference(self.sound.get())
            self.workspace.save(state)
            self.workspace_status.set(f"{self.workspace.root} — project saved")
            return True
        except Exception as error:
            self.workspace_status.set(f"Project not saved: {error}")
            if not quiet:
                messagebox.showerror("Project not saved", str(error))
            return False

    def restore_project(self):
        self.restoring = True
        state = self.workspace.state
        for key, variable in self.paths.items():
            variable.set(self.workspace.resolve(state["paths"][key]))
        self.sound.set(self.workspace.resolve(state["paths"]["sound"]))
        for key, variable in self.values.items():
            variable.set(state["options"][key])
        self.direct.set(state["direct"])
        self.reduced.set(state["reduced"])
        self.export_path = self.workspace.resolve(state["export_path"])
        self.workspace_status.set(f"{self.workspace.root} — project loaded")
        self.root.title(f"Gloam Splash Builder — {self.workspace.root.name}")
        self.restoring = False

    def open_workspace(self):
        if self.workspace and not self.save_project():
            if not messagebox.askyesno(
                "Open without saving?",
                "Discard the latest edits and open or reload a working folder?",
            ):
                return False
        folder = filedialog.askdirectory(
            title="Create or reopen a splash working folder",
            initialdir=(
                str(self.workspace.root)
                if self.workspace
                else splash_project.last_workspace() or None
            ),
        )
        if not folder:
            return False
        try:
            workspace = splash_project.Workspace(folder)
            # Validate all references before changing the currently open project.
            for value in (
                *workspace.state["paths"].values(),
                workspace.state["export_path"],
            ):
                workspace.resolve(value)
            self.stop()
            self.workspace = workspace
            self.restore_project()
            self.save_project()
            try:
                splash_project.remember_workspace(workspace.root)
            except OSError:
                pass
            self.canvas.delete("all")
            self.status.set("Project loaded. Build & preview to see it.")
            return True
        except Exception as error:
            messagebox.showerror("Project not opened", str(error))
            return False

    def close(self):
        if self.workspace and not self.save_project():
            if not messagebox.askyesno(
                "Close without saving?",
                "The project could not be saved. Close and discard the latest changes?",
            ):
                return
        self.stop()
        self.root.destroy()

    def selected_asset(self, path, variable):
        try:
            value = self.workspace.import_asset(path) if self.workspace else Path(path)
            variable.set(str(value))
        except Exception as error:
            messagebox.showerror("Asset not imported", str(error))

    def choose_file(self, variable, sound=False):
        path = filedialog.askopenfilename(
            filetypes=(
                [("WAV audio", "*.wav")]
                if sound
                else [
                    ("Images / animation", "*.png *.gif *.jpg *.jpeg"),
                    ("All files", "*"),
                ]
            )
        )
        if path:
            self.selected_asset(path, variable)

    def choose_frames(self, variable):
        path = filedialog.askdirectory(title="Choose a folder of numbered PNG frames")
        if path:
            self.selected_asset(path, variable)

    def build(self):
        values = {key: variable.get() or None for key, variable in self.paths.items()}
        if self.workspace:
            values = {
                key: self.workspace.resolve(self.workspace.reference(value)) or None
                for key, value in values.items()
            }
        values.update({key: variable.get() for key, variable in self.values.items()})
        for key in ("duration", "poster"):
            values[key] = float(values[key]) if values[key] else None
        values["transition"] = float(values["transition"])
        values["fps"] = int(values["fps"])
        values["logo_width"] = int(values["logo_width"])
        sound = self.sound.get()
        if self.workspace:
            sound = self.workspace.resolve(self.workspace.reference(sound))
        values.update(direct=self.direct.get(), sound=sound or None)
        self.data = pack_splash.build(**values)
        self.status.set(
            f"Prepared {len(self.data):,} bytes ({len(self.data) / pack_splash.LIMIT:.1%} of the limit)."
        )
        return self.data

    def stop(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.status.set("Preview skipped. The launcher would now show the browser.")

    def preview(self, ready_after=None):
        self.stop()
        try:
            data = self.build()
        except Exception as error:
            messagebox.showerror("Splash not prepared", str(error))
            return
        started = time.monotonic()
        length = struct.unpack_from("<H", data, 16)[0]

        def draw():
            elapsed = time.monotonic() - started
            if ready_after is not None and elapsed >= ready_after:
                self.stop()
                return
            tick = min(length - 1, int(elapsed * 60))
            image = render(data, tick, self.reduced.get()).resize(
                (320, 480), Image.Resampling.NEAREST
            )
            self.image = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.image, anchor="nw")
            self.timer = (
                self.root.after(50, draw)
                if tick < length - 1 and not self.reduced.get()
                else None
            )

        draw()

    def export(self, theme=False):
        try:
            data = self.build()
            if theme:
                folder = filedialog.askdirectory(
                    title="Choose the theme folder containing theme.ini"
                )
                if not folder:
                    return
                if not (Path(folder) / "theme.ini").is_file():
                    raise ValueError(
                        "Choose an existing Gloam theme folder containing theme.ini."
                    )
                target = Path(folder) / "splash.gsp"
            else:
                chosen = filedialog.asksaveasfilename(
                    defaultextension=".gsp",
                    filetypes=[("Gloam splash", "*.gsp")],
                    initialdir=(
                        str(Path(self.export_path).parent)
                        if self.export_path
                        else str(self.workspace.root) if self.workspace else None
                    ),
                    initialfile=(
                        Path(self.export_path).name
                        if self.export_path
                        else "splash.gsp"
                    ),
                )
                if not chosen:
                    return
                target = Path(chosen)
            if target.exists() and not messagebox.askyesno(
                "Replace splash?",
                f"Replace {target}? Other theme files stay unchanged.",
            ):
                return
            pack_splash.write_package(target, data, replace=target.exists())
            self.export_path = str(target)
            if self.workspace:
                self.save_project(quiet=True)
            self.status.set(f"Saved {target}")
        except Exception as error:
            messagebox.showerror("Splash not exported", str(error))

    def install(self):
        try:
            data = self.build()
            folder = filedialog.askdirectory(
                title="Choose the SD root or staging folder"
            )
            if not folder:
                return
            if not messagebox.askyesno(
                "Install custom splash?",
                f"Install in {folder} and set Gloam's splash to Custom? Existing settings will be backed up.",
            ):
                return
            self.status.set(f"Installed {install_custom(Path(folder), data)}")
        except Exception as error:
            messagebox.showerror("Splash not installed", str(error))


def main(argv=None):
    global tk, ttk, filedialog, messagebox, ImageTk
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import ImageTk

    parser = argparse.ArgumentParser(
        description="Create or resume a Gloam splash project."
    )
    parser.add_argument(
        "--workspace", type=Path, help="Working folder containing splash-project.json"
    )
    args = parser.parse_args(argv)
    root = create_root()
    try:
        folder = args.workspace or filedialog.askdirectory(
            title="Create or reopen a splash working folder",
            initialdir=splash_project.last_workspace() or None,
        )
        if not folder:
            root.destroy()
            return
        workspace = splash_project.Workspace(folder)
        for value in (
            *workspace.state["paths"].values(),
            workspace.state["export_path"],
        ):
            workspace.resolve(value)
        builder = Builder(root, workspace)
        if not builder.save_project():
            root.destroy()
            return
        try:
            splash_project.remember_workspace(workspace.root)
        except OSError:
            pass
    except Exception as error:
        messagebox.showerror("Project not opened", str(error))
        root.destroy()
        return
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
