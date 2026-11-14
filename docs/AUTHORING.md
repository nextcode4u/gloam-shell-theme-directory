# Authoring and validating the art collection

For startup artwork and animation, use the [Splash Builder](STARTUP_SPLASHES.md).
Its GUI, converter and tests are maintained here; Gloam owns native playback and
the package format.

Production illustration masters live in `source/art/`. Their generation prompts
and draft explorations are not part of the repository. The selected masters,
configurations and generated runtime artwork are included so builds do not require
an image-generation service. Credits identify their agent-assisted origin.

Use Python 3.10+ with `pip install -r requirements.txt`, then:

```sh
python tools/build_collection.py --gloam /path/to/gloam-shell-ndx --font-dir /path/to/dejavu
python tools/render_previews.py --gloam /path/to/gloam-shell-ndx
python tools/package_collection.py
```

Use the Gloam revision required by `catalog.json` or later.
Run Gloam’s `tools/host-check.sh` first to obtain its sanitizer-built model/render
objects. The preview tool compiles `check_gloam.c` against those objects and makes
an isolated synthetic SD fixture under this repository’s ignored `build/` folder.
It neither edits Gloam nor accesses a physical SD card. It creates real renderer
previews, checks preview/cancel/apply and validates all browser views, icon sizes,
category screens, the item inspector, Reduced motion, settings and audio assets.
Leak checking is disabled for process-exit global caches; address and undefined
behavior checks remain enabled. These are host tests, not hardware certification.

Keep the DejaVu license beside every font when rebuilding. The font source hash
is recorded in each theme’s credits. Gloam’s authoritative DSFONT03 packer measures every glyph and rejects
ink outside its advance or line height. The body remains 12 pixels high; headings
use independent faces at up to 16 pixels. The profile records size and baseline
for reproducible glyph placement. Coverage uses four grayscale levels, never RGB
subpixel smoothing. Other source fonts require a fresh bounds/readability review.

The audio generator composes four bars with a varied second phrase, sustained
harmony, melodic voices and circular delay tails. Music is 16 kHz, mono PCM16,
below Gloam’s 1 MiB cap. All cues are also bounded mono PCM16. No recordings from
commercial games or royalty-free marketplaces are embedded.

Packaging writes eight individual ZIPs, illustrated/starter collection ZIPs and SHA256SUMS under `dist/`.
Paths are ready for extraction into an SD root. Each archive contains its theme
credits, font license, GPL notice and licensing summary. Source masters, previews,
build tools and testing fixtures are excluded from runtime packs.

## Version 2 materials and composition

The profiles in `build_collection.py` define independent top/bottom reading-surface
opacity, body/heading font selection and named layouts. Aerial uses Spotlight;
Koi, Tidal and Slate use Gallery; Morrow and Folio use Journal. Vesper retains its
illustrated Scene and Phosphor its terminal sidebar. Top/bottom tab placement is
available for the three new presets. The bottom browser retains its shared touch
geometry. Existing user view and wallpaper overrides remain independent.

All packs set `[components] alpha=coverage`. Author PNG alpha as 0, 85, 170 or 255:
transparent, one-third, two-thirds or opaque coverage. Card fills and soft outer
edges reveal the background; solid rims protect structure. Panels and selected
tabs stay opaque for contrast. Native ROM banners and icon PNGs retain their
binary transparency. No blur is applied. Illustration masters are unchanged;
lower-screen images receive a small base tint before Gloam's reading surface.

The five illustrated themes are regenerated entirely by this repository's tool.
Starter themes keep their original artwork/icons/audio; the tool uses Gloam's
component generator for their material shapes, then adds coverage and fonts.
Each pack retains asset provenance and a copy of the applicable font license.
Do not label format-2 packs as compatible with Gloam 1.0.0.

Morrow uses `[backgrounds] top_surface` and `bottom_surface` for separate
256×192 RGBA PNG reading surfaces. These replace the flat mat and are blended
once during theme loading. Its generated paper master is retained under
`source/materials/`; `paper_surfaces()` builds native-size sheets so their grain
is not stretched. `paper_component()` supplies the moving selection and cards.
Keep opaque text areas quiet and corner details inside the six-pixel slice border.
Surface alpha is multiplied by the corresponding screen's content opacity;
Morrow uses 100 to retain the authored coverage. See its catalog entry for the
required frontend revision. Earlier format-2 builds do not recognize these keys.
