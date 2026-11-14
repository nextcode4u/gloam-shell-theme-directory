# Create a startup splash

The Splash Builder and command-line converter live in this repository. Gloam
loads their prepared `.gsp` packages; the console does not need Python or a copy
of the builder.

Splash playback requires a Gloam build containing commit
[`82e6116`](https://github.com/nextcode4u/gloam-shell-ndx/commit/82e6116).
Gloam 1.0.0 does not support splashes. Existing themes still work without one.

## Build and preview

From the root of this repository, use Python 3.10+ and run:

```sh
python -m pip install -r requirements.txt
python tools/pack_splash.py
```

The graphical Splash Builder uses Python's Tk interface (included with the
standard Windows Python installer; some Linux distributions package Tk separately).
It is a small splash tool, independent of a full theme editor.

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
conversion, file limits and preserving SD settings. They use temporary synthetic
fixtures and do not need an SD card or a Gloam checkout.

For native compatibility checks, run Gloam's `tools/host-check.sh`, then generate
an isolated fixture with `python tests/test_splash.py --fixture /tmp/splash-check`.
Run Gloam's `build/host/splash-test /tmp/splash-check` against it. Use a new temporary
folder each time: the native suite writes test preferences inside that fixture.
Keep generated packages under ignored `build/` or `dist/` while designing; commit
only intended production `splash.gsp` assets with their theme's source and credits.
