#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create installable ZIPs with runtime assets, credits and all font notices."""

from pathlib import Path
import hashlib
import zipfile
from build_collection import ROOT, SPECS


def package(path, ids):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for id in ids:
            p = ROOT / "themes" / id
            for file in sorted(p.rglob("*")):
                if file.is_file() and file.name not in (
                    "README.md",
                    "preview.png",
                    "settings-preview.png",
                ):
                    assert not file.is_symlink()
                    z.write(
                        file,
                        Path("_nds/dsi-frontend/themes") / id / file.relative_to(p),
                    )
        z.write(ROOT / "LICENSE", "licenses/GPL-3.0.txt")
        z.write(ROOT / "LICENSES.md", "licenses/README.md")


def main():
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    for id in SPECS:
        package(out / f"{id}.zip", [id])
    package(out / "gloam-art-collection.zip", list(SPECS))
    names = [f"{id}.zip" for id in SPECS] + ["gloam-art-collection.zip"]
    (out / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256((out/n).read_bytes()).hexdigest()}  {n}\n" for n in names
        )
    )
    print("Packaged five themes and combined collection in dist/")


if __name__ == "__main__":
    main()
