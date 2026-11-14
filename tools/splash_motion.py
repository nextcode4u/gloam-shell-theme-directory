# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded layer authoring and a pixel-accurate preview for GLOMSP02/03 packages."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib
from PIL import Image, ImageColor, ImageOps

LAYER_KEYS = ("top", "bottom", "top_logo", "bottom_logo")
FITS = ("fit", "crop", "stretch", "native")
EASING = ("linear", "ease-in", "ease-out", "smooth")
REPEAT = ("once", "loop", "ping-pong")
REVEAL = ("none", "right", "left", "up", "down")
DEFAULTS = {
    "preset": "none",
    "fit": "fit",
    "delay": "0",
    "transition": "0.5",
    "easing": "linear",
    "repeat": "once",
    "sequence": "once",
    "start_x": "0",
    "start_y": "0",
    "end_x": "0",
    "end_y": "0",
    "scale_from": "100",
    "scale_to": "100",
    "opacity_from": "100",
    "opacity_to": "100",
    "reveal": "none",
    "width": "128",
}
PRESETS = {
    "none": {},
    "fade": {"opacity_from": "0"},
    "slide-up": {"start_y": "32"},
    "slide-down": {"start_y": "-32"},
    "slide-left": {"start_x": "32"},
    "slide-right": {"start_x": "-32"},
    "reveal": {"reveal": "right"},
    "reveal-left": {"reveal": "left"},
    "reveal-up": {"reveal": "up"},
    "reveal-down": {"reveal": "down"},
    "zoom-in": {"scale_from": "65", "easing": "ease-out"},
    "zoom-out": {"scale_from": "135", "easing": "ease-out"},
    "fade-zoom": {"scale_from": "80", "opacity_from": "0", "easing": "smooth"},
    "pulse": {
        "scale_from": "90",
        "scale_to": "110",
        "repeat": "ping-pong",
        "easing": "smooth",
    },
    "drift": {
        "start_x": "-12",
        "end_x": "12",
        "repeat": "ping-pong",
        "easing": "smooth",
    },
}
MOTION_KEYS = tuple(
    k for k in DEFAULTS if k not in ("fit", "delay", "transition", "sequence", "width")
)


def preset(name):
    if name not in PRESETS and name != "custom":
        raise ValueError("Unknown motion preset.")
    return DEFAULTS | PRESETS.get(name, {}) | {"preset": name}


def number(options, key, low, high):
    value = float(options[key])
    if not math.isfinite(value) or value != int(value) or not low <= value <= high:
        raise ValueError(
            f"{key.replace('_', ' ')} must be a whole number from {low} to {high}."
        )
    return int(value)


def prepare_frames(path, fps, fit, width=None):
    import pack_splash

    frames = pack_splash.source_frames(Path(path), fps, upscale=False)
    if fit not in FITS:
        raise ValueError("Choose fit, crop, stretch or native sizing.")
    size = (256, 192) if width is None else (width, min(192, width))
    result = []
    for image in frames:
        if fit == "native":
            image = image.copy()
            image.thumbnail(size, Image.Resampling.LANCZOS)
        elif fit == "stretch":
            image = image.resize(size, Image.Resampling.LANCZOS)
        elif fit == "crop":
            image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        else:
            image = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
        result.append(image)
    if any(frame.size != result[0].size for frame in result):
        raise ValueError("Every frame in a layer must have the same fitted size.")
    return result


def compress_frames(content, frame_bytes, count, indexed):
    """Independent streams allow skipping directly to a frame with fixed RAM."""
    palette_bytes = 512 if indexed else 0
    table = bytearray(4 * (count + 1))
    for frame in range(count):
        struct.pack_into("<I", table, frame * 4, len(table))
        start = palette_bytes + frame * frame_bytes
        table.extend(zlib.compress(content[start : start + frame_bytes], level=9))
    struct.pack_into("<I", table, count * 4, len(table))
    return content[:palette_bytes] + table


def build(
    *,
    top=None,
    bottom=None,
    top_logo=None,
    bottom_logo=None,
    fps=20,
    duration=None,
    poster=None,
    effect="fade",
    transition=0.5,
    fit="fit",
    background="#080e18",
    logo_width=128,
    direct=False,
    sound=None,
    layer_options=None,
    compress=False,
):
    import pack_splash

    if fps not in pack_splash.FPS:
        raise ValueError("Unsupported frame rate.")
    layer_options = layer_options or {}
    if not isinstance(layer_options, dict) or set(layer_options) - set(LAYER_KEYS):
        raise ValueError("Layer options must use top, bottom, top_logo or bottom_logo.")
    sources = dict(top=top, bottom=bottom, top_logo=top_logo, bottom_logo=bottom_logo)
    layers = []
    for key in LAYER_KEYS:
        if not sources[key]:
            continue
        # Legacy global effects apply to the overlay when one exists on that screen.
        base_effect = (
            effect if key.endswith("_logo") or not sources[key + "_logo"] else "none"
        )
        options = layer_options.get(key, {})
        if not isinstance(options, dict) or set(options) - set(DEFAULTS):
            raise ValueError(f"Unknown controls for {key}.")
        options = (
            preset(options.get("preset", base_effect))
            | {"fit": fit, "transition": str(transition), "width": str(logo_width)}
            | options
        )
        for field, allowed in (
            ("easing", EASING),
            ("repeat", REPEAT),
            ("sequence", REPEAT),
            ("reveal", REVEAL),
        ):
            if options[field] not in allowed:
                raise ValueError(f"Invalid {field} for {key}.")
        delay = pack_splash.ticks(float(options["delay"]))
        time = pack_splash.ticks(float(options["transition"]))
        if not time and (options["repeat"] != "once" or options["reveal"] != "none"):
            raise ValueError(
                "Repeated motion and reveals need a positive effect duration."
            )
        width = number(options, "width", 1, 256) if key.endswith("_logo") else None
        frames = prepare_frames(sources[key], fps, options["fit"], width)
        values = [
            number(options, k, -512, 512)
            for k in ("start_x", "start_y", "end_x", "end_y")
        ]
        scales = [number(options, k, 0, 400) for k in ("scale_from", "scale_to")]
        opacity = [
            (number(options, k, 0, 100) * 32 + 50) // 100
            for k in ("opacity_from", "opacity_to")
        ]
        layers.append((key, options, frames, delay, time, values, scales, opacity))
    if not layers:
        raise ValueError("Choose artwork for at least one screen.")
    natural = max(
        delay + max(time, len(frames) * 60 // fps if len(frames) > 1 else 180)
        for _, _, frames, delay, time, *_ in layers
    )
    length = pack_splash.ticks(duration) if duration is not None else natural
    if not 1 <= length <= 600:
        raise ValueError("Keep total duration between 1/60 second and 10 seconds.")
    still = pack_splash.ticks(poster) if poster is not None else length - 1
    if still >= length:
        raise ValueError("The still-frame time must be before the end.")
    data = bytearray(32 + 64 * len(layers))
    compressed = False
    for i, (key, options, frames, delay, time, values, scales, opacity) in enumerate(
        layers
    ):
        if delay >= length or time > length:
            raise ValueError(
                f"{key}: delay and effect duration must fit the splash duration."
            )
        w, h = frames[0].size
        content = pack_splash.encode_frames(frames, direct)
        if compress:
            candidate = compress_frames(
                content, w * h * (2 if direct else 1), len(frames), not direct
            )
            if len(candidate) < len(content):
                content = candidate
                data[32 + i * 64 + 49] = 1
                compressed = True
        struct.pack_into(
            "<4B4H2h2H3I",
            data,
            32 + i * 64,
            int(key.startswith("bottom")),
            int(not direct),
            REVEAL.index(options["reveal"]),
            0,
            w,
            h,
            len(frames),
            60 // fps,
            (256 - w) // 2,
            (192 - h) // 2,
            delay,
            time,
            len(data),
            len(content),
            0,
        )
        struct.pack_into(
            "<4h2H5B",
            data,
            64 + i * 64,
            *values,
            *scales,
            *opacity,
            EASING.index(options["easing"]),
            REPEAT.index(options["repeat"]),
            REPEAT.index(options["sequence"]),
        )
        data.extend(content)
        data.extend(bytes(-len(data) % 4))
        if len(data) > pack_splash.LIMIT:
            raise ValueError(
                "Splash exceeds 2 MiB. Lower the frame rate or use smaller layers."
            )
    audio = pack_splash.sound_pcm(Path(sound) if sound else None, length)
    offset = len(data) if audio else 0
    data.extend(audio)
    if len(data) > pack_splash.LIMIT:
        raise ValueError("Splash plus sound exceeds 2 MiB.")
    struct.pack_into(
        "<8sIIHHBBHII",
        data,
        0,
        b"GLOMSP03" if compressed else b"GLOMSP02",
        len(data),
        0,
        length,
        still,
        len(layers),
        0,
        pack_splash.rgb555(*ImageColor.getrgb(background)),
        offset,
        len(audio),
    )
    struct.pack_into("<I", data, 12, zlib.crc32(data[16:]))
    return bytes(data)


def divide(value, denominator):
    """Match C's signed division (toward zero), including negative motion offsets."""
    return value // denominator if value >= 0 else -((-value) // denominator)


def progress_at(elapsed, duration, easing, repeat):
    if not duration:
        return 1024
    if repeat == 1:
        elapsed %= duration
    elif repeat == 2:
        elapsed %= duration * 2
        if elapsed > duration:
            elapsed = duration * 2 - elapsed
    p = min(1024, elapsed * 1024 // duration)
    if easing == 1:
        return p * p // 1024
    if easing == 2:
        return 1024 - (1024 - p) ** 2 // 1024
    if easing == 3:
        return p * p * (3072 - 2 * p) // (1024 * 1024)
    return p


def frame_at(elapsed, hold, count, sequence):
    frame = elapsed // hold
    if sequence == 1:
        return frame % count
    if sequence == 2 and count > 1:
        cycle = (count - 1) * 2
        frame %= cycle
        return frame if frame < count else cycle - frame
    return min(frame, count - 1)


def render(data, tick, reduced=False):
    if reduced:
        tick = struct.unpack_from("<H", data, 18)[0]
    backdrop = struct.unpack_from("<H", data, 22)[0]
    pixels = [backdrop] * (256 * 384)
    for i in range(data[20]):
        (
            screen,
            fmt,
            reveal,
            _,
            w,
            h,
            count,
            hold,
            x,
            y,
            delay,
            duration,
            offset,
            _,
            _,
        ) = struct.unpack_from("<4B4H2h2H3I", data, 32 + i * 64)
        if tick < delay and not reduced:
            continue
        (
            sx,
            sy,
            ex,
            ey,
            first_scale,
            last_scale,
            first_alpha,
            last_alpha,
            easing,
            repeat,
            sequence,
        ) = struct.unpack_from("<4h2H5B", data, 64 + i * 64)
        elapsed = max(0, tick - delay)
        p = 1024 if reduced else progress_at(elapsed, duration, easing, repeat)
        lerp = lambda a, b: a + divide((b - a) * p, 1024)
        alpha, scale = lerp(first_alpha, last_alpha), lerp(first_scale, last_scale)
        width, height = w * scale // 100, h * scale // 100
        if not width or not height or not alpha:
            continue
        x += divide(w - width, 2) + lerp(sx, ex)
        y += divide(h - height, 2) + lerp(sy, ey)
        left, top, right, bottom = (
            max(0, x),
            max(0, y),
            min(256, x + width),
            min(192, y + height),
        )
        if reveal == 1:
            right = min(right, x + width * p // 1024)
        if reveal == 2:
            left = max(left, x + width - width * p // 1024)
        if reveal == 3:
            top = max(top, y + height - height * p // 1024)
        if reveal == 4:
            bottom = min(bottom, y + height * p // 1024)
        if left >= right or top >= bottom:
            continue
        frame = frame_at(elapsed, hold, count, sequence)
        palette = struct.unpack_from("<256H", data, offset) if fmt else None
        size = w * h * (1 if fmt else 2)
        origin = offset + (512 if fmt else 0)
        if data[:8] == b"GLOMSP03" and data[32 + i * 64 + 49]:
            start, end = struct.unpack_from("<2I", data, origin + frame * 4)
            decoder = zlib.decompressobj()
            pixels_data = decoder.decompress(
                data[origin + start : origin + end], size + 1
            )
            if len(pixels_data) != size or not decoder.eof or decoder.unused_data:
                raise ValueError("Invalid compressed splash frame.")
        else:
            origin += frame * size
            pixels_data = data[origin : origin + size]
        words = (
            [palette[index] for index in pixels_data]
            if fmt
            else struct.unpack(f"<{w*h}H", pixels_data)
        )
        columns = [(col - x) * w // width for col in range(left, right)]
        for row in range(top, bottom):
            source = (row - y) * h // height * w
            destination = (screen * 192 + row) * 256 + left
            for col, source_x in enumerate(columns):
                color = words[source + source_x]
                if color & 0x8000:
                    behind = pixels[destination + col]
                    pixels[destination + col] = (
                        color
                        if alpha == 32
                        else 0x8000
                        | sum(
                            (
                                (
                                    ((color >> shift) & 31) * alpha
                                    + ((behind >> shift) & 31) * (32 - alpha)
                                )
                                >> 5
                            )
                            << shift
                            for shift in (0, 5, 10)
                        )
                    )
    image = Image.new("RGB", (256, 384))
    image.putdata(
        [
            tuple(((word >> shift) & 31) * 255 // 31 for shift in (0, 5, 10))
            for word in pixels
        ]
    )
    return image
