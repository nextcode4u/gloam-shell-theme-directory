# SPDX-License-Identifier: GPL-3.0-or-later
"""Use verified source faces and Gloam's authoritative bounded font converter."""

import json
from pathlib import Path
from theme_font_sources import verified_source

ROOT = Path(__file__).resolve().parents[1]


def prepare_fonts(theme, folder, packer, profile, font_dir, download=False):
    notices, notes = [], []
    if theme == "morrow":
        # Preserve the type pairing used by the approved parchment design.
        for role, filename in (("body", "ui"), ("heading", "heading")):
            family, size, baseline, height = profile[role]
            (folder / "fonts" / (filename + ".dsfont")).write_bytes(
                packer.pack_font(
                    font_dir / (family + ".ttf"),
                    size,
                    baseline,
                    True,
                    proportional=True,
                    height=height,
                )
            )
            notes.append(f"- {role.title()}: {family}, {size}px; line height {height}.")
        notices.append((ROOT / "source/fonts/DEJAVU-LICENSE.txt").read_text())
    else:
        # Filter before resolving: building one theme should not need every font.
        manifest = json.loads((ROOT / "config/theme-fonts.json").read_text())
        for role, filename in (("body", "ui"), ("heading", "heading")):
            spec = manifest["themes"][theme][role]
            face = manifest["faces"][spec["family"]]
            source = verified_source(
                spec["family"], "font", face["font"], download=download
            )
            license_path = verified_source(
                spec["family"], "license", face["license"], download=download
            )
            settings = {key: value for key, value in spec.items() if key != "family"}
            (folder / "fonts" / (filename + ".dsfont")).write_bytes(
                packer.pack_font(source, latin1=True, proportional=True, **settings)
            )
            notices.append(
                f"{role.title()}: {face['name']}\n\n{license_path.read_text().strip()}\n"
            )
            notes.append(
                f"- {role.title()}: {face['name']}, {spec['size']}px; line height {spec['height']}."
            )
    text = (
        "\n".join(line.rstrip() for line in "\n".join(notices).splitlines()).rstrip()
        + "\n"
    )
    (folder / "fonts/LICENSE.txt").write_text(text)
    return notes
