# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspectable theme controls, matching the bounded Gloam version-2 contract."""

ICONS = "file folder game application audio video book text image save config archive shortcut system missing settings camera sound pictochat download-play system-menu slot1 tab-home tab-games tab-apps tab-media tab-system tab-files tab-folder".split()
COMPONENTS = "header footer panel row-selected tab-selected card card-selected row icon-frame artwork-frame battery-empty battery-low battery-half battery-high battery-full battery-charging battery-unknown wireless-idle update-available check-off check-on toggle-off toggle-on arrow-left arrow-right arrow-up arrow-down scroll-track scroll-thumb busy".split()
COLORS = dict(
    background="#101820",
    surface="#233342",
    line="#536579",
    text="#f0f4f8",
    muted="#b0c2d4",
    accent="#b9a5f4",
    ink="#171126",
)


def choice(values, default=None, help=""):
    return dict(type="choice", choices=values.split(), default=default, help=help)


def number(low, high, default=None, help=""):
    return dict(type="number", min=low, max=high, default=default, help=help)


def path(help=""):
    return dict(type="path", help=help)


SCHEMA = {
    "theme": {
        "version": choice("1 2", "2"),
        "name": dict(type="text", default="Untitled theme", max_bytes=63),
        "header": dict(type="text", max_bytes=63, help="Empty hides the header label."),
        "min_frontend": dict(
            type="text",
            help="Optional vX.Y.Z / preview / rc requirement; requires a current Gloam build.",
        ),
    },
    "colors": {key: dict(type="color", default=value) for key, value in COLORS.items()}
    | {
        key: dict(type="color", help="Omit to inherit the normal text role.")
        for key in (
            "selection_text",
            "tab_text",
            "header_text",
            "footer_text",
            "header_link_text",
        )
    },
    "layout": {
        "view": choice("classic extended list grid shelf index", "extended"),
        "icon_size": choice(
            "small medium large",
            "large",
            "Small 16px, medium 24px and large 32px. Shelf scales these to 32/40/48px; List hides icons.",
        ),
        "row_padding": number(0, 12, "2"),
        "large_grid_columns": number(2, 4, "3"),
        "top_content": choice(
            "theme neighbors smart",
            help="Optional preset for development Gloam after 1.2.0. Theme follows the layout below. Neighbors shows nearby covers; Smart adapts to the selection. Users press Y for item details and can override this setting in Gloam.",
        ),
        "top_layout": choice(
            "sidebar sidebar_left poster scene spotlight gallery journal panorama dossier portrait",
            "gallery",
            "Sidebar: side navigation. Scene: artwork over wallpaper. Spotlight: centered card. Gallery: artwork and facts. Journal: small artwork. Panorama: wide card with caption below. Dossier: right artwork, left facts. Portrait: tall left artwork, right title and facts.",
        ),
        "chrome": choice(
            "full minimal",
            "full",
            "Interface framing: Full draws header/footer skins and divider lines; Minimal leaves wallpaper visible. Text and controls remain available.",
        ),
        "content_opacity": number(0, 100, "0"),
        "top_content_opacity": number(0, 100),
        "bottom_content_opacity": number(0, 100),
        "tabs_position": choice(
            "top bottom",
            help="Spotlight, Gallery, Journal, Panorama, Dossier and Portrait reserve space for top or bottom tabs. Sidebar uses a side rail; Scene and Poster use a bottom dock.",
        ),
        "tab_style": choice(
            "labels icons numbered pager",
            "labels",
            "Labels, icon buttons, numbered labels or a focused-tab pager. Styles work on both side rails and horizontal docks.",
        ),
        "tab_highlight": choice(
            "skin underline outline",
            "skin",
            "Skin uses components/tab-selected.png from the component directory (a 32×32 nine-slice PNG). Without an asset, Gloam uses the accent color. Design or import it below.",
        ),
        "tab_visible": number(
            3,
            5,
            "3",
            "Number of visible entries in a horizontal dock. Side rails show up to six entries.",
        ),
        "tab_gap": number(
            0,
            8,
            "4",
            "Spacing between horizontal dock buttons. Side rails use fixed spacing.",
        ),
        "scene_cover_x": number(2, 246, "18"),
        "scene_cover_y": number(26, 108, "34"),
        "scene_cover_width": number(8, 96, "48"),
        "scene_cover_height": number(8, 90, "72"),
    },
    "backgrounds": {
        key: path("256×192 recommended; surfaces must be exactly 256×192 RGBA PNG.")
        for key in ("top", "bottom", "top_surface", "bottom_surface")
    }
    | {"strength": number(0, 100, "100")},
    "fonts": {
        "ui": path("builtin or a 12-pixel DSFONT pack."),
        "heading": path("builtin or a 12–16-pixel DSFONT pack."),
    },
    "icons": {
        "directory": path("Optional 32×32 PNGs; native title icons retain priority.")
    },
    "components": {
        "directory": path("Optional 32×32 nine-slice / status / control PNGs."),
        "border": number(0, 12, "6"),
        "alpha": choice("binary coverage", "coverage"),
        "fill": choice("stretch tile", "stretch"),
        "controls": choice("off on", "on"),
        "material": path("Opaque 256×192 shade map; sampled at screen coordinates."),
        "focus_material": path("Separate opaque 256×192 shade map for selection."),
    },
    "audio": {
        key: path("Mono PCM16 WAV, 8–48 kHz; music ≤1 MiB PCM, cues ≤64 KiB.")
        for key in ("music", "cursor", "confirm", "back")
    },
    "motion": {
        "ambient": path(
            "Prepared header-accent file. Import below creates it; it appears beside the top-screen heading, not over the wallpaper."
        ),
        "ambient_ticks": number(
            5,
            120,
            "12",
            "DS display ticks per frame, about 60 ticks per second. 12 = 0.2 seconds per frame (5 fps); larger values are slower. GIF timing is replaced by this uniform interval.",
        ),
        "focus": choice(
            "off pulse",
            "off",
            "Pulse is a short edge gleam when selecting a browser item, lasting about 0.2 seconds. It does not animate the icon or wallpaper. Reduced motion disables it.",
        ),
    },
    "assets": {
        "prepared": path("Rebuilt at export; GLMART02 avoids many small SD reads.")
    },
}


# Existing authored presets remain valid, but are not offered for new designs.
SCHEMA["layout"]["top_content"]["legacy_choices"] = {
    "context": "Context (existing theme)",
    "folder": "Folder overview (existing theme)",
    "activity": "Home activity (existing theme)",
    "layout": "Layout only (existing theme)",
}


def defaults():
    result = {
        section: {
            key: str(spec["default"])
            for key, spec in fields.items()
            if spec.get("default") is not None
        }
        for section, fields in SCHEMA.items()
    }
    result["fonts"] = {"ui": "builtin", "heading": "builtin"}
    result["colors"].update(selection_text=COLORS["ink"], tab_text=COLORS["ink"])
    result["icons"] = {"directory": "icons"}
    result["components"]["directory"] = "components"
    return {section: values for section, values in result.items() if values}


PALETTES = {
    "Dusk": COLORS,
    "Paper": dict(
        background="#f2e8d8",
        surface="#fff5e5",
        line="#a89c87",
        text="#342d28",
        muted="#746252",
        accent="#745039",
        ink="#fff5e9",
    ),
    "Coast": dict(
        background="#e6f2ee",
        surface="#f5faf3",
        line="#8cafa7",
        text="#1e3e4c",
        muted="#476b71",
        accent="#285e69",
        ink="#f4f8dc",
    ),
    "Arcade": dict(
        background="#1d112f",
        surface="#302144",
        line="#776181",
        text="#fff2e8",
        muted="#d2b3d8",
        accent="#fb88c8",
        ink="#271333",
    ),
}
