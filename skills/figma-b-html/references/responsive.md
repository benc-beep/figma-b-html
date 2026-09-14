# Breakpoints, built from his designs

Only after the intent gate returned `+ breakpoints` and he has supplied a frame
per width. **A width with no Figma frame does not get built.** Inventing a
mobile layout and calling the screen responsive is the failure this whole path
exists to prevent — the number would look fine because there would be nothing
to measure it against.

## One file, not three

He gets **one** `screens/<slug>.html` with media queries, not a screen per
width. That is the deliverable a developer can use; three separate files leave
them to work out which is authoritative.

The breakpoints come from **his frame widths**, never from a convention. If his
frames are 1440 / 834 / 390, the queries are written against 834 and 390 — not
768 and 375 because those are the usual numbers.

Build the largest width first and completely, then add each smaller width
underneath as a `max-width` block. Written that way, the desktop rendering
cannot be disturbed by a later query — which matters, because it is the one you
have already got to a number.

```css
/* the design width, untouched by anything below */
.card { width: 286px; }

@media (max-width: 833px)  { /* his tablet frame */ }
@media (max-width: 389px)  { /* his mobile frame */ }
```

## Per-width references

Each width is captured, stored and scored on its own:

```
.fidelity/<slug>/
  figma-1440.png   render-1440.png   report-1440.json
  figma-834.png    render-834.png    report-834.json
  figma-390.png    render-390.png    report-390.json
```

Get each reference the same way as the first — `get_screenshot` at the frame's
natural size, checking `original_width`/`original_height` (`extraction.md`).

```bash
for w in 1440 834 390; do
  python3 $S/capture.py --file $P/screens/<slug>.html --width $w \
    --height <that frame's height> --out $P/.fidelity/<slug>/render-$w.png
  python3 $S/compare.py --reference $P/.fidelity/<slug>/figma-$w.png \
    --render $P/.fidelity/<slug>/render-$w.png --out /tmp/w$w
done
```

`capture.py` already renders widths under 500px inside an exact-width iframe,
so a 390 capture is a real 390 layout and not Chrome's 500px minimum.

Copy each width's `report.json` to `report-<width>.json`; the plain
`report.json` stays the design width, which is what the gallery badge reads.

## The order that converges

1. Get the design width to its number first. Do not start the smaller widths
   until it is done — every later query is measured against a moving target
   otherwise.
2. Add the next width down. Run its comparison. Then re-run the **design
   width** to prove the query did not leak upward. That check is cheap and it
   catches the most common mistake in this path.
3. Repeat downward.

## What differs between widths is design, not guesswork

Read each frame's own structure. Figma's mobile frame will have its own column
count, its own type sizes, its own nav. Take those from the frame, the same way
you took the desktop ones — `get_design_context` per width, not "shrink the
desktop and hope".

Where his frames genuinely leave a width undefined — a component that appears
at 1440 and 390 but not in the 834 frame — that is a question for him, recorded
as a blocker. It is not a gap to fill.

## Reporting

`notes.json` carries a line per width, and the report to him names each:

> `דסקטופ 1440 — 1.4%. טאבלט 834 — 2.1%. מובייל 390 — 1.9%. שלושתם מול המסגרות
> שלך, לא מול הסקה.`

That last clause is the point of this whole file. Say it, because the previous
behaviour was the opposite and he needs to know which he is getting.
