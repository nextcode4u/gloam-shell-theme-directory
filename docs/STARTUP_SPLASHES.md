# Create a startup splash

The Splash Builder and command-line converter live in this repository. Gloam
loads their prepared `.gsp` packages; the console does not need Python or a copy
of the builder.

Splash playback requires a Gloam build containing commit
[`82e6116`](https://github.com/nextcode4u/gloam-shell-ndx/commit/82e6116).
Gloam 1.0.0 does not support splashes. Existing themes still work without one.

## Launch from Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/nextcode4u/gloam-shell-theme-directory/main/splash.ps1 | iex
```

The command downloads and runs this repository's [launcher](../splash.ps1).
It opens a working-folder picker after checking the builder's dependencies.
Select the same folder on a later run to resume; the picker starts in the last
folder you used. You do not need Git or a repository checkout.

- An existing Python 3.10–3.13 installation with Tcl/Tk can be used. If none is
  found, choose installation through WinGet, enter an existing `python.exe`, or
  cancel. The WinGet option installs Python 3.13 for your Windows account. If
  WinGet is unavailable, the launcher offers the official Python downloads page.
- The launcher asks before preparing its private environment with Pillow. It
  does not install packages into your existing Python environment. This launch
  path does not need NumPy, which is used by other theme-authoring tools.
- Builder files and dependencies are cached in
  `%LOCALAPPDATA%\Gloam\SplashBuilder`, separately from your working folder.
  Online runs check for a newer builder. All downloaded files come from one
  commit and their sizes and SHA-256 hashes are checked against its manifest.
- If a tool update fails, a previously verified cached copy can still open.
  The `irm` command itself needs a connection. For offline use, save `splash.ps1`
  locally while online, then run the saved script after preparing dependencies
  at least once:

```powershell
irm https://raw.githubusercontent.com/nextcode4u/gloam-shell-theme-directory/main/splash.ps1 -OutFile splash.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\splash.ps1 -Offline -Workspace "D:\Artwork\My Splash"
```

Omit `-Workspace` to use the picker. `-Python "C:\path\to\python.exe"` selects a
particular interpreter. The execution-policy option above applies only to that
PowerShell process. Updating the builder does not replace project files or source
artwork. An exported splash is installed on an SD card only through an explicit
export/install action in the builder.

## Build and preview

From the root of this repository, use Python 3.10+ and run:

```sh
python -m pip install -r requirements.txt
python tools/pack_splash.py
```

The graphical Splash Builder uses Python's Tk interface (included with the
standard Windows Python installer; some Linux distributions package Tk separately).
It is a small splash tool, independent of a full theme editor.

Choose or create a **working folder** when the builder opens. To continue later,
open the same folder. The builder restores your artwork, animation settings and
last export location. You can also open it directly:

```sh
python tools/splash_builder.py --workspace "path/to/My Splash"
```

Changes save automatically after a short pause; **Save project** saves immediately.
The folder contains `splash-project.json`, a backup of the previous save named
`splash-project.json.bak`, and an `assets/` directory for imported artwork/audio.
The file pickers copy external source files into `assets/`, so moving the whole
working folder to another computer keeps those sources available. Selecting a
frame folder imports its PNG frames. Typing an external path manually instead
keeps a reference to that file; copy it into the working folder for portability.
Files already inside the working folder are used in place.

Project saves preserve unfinished entries, including incomplete numbers; build
validation happens when you preview or export. The builder refuses to overwrite
a project changed by another window. Reopen it to load the saved version before
editing further. A `.gsp` export is separate from the editable project: autosave
does not rebuild or overwrite an installed splash.

1. Open the **Top**, **Bottom**, **Top overlay** or **Bottom overlay** tab and
   choose PNG/JPEG artwork, an animated GIF or numbered PNG frames. Leave unused
   layers empty. Each layer has its own settings.
2. Choose sizing: **fit** preserves aspect ratio, **crop** fills the layer's box,
   **stretch** fills it without preserving proportions, and **native** keeps small
   artwork at its original size (oversized artwork is reduced to fit). Overlays
   also have a width control, independent for each screen.
3. Choose a motion preset, then tune its values. **Start/End scale** support
   0–400%; use equal values for a static size, or different values for zoom.
   Scaling is centred. **Start/End X/Y** offsets move the layer relative to its
   centred position. Motion outside its screen is clipped.
4. Adjust **Start/End opacity**, **Start delay**, **Motion duration**, and easing
   (**linear**, **ease-in**, **ease-out**, **smooth**). Combine movement, zoom and
   fade. **Reveal direction** can independently reveal right, left, up or down.
5. **Motion repeat** and **GIF/frame repeat** each offer once, loop or ping-pong.
   Once holds the final state. A pulse can run independently of an animated logo's
   frame sequence. Repeated motion and reveals require a positive duration.
6. Set the whole splash's frame rate, duration, still-frame time and background
   colour. Automatic duration covers source sequences and layer effects including
   delays. A shorter explicit duration deliberately cuts playback short. Animated
   GIF timing is resampled at the chosen rate; the rate does not add frames to
   a static-image motion effect.
7. Optionally choose a WAV. Mono/stereo 8/16-bit PCM at 8–48 kHz is converted to
   mono PCM16 at 16 kHz, limited to the splash duration. The PC preview is silent.
8. Build and preview. Check Reduced motion, Skip and fast-startup simulation.
   Reduced motion uses the selected source frame with final position/scale/opacity;
   it does not play transforms. While loading may end partway through the intro.
9. Save a `.gsp`, **Add to theme**, or **Install as custom splash**. All layer
   settings save with the working project, including unfinished numeric entries.

Presets include fade, four slides, four reveals, zoom-in, zoom-out, fade-zoom,
pulse and drift. Choosing a preset fills motion fields; subsequent edits remain
in effect even while its name is selected. Choose Custom to edit without applying
another preset. Sizing, delay, duration and frame-repeat choices survive changing
a preset. The controls pane scrolls on smaller windows.

**Uncompressed layer controls export splash format 2 and require Gloam commit
[`9cb5604`](https://github.com/nextcode4u/gloam-shell-ndx/commit/9cb5604) or later.**
Existing version-1 splashes still play. Old saved projects migrate when
opened, preserving their global choices and overlay behavior. The previous file
is backed up when saved. Older builders cannot edit version-2 projects.

The GUI also compresses each layer's prepared frames when this makes the package
smaller. Compressed exports use **splash format 3**, requiring a matching Gloam
build with compressed-frame playback. Compression preserves the prepared pixels,
timing and motion controls; it does not drop frames or reduce resolution. Both
formats use the same editable project files. The standalone Gloam 1.0.0 release
supports neither format.

Add to theme writes only `splash.gsp`; it needs no INI changes. Include the source
artwork's credits/license with the theme. Custom installation keeps the package
under `splashes/`, backs up an existing valid state file, and preserves unrelated
settings and repeated navigation/favorite records. It does not change ROMs or saves.

For repeatable command-line builds:

```sh
python tools/pack_splash.py splash.gsp --top sky.png --top-logo logo.png --effect fade
python tools/pack_splash.py splash.gsp --top animation.gif --bottom still.png --fps 15
python tools/pack_splash.py splash.gsp --top frames/ --fps 20 --sound intro.wav
python tools/pack_splash.py splash.gsp --top sky.png --effect fade-zoom
python tools/pack_splash.py splash.gsp --top sky.png --bottom-logo logo.png --layers motion.json
python tools/pack_splash.py splash.gsp --top top.gif --bottom bottom.gif --fps 20 --compress
```

`--layers` accepts a JSON object with optional `top`, `bottom`, `top_logo` and
`bottom_logo` objects. Example:

```json
{
  "top": {"preset": "none", "fit": "crop"},
  "bottom_logo": {
    "preset": "fade-zoom", "width": 96, "delay": 0.3,
    "transition": 0.8, "scale_from": 45, "scale_to": 100,
    "start_y": 24, "end_y": 0, "easing": "ease-out"
  }
}
```

Other keys are `start_x`, `end_x`, `opacity_from`, `opacity_to`, `repeat`,
`sequence` and `reveal`. Effects and full per-layer controls are shared with the
GUI. Legacy CLI requests using only old effects/fit modes still export version 1;
new controls export version 2, or version 3 when `--compress` saves space.
The CLI leaves compression off unless requested. New exports never silently drop
motion options to accommodate an older runtime.

An existing output requires `--replace`. `--duration` and `--poster` use seconds;
`--transition` controls effect duration. The default is shared indexed colour;
`--direct` retains RGB555 colours with greater memory/SD cost. Source images and
frame sequences remain editable; the `.gsp` is the runtime asset.

## Package limits and playback

Both format versions can use one or both 256×192 screens, four layers, up to 120 frames
per layer and ten seconds of playback, within 2 MiB total. Prefer a static
background and a small animated overlay to keep loading fast. The builder
supports 5, 6, 10, 12, 15 and 20 fps and reports the final size before export.
Transforms reuse their prepared images without baking intermediate frames.
Scaling uses nearest-neighbour sampling on the DSi; use suitable source artwork
and test small text on hardware. Source GIF frames still count against the
2 MiB package limit. Compression can make a full-screen animation fit, but noisy
or long sequences can still exceed the limit. Use fewer/smaller source frames
when that happens; the builder never changes your frame rate automatically.

Gloam reads the complete package once and decodes only the current source frame
per compressed layer. It uses one reusable frame buffer for each compressed
layer (48 KiB for a full indexed screen, 96 KiB for direct colour). There are no
per-frame SD reads or heap allocations. Missed deadlines skip directly to the
current frame. Test timing on a DSi as well as the PC preview, especially with
several full-screen layers. The supplied Gloam default has two 64-frame screens
at 20 fps and remains outside the executable, under
`/_nds/dsi-frontend/themes/default/splash.gsp`.

In Gloam, use **START → Appearance** to select Theme or Custom and preview the
result. While loading can finish early; Play once allows the full intro. Any
button skips, and Reduced motion uses the designated still frame without sound.

The authoritative [runtime settings and package format](https://github.com/nextcode4u/gloam-shell-ndx/blob/main/docs/guides/STARTUP_SPLASHES.md)
live with Gloam's source. Keep package-version changes coordinated with its
native decoder.

## Checks

```sh
python -m unittest discover -s tests -p 'test_*.py'
```

Tests cover prepared pixels, GIF timing, transparency, colour modes, audio
conversion, file limits, preserving SD settings, portable projects and interrupted
saves. GUI tests exercise autosave, reopening, preview and export; on headless
Linux run the command through `xvfb-run -a`. Windows PowerShell tests check download
verification, cached fallback and cancellation without installing Python. Tests use
temporary synthetic fixtures and do not need an SD card or a Gloam checkout.

For pixel-for-pixel checks against the updated native runtime, set `GLOAM_SOURCE`
to a Gloam checkout and run `tests/test_splash_motion.py` with a host C compiler
available. It checks presets, clipping, scaling, opacity, frame repetition and
Reduced motion under address/undefined-behavior sanitizers. Normal tool tests do
not require that checkout. DSi frame timing still requires hardware testing.

After editing a downloaded builder file or its license notices, maintainers must
refresh the launcher's manifest before committing:

```sh
python tools/update_splash_manifest.py
python tools/update_splash_manifest.py --check
```

CI checks the manifest on Linux and Windows. To test the bootstrap against a local
checkout, run `splash.ps1 -SourceDirectory . -NoLaunch`; use `-CacheDirectory` to
isolate its cache. Dependency downloads still require confirmation. `-NoLaunch`
prepares and verifies the tool without opening its window.

For native compatibility checks, run Gloam's `tools/host-check.sh`, then generate
an isolated fixture from that checkout with
`python tests/splash_fixture.py /tmp/splash-check`.
Run Gloam's `build/host/splash-test /tmp/splash-check` against it. Use a new temporary
folder each time: the native suite writes test preferences inside that fixture.
Keep generated packages under ignored `build/` or `dist/` while designing; commit
only intended production `splash.gsp` assets with their theme's source and credits.

## Included theme intros

All sixteen packs include a short `splash.gsp`. Choose **Startup splash → Theme**
in Gloam to use the selected pack’s intro. **Preview splash** plays it without
restarting. Custom overrides, Off, skipping and Reduced motion still apply.

These intros use two still backgrounds and one title layer, not full-screen
animation sequences. Each lasts 1.2 seconds and stays below 128 KiB. Reveal,
slide, fade and gentle scale effects vary by theme; the title uses that pack’s
heading/body faces. They are silent so they do not compete with theme music.
While loading may finish early; choose Play once to see the complete intro.

Rebuild the collection using its existing artwork and verified font sources:

```sh
python tools/build_theme_splashes.py --download-fonts --font-dir /path/to/dejavu
```

`--gloam /path/to/gloam-shell-ndx` also prepares the eleven bundled Gloam themes.
Omit `--download-fonts` to use the previously verified authoring cache. Morrow
needs `DejaVuSerif-Italic.ttf` and `DejaVuSans.ttf` in `--font-dir`; their notice
already ships with the theme. Other font revisions and hashes are pinned in
each repository’s `config/theme-fonts.json`.

`--check` rebuilds in temporary storage and compares the installed packages
without writing. The current packages were authored with Pillow 11.3.0;
font rasterization changes in other Pillow/FreeType versions can change bytes.
The tool changes only `splash.gsp`; source artwork, previews, music and settings
are preserved. Splash artwork and type remain covered by the pack’s existing
credits and licenses, including BUUF’s noncommercial terms.

The seven desktop/device packs can be regenerated with
`python tools/build_inspired_collection.py --gloam /path/to/gloam --download-fonts`.
Their recorded music remains pinned and separate. The builder uses
`config/inspired-themes.json` for authored defaults and `config/inspired-art.json`
for original artwork checksums; only prepared runtime assets enter theme ZIPs.
