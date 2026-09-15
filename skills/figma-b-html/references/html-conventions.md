# How the HTML is written

One file per screen in `screens/`, standalone, opens by double-clicking.

## The skeleton

```html
<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>מסך הבית</title>

<!-- read by build_index.py; keep all four -->
<meta name="design-width" content="1440">
<meta name="figma:node" content="12:345">
<meta name="figma:url" content="https://figma.com/design/…?node-id=12-345">
<meta name="conversion-mode" content="נאמן">

<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="../base.css">
<style>
  /* this screen only */
</style>
</head>
<body>
…
</body>
</html>
```

`lang` and `dir` follow the content. The four `meta` tags are how the gallery
knows the screen's width, mode and origin — drop them and the card comes out
blank and the thumbnail wrongly scaled.

Screen CSS goes in one inline `<style>`, not a separate file. It keeps the screen
readable as a single unit, and a developer opening one file sees everything that
governs it.

## The two modes

### נאמן / faithful — the default

Real tags, real layout, holds up when the content changes.

- `header` `nav` `main` `section` `footer`, `button` for actions, `a` for
  navigation, `ul`/`li` for repeated items, `h1`–`h3` in order.
- Flex and grid. **No `position: absolute` for layout** — only for genuine
  overlays: badges on avatars, a close button in a corner, a dropdown.
- Repeated Figma layers become repeated markup with one shared class, not five
  copies of the same inline style.
- Fixed heights only where the design genuinely fixes them. A fixed height on a
  text container breaks the moment the text is real.
- Class names from the design's own vocabulary — `.product-card`, `.price-row`.
  Not `.frame-427`.

### מדויק / exact — on request

`position: absolute` from the Figma coordinates, inside a
`position: relative; width: <frameW>px` container. Faster and exact. Say once, in
the handoff, that it is a presentation artifact and not a development starting
point.

Even here: no raw hex values. Tokens cost nothing and keep the file editable.

## RTL

The direction comes from the content, and getting it wrong is the most visible
possible error.

- `dir="rtl"` on `<html>`, not on a wrapper.
- **Logical properties throughout**: `margin-inline-start`, `padding-inline-end`,
  `inset-inline-start`, `border-start-start-radius`. They flip automatically;
  `margin-left` does not.
- Flex `row` already reverses under RTL. Do not add `row-reverse` to "fix" it —
  that double-flips it back and breaks responsiveness.
- Numbers, prices, phone numbers, times and code are **LTR runs inside RTL
  text**. `1,299 ₪` renders wrong without help. Wrap them:
  `<span dir="ltr">+972-3-1234567</span>`. A subtree carrying its own `dir`
  keeps its internal order and ignores the outer context.
- Icons that indicate direction — arrows, chevrons, back — mirror. Icons that
  represent objects — a clock, a logo, a person — do not.
- `text-align: start`, never `left`.

Check RTL against the reference image specifically. A layout that is mirrored
where it should not be still scores well on colour and badly on everything else,
and the diff bands will look like noise.

### Child order — decide it per row, never by rule

In an RTL document `flex-direction: row` puts the **first DOM child on the
right**. Figma's export usually lists children in visual left-to-right order, so
copying that order straight into HTML usually mirrors the row.

**Usually is not always, and assuming it is costs a round.** One real file mixed
both inside a single screen: the card's spec-chip row was authored RTL, while
the button row, the stepper and the back control were authored LTR. Nothing in
the export tells you which one you are holding.

So decide **per row, against the reference render**. Crop the row out of the
Figma screenshot and ask: which element is physically rightmost? That element is
the first DOM child. Then ask the same question about the next row — the answer
does not carry over, not even within one component.

## Two traps that decide whether this converges

Learned on the first real page; each was worth several rounds of the loop.
The third, RTL child order, is above under **RTL**.

**1. Figma's padding includes the stroke.** A 25px inset on a bordered frame is
`border:1px` **plus `padding:24px`** — not `padding:25px`. Get it wrong and every
card is 2px too tall, and in a column that error compounds downward.

**2. Text boxes are cap-height trimmed.** Figma measures many text layers from
cap-height to baseline and lays out the siblings below against that smaller box,
so a layer's box is routinely shorter than the text it draws. Figma's own export
marks these `[text-box-trim:trim-both] [text-box-edge:cap_alphabetic]`. CSS has
the same primitive — `text-box: trim-both cap alphabetic` (Chrome 133+):

```css
.trim { text-box: trim-both cap alphabetic; }
```

Apply it **only** where the export marked the layer trimmed. Without it, every
such text node is 8-16px too tall. Where the design also fixes a height, the copy
genuinely overflows its box: that is the design, so reproduce it — and say so in
the handoff, because it means the layout has no slack if the copy grows.

## Matching Figma's box model

Where the remaining pixel differences come from, in the order they usually bite:

1. **Line height.** Figma sets it explicitly; the browser default does not match.
   Set it on every text element.
2. **Auto-layout is flex.** Figma's spacing between items → `gap`. Its padding →
   `padding`. Do not reproduce Figma's gaps with margins; the numbers drift.
3. **Figma strokes sit centred by default**, CSS borders sit inside the box. A
   1px border shifts content by 1px. Use `box-shadow: inset 0 0 0 1px` when the
   Figma stroke is inside, or `outline` when it is outside.
4. **Letter spacing** in Figma is often a percentage; CSS wants `em`.
   `-2%` → `-0.02em`.
5. **`box-sizing: border-box`** — already in `base.css`, and Figma's frames
   behave the same way.
6. **Text vertical alignment.** A Figma text layer with a fixed height centres
   its text; a `div` does not. Use flex centring, not padding guessed to match.

## Fonts — mandatory gate before writing any HTML

**Never ship a screen that silently falls back to a system font.** A missing
font is the single most visible gap between the HTML and the Figma render, and
it compounds across every text element on the page.

After `get_design_context` identifies the font family:

1. **If the font is on Google Fonts** — link it directly in `<head>`.
2. **If the font is proprietary or licensed** — ask before writing the HTML,
   naming the font the file actually uses:
   > *"`<font>` is not on Google Fonts. Do you have the font files? Send them
   > and I will embed them as `@font-face` — or share an HTML file that already
   > carries them. Without it the browser substitutes a system font and you will
   > see a large gap."* (in their language; this is the shape, not the string)
3. **If they do not have it** — say so in the handoff, warn at the top of the
   file, and record a **blocker** in `notes.json`:
   ```html
   <!-- ⚠️ <font> not embedded — the browser will substitute a system font -->
   ```

**Do not start writing until the font question has an answer.**

## States

The design usually shows one state. A developer needs the rest, and it is far
cheaper to add them now:

- `:hover` and `:active` on anything clickable
- `:focus-visible` — already in `base.css`, do not remove it
- `:disabled` where the design implies it
- the longest realistic string in every text slot

**Where the states come from decides everything.** If the intent gate returned
`+ states`, they are read out of their component variants and measured —
`states.md`. If it returned AS IS, the only states in the output are the ones
above that cost nothing and break nothing (`:focus-visible`, a cursor), and the
handoff says the rest were not designed. Never derive a hover colour from the
palette and ship it as though the designer chose it.

## Accessibility, the parts that are not optional

These are cheap here and expensive later:

- `alt` on every meaningful image, `alt=""` on decoration
- a real `<button>`, never a clickable `div`
- form inputs with a `<label>`, even a visually hidden one
- computed contrast on text — if a design value fails 4.5:1, **say it once with
  the number** and let them decide. Do not silently correct the design.
