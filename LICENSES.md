# Licenses and credits

Repository-authored tools, tests, documentation and starter theme configuration
use GPL-3.0-or-later; the full text is in LICENSE. This does not override the
licenses of contributed assets.

Theme Studio's header and browser-tab mark reuse Gloam Shell NDX's original
32×32 application icon (`forwarder/icon.png`), under the project's GPL-3.0-or-later
terms. It is the same artwork used for BOOT.NDS, kept at native pixel dimensions.

Theme Studio includes unchanged Gloam font and prepared-asset converters under
`tools/theme_native/`. UPSTREAM.json records their exact revision and SHA-256
hashes; they retain Gloam’s GPL-3.0-or-later terms. Shared splash tools retain the
same license. Pillow is installed separately under its own terms. Imported
fonts, illustrations and audio retain their licenses; export credits do not
replace required third-party notices.

Original artwork and synthesized UI cues in Slate, Folio and Phosphor are dedicated
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Each theme’s CREDITS.md identifies its source and asset terms.

Community authors retain their copyright and choose their own explicit licenses.
Submitting a theme does not automatically place it under the repository’s default
license. Include redistribution permission, attribution and license notices for
every external asset. Do not assume that an image or song being downloadable gives
permission to redistribute it.

The Aerial, Koi, Vesper, Tidal and Morrow collection includes agent-assisted wallpaper
illustrations, code-authored geometry and original synthesized UI cues. Project-held
rights in those assets are dedicated under CC0-1.0; their fonts retain the full original notices beside each pack. Updated packs
use the SIL Open Font License; Morrow retains its DejaVu pairing. Immutable OFL
source revisions and hashes are recorded in `config/theme-fonts.json`. See individual CREDITS.md files.

## BUUF adaptation

Original BUUF icons are by [mattahan](https://www.deviantart.com/mattahan).
The upstream theme credits fana-m and Hybrid Son Of Oxayotl. Icons and the
adapted theme artwork use **CC-BY-NC-SA-2.5**; this includes the new Gloam
supporting illustration and skins, and overrides any general CC0 wording for
those BUUF assets. Commercial use is not granted. Preserve the full
[BUUF license](themes/buuf/BUUF-LICENSE.txt) and [credits](themes/buuf/CREDITS.md).
Unmodified upstream originals and hashes are retained in `source/buuf/`.

BUUF fonts retain SIL OFL 1.1; original synthesized UI cues are CC0-1.0; background music is CC-BY-4.0;
configuration/tools are GPL-3.0-or-later. `buuf.zip` is packaged separately and
is not included in the original-art or starter collection archives.

## Background music

Prepared background music by **Kevin MacLeod (incompetech.com)** uses CC-BY-4.0,
separate from project artwork and synthesized UI-cue licenses. Each pack includes
MUSIC.md with track credit, source and adaptation notes, and MUSIC-LICENSE.txt
with the full license. Source/output hashes and conversion settings are in
`config/theme-music.json`; `tools/prepare_theme_music.py` verifies or reproduces
the prepared WAVs. No theme build regenerates placeholder music over these tracks.

## Desktop and device interpretations

Luna XP, Desktop 98, Classic DS, Portal Terminal, Aero Glass, Pokédex and
Synthwave use original illustrations and code-authored UI assets. Classic DS
uses a code-authored gray grid and monochrome glyphs; Desktop 98 uses a solid
palette background and original code-authored pixel icons. The other five use
agent-assisted wallpaper/icon illustrations. Project-held rights in these artworks, original UI cues
and splash compositions are dedicated under CC0-1.0. Fonts retain SIL OFL 1.1;
recorded music by Kevin MacLeod retains CC-BY-4.0 and per-pack attribution.

These packs are unofficial interpretations, not endorsed products. Referenced
Windows/Microsoft, Nintendo, Pokémon and Rick and Morty names/marks remain with
their respective owners. No extracted official wallpaper, icons, character
sprites, television clips or franchise/system audio is included. The dedication
covers project-held rights only. See each pack's CREDITS.md and original font
and music license texts; artwork hashes are in config/inspired-art.json.
