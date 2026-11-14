# Authoring and validating the art collection

Production illustration masters live in `source/art/`. Their generation prompts
and draft explorations are not part of the repository. The selected masters,
configurations and generated runtime artwork are included so builds do not require
an image-generation service. Credits identify their AI-assisted origin.

Use Python 3.10+ with `pip install -r requirements.txt`, then:

```sh
python tools/build_collection.py --font /path/to/DejaVuSansMono.ttf
python tools/render_previews.py --gloam /path/to/gloam-shell-ndx
python tools/package_collection.py
```

Run Gloam’s `tools/host-check.sh` first to obtain its sanitizer-built model/render
objects. The preview tool compiles `check_gloam.c` against those objects and makes
an isolated synthetic SD fixture under this repository’s ignored `build/` folder.
It neither edits Gloam nor accesses a physical SD card. It creates real renderer
previews, checks preview/cancel/apply and validates all browser views, icon sizes,
category screens, the item inspector, Reduced motion, settings and audio assets.
Leak checking is disabled for process-exit global caches; address and undefined
behavior checks remain enabled. These are host tests, not hardware certification.

Keep the DejaVu license beside every font when rebuilding. The font source hash
is recorded in each theme’s credits. The packer measures every glyph and rejects
ones wider/taller than the cell; it shifts a few accents/underscores to stay in
bounds instead of clipping them. Coverage uses four grayscale levels, never RGB
subpixel smoothing. Other source fonts require a fresh bounds/readability review.

The audio generator composes eight bars with a varied second phrase, sustained
harmony, melodic voices and circular delay tails. Music is 16 kHz, mono PCM16,
below Gloam’s 1 MiB cap. All cues are also bounded mono PCM16. No recordings from
commercial games or royalty-free marketplaces are embedded.

Packaging writes individual ZIPs, a combined ZIP and SHA256SUMS under `dist/`.
Paths are ready for extraction into an SD root. Each archive contains its theme
credits, font license, GPL notice and licensing summary. Source masters, previews,
build tools and testing fixtures are excluded from runtime packs.
