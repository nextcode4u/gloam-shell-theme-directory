# Morrow

Terracotta, olive leaves and a sunlit sea. Paper tabs, stitched borders, quiet marimba and warm chord voicings.

![Actual Gloam host-renderer preview](preview.png)

## Design

- Top composition: **scene**. Navigation: **numbered**.
- Default browser: **index**, large icons; other views remain selectable.
- Original full-screen illustration, matching lower-screen reading surface,
  29 icons, selection frames and battery/Wi-Fi/update symbols.
- Softly antialiased Latin-1 font using Gloam’s existing four-level coverage.
- Original **21.82-second** mono music loop at 88 BPM,
  plus cursor, confirm and back cues. [Listen to the music](sounds/loop.wav).

## Install

Requires **Gloam Shell NDX 1.0.0 or later**, theme format 1. Copy the whole `morrow`
folder to `/_nds/dsi-frontend/themes/morrow/` on the SD card, or extract this theme’s
install ZIP into the SD root. Back up an existing theme with the same ID first.

Open **START → Appearance → Theme**, select Morrow and press A. Set
**Audio → Background music → Theme** and enable theme sounds. Reset personal
wallpaper overrides if the illustration does not appear. Reapply the theme to
restore its default view and accent; your audio-volume settings are respected.

## Validation and limits

Preview images are actual Gloam host-renderer output with synthetic folder/file
names, not console photographs. Checked with Gloam 1.0’s loader/rendering code:
preview/cancel/apply, all six browser views at both icon sizes, category screens,
item details, Reduced motion, settings, every icon/component and all WAV assets.
Framebuffer bounds were checked under AddressSanitizer/UndefinedBehaviorSanitizer.
Physical LCD readability and on-console audio balance remain to be checked.

Transparent frame centers work in Gloam 1.0. Glass/metal depth is shaded artwork;
components do not perform translucent alpha blending or background blur. Native
ROM/system banners still take priority over theme fallback icons. Library Index
and item details intentionally use Gloam’s shared index/inspector arrangement.

[Settings preview](settings-preview.png) · [Credits and licenses](CREDITS.md)
