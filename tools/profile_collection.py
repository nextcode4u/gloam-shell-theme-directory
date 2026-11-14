#!/usr/bin/env python3
"""Compare native host loading/rendering; never interprets host timings as DSi timings."""

import argparse
import configparser
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(preview, source, work, name, packed, repeats):
    folder = work / name / ("packed" if packed else "png")
    theme = folder / "_nds/dsi-frontend/themes" / name
    shutil.copytree(source, theme)
    config = configparser.ConfigParser()
    config.read(theme / "theme.ini")
    if not packed and config.has_section("assets"):
        config.remove_section("assets")
        with (theme / "theme.ini").open("w") as file:
            config.write(file, space_around_delimiters=False)
    roms = folder / "roms"
    roms.mkdir()
    for i in range(1000):
        (roms / f"Library item {i:04d}.txt").write_text("Authored fixture\n")
    samples = []
    for _ in range(repeats):
        (folder / "_nds/dsi-frontend/state.ini").write_text(
            f"version=1\ntheme_id={name}\ncategory=1\nbrowser_style=1\nicon_size=1\nmusic_mode=1\n"
        )
        samples.append(
            json.loads(
                subprocess.check_output(
                    [
                        str(preview),
                        str(folder),
                        str(folder / "unused"),
                        "1",
                        "profile",
                        "0",
                    ],
                    text=True,
                )
            )
        )
    return {
        "samples": samples,
        "median": {
            key: statistics.median(sample[key] for sample in samples)
            for key in samples[0]
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gloam", required=True, type=Path)
    parser.add_argument(
        "--baseline", help="Local theme-repository Git revision, for comparison"
    )
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 10))
    args = parser.parse_args()
    preview = args.gloam.resolve() / "build/host/preview"
    if not preview.is_file():
        parser.error("Run Gloam tools/host-check.sh first")
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    report = {
        "environment": "Native host CPU/filesystem. Not DSi boot or frame times; heap samples exclude transient peaks and static App/framebuffers.",
        "themes": {},
    }
    with tempfile.TemporaryDirectory(prefix="theme-profile-", dir=out) as temporary:
        work = Path(temporary)
        if args.baseline:
            archive = work / "baseline.tar"
            subprocess.run(
                [
                    "git",
                    "archive",
                    "--format=tar",
                    f"--output={archive}",
                    args.baseline,
                    "themes",
                ],
                cwd=ROOT,
                check=True,
            )
            with tarfile.open(archive) as packed:
                packed.extractall(work / "baseline", filter="data")
        for name in sorted(p.name for p in (ROOT / "themes").iterdir() if p.is_dir()):
            item = {}
            item["packed"] = run(
                preview,
                ROOT / "themes" / name,
                work / "current",
                name,
                True,
                args.repeats,
            )
            item["png"] = run(
                preview,
                ROOT / "themes" / name,
                work / "current",
                name,
                False,
                args.repeats,
            )
            if args.baseline:
                item["baseline"] = run(
                    preview,
                    work / "baseline/themes" / name,
                    work / "prior",
                    name,
                    True,
                    args.repeats,
                )
            report["themes"][name] = item
            print(
                name,
                {key: value["median"]["prepare_ms"] for key, value in item.items()},
                flush=True,
            )
    (out / "theme-performance.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
