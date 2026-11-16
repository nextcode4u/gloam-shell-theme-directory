# SPDX-License-Identifier: GPL-3.0-or-later
"""PC-only asset conversion, material recipes, sprite sheets and motion packing."""

from __future__ import annotations
from array import array
import io
import math
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence
from theme_schema import COLORS, COMPONENTS, ICONS
from theme_validate import inside, audio_info


def png(image):
    output = io.BytesIO()
    image.save(output, "PNG", optimize=True)
    return output.getvalue()


def material(options):
    width, height = int(options.get("width", 32)), int(options.get("height", 32))
    if not 1 <= width <= 512 or not 1 <= height <= 512:
        raise ValueError("Material size must be 1–512.")
    style = options.get("style", "paper")
    if style not in ("paper", "linen", "glass", "metal", "wood", "flat", "gradient"):
        raise ValueError("Unknown material recipe.")
    base = options.get("color", "#e8dcc5")
    edge = options.get("edge", "#84664a")
    fill = Image.new("RGBA", (width, height), base)
    rgb = fill.getpixel((0, 0))[:3]
    seed = int(options.get("seed", 17))
    rng = random.Random(seed)
    grain = max(0, min(30, int(options.get("grain", 8))))
    opacity = max(0, min(255, int(options.get("opacity", 255))))
    pixels = []
    for y in range(height):
        for x in range(width):
            noise = rng.uniform(-grain, grain)
            if style == "linen":
                noise += (5 if x % 3 == 0 else -2) + (5 if y % 3 == 0 else -2)
            if style == "metal":
                noise += 8 * math.sin(y * 0.6)  # horizontal brushing
            if style == "wood":
                noise += 7 * math.sin(y * 0.25 + math.sin(x * 0.03) * 2)
            if style in ("glass", "gradient"):
                noise += 20 * (1 - y / max(1, height - 1)) - 8
            if style == "flat":
                noise = 0
            if style == "paper":
                distance = min(x, y, width - 1 - x, height - 1 - y)
                noise -= max(0, 7 - distance) * 2
            pixels.append(
                tuple(max(0, min(255, int(c + noise))) for c in rgb) + (opacity,)
            )
    fill.putdata(pixels)
    radius = max(0, min(min(width, height) // 2, int(options.get("radius", 5))))
    mask = Image.new("L", fill.size)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius, fill=opacity)
    fill.putalpha(mask)
    border = max(0, min(12, int(options.get("border", 1))))
    if border:
        draw = ImageDraw.Draw(fill)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1), radius, outline=edge, width=border
        )
        if options.get("bevel", True) and width > 5 and height > 5:
            draw.line(
                (radius + 1, 2, width - radius - 2, 2),
                fill=(255, 255, 255, 110),
                width=1,
            )
    if options.get("coverage", True):
        fill.putalpha(fill.getchannel("A").point(lambda a: round(a / 85) * 85))
    return fill


def starter_icon(name, palette, style="soft"):
    """Editable geometric starters; imported illustrations remain independent."""
    image = Image.new("RGBA", (128, 128))
    d = ImageDraw.Draw(image)
    fg = palette.get("accent", COLORS["accent"])
    ink = palette.get("ink", COLORS["ink"])
    edge = palette.get("line", COLORS["line"])
    if "folder" in name:
        d.rounded_rectangle((12, 32, 64, 56), 8, fill=fg, outline=edge, width=4)
        d.rounded_rectangle((12, 44, 116, 106), 8, fill=fg, outline=edge, width=4)
        d.line((22, 57, 106, 57), fill=ink, width=3)
    elif name in ("game", "tab-games"):
        d.rounded_rectangle((12, 35, 116, 99), 22, fill=fg, outline=edge, width=4)
        d.line((34, 53, 34, 81), fill=ink, width=7)
        d.line((20, 67, 48, 67), fill=ink, width=7)
        for x, y in ((85, 58), (99, 76)):
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=ink)
    elif name in ("settings", "system", "tab-system"):
        for angle in range(0, 360, 45):
            x = 64 + math.cos(math.radians(angle)) * 37
            y = 64 + math.sin(math.radians(angle)) * 37
            d.rounded_rectangle((x - 12, y - 12, x + 12, y + 12), 4, fill=fg)
        d.ellipse((25, 25, 103, 103), fill=fg, outline=edge, width=4)
        d.ellipse((47, 47, 81, 81), fill=ink)
    elif name in ("tab-home", "system-menu"):
        d.polygon(((14, 58), (64, 18), (114, 58)), fill=fg)
        d.rounded_rectangle((29, 53, 100, 112), 4, fill=fg)
        d.rectangle((53, 77, 76, 112), fill=ink)
    elif name in ("audio", "sound", "tab-media"):
        d.line((61, 90, 61, 30, 100, 20, 100, 78), fill=fg, width=10)
        d.ellipse((25, 77, 63, 105), fill=fg)
        d.ellipse((64, 66, 102, 94), fill=fg)
    elif name in ("application", "tab-apps"):
        for x, y in ((20, 20), (69, 20), (20, 69), (69, 69)):
            d.rounded_rectangle(
                (x, y, x + 39, y + 39), 7, fill=fg, outline=edge, width=3
            )
    else:
        d.rounded_rectangle((29, 15, 102, 114), 8, fill=fg, outline=edge, width=4)
        glyph = {
            "video": "▶",
            "book": "B",
            "text": "T",
            "image": "I",
            "save": "S",
            "archive": "Z",
            "config": "⚙",
            "camera": "C",
            "pictochat": "P",
            "download-play": "↓",
            "slot1": "1",
            "shortcut": "↗",
            "missing": "?",
            "tab-files": "F",
        }.get(name, "•")
        # Portable default font; the source PNG can be replaced or painted.
        font = ImageFont.load_default(size=37)
        box = d.textbbox((0, 0), glyph, font=font)
        d.text(((128 - (box[2] - box[0])) / 2 - box[0], 47), glyph, font=font, fill=ink)
    return image.resize(
        (32, 32),
        Image.Resampling.NEAREST if style == "pixel" else Image.Resampling.LANCZOS,
    )


def generate_set(project, kind, options):
    if kind not in ("icons", "components"):
        raise ValueError("Choose icons or components.")
    names = ICONS if kind == "icons" else COMPONENTS
    directory = project.data["config"].get(kind, {}).get("directory", kind)
    files = [directory + "/" + name + ".png" for name in names]
    project.checkpoint(files)
    palette = COLORS | project.data["config"].get("colors", {})
    for name, relative in zip(names, files):
        target = inside(project.theme, relative)
        if target.exists() and not options.get("replace", False):
            continue
        if kind == "icons":
            image = starter_icon(name, palette, options.get("style", "soft"))
        else:
            active = name in (
                "row-selected",
                "card-selected",
                "tab-selected",
                "check-on",
                "toggle-on",
            )
            image = material(
                options
                | dict(
                    width=32,
                    height=32,
                    color=palette["accent" if active else "surface"],
                    edge=palette["line"],
                )
            )
            draw = ImageDraw.Draw(image)
            ink = palette["ink" if active else "text"]
            if name.startswith("arrow-"):
                image = Image.new("RGBA", (32, 32))
                draw = ImageDraw.Draw(image)
                points = [(20, 6), (9, 16), (20, 26)]
                draw.line(points, fill=ink, width=3)
                angle = {"left": 0, "right": 180, "up": 270, "down": 90}[
                    name.split("-")[1]
                ]
                image = image.rotate(angle)
            elif name.startswith("battery-"):
                image = Image.new("RGBA", (32, 32))
                draw = ImageDraw.Draw(image)
                draw.rounded_rectangle((3, 8, 27, 24), 2, outline=ink, width=2)
                draw.rectangle((28, 13, 30, 19), fill=ink)
                level = {
                    "empty": 0,
                    "low": 1,
                    "half": 2,
                    "high": 3,
                    "full": 4,
                    "charging": 3,
                    "unknown": 0,
                }[name.split("-")[1]]
                if level:
                    draw.rectangle((6, 11, 6 + level * 4, 21), fill=palette["accent"])
                if name.endswith("charging"):
                    draw.line((18, 7, 12, 17, 19, 17, 13, 26), fill=ink, width=2)
            elif name in ("wireless-idle", "update-available", "busy"):
                image = Image.new("RGBA", (32, 32))
                draw = ImageDraw.Draw(image)
                if name == "wireless-idle":
                    for inset in (2, 7, 12):
                        draw.arc(
                            (inset, inset, 32 - inset, 32 - inset),
                            210,
                            330,
                            fill=ink,
                            width=2,
                        )
                    draw.ellipse((14, 22, 18, 26), fill=ink)
                elif name == "update-available":
                    draw.line((16, 27, 16, 5, 8, 13, 16, 5, 24, 13), fill=ink, width=3)
                else:
                    draw.arc((5, 5, 27, 27), 20, 300, fill=ink, width=3)
            elif name in ("check-on", "check-off"):
                image = Image.new("RGBA", (32, 32))
                draw = ImageDraw.Draw(image)
                draw.rectangle((7, 7, 25, 25), outline=ink, width=2)
                if active:
                    draw.line((10, 15, 15, 21, 23, 10), fill=ink, width=3)
            elif name.startswith("toggle-"):
                image = Image.new("RGBA", (32, 32))
                draw = ImageDraw.Draw(image)
                draw.rounded_rectangle(
                    (2, 8, 30, 24),
                    8,
                    fill=palette["accent"] if active else palette["line"],
                )
                x = 20 if active else 10
                draw.ellipse((x - 6, 10, x + 6, 22), fill=palette["text"])
        from splash_project import atomic_write

        project.clear_artboard(relative)
        atomic_write(target, png(image))
    project.data["config"].setdefault(kind, {})["directory"] = directory
    project.save()
    return len(files)


def atlas_import(project, data, kind, columns, rows):
    names = ICONS if kind == "icons" else COMPONENTS if kind == "components" else []
    if not names or not 1 <= columns <= 16 or not 1 <= rows <= 16:
        raise ValueError("Invalid atlas grid.")
    with Image.open(io.BytesIO(data)) as source:
        if source.width * source.height > 16777216:
            raise ValueError("Atlas exceeds 16 megapixels.")
        if source.width % columns or source.height % rows:
            raise ValueError("Atlas dimensions must divide evenly by its grid.")
        source = source.convert("RGBA")
        w, h = source.width // columns, source.height // rows
        directory = project.data["config"].get(kind, {}).get("directory", kind)
        names = names[: columns * rows]
        project.checkpoint([directory + "/" + n + ".png" for n in names])
        project.record_source("atlas.png", data)
        from splash_project import atomic_write

        for i, name in enumerate(names):
            project.clear_artboard(directory + "/" + name + ".png")
            image = source.crop(
                (
                    i % columns * w,
                    i // columns * h,
                    (i % columns + 1) * w,
                    (i // columns + 1) * h,
                )
            ).resize((32, 32), Image.Resampling.LANCZOS)
            atomic_write(
                inside(project.theme, directory + "/" + name + ".png"), png(image)
            )
        project.data["config"].setdefault(kind, {})["directory"] = directory
        project.save()
    return len(names)


def convert_audio(
    source,
    *,
    rate=16000,
    start=0.0,
    seconds=15.0,
    gain=1.0,
    fade=0.05,
    loop=0.0,
    music=True,
):
    if rate not in (8000, 12000, 16000, 22050, 24000, 32000, 44100, 48000):
        raise ValueError("Unsupported output rate.")
    cap = 1048576 if music else 65536
    if (
        not 0 < float(seconds) <= cap / (rate * 2)
        or start < 0
        or not 0 <= gain <= 4
        or not 0 <= fade <= 5
        or not 0 <= loop <= 5
    ):
        raise ValueError("Audio length/level exceeds runtime bounds.")
    with tempfile.TemporaryDirectory() as folder:
        source = Path(source)
        if source.suffix.lower() != ".wav":
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise ValueError(
                    "This input needs FFmpeg on PATH. WAV PCM inputs work without it."
                )
            target = Path(folder) / "decoded.wav"
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-nostdin",
                    "-y",
                    "-ss",
                    str(start),
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(source),
                    "-t",
                    str(seconds),
                    "-ac",
                    "1",
                    "-ar",
                    str(rate),
                    "-c:a",
                    "pcm_s16le",
                    str(target),
                ],
                check=True,
                timeout=60,
                capture_output=True,
            )
            source = target
            start = 0
        with wave.open(str(source), "rb") as wav:
            channels, width, input_rate = (
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getframerate(),
            )
            if (
                wav.getcomptype() != "NONE"
                or channels not in (1, 2)
                or width not in (1, 2, 3, 4)
            ):
                raise ValueError("Use mono/stereo PCM WAV or convert through FFmpeg.")
            wav.setpos(min(wav.getnframes(), int(start * input_rate)))
            raw = wav.readframes(int(float(seconds) * input_rate))
        values = []
        for offset in range(0, len(raw) - width * channels + 1, width * channels):
            samples = []
            for c in range(channels):
                chunk = raw[offset + c * width : offset + (c + 1) * width]
                value = (
                    (chunk[0] - 128) * 256
                    if width == 1
                    else int.from_bytes(chunk, "little", signed=True)
                    / (2 ** (width * 8 - 16))
                )
                samples.append(value)
            values.append(sum(samples) / channels)
        if not values:
            raise ValueError("The selected audio range is empty.")
        count = min(cap // 2, int(len(values) * rate / input_rate))
        out = []
        for i in range(count):
            position = i * input_rate / rate
            index = min(len(values) - 1, int(position))
            fraction = position - index
            sample = (
                values[index] * (1 - fraction)
                + values[min(index + 1, len(values) - 1)] * fraction
            )
            out.append(max(-32768, min(32767, round(sample * gain))))
        blend = min(len(out) // 4, int(loop * rate))
        if blend:
            # Circular overlap removes the duplicate lead-in and retains phase continuity.
            for i in range(blend):
                out[len(out) - blend + i] = round(
                    out[len(out) - blend + i] * (1 - i / blend) + out[i] * (i / blend)
                )
            out = out[blend:]
        else:
            edge = min(len(out) // 2, int(fade * rate))
            for i in range(edge):
                out[i] = round(out[i] * i / max(1, edge))
                out[-1 - i] = round(out[-1 - i] * i / max(1, edge))
        pcm = array("h", out)
        if sys.byteorder != "little":
            pcm.byteswap()
        data = io.BytesIO()
        with wave.open(data, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(pcm.tobytes())
        audio_info(data.getvalue(), music)
        return data.getvalue()


def ambient(data, count=8):
    if not 1 <= count <= 8:
        raise ValueError("Ambient accents support 1–8 frames.")
    from theme_native.pack_theme_assets import sprite

    with Image.open(io.BytesIO(data)) as source:
        frames = []
        for i, frame in enumerate(ImageSequence.Iterator(source)):
            if i >= 256:
                raise ValueError("Accent source has more than 256 frames.")
            frames.append(frame.convert("RGBA").copy())
    selected = [
        frames[i * len(frames) // min(count, len(frames))]
        for i in range(min(count, len(frames)))
    ]
    output = b"GLMFX001" + bytes((len(selected), 32, 32)) + b"\0" * 5
    for image in selected:
        image.thumbnail((32, 32), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (32, 32))
        canvas.alpha_composite(
            image, ((32 - image.width) // 2, (32 - image.height) // 2)
        )
        output += sprite(canvas)
    return output
