# SPDX-License-Identifier: GPL-3.0-or-later
"""Original Luna-era chrome: cobalt title bars, Explorer panes and green controls."""

from PIL import Image, ImageDraw


def gradient(image, bounds, stops):
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = bounds
    for y in range(top, bottom + 1):
        position = (y - top) / max(1, bottom - top)
        for index in range(1, len(stops)):
            if position <= stops[index][0]:
                break
        a, first = stops[index - 1]
        b, second = stops[index]
        t = (position - a) / max(0.001, b - a)
        color = tuple(round(x * (1 - t) + z * t) for x, z in zip(first, second)) + (
            255,
        )
        draw.line((left, y, right, y), fill=color)


def skin(name):
    im = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(im)
    if name in ("icon-frame", "row"):
        return im
    if name in ("header", "footer"):
        gradient(
            im,
            (0, 0, 31, 31),
            [
                (0, (86, 155, 249)),
                (0.12, (35, 112, 230)),
                (0.56, (0, 82, 204)),
                (1, (17, 67, 170)),
            ],
        )
        d.line((0, 0, 31, 0), fill="#99c7ff")
        d.line((0, 31, 31, 31), fill="#17439c")
        if name == "footer":
            # Reserve the status line above the narrow blue taskbar.
            d.rectangle((0, 0, 31, 4), fill=(0, 0, 0, 0))
        return im
    if name == "tab-selected":
        gradient(
            im,
            (0, 0, 31, 31),
            [
                (0, (138, 205, 118)),
                (0.12, (64, 160, 55)),
                (0.55, (35, 137, 36)),
                (1, (23, 99, 33)),
            ],
        )
        d.rounded_rectangle((0, 0, 31, 31), radius=5, outline="#175b24", width=1)
        d.line((5, 2, 26, 2), fill="#a8df8e")
        d.line((5, 29, 26, 29), fill="#1b6226")
        return im
    if name in ("row-selected", "card-selected"):
        d.rectangle((0, 0, 31, 31), fill="#316ac5", outline="#2454a1")
        return im
    if name == "artwork-frame":
        d.rectangle((0, 0, 31, 31), fill="#ffffff", outline="#7f9db9")
        d.rectangle((2, 2, 29, 29), outline="#d2e0ef")
        d.rectangle((6, 6, 25, 25), fill=(0, 0, 0, 0))
        return im
    d.rectangle(
        (0, 0, 31, 31),
        fill=(255, 255, 251, 170) if name == "card" else "#ece9d8",
        outline="#7f9db9",
    )
    d.line((1, 29, 1, 1, 29, 1), fill="#ffffff")
    d.line((2, 30, 30, 30, 30, 2), fill="#aca899")
    return im


def reading_surface(screen):
    image = Image.new("RGBA", (256, 192))
    d = ImageDraw.Draw(image)
    if screen == "top":
        # Selected-item details are the white left column; navigation sits on
        # the familiar pale-blue right pane. Keep wallpaper at window margins.
        d.rectangle((5, 25, 250, 174), fill="#fffefb", outline="#2f68c0")
        d.rectangle((175, 26, 249, 173), fill="#d3e5fa")
        d.line((174, 26, 174, 173), fill="#a0bce6")
    else:
        d.rectangle((5, 25, 250, 174), fill="#ffffff", outline="#7f9db9")
    return image
