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

1. Choose PNG/JPEG artwork, an animated GIF, or a folder of numbered PNG frames
   for each screen. A single screen is enough; unused screens stay black.
2. Optionally add a transparent overlay/logo for either screen. Overlays are
   centered; their width can be adjusted. Without an overlay, the chosen effect
   applies to the screen image instead.
3. Choose fit or crop, frame rate and effect: none, fade, slide up, slide left or
   reveal. Effects last 0.5 seconds by default. Fit preserves aspect ratio and
   uses the selected letterbox colour; crop explicitly fills the screen.
4. Set duration and a still-frame time, or leave them automatic. Animated inputs
   retain their timing through fixed-rate sampling; PNG folders use the selected
   frame rate. Short sequences hold their last frame. Frames beyond an explicitly
   shorter package duration are not shown.
5. Optionally choose a WAV. The converter accepts mono/stereo 8/16-bit PCM at
   8–48 kHz and converts it to mono PCM16 at 16 kHz. Sound is limited to the package
   duration. The PC visual preview is silent; check audio in Gloam.
6. Build and preview. Check Reduced motion, Skip, and the fast-startup simulation.
   The opening image should already make sense: While loading may end mid-animation.
7. Save a `.gsp`, **Add to theme** (choose the folder containing `theme.ini`), or
   **Install as custom splash** (choose the SD root/staging folder).

Add to theme writes only `splash.gsp`; it needs no INI changes. Include the source
artwork's credits/license with the theme. Custom installation keeps the package
under `splashes/`, backs up an existing valid state file, and preserves unrelated
settings and repeated navigation/favorite records. It does not change ROMs or saves.

For repeatable command-line builds:

```sh
python tools/pack_splash.py splash.gsp --top sky.png --top-logo logo.png --effect fade
python tools/pack_splash.py splash.gsp --top animation.gif --bottom still.png --fps 15
python tools/pack_splash.py splash.gsp --top frames/ --fps 20 --sound intro.wav
```

An existing output requires `--replace`. `--duration` and `--poster` use seconds;
`--transition` controls effect duration. The default is shared indexed colour;
`--direct` retains RGB555 colours with greater memory/SD cost. Source images and
frame sequences remain editable; the `.gsp` is the runtime asset.

## Package limits and playback

A package can use one or both 256×192 screens, four layers, up to 120 frames
per layer and ten seconds of playback, within 2 MiB total. Prefer a static
background and a small animated overlay to keep loading fast. The builder
supports 5, 6, 10, 12, 15 and 20 fps and reports the final size before export.

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
an isolated fixture with `python tests/test_splash.py --fixture /tmp/splash-check`.
Run Gloam's `build/host/splash-test /tmp/splash-check` against it. Use a new temporary
folder each time: the native suite writes test preferences inside that fixture.
Keep generated packages under ignored `build/` or `dist/` while designing; commit
only intended production `splash.gsp` assets with their theme's source and credits.
