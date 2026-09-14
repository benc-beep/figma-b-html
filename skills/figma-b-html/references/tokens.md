# tokens.css — the design system

Every value a screen uses comes from here as `var(--token)`. A raw hex inside
`screens/*.html` is a bug, and it is the bug that makes the output useless to a
developer: they cannot map `#3D8168` to their codebase, but they can map
`--color-brand-600`.

## Writing it

`get_variable_defs` returns Figma's own names, e.g. `{"icon/default/secondary": "#949494"}`.

**Keep Figma's names.** Do not rename them to something you find tidier. The
whole point is that the developer can search their design system for the same
string. Convert only the syntax:

```
icon/default/secondary   →  --icon-default-secondary
color/Brand/600          →  --color-brand-600
spacing/lg               →  --spacing-lg
```

Rules for the conversion: lowercase, `/` and space and `_` become `-`, collapse
repeats, strip anything that is not `a-z 0-9 -`. Two Figma names that collapse to
the same CSS name is a real collision — keep the second one distinct by
retaining a distinguishing segment, and note it in the file.

Group them under the section comments already in the scaffold: colour,
typography, spacing, radius, elevation. An empty section stays empty with a one
line comment saying the file exposed none — **do not invent tokens to fill it.**

Aliases are worth preserving. If Figma has `button/bg` → `color/brand/600`,
write both, with the alias pointing at the primitive:

```css
--color-brand-600: #3D8168;
--button-bg: var(--color-brand-600);
```

That is the structure a design system actually has, and flattening it loses the
information that these two are the same decision.

## Typography

Figma variables rarely carry the whole type scale. Read the text styles out of
`get_design_context` for the screens you convert and add what you find:

```css
--font-family-base: "Inter", system-ui, sans-serif;
--font-size-h1: 32px;
--line-height-h1: 40px;
--letter-spacing-h1: -0.02em;
```

**Line height is not optional.** Figma sets an explicit line height on nearly
every text layer; a browser's default is around 1.2 and differs per font. Leaving
it out is the single most common cause of a screen that is 40px too short and
fails the comparison for reasons that look mysterious.

## Fonts

Name the real family, then a real fallback stack. Do not substitute a lookalike
silently.

If the design uses a font that is not on this machine, the render will fall back
and the comparison will show text differences everywhere. When that happens:

1. Say it plainly — *"הפונט X לא מותקן, הטקסט מוצג בפונט חלופי"*.
2. Ask them for the font file. If they have it, drop it in `assets/fonts/` and add an
   `@font-face` with a relative `url()`.
3. If they do not, record it in `notes.json` for every affected screen and let
   the numbers be honest. **Do not tune spacing to make a substitute font hit the
   pixel target** — that bakes a lie into the file, and it breaks the moment the
   real font arrives.

Web fonts from Google Fonts are fine to link, and they make the file work on any
machine. A local `@font-face` is more faithful but only works next to the file.
Prefer the local file when they have it; say which one you used.

## When the file has no Variables

Plenty of real files use raw styles. Then:

1. Collect every colour, size and radius that actually appears across the screens
   in the batch.
2. Cluster them — designers do not use 40 greys, they use 6 and a few accidents.
   Values within about 2% are the same intent.
3. Name them by **role where the usage makes it obvious** (`--surface-card`,
   `--text-muted`), by scale where it does not (`--gray-300`).
4. Say so in `tokens.css` and to them: *"בקובץ אין Variables — בניתי טוקנים מהערכים
   שבפועל, כדאי לאשר את השמות."*

An accident kept as a token is better than a hex in a screen file: it is visible,
named, and one edit fixes every use. But flag the near-duplicates you merged, so
they can tell you if two of them were meant to be different.
