# Authoring and validating the art collection

For interactive full-theme creation, use [Theme Studio](THEME_STUDIO.md).
For startup artwork and animation alone, use the [Splash Builder](STARTUP_SPLASHES.md).
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

Keep each font’s own complete notice beside its prepared pack. OFL source hashes
and immutable revisions are recorded in `config/theme-fonts.json`; Morrow retains
its original DejaVu notices. Gloam’s authoritative DSFONT03 packer measures every glyph and rejects
ink outside its advance or line height. The body remains 12 pixels high; headings
use independent faces at up to 16 pixels. The profile records size and baseline
for reproducible glyph placement. Coverage uses four grayscale levels, never RGB
subpixel smoothing. Other source fonts require a fresh bounds/readability review.

Background loops use the licensed recordings documented in each theme’s `MUSIC.md` (for example, [Aerial](../themes/aerial/MUSIC.md));
original synthesized UI cues are generated separately. Music is converted offline
to bounded mono PCM16 WAV files under Gloam’s 1 MiB cap. Preserve each track’s
credits and redistribution terms when rebuilding or replacing audio.

Packaging writes nine individual ZIPs, illustrated/starter collection ZIPs and SHA256SUMS under `dist/`.
Paths are ready for extraction into an SD root. Each archive contains its theme
credits, font license, GPL notice and licensing summary. Source masters, previews,
build tools and testing fixtures are excluded from runtime packs.

## Version 2 materials and composition

The profiles in `build_collection.py` select body/heading fonts and named layouts.
Aerial uses Spotlight, Koi uses Gallery, Tidal uses Poster, Slate uses a left icon
rail, and Morrow and Folio use Journal. Vesper retains its illustrated Scene and
Phosphor its right sidebar. Top/bottom tab placement is available for Spotlight,
Gallery and Journal. The bottom browser retains its shared touch geometry.
Existing user view and wallpaper overrides remain independent.

`theme_materials.py` authors the seven glass, lacquer, velvet, lens, archive,
notebook and instrument families. Each has its own edge details, selection shape,
control silhouettes and reading-surface coverage. Its `STYLES` table records
screen alpha and ambient cadence; shading and quiet texture are baked offline.
The older paper helpers in `theme_finishing.py` preserve Morrow's aged parchment.
Use `--theme NAME` with the collection builder to update just one pack.

All packs set `[components] alpha=coverage`. Author PNG alpha as 0, 85, 170 or 255:
transparent, one-third, two-thirds or opaque coverage. Card fills and soft outer
edges reveal the background; solid rims protect structure. Panels and selected
tabs stay opaque for contrast. Native ROM banners and icon PNGs retain their
binary transparency. No blur is applied. Illustration masters are unchanged;
lower-screen images receive a small base tint before Gloam's reading surface.

The five illustrated themes are regenerated entirely by this repository's tool.
Starter themes keep their original illustrations and audio choices; all packs
use independent illustrated icon masters with locally authored materials and controls. Gloam provides the authoritative
font and prepared-sprite packers.
Each pack retains asset provenance and a copy of the applicable font license.
Do not label format-2 packs as compatible with Gloam 1.0.0.

Every pack uses `[backgrounds] top_surface` and `bottom_surface` for separate
256×192 RGBA reading surfaces, blended once during loading. The material generator
keeps edge decoration outside live text. Morrow's aged parchment master lives in
`source/materials/`; Folio uses a lighter procedural tracing-paper surface.
Morrow's `paper_component()` retains the darkened worn outlines on selections and cards;
its calm flat center receives continuous detail from the full-image material field. Keep detail
inside the six-pixel slice border. Surface alpha is multiplied by screen opacity;
these packs use 100 to preserve the authored coverage.

Morrow's parchment uses a feathered alpha profile: the interior is about 42%
opaque on top and 62% on the bottom, increasing toward its worn perimeter.
Selections and cards retain two-thirds center coverage; modal panels stay opaque.
`parchment_coverage()` applies this during asset generation. The reading surface is blended once without an extra framebuffer. Optional
material fields use the separate bounded cache described below.

## Controls, motion and prepared assets

`theme_materials.py` generates each updated family's checkbox, toggle, arrow,
scrollbar and busy sprites; `theme_finishing.py` retains Morrow's controls.
`[components] controls=on` enables them; absent sprites retain Gloam's
standard controls. Their images never change touch targets or input behavior.

Each pack supplies eight 32×32 ambient frames in `motion/ambient.gtm`. Gloam draws
them at 16×16 in reserved header space, loads them after browsing is usable and
pauses them during navigation/modal work. Reduced motion holds the first frame.
The shared selection-margin pulse is disabled in this collection. The complete accent is 18 KiB
decoded, with no frame-by-frame file reads. Do not expand it into a background
movie. Frame count, dimensions, duration and coverage follow the upstream guide.

After PNG generation, the build invokes Gloam's `pack_theme_assets.py` to create
`assets.gfx`. This bundles icons and components into one checked compressed file,
replacing dozens of PNG opens/decodes. PNGs remain the editable sources and runtime
fallbacks. **Rebuild after editing PNGs**, or remove `[assets] prepared` temporarily;
the console does not check source timestamps. Fonts and audio remain separate; current bundles also prepare screens and material maps.
The converter is kept in Gloam beside its reader to keep their format definitions
aligned. Ordinary users copy the completed folder without authoring tools.

The recorded background music is converted to 16-kHz mono PCM16, with circular
crossfades and quiet loop boundaries. Every loop stays inside the existing 1-MiB
limit without streaming or a runtime audio decoder. Do not remove font/audio notices
to reduce archive size.

## Comparing resource costs

Run Gloam's host checks, then:

```sh
python tools/profile_collection.py --gloam /path/to/gloam-shell-ndx
python tools/profile_collection.py --gloam /path/to/gloam-shell-ndx --baseline LOCAL_GIT_REVISION
```

The second form compares a locally available theme-repository revision. The tool
uses isolated synthetic libraries, repeats loading three times, and compares
prepared bundles with PNG fallback. Its ignored `build/theme-performance.json`
records startup preparation, deferred accent/audio setup, rendering and retained
heap samples. These are host CPU/filesystem comparisons, **not DSi boot times**.
Heap samples do not measure transient peaks or static application/frame buffers.
Check cold boot, theme switching, rapid input and music on a physical DSi before
claiming a hardware performance improvement. No personal SD card is accessed.

## Full-image materials and illustrated icons

The current packs require Gloam 1.1.0 or later; Luna, Desktop 98, Classic DS,
Aero Glass and Pokédex require 1.2.0 for separate header/footer colors. Use
Gloam 1.2.0 when rebuilding previews for the complete collection. Their ordinary/focus material
PNGs are complete 256×192 shade fields, sampled without tiling. The optional
fields add up to 48 KiB per active/preview theme bank; Morrow shares one 24-KiB
field while retaining its complete translucent parchment composition. Headers
and body reading surfaces use full images prepared on the PC. Trim stays in
32×32 component PNGs, with live artwork kept clear. Focus skins use distinct
fills and silhouettes rather than a common margin stripe. The shared margin
pulse is disabled; the small per-theme ambient accent remains available.

`source/art/*-icons.png` contains each theme's independently illustrated 4×4
icon atlas. `theme_icons.py` fits each object into a 28×28 envelope inside the
native 32×32 PNG. Native DS/DSi banners and associated application icons retain
priority. `collection_surfaces.py` owns full-image materials and focus shapes;
it uses the original material studies in `source/materials/collection.png`.
Keep broad text areas quiet and put corner details inside the six-pixel border.

OFL font families, immutable source URLs, hashes and native metrics live in
`config/theme-fonts.json`. First-time authors can add `--download-fonts` to the
build command to populate the ignored font cache. Subsequent builds work offline.
Normal theme installation needs only the prepared packs, not Python or source
fonts. Morrow's existing type pairing still uses `--font-dir`; its notice is
retained independently under `source/fonts/`. Prepared sprite banks now permit
up to 256 KiB compressed with a bounded 512-KiB decoded cap; native sprite
counts and sizes remain unchanged.

## Rebuilding BUUF

`tools/buuf_theme.py` checks every retained upstream PNG against
`source/buuf/UPSTREAM.json` before preparing native icons and controls. The
original files and license remain unchanged. Its full-image fields, translucent
labels, Public Sans/Delius typography, original synthesized UI cues, licensed background music and bounded
ambient mark use the same runtime contracts as the other packs.

Build with `--theme buuf` after obtaining the verified OFL font inputs. The
standalone `buuf.zip` includes its full CC-BY-NC-SA-2.5 license, credits and
provenance. It is excluded from both CC0-art collection archives. See
[BUUF credits](../themes/buuf/CREDITS.md) before adapting or redistributing it.

## Prepared screens and material fields

Repacking with the current Gloam converter writes `GLMART02`. It combines icons,
components, preblended RGB555 screens, optional scene strips and four-bit material
fields in one compressed bundle. Rendering is pixel-equivalent to the PNG path;
fonts and audio remain separate. Temporary decode memory is bounded to 512 KiB
plus the compressed input and released after filling the existing banks.

Personal wallpaper/blend overrides or changed source sizes bypass the relevant
prepared screen. Rebuild after every source PNG edit, including same-size edits.
Older compatible Gloam builds fall back to the retained PNGs; update BOOT.NDS and
the theme's assets.gfx for the acceleration. No theme.ini changes are required.

## Music

Background music is licensed recorded music, independent of the synthesized UI cues.
`tools/build_collection.py` and `tools/buuf_theme.py` preserve these WAV files.
Run `python tools/prepare_theme_music.py` to verify reviewed hashes and runtime
format, or `--rebuild --download` to obtain pinned original MP3s and reproduce
the excerpts with the recorded FFmpeg version. Source downloads stay in ignored
`build/`. The final mono PCM16, 16-kHz loops remain within the existing 1-MiB cap.
Each pack must retain MUSIC.md and MUSIC-LICENSE.txt.

## Desktop and device packs

Use the matching Gloam checkout and the pinned fonts:

```sh
python tools/build_inspired_collection.py --gloam /path/to/gloam --download-fonts
python tools/prepare_theme_music.py
python tools/package_collection.py
```

Run `python tools/classic_ds_assets.py` before rebuilding Classic DS. Layouts and
palettes are in `config/inspired-themes.json`; artwork masters and hashes are
under `source/art/` and `config/inspired-art.json`. Ordinary builds preserve the
recorded music. Reproduce its pinned loops separately with
`python tools/prepare_theme_music.py --rebuild --download`.

Packaging writes per-theme ZIPs and `dist/gloam-desktop-device-themes.zip`, with
notices but no preview screenshots. Use `tools/render_previews.py --gloam` with
`--only` theme IDs and `--gallery docs/inspired-preview.png` to regenerate a
selected gallery. These authoring commands do not install anything on SD.
