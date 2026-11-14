# Morrow

Terracotta, olive leaves and a sunlit sea. Paper tabs, stitched borders, quiet marimba and warm chord voicings.

![Actual Gloam renderer preview](preview.png)

## Design

- **Journal** composition; numbered navigation at the bottom.
- **Extended** browser by default; other views and icon sizes remain selectable.
- DejaVu Serif body at 10 px, with a separate DejaVu Serif-Italic heading face at 12 px.
- Independent reading surfaces: top 76%, bottom 88% opacity.
- Four-level component coverage for translucent cards and layered edges. Modal panels retain solid reading surfaces.
- Native title banners retain priority over themed fallback icons.

Original background music and cursor/confirm/back cues. Select **Audio → Background music → Theme** to hear the loop.

## Install

**Requires the updated Gloam build with theme format 2. Gloam 1.0.0 cannot load this revision.**
The [format guide](https://github.com/nextcode4u/gloam-shell-ndx/blob/main/docs/guides/THEME_PACKAGES.md)
describes the new capability. The [original 1.0-compatible collection](https://github.com/nextcode4u/gloam-shell-theme-directory/tree/74fd2dd/themes/morrow) remains available in history.

Copy the entire `morrow` folder to `/_nds/dsi-frontend/themes/morrow/` on your SD card,
backing up any existing theme with that name. In Gloam, choose **START → Appearance → Theme**,
select Morrow and press A. Reapply to restore the default view and accent.
Reset personal wallpaper overrides to see the supplied backgrounds.

## Preview and limits

Previews use Gloam's actual renderer and synthetic content. Library index and
item details use the shared index/inspector arrangement. Component coverage blends
existing pixels; there is no live blur. Physical LCD contrast and frame timing
still need testing on a DSi.

[Settings preview](settings-preview.png) · [Credits and licenses](CREDITS.md)
