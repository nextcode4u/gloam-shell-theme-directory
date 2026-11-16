# SPDX-License-Identifier: GPL-3.0-or-later
"""Theme authoring diagnostics. Native Gloam remains the compatibility authority."""

from __future__ import annotations

import configparser
import io
from pathlib import Path, PurePosixPath
import re
import struct
import wave
import zlib

from PIL import Image
from theme_schema import SCHEMA, COLORS, ICONS, COMPONENTS

VERSION = re.compile(
    r"v(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})(?:-(?:preview|rc)\.(0|[1-9][0-9]{0,5}))?\Z"
)


def inside(root, relative):
    """All project/package access is relative and rejects linked path components."""
    root = Path(root).resolve()
    relative = str(relative)
    if not relative or "\\" in relative or ":" in relative or "\0" in relative:
        raise ValueError("Use a relative path inside the theme.")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(
        part in ("..", ".", "") for part in relative.split("/")
    ):
        raise ValueError("Asset path must stay inside the theme.")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root):
        raise ValueError("Asset path leaves the theme.")
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("Linked project assets are not supported.")
    return target


def parse_ini(text):
    if len(text.encode("utf-8")) > 4096 or "\0" in text:
        raise ValueError("theme.ini must be at most 4 KiB without NUL bytes.")
    if any(len(line.encode("utf-8")) >= 1023 for line in text.splitlines()):
        raise ValueError("INI lines must be shorter than 1,023 bytes.")
    parser = configparser.ConfigParser(
        interpolation=None, strict=True, empty_lines_in_values=False
    )
    parser.optionxform = str
    parser.read_string(text)
    if parser.defaults():
        raise ValueError("DEFAULT sections are not supported by Gloam.")
    return {section: dict(parser[section]) for section in parser.sections()}


def to_ini(config):
    return "".join(
        f"[{section}]\n"
        + "".join(f"{key}={value}\n" for key, value in values.items())
        + "\n"
        for section, values in config.items()
        if values
    )


def font_info(data, heading=False):
    if len(data) < 16:
        raise ValueError("Truncated DSFONT header.")
    magic = data[:8]
    if magic == b"DSFONT03":
        width, height, first, count, latin_first, latin_count = data[8:14]
        if not (
            1 <= width <= 16
            and 12 <= height <= 16
            and (heading or height == 12)
            and first == 32
            and count == 95
            and (latin_first, latin_count) in ((0, 0), (160, 96))
            and data[14:16] == b"\0\0"
        ):
            raise ValueError("Invalid proportional font header / role height.")
        stride = 2 + height * 4
        if len(data) != 16 + (count + latin_count) * stride:
            raise ValueError("Invalid proportional font length.")
        for index in range(count + latin_count):
            start = 16 + index * stride
            advance, reserved = data[start : start + 2]
            rows = struct.unpack_from("<" + "I" * height, data, start + 2)
            if (
                not 1 <= advance <= width
                or reserved
                or any(row >> (advance * 2) for row in rows)
            ):
                raise ValueError("Invalid glyph bounds or reserved bits.")
            cp = index + 32 if index < 95 else index - 95 + 160
            if cp not in (32, 160, 173) and not any(rows):
                raise ValueError("Empty printable glyph.")
        return dict(height=height, glyphs=count + latin_count, format="DSFONT03")
    count = 95 if magic == b"DSFONT01" else 191 if magic == b"DSFONT02" else 0
    expected = (
        bytes((7, 12, 32, 95, 0, 0, 0, 0))
        if count == 95
        else bytes((7, 12, 32, 95, 160, 96, 0, 0))
    )
    if not count or data[8:16] != expected or len(data) != 16 + count * 24:
        raise ValueError("Invalid fixed-cell font.")
    if any(row >> 14 for row in struct.unpack_from("<" + "H" * (count * 12), data, 16)):
        raise ValueError("Fixed glyph exceeds its cell.")
    return dict(height=12, glyphs=count, format=magic.decode())


def audio_info(data, music=False):
    with wave.open(io.BytesIO(data)) as wav:
        if (
            wav.getcomptype() != "NONE"
            or wav.getnchannels() != 1
            or wav.getsampwidth() != 2
            or not 8000 <= wav.getframerate() <= 48000
        ):
            raise ValueError("Audio must be mono PCM16 WAV at 8–48 kHz.")
        count = wav.getnframes() * 2
        if (
            not count
            or count > (1048576 if music else 65536)
            or len(wav.readframes(wav.getnframes())) != count
        ):
            raise ValueError("Empty, truncated or oversized PCM payload.")
        return dict(
            seconds=round(wav.getnframes() / wav.getframerate(), 3),
            pcm_bytes=count,
            rate=wav.getframerate(),
        )


def splash_info(data):
    if not 32 <= len(data) <= 2 * 1024 * 1024 or data[:8] not in (
        b"GLOMSP01",
        b"GLOMSP02",
        b"GLOMSP03",
    ):
        raise ValueError("Invalid splash header or 2-MiB limit.")
    length, checksum = struct.unpack_from("<II", data, 8)
    duration, poster = struct.unpack_from("<HH", data, 16)
    count = data[20]
    stride = 32 if data[:8] == b"GLOMSP01" else 64
    if (
        length != len(data)
        or checksum != zlib.crc32(data[16:])
        or not 1 <= duration <= 600
        or poster >= duration
        or not 1 <= count <= 4
        or 32 + stride * count > len(data)
    ):
        raise ValueError("Invalid splash size, checksum, duration or layer count.")
    regions = []
    for i in range(count):
        base = 32 + i * stride
        (
            screen,
            fmt,
            effect,
            reserved,
            w,
            h,
            frames,
            hold,
            x,
            y,
            delay,
            transition,
            offset,
            size,
            unused,
        ) = struct.unpack_from("<4B4H2h2H3I", data, base)
        if (
            screen > 1
            or fmt > 1
            or effect > 4
            or reserved
            or unused
            or not 1 <= w <= 256
            or not 1 <= h <= 192
            or not 1 <= frames <= 120
            or not 1 <= hold <= 12
            or delay >= duration
            or transition > duration
            or offset < 32 + stride * count
            or offset + size > len(data)
        ):
            raise ValueError("Invalid splash layer bounds.")
        regions.append((offset, offset + size))
        frame_size = w * h * (1 if fmt else 2)
        palette = 512 if fmt else 0
        compressed = stride == 64 and data[base + 49]
        if compressed:
            if (
                data[:8] != b"GLOMSP03"
                or compressed != 1
                or size < palette + 4 * (frames + 1)
            ):
                raise ValueError("Invalid compressed splash table.")
            table_start = offset + palette
            table = struct.unpack_from("<" + "I" * (frames + 1), data, table_start)
            if table[0] != 4 * (frames + 1) or table[-1] != size - palette:
                raise ValueError("Invalid splash offsets.")
            for start, end in zip(table, table[1:]):
                if not start < end <= size - palette:
                    raise ValueError("Invalid splash frame interval.")
                decoder = zlib.decompressobj()
                frame = decoder.decompress(
                    data[table_start + start : table_start + end], frame_size + 1
                )
                if len(frame) != frame_size or not decoder.eof or decoder.unused_data:
                    raise ValueError("Invalid compressed splash frame.")
        elif size != palette + frame_size * frames:
            raise ValueError("Invalid splash pixel length.")
    audio_offset, audio_length = struct.unpack_from("<II", data, 24)
    if audio_length:
        if (
            audio_length > 320000
            or audio_length % 2
            or audio_offset < 32 + stride * count
            or audio_offset + audio_length > len(data)
        ):
            raise ValueError("Invalid splash audio region.")
        regions.append((audio_offset, audio_offset + audio_length))
    elif audio_offset:
        raise ValueError("Empty splash audio has a nonzero offset.")
    regions.sort()
    if any(a[1] > b[0] for a, b in zip(regions, regions[1:])):
        raise ValueError("Splash regions overlap.")
    return dict(frames=duration, layers=count, bytes=len(data))


def check(root, config, metadata=None):
    root = Path(root)
    errors, warnings, assets = [], [], []

    def error(text):
        errors.append(text)

    def warning(text):
        warnings.append(text)

    try:
        parse_ini(to_ini(config))
    except (ValueError, configparser.Error) as exc:
        error(str(exc))
    for section, fields in config.items():
        if section not in SCHEMA:
            error("Unsupported section: " + section)
            continue
        for key, value in fields.items():
            spec = SCHEMA[section].get(key)
            label = section + "." + key
            if spec is None:
                error("Unsupported field: " + label)
                continue
            if not isinstance(value, str) or any(c in value for c in "\0\n\r"):
                error("Invalid text: " + label)
                continue
            kind = spec["type"]
            if kind == "choice" and value not in spec["choices"]:
                error("Unsupported option: " + label)
            if kind == "number" and (
                not re.fullmatch("[0-9]+", value)
                or not spec["min"] <= int(value) <= spec["max"]
            ):
                error(f"{label}: expected {spec['min']}–{spec['max']}.")
            if kind == "color" and not re.fullmatch("#[0-9a-fA-F]{6}", value):
                error("Expected #RRGGBB: " + label)
            if kind == "text" and len(value.encode()) > spec.get("max_bytes", 255):
                error("Text exceeds byte limit: " + label)
            if kind == "path" and not (section == "fonts" and value == "builtin"):
                try:
                    target = inside(root, value)
                    if key != "prepared" and not target.exists():
                        (warning if key == "directory" else error)(
                            "Missing asset: " + value
                        )
                    elif target.is_file():
                        assets.append(dict(path=value, bytes=target.stat().st_size))
                except ValueError as exc:
                    error(label + ": " + str(exc))
    version = config.get("theme", {}).get("version")
    if version not in ("1", "2"):
        error("A theme needs version=1 or version=2.")
    if not config.get("theme", {}).get("name", "Theme"):
        error("Theme name cannot be empty.")
    minimum = config.get("theme", {}).get("min_frontend")
    if minimum is not None and not VERSION.fullmatch(minimum):
        error("Minimum frontend must be vX.Y.Z or a numeric preview/rc tag.")
    layout = config.get("layout", {})
    if layout.get("tabs_position") and layout.get("top_layout", "sidebar") not in (
        "spotlight",
        "gallery",
        "journal",
    ):
        error("Tab position is only supported by Spotlight, Gallery and Journal.")
    try:
        x, y, w, h = (
            int(layout.get(k, str(v)))
            for k, v in zip(
                (
                    "scene_cover_x",
                    "scene_cover_y",
                    "scene_cover_width",
                    "scene_cover_height",
                ),
                (18, 34, 48, 72),
            )
        )
        if x + w > 254 or y + h > 116:
            error("Scene cover must fit inside x=2..253 and y=26..115.")
    except ValueError:
        pass
    if version == "1" and (
        any(s in config for s in ("motion", "assets"))
        or any(k in config.get("fonts", {}) for k in ("heading",))
        or any(
            k in layout
            for k in ("tabs_position", "top_content_opacity", "bottom_content_opacity")
        )
        or layout.get("top_layout") in ("spotlight", "gallery", "journal")
        or any(
            k in config.get("backgrounds", {})
            for k in ("top_surface", "bottom_surface")
        )
        or any(
            k in config.get("components", {})
            for k in ("material", "focus_material", "alpha", "controls", "fill")
        )
    ):
        error("These features require theme format version 2.")
    palette = COLORS | config.get("colors", {})
    if all(re.fullmatch("#[0-9a-fA-F]{6}", palette[k]) for k in COLORS):

        def luminance(key):
            rgb = [int(palette[key][i : i + 2], 16) >> 3 for i in (1, 3, 5)]
            return (3 * rgb[0] + 6 * rgb[1] + rgb[2]) // 10

        for a, b, minimum in [
            ("text", "background", 12),
            ("text", "surface", 10),
            ("muted", "background", 6),
            ("accent", "background", 8),
            ("ink", "accent", 8),
        ]:
            if abs(luminance(a) - luminance(b)) < minimum:
                error(f"Native palette contrast fails: {a} / {b}.")
    for section, names in (("icons", ICONS), ("components", COMPONENTS)):
        directory = config.get(section, {}).get("directory")
        if not directory:
            continue
        for name in names:
            relative = directory + "/" + name + ".png"
            try:
                file = inside(root, relative)
                if not file.is_file():
                    continue
                assets.append(dict(path=relative, bytes=file.stat().st_size))
                with Image.open(file) as image:
                    if (
                        image.format != "PNG"
                        or image.size != (32, 32)
                        or file.stat().st_size > 65536
                    ):
                        error("Sprite must be a 32×32 PNG ≤64 KiB: " + relative)
            except (ValueError, OSError) as exc:
                error(relative + ": " + str(exc))
    for section, fields in config.items():
        for key, value in fields.items():
            if section not in ("backgrounds", "components", "fonts", "audio", "motion"):
                continue
            if (
                SCHEMA.get(section, {}).get(key, {}).get("type") != "path"
                or value == "builtin"
            ):
                continue
            try:
                file = inside(root, value)
                if not file.is_file():
                    continue
                if section == "fonts":
                    font_info(file.read_bytes(), key == "heading")
                elif section == "audio":
                    audio_info(file.read_bytes(), key == "music")
                elif section == "motion":
                    data = file.read_bytes()
                    if (
                        len(data) < 16
                        or data[:8] != b"GLMFX001"
                        or not 1 <= data[8] <= 8
                        or data[9:11] != b"  "
                        or any(data[11:16])
                        or len(data) != 16 + data[8] * 2304
                    ):
                        raise ValueError("Invalid ambient frame package.")
                elif key not in ("directory",):
                    with Image.open(file) as image:
                        exact = key in (
                            "top_surface",
                            "bottom_surface",
                            "material",
                            "focus_material",
                        )
                        if (
                            file.stat().st_size > 262144
                            or not 1 <= image.width <= 512
                            or not 1 <= image.height <= 512
                            or image.format not in ("PNG", "JPEG")
                            or (
                                exact
                                and (image.size != (256, 192) or image.format != "PNG")
                            )
                        ):
                            raise ValueError(
                                "Invalid image dimensions, format or size."
                            )
                        if key in ("material", "focus_material") and image.convert(
                            "RGBA"
                        ).getextrema()[3] != (255, 255):
                            raise ValueError("Material maps must be opaque.")
            except (ValueError, OSError, wave.Error) as exc:
                error(value + ": " + str(exc))
    if metadata is not None and (
        not metadata.get("author") or not metadata.get("license")
    ):
        warning("Add your author name, asset licenses and attribution before sharing.")
    splash = root / "splash.gsp"
    if splash.is_file():
        try:
            if splash.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Splash exceeds 2 MiB.")
            splash_info(splash.read_bytes())
            assets.append(dict(path="splash.gsp", bytes=splash.stat().st_size))
        except (ValueError, OSError, struct.error, zlib.error) as exc:
            error("splash.gsp: " + str(exc))
    warning(
        "Authoring preview is approximate. Verify layout, contrast, audio and Reduced motion in Gloam and on the LCD."
    )
    return dict(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        assets=assets,
        total_bytes=sum(item["bytes"] for item in assets),
        manifest_bytes=len(to_ini(config).encode()),
    )
