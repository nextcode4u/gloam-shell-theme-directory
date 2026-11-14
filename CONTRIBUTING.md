# Contributing a theme

1. Give your theme a unique folder ID: ASCII letters, numbers, hyphens or underscores,
   up to 63 characters. Put it in `themes/<id>/` with a format-1 `theme.ini`.
2. Keep all referenced assets inside that folder. Include only runtime assets,
   documentation and editable source where useful; no executables, ROMs, BIOS,
   user settings, generated archives, prompt logs or private testing files.
3. Add a README with author, description, minimum Gloam version, installation
   instructions and previews. Label wallpaper-only or renderer previews clearly.
4. Add CREDITS.md with license terms, source links and attribution for your own and
   third-party assets. Include required license texts. Only submit assets you own
   or have explicit permission to redistribute; retain original authors’ credit.
5. Add the entry to catalog.json. Separate configuration and asset licenses when
   they differ; do not claim CC0 for third-party fonts or music.
6. Test the theme in Gloam: preview/apply/cancel, both screens, long names, settings,
   all browser views, small/large icons, touch targets and Reduced motion. Check
   contrast, clipping, memory limits and audio. Report what you actually tested;
   emulator-only submissions are welcome if labeled honestly.
7. Open a pull request. Explain any limitations and whether an existing theme ID
   is being updated. Screenshots must not expose personal paths or user data.

Use the upstream [theme guide](https://github.com/nextcode4u/gloam-shell-ndx/blob/main/docs/guides/THEME_PACKAGES.md)
for supported keys, image/audio formats and bounds. Keep community theme artwork
original or properly licensed; do not copy another frontend’s theme library.
