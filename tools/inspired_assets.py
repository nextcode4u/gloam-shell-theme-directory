# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline skins, full-screen shade maps, controls, ambient frames and UI cues."""

import json
import math
from pathlib import Path
import wave
import numpy as np
from PIL import Image, ImageColor, ImageDraw
from luna_assets import skin as luna_skin
from portal_assets import skin as portal_skin

ROOT = Path(__file__).resolve().parents[1]
SPECS = json.loads((ROOT / "config/inspired-themes.json").read_text(encoding="utf-8"))[
    "themes"
]
KEYS = "background surface line text muted accent ink".split()
COMPONENTS = "header footer panel row-selected tab-selected card card-selected row icon-frame artwork-frame battery-empty battery-low battery-half battery-high battery-full battery-charging battery-unknown wireless-idle update-available check-off check-on toggle-off toggle-on arrow-left arrow-right arrow-up arrow-down scroll-track scroll-thumb busy".split()


def color(value, alpha=255):
    return (*ImageColor.getrgb(value), alpha)


def material(theme, focused=False):
    """A full-canvas shade field: no repeating tiles behind labels or rows."""
    im = Image.new("RGB", (256, 192))
    pixels = im.load()
    for y in range(192):
        for x in range(256):
            noise = (x * 37 + y * 19 + x * y * 3) % 17 - 8
            if theme == "desktop-98":
                v = 130  # Flat plastic is intentional for this era.
            elif theme == "luna":
                v = 130 + round(18 * math.cos(y / 75)) + noise // 4
            elif theme == "classic-ds":
                v = 136 - (10 if y % 3 == 0 else 0) - (5 if x % 16 == 0 else 0)
            elif theme == "portal-terminal":
                v = 130  # Flat cel fill; do not add metallic/grunge noise.
            elif theme == "aero-glass":
                v = (
                    125
                    + round(23 * math.sin((x + y) / 110))
                    + round(14 * math.exp(-(((y - 45) / 20) ** 2)))
                )
            elif theme == "pokedex":
                v = 139 - round(y / 26) + (2 if (x + y) % 6 == 0 else 0)
            else:
                v = (
                    125
                    + round(15 * math.sin(y / 100))
                    + round(12 * math.exp(-(((y - 18) / 12) ** 2)))
                )
            if focused:
                v += 5
            v = max(0, min(255, v))
            pixels[x, y] = (v, v, v)
    return im


def skin(theme, name):
    if theme == "luna":
        return luna_skin(name)
    if theme == "portal-terminal":
        return portal_skin(name)
    s = SPECS[theme]
    c = dict(zip(KEYS, s["colors"]))
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    if name == "icon-frame":
        return im  # Let native game banners keep their own silhouette.
    selected = name in ("row-selected", "card-selected", "tab-selected")
    frame = name == "artwork-frame"
    panel = name == "panel"
    raised = name in ("card", "card-selected", "tab-selected", "panel")
    fill = color(
        c["accent"] if selected and theme != "classic-ds" else c["surface"],
        255 if panel or selected else 170 if name == "card" else 220,
    )
    edge = color(c["line"])
    shine = color("#ffffff", 170)
    shadow = color(c["text"], 110)
    radius = s["radius"]
    bounds = (0, 0, 31, 31)
    d.rounded_rectangle(bounds, radius=radius, fill=fill, outline=edge, width=1)
    if theme == "desktop-98":
        light = color("#ffffff")
        dark = color("#404040")
        d.line([(0, 31), (0, 0), (31, 0)], fill=light, width=2)
        d.line([(1, 31), (31, 31), (31, 1)], fill=dark, width=2)
        d.line([(2, 29), (29, 29), (29, 2)], fill=color("#808080"), width=1)
        if selected:
            d.rectangle((3, 3, 28, 28), outline=color("#d3d3ff"), width=1)
    elif theme == "classic-ds":
        if name == "header":
            d.rectangle((0, 0, 31, 31), fill=color("#c9d8df"))
        d.rectangle((0, 0, 31, 31), outline=color("#343a3c"))
        d.line([(1, 29), (1, 1), (29, 1)], fill=color("#ffffff"))
        d.line([(2, 30), (30, 30), (30, 2)], fill=color("#929b9e"))
        if selected:
            for x, y, dx, dy in (
                (0, 0, 1, 1),
                (31, 0, -1, 1),
                (0, 31, 1, -1),
                (31, 31, -1, -1),
            ):
                d.line(
                    [(x, y + dy * 5), (x, y), (x + dx * 5, y)],
                    fill=color(c["accent"]),
                    width=2,
                )
    elif theme == "aero-glass":
        d.rounded_rectangle((1, 1, 30, 30), radius=6, outline=color("#ffffff", 220))
        d.rounded_rectangle((2, 2, 29, 29), radius=5, outline=color("#e6f9ff", 85))
        d.line((7, 3, 24, 3), fill=color("#ffffff", 230), width=2)
        d.line((6, 28, 25, 28), fill=color("#5a9bbd", 170), width=2)
    elif theme == "pokedex":
        d.rounded_rectangle((1, 1, 30, 30), radius=2, outline=color("#a6c2ae"))
        d.line((4, 3, 27, 3), fill=color("#ffffff", 170), width=2)
        d.line(
            (4, 28, 27, 28), fill=color("#365f55" if selected else "#9eb29a"), width=2
        )
        if name == "tab-selected":
            d.ellipse((3, 12, 8, 17), fill=color("#72d7ed"), outline=color("#163f4e"))
    else:
        d.line(
            [(1, 26), (1, 2), (4, 0), (27, 0), (31, 4), (31, 29)],
            fill=color("#77e4e7"),
            width=1,
        )
        d.line([(4, 31), (28, 31), (31, 28)], fill=color("#f99cc8"), width=2)
        if selected:
            d.line((5, 3, 26, 3), fill=color("#ffe3b6"), width=2)
    if frame:
        d.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
    if name in ("header", "footer"):
        # Text uses the normal palette; reserve saturated color for narrow trim.
        if theme in ("luna", "desktop-98"):
            d.line((3, 29, 28, 29), fill=color(c["accent"]), width=2)
    return im


def control(theme, name):
    s = SPECS[theme]
    c = dict(zip(KEYS, s["colors"]))
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    ink = (
        color("#ffffff")
        if theme == "luna"
        and (
            name.startswith("battery-") or name in ("wireless-idle", "update-available")
        )
        else color(c["text"])
    )
    a = (
        color("#82cf67")
        if theme == "luna" and name.startswith("battery-")
        else color(c["accent"])
    )
    surface = color(c["surface"])
    if name.startswith("battery-"):
        d.rounded_rectangle(
            (3, 9, 26, 23),
            radius=2 if s["radius"] else 0,
            fill=surface,
            outline=ink,
            width=2,
        )
        d.rectangle((27, 13, 29, 19), fill=ink)
        level = {
            "empty": 0,
            "low": 1,
            "half": 2,
            "high": 3,
            "full": 4,
            "charging": 4,
            "unknown": 0,
        }[name[8:]]
        for index in range(level):
            d.rectangle(
                (6 + index * 5, 12, 9 + index * 5, 20),
                fill=color("#669455") if theme == "classic-ds" else a,
            )
        if name.endswith("charging"):
            d.polygon(
                [(17, 7), (10, 17), (15, 17), (12, 25), (23, 13), (17, 13)],
                fill=color("#669455" if theme == "classic-ds" else "#eab14b"),
                outline=ink,
            )
        if name.endswith("unknown"):
            d.line((13, 14, 18, 14, 18, 17, 15, 18), fill=ink, width=2)
            d.point((15, 21), fill=ink)
    elif name == "wireless-idle":
        for radius in (8, 13):
            d.arc(
                (16 - radius, 20 - radius, 16 + radius, 20 + radius),
                215,
                325,
                fill=ink,
                width=2,
            )
        d.ellipse((14, 22, 18, 26), fill=a)
    elif name == "update-available":
        d.line((16, 4, 16, 23), fill=a, width=4)
        d.polygon([(8, 12), (16, 3), (24, 12)], fill=a)
        d.line((6, 27, 26, 27), fill=ink, width=2)
    elif name.startswith("arrow-"):
        d.polygon([(9, 5), (24, 16), (9, 27)], fill=a, outline=ink)
        im = im.rotate({"right": 0, "up": 90, "left": 180, "down": 270}[name[6:]])
    elif name.startswith("scroll-"):
        d.rounded_rectangle(
            (7, 1, 24, 30),
            radius=s["radius"],
            fill=a if name.endswith("thumb") else surface,
            outline=color(c["line"]),
            width=2,
        )
        if name.endswith("thumb"):
            for y in (12, 16, 20):
                d.line((11, y, 20, y), fill=ink)
    elif name.startswith("check-"):
        d.rounded_rectangle(
            (5, 5, 26, 26), radius=s["radius"], fill=surface, outline=ink, width=2
        )
        if name.endswith("-on"):
            d.line([(9, 16), (14, 22), (23, 10)], fill=a, width=4)
    elif name.startswith("toggle-"):
        on = name.endswith("-on")
        d.rounded_rectangle(
            (2, 8, 29, 24), radius=7, fill=a if on else surface, outline=ink, width=2
        )
        x = 20 if on else 10
        d.ellipse((x - 6, 10, x + 6, 22), fill=color("#ffffff"), outline=ink)
    else:
        for i in range(8):
            t = i * math.pi / 4
            d.ellipse(
                (
                    14 + round(math.cos(t) * 10),
                    14 + round(math.sin(t) * 10),
                    18 + round(math.cos(t) * 10),
                    18 + round(math.sin(t) * 10),
                ),
                fill=a if i < 3 else color(c["line"]),
            )
    return im


def ambient(theme, frame):
    s = SPECS[theme]
    c = dict(zip(KEYS, s["colors"]))
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    a = color("#ffffff" if theme == "luna" else c["accent"], 170)
    if theme == "portal-terminal":
        d.ellipse((3, 3, 29, 29), outline=a, width=2)
        r = 4 + frame % 4 * 2
        d.arc(
            (16 - r, 16 - r, 16 + r, 16 + r),
            frame * 45,
            frame * 45 + 210,
            fill=color("#c8ef65"),
            width=2,
        )
    elif theme == "pokedex":
        d.ellipse((5, 5, 27, 27), fill=color("#388aab", 170), outline=a, width=2)
        d.ellipse((10, 8, 14 + frame // 2, 12 + frame // 2), fill=color("#e7ffff", 170))
    elif theme == "classic-ds":
        for i in range(3):
            d.rounded_rectangle(
                (5 + i * 8, 12, 10 + i * 8, 20),
                radius=2,
                fill=a if frame % 3 == i else color(c["line"], 85),
            )
    elif theme == "synthwave":
        for i in range(4):
            h = 4 + (i * 3 + frame) % 8
            d.rectangle((3 + i * 7, 24 - h, 7 + i * 7, 25), fill=a)
    elif theme == "desktop-98":
        d.rectangle((7, 8, 24, 24), outline=color(c["text"], 170), width=2)
        d.rectangle((10, 11, 21, 20), fill=a if frame < 4 else color(c["line"], 170))
    else:
        r = 2 + round(2 * math.sin(frame * math.pi / 4) ** 2)
        d.line((16 - r, 16, 16 + r, 16), fill=a, width=2)
        d.line((16, 16 - r, 16, 16 + r), fill=a, width=2)
    return im


def cues(theme, folder):
    s = SPECS[theme]
    rate = 16000
    seed = sum(map(ord, theme))
    rng = np.random.default_rng(seed)
    for index, (name, duration) in enumerate(
        (("cursor", 0.055), ("confirm", 0.18), ("back", 0.105))
    ):
        count = round(duration * rate / 2) * 2
        t = np.arange(count) / rate
        f = s["pitch"] * (1 + index * 0.22)
        if theme == "desktop-98":
            signal = (
                np.sin(2 * np.pi * f * t) * 0.7
                + rng.standard_normal(count) * np.exp(-t * 180) * 0.18
            )
        elif theme == "portal-terminal":
            signal = np.sin(
                2 * np.pi * (f * t + 85 * t * t + 0.025 * np.sin(2 * np.pi * 27 * t))
            )
        elif theme == "classic-ds":
            signal = np.sin(2 * np.pi * f * t) + 0.26 * np.sin(2 * np.pi * f * 2.8 * t)
        elif theme == "aero-glass":
            signal = (
                np.sin(2 * np.pi * f * t)
                + 0.35 * np.sin(2 * np.pi * f * 2.01 * t)
                + 0.2 * np.sin(2 * np.pi * f * 3.98 * t)
            )
        elif theme == "pokedex":
            signal = np.sin(
                2 * np.pi * f * t * (1 + 0.25 * (t > duration / 2))
            ) + 0.12 * np.sin(2 * np.pi * f * 3 * t)
        elif theme == "synthwave":
            signal = np.sin(2 * np.pi * (f * t - 65 * t * t)) + 0.2 * np.sin(
                2 * np.pi * f * 2 * t
            )
        else:
            signal = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * f * 1.5 * t)
        envelope = (
            np.minimum(1, t * 1200)
            * np.exp(-t * (35 if index == 0 else 17))
            * np.minimum(1, (duration - t) * 500)
        )
        pcm = np.round(signal * envelope * 3500).astype("<i2")
        with wave.open(str(folder / (name + ".wav")), "wb") as out:
            out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            out.writeframes(pcm.tobytes())
