# Theme Studio

Theme Studio edits Gloam’s supported theme format in a resumable desktop
workspace. Its interface opens in your browser, backed by a local Python process.
Project artwork stays on your computer. The launch command downloads the builder
and offers its dependencies; it does not download collection artwork or music.

## Launch and resume

```powershell
irm https://raw.githubusercontent.com/nextcode4u/gloam-shell-theme-directory/main/theme.ps1 | iex
```

Choose a new or existing working folder. Missing Python/Tk or Pillow is offered
for installation; declining stops setup. The launcher uses a private environment
and verifies a complete immutable repository snapshot before switching its cache.
Failed refreshes retain the verified cached copy.

From a checkout, or with a previously prepared offline cache:

```powershell
.\theme.ps1 -Workspace D:\Themes\MyTheme -SourceDirectory .
.\theme.ps1 -Workspace D:\Themes\MyTheme -Offline
```

Other systems can use Python 3.10+ with Tk:

```sh
python -m pip install -r requirements.txt
python tools/theme_builder.py --workspace /path/to/my-theme-project
```

Without `--workspace`, a folder picker opens. `--no-browser` prints the local
URL instead of opening it. Keep the terminal running; Ctrl+C stops the editor.
It binds only to `127.0.0.1`, chooses an unused port and checks origin/tokens for
project actions. Use one instance per working folder. A stale editor refuses to
overwrite newer metadata; Reload project reads the current disk version. Help
opens this guide locally, including with the verified offline cache.

## Working folder and saving

```text
theme-project.json           Settings, author metadata and source inventory
theme-project.previous.json  Previous saved metadata
theme/                      Editable runtime pack, including theme.ini
sources/                    Content-addressed original imports
artboards/                  Saved editable layers, outside runtime packages
splash/                     Shared Splash Builder project and source imports
imports/                    Previous theme retained before pack import
exports/                    SD-ready ZIPs and optional native screenshots
exports/backups/             Previous installed theme before replacement
```

Configuration and metadata fields save on change. Save artwork writes both the
flattened PNG and editable layers. The top Save button also saves pending artwork;
the browser warns before discarding it. Source masters remain when outputs are
regenerated. Switching assets or leaving an edited INI offers Save, Discard and
Cancel. Export, preparation and installation save pending artwork/INI first.
The artwork toolbar has labeled **Undo** and **Redo** buttons (Ctrl+Z and
Ctrl+Shift+Z), enabled when drawing history is available. Global undo retains up to 30 edits and 64 MiB of asset/layer snapshots in
the session; drawing has separate undo. Neither undo stack survives a restart.
Replacing an image outside the layer editor invalidates its old artboard.

Direct edits to `theme/theme.ini` are read on project reopen. Visual controls
rewrite it in canonical form; keep prose in credits files.

If external edits damage the INI or project metadata, interactive launch offers
recovery from valid saved metadata. Current metadata is copied into
`imports/recovery-*` first; artwork stays in place. Direct Python launch also
accepts `--recover --workspace PATH`. If neither the current project nor its
previous metadata is valid, recovery leaves the files unchanged and reports it.

## Authoring tools

Hover over the texture, import, copying, atlas and preparation buttons for short
explanations. Drawing guides and recipe controls also have descriptions, exposed
to assistive technology. **Generate texture…** (formerly Material recipe) creates
paper, linen, glass, metal, wood or gradient artwork from adjustable parameters.
It generates a replacement image for the selected slot; it does not add a texture
effect over existing artwork. Imported source masters remain in the project.

| Area | Choices |
| --- | --- |
| Project | Blank theme, palette starter, local folder clone or single-theme ZIP import. Imported notices remain intact. |
| Palette | Color picker, RGB entry, inheritance, starter palettes and colors extracted from an image. Native brightness checks report invalid combinations. |
| Layout | Ten top compositions, all browser views, small/medium/large icon sizes, row spacing, grid columns, tab presentation, per-screen opacity and Scene cover bounds. With Scene and Safe areas enabled, drag the artwork box to reposition its cover. |
| Backgrounds | Image import, contain/cover/stretch/native fit, crop anchor, opacity and smooth/nearest resampling; separate wallpapers, reading surfaces and shade maps. |
| Artwork editor | Brush, eraser, flood fill, line, rectangle, ellipse, gradient, text, eyedropper and layer movement. Visibility, opacity, blending, duplication and reordering; resize, rotate/flip, alpha quantization, PNG export and pixel/nine-slice guides. |
| Icons | All file/system/tab slots; PNG import, geometric starters, pixel editing, sprite-sheet import/export and copying an asset to multiple slots. |
| Components | All skin/status/control slots; independent artwork and paper/linen/glass/metal/wood/flat/gradient recipes; border, fill, controls and coverage settings. |
| Fonts | Prepared DSFONT import or proportional TTF/OTF conversion with separate body/heading metrics, baseline, variable weight and bounded bearing adjustment. |
| Audio | WAV conversion, mono mixdown, resampling, trim range, gain, fades and circular loop crossfade. Optional FFmpeg on PATH adds MP3/OGG/FLAC/M4A inputs. Embedded playback controls audition the result. |
| Motion | Separate Play/Stop demonstrations for the 16×16 header accent and brief selection-edge gleam; GIF/PNG conversion, uniform frame timing and feedback controls. |
| Splash | Full shared designer in the project’s splash folder; build saved layers into the theme or import a prepared splash. |
| Manifest | Direct INI editing with the same validation as visual controls. |

Drop an image into the artwork editor to add a layer. Elsewhere, dropping opens
import options for the selected asset. Atlas tiles map left-to-right, top-to-bottom
in the displayed slot order. Recipes are baked on the PC; no texture synthesis or
new runtime animation scripts are added to Gloam.

Artwork opened through a background or sprite slot keeps that assignment when
saved. Generic canvases have a Save as selector for wallpapers, reading surfaces,
material maps and native sprite slots. Renaming the destination does not silently
replace an existing image; replacement asks first. UI sound roles default to short
clips, with the length bounded by their rate and PCM cap.

## Preview and checks

The two-screen authoring preview is **approximate**. It uses shared prepared
background conversion, sprites and packed font glyphs, but its composition is a
PC illustration of Gloam’s layout. Switch browser views, settings context, focus
and guides to inspect common cases. Native banners, marquees, touch behavior,
ambient animation, Reduced motion and LCD contrast still require Gloam testing.

Publish can run a trusted local Gloam `build/host/preview` executable. Build it in
Gloam first; the editor never downloads or selects an executable from a theme.
This optional check creates a temporary synthetic SD fixture and captures the
actual renderer, without using a physical NAND or launching a title. The host
executable must match the computer running the editor.

Check theme validates manifest bounds, fields, paths, palette separation, fonts,
sprite dimensions, audio limits, ambient data and splash structure. Errors are
reported without discarding project edits. These checks do not certify licensing,
every native parser edge case or physical readability.

## Export and installation

Enter author, asset terms and source credits under Project. Add complete license
texts with Add a full license / credits file, and retain imported notices.
Imported author credits, including credits generated by another Studio project,
are kept; your adaptation gets a separate generated notice. Prepared output must
use its own `.gfx` path and cannot replace source artwork, fonts or notices.
Check theme, resolve errors, then Export ZIP. Export regenerates `assets.gfx`
through Gloam’s converter so old prepared data cannot hide PNG edits.

ZIPs contain this pack under `/_nds/dsi-frontend/themes/<id>/`, referenced runtime
assets and notices. Project metadata, source masters, layers, screenshots and
import backups stay on the PC. Extract onto the SD root, or install from Publish.
Replacement requires the checkbox and keeps the previous theme in the PC project.
Gloam settings, BOOT.NDS, games, saves and other themes remain untouched.

Body fonts remain 12 pixels; headings 12–16. Sprites are 32×32 PNGs, reading surfaces
and material maps 256×192. Music stays within 1 MiB PCM; cues within 64 KiB. Existing
prepared-bundle and motion caps remain. The editor requires no new frontend
features. Check the [theme contract](https://github.com/nextcode4u/gloam-shell-ndx/blob/main/docs/guides/THEME_PACKAGES.md)
for each field’s version requirements. Minimum-version declarations are optional
because older parsers reject that newer key.

## Source and maintenance

`theme.ps1` owns bootstrap/dependencies. `tools/theme_builder.py` owns the local
API, dialogs and converter dispatch. `theme_project.py` owns projects, history and
exports; `theme_schema.py` and `theme_validate.py` own controls/diagnostics.
`theme_media.py` owns conversions; `theme_preview.py` owns authoring/native preview.
`tools/theme_studio/` contains the browser interface. Unchanged Gloam packers and
their revision/hashes live in `tools/theme_native/`.

Run the Python suite and both download-manifest checks after changes. Refresh
`tools/theme-downloads.json` with `python tools/update_theme_manifest.py` whenever
a downloaded file changes. Keep generated projects under ignored build storage
or outside the repository. The editor does not modify checked-in collection packs.

## Back, close and playback controls

The persistent Back button returns to the previous section, asset library or
editor view. Escape and Alt+Left do the same; at the beginning of a session they
return to Project. Pending artwork/INI changes still offer Save, Discard and
Cancel. Escape in that confirmation cancels the navigation, rather than closing
the project. Back also restores the previous view's scroll and preview controls.

Temporary import, palette, atlas and material panels have their own Close button;
Back/Escape closes the latest panel first. Leaving audio stops playback. Native
renderer previews have Back to editor. If a preview/conversion finishes after
you navigate away, its output is saved without forcing you back into that view.

Help opens separately with Close help / return to editor, leaving the original
editor tab intact. In the shared splash designer, Escape or Stop preview / return
to editing stops playback. Save & close designer saves the splash project and
closes its window; Studio remains open. Use Build saved splash into theme there
when ready to prepare the package.

Linux CI installs `requirements-dev.txt` and Chromium to exercise the actual
browser journeys, including drawing, cancellation, conversion and a disposable
SD install. These are development dependencies only. To run those tests locally,
set `GLOAM_STUDIO_BROWSER` to a compatible Chromium executable and run the suite;
use `xvfb-run -a` when the shared Tk splash-editor tests need a virtual display.

Each reading-surface card in Backgrounds has an opacity slider and exact
percentage input. Top and bottom are independent; **Use shared opacity** inherits
Layout's common content opacity. Editing a value creates a per-screen override.
The screen preview updates after each adjustment; source PNG pixels are preserved.
These controls edit the same values shown in Layout.

### Composition and tab artwork

Panorama places a wide card above its caption; Dossier places artwork at right
with facts at left; Portrait gives artwork a tall left column. These join the
existing seven top layouts. The six composed layouts reserve separate title,
artwork and top/bottom navigation regions, including icon-tab captions. Scene
retains its movable artwork box. Panorama/Dossier/Portrait and medium icons need
a Gloam build after 1.1.0; older layouts and small/large sizes remain compatible.

**Interface framing** is the `chrome` setting in theme.ini: Full draws the
header/footer skins and dividers; Minimal leaves these areas open. It does not
remove labels or controls. Each layout control has explanatory help.

Beside **Tab highlight**, Design opens the exact `tab-selected.png` artboard;
Import opens image conversion for that slot. The thumbnail and theme-relative
path identify the asset in use. Component settings opens the slot library and
nine-slice border/alpha controls. Skin falls back to the accent color when no
image exists; Underline and Outline use the accent without a skin image.

### What Motion animates

**Header accent** places a small mark at top-screen coordinates (136, 4), just
left of the battery icon. The local preview shows the actual header position and
a magnified frame. Import a GIF to keep up to eight sampled frames, or a PNG for
a single still. Prepared frames are stored at 32×32 and displayed at 16×16.
Frame interval uses roughly 60 display ticks per second: 12 ticks means 0.2
seconds per frame (5 fps). GIF frame delays are replaced by this uniform timing.
The console advances the accent during idle browsing; Reduced motion holds the
first frame. These are browsing accents, separate from startup splashes.

**Selection feedback** adds a brief left-edge gleam after moving to an item;
`pulse` lasts about 0.2 seconds, rather than continuously pulsing an icon. The
local demonstration repeats that selection with a pause; the actual appearance
depends on the selected-row/card skin. Reduced motion disables the gleam. Native
DS/DSi banner animation is independent.

Both demonstrations start only when Play is pressed, and have visible Stop
buttons. Switching views stops playback. Changing a setting is reflected the
next time Play is pressed; the main two-screen authoring image remains static.

### Zooming and panning the two-screen preview

Use **+** and **−** beside Zoom, or choose 25–800% from the menu. **Fit** fits
both screens and resets panning. The percentage readout reports the actual scale,
including automatic Fit sizes. Enlarged images remain full-sized inside a
scrollable viewport instead of being shrunk back to the panel width.

Drag the image or surrounding preview area to pan; the middle mouse button also
works. Focus the viewport to use arrow-key scrolling, **+ / −** to zoom and **0**
to fit. Zoom and pan are viewing controls: they do not edit theme files. Back
restores the previous preview's scale and scroll position.

In Layout's Scene composition, Safe areas enables dragging the artwork box to
change its coordinates. Drag outside that box, hold **Alt** while dragging, or
use the middle button to pan without repositioning artwork. Releasing or
cancelling a drag ends it, including outside the viewport.

Tab styles and highlights preview on both side rails and horizontal docks:
Labels, Icons (a two-column grid on a side rail), Numbered and Pager (one focused
tab). Sidebar/Sidebar left keep side navigation; Poster/Scene keep a bottom dock.
Studio disables Top/Bottom position for those layouts, and disables horizontal
count/gap controls on side rails. Switching to a fixed-position layout removes
an incompatible position override in the same undoable edit. Inherited positions
show the actual preset default: Gallery uses Top; the other composed layouts use
Bottom. Imported incompatible overrides can be cleared with **Use layout's fixed
position** before export.
