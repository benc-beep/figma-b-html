# Images and icons

`download_assets` returns three things for a node:

| | |
|---|---|
| `export` | a flat render of the whole node — a fallback, not a deliverable |
| `rawImages` | the original uploaded photos found as fills, **capped at 20** |
| `svgAssets` | vector layers best represented as SVG, **capped at 20** |

URLs are temporary. Download them in the same turn you receive them.

## The icon trap — read this before placing a single icon

**Figma exports an icon SVG at the glyph's own size, not at the icon's box
size,** and stamps `preserveAspectRatio="none"` on it. `icon-arrow-down-2.svg`
is 10.83x6.17; the icon it belongs to is 16x16. The export then places that
glyph inside the nominal box with nested percentage-inset wrappers, and those
wrappers are what carry its real size, offset and rotation.

Write `width:16px; height:16px` on the `<img>` and the glyph is stretched to a
square. Every chevron on the page comes out fat and wrong.

The shape that works: the box carries the layout size, the glyph keeps its own.

```css
.gi { position: relative; flex: none; display: block; }
.gi img { position: absolute; left: 50%; top: 50%; max-width: none;
          transform: translate(-50%, -50%); }
.crumbs__sep     { width: 16px; height: 16px; }          /* the nominal box */
.crumbs__sep img { width: 10.8333px; height: 6.16667px;  /* the SVG's own size */
                   transform: translate(-50%, -50%) rotate(90deg); }
```

Read the natural size straight off the file — `<svg width="…" height="…">` — and
the rotation off the export. Nested rotations compose: a `-rotate-90` inside a
`rotate-180` wrapper is one `rotate(90deg)`. Where Figma's insets are asymmetric,
place the glyph with `left`/`top` instead of centring it.

**Then prove it, because the score will not:**

```bash
python3 ~/.claude/skills/figma-b-html/scripts/measure.py \
  --file <project>/screens/<slug>.html --width 1440 --icons
```

It compares every local SVG's own dimensions against the box it renders in and
names anything being stretched. Run it on every screen before the handoff.

## Icons — inline SVG

Icons go **into the HTML**, not into files:

```html
<svg class="icon" width="20" height="20" viewBox="0 0 20 20" fill="none"
     aria-hidden="true">
  <path d="…" fill="currentColor"/>
</svg>
```

Three reasons this is worth the verbosity: the file stays self-contained,
`currentColor` makes the icon follow its text so one token change recolours it,
and the developer can see immediately that it is an icon rather than a mystery
asset reference.

Clean up what Figma emits: drop `width`/`height` from the inner paths, keep the
`viewBox`, replace hardcoded fills with `currentColor` **when the icon is
monochrome**. A multi-colour logo keeps its own fills — do not flatten it.

`aria-hidden="true"` on decorative icons. An icon that is the only content of a
button needs the button to carry an `aria-label`.

## Photographs — files

Into `assets/`, referenced relatively:

```html
<img src="../assets/hero.jpg" alt="…" width="1200" height="600">
```

- Keep the format `download_assets` reports in each image's `format` field. Save
  with the matching extension; a `.png` that is actually a JPEG confuses tooling
  later.
- **Always set `width` and `height` attributes.** Without them the page reflows as
  images load, and a capture taken mid-load compares against a shifted layout —
  a fidelity failure with no design cause.
- Descriptive filenames: `hero-family-car.jpg`, not `image_427.png`.

## When the source image is smaller than the box it fills

Check it. A Figma layer can display a 192x375 upload at 240x470 — the designer
sees Figma's upscaling, and the browser's upscaling of the same file will not
match, so the region shows up in the diff with no layout cause.

The fix is to stop shipping the raw fill and export the **node** instead, at a
scale that oversamples:

```
download_assets(fileKey, nodeId=<the image layer>, defaultFormat="png", defaultScale=3)
```

Use the `export` entry, size it to the layer box, and drop the raw fill's crop
offsets — the export already is the layer. Some residual difference between the
two renderers' resampling will remain; record it rather than chasing it.

## Backgrounds

A Figma image fill on a shape becomes CSS:

```css
background-image: url("../assets/pattern.png");
background-size: cover;   /* Figma "Fill" */
```

Figma's fill modes map: Fill → `cover`, Fit → `contain`, Crop → `cover` plus a
`background-position`, Tile → `repeat` with `background-size` set to the tile.

## When the caps bite

A screen with more than 20 photos or more than 20 vectors gets truncated
silently. Two symptoms: missing images in the render, and a diff heatmap with
large solid red blocks. When a screen is that dense, call `download_assets` per
**section** node instead of on the whole frame.

## Illustrations

A complex illustration is often better as one exported PNG at 2x than as a
thousand-node SVG that renders slightly differently in every browser. Judgement
call: if the SVG is over roughly 100KB or has hundreds of paths, export it as an
image and note it in the handoff so nobody expects it to be themeable.

## What never goes in

Do not embed images as `data:` URIs. It bloats the file past the point where the
live editor and a normal diff can work with it, and the developer cannot reuse
the asset.
