# Possible Gloam improvements — not implemented

These five packs work with 1.0.0. No frontend changes were made for this collection.

## Optional translucent component coverage

Current components/icons discard alpha below 128 and draw the remaining pixels
opaquely. Rounded cutouts and empty centers work, but translucent glass does not.
A future format could add a 2-bit alpha plane for components (not native banners),
retain the current binary-alpha fast path, and blend only partial-coverage pixels.
A 32×32 component would need 256 extra bytes of packed coverage; 19 components
would need 4,864 bytes per active/preview set, plus rendering work. Actual speed
must be measured before adoption. Keep existing packs compatible and avoid live
blur, which has a considerably higher cost.

## Font authoring versus proportional text

Four-level grayscale text blending already exists. This collection uses it,
requiring no Gloam changes. At 256×192, excessive smoothing can reduce contrast;
retain full-coverage stems and evaluate both light and dark themes on the LCD.

Proportional fonts, larger headings and separate heading/body faces would make a
larger stylistic difference. They need consistent pixel-width measurement for
wrapping, scrolling, clipping and touch/layout calculations, plus explicit theme
format/version compatibility. That is a separate frontend change requiring owner
approval and regression testing, not something hidden in an asset pack.

## Further layout control

Independently configurable top/bottom reading-surface opacity would preserve more
illustration while protecting browser text. Larger composition changes should use
bounded named layouts, not unrestricted widget positions or theme scripts.
