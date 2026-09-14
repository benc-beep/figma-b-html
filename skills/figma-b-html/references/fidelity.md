# The verification loop

This is the part that replaces the dozen prompts he runs by hand. Without it the
tool is just a nicer way to paste Figma output; with it, the screen is measured
and the number is real.

## The loop

```bash
S=~/.claude/skills/figma-b-html/scripts
P=~/Design/figma-html/<project>

# 1. render the HTML at the frame's exact width and height
python3 $S/capture.py --file $P/screens/<slug>.html \
  --width <frameW> --height <frameH> --out $P/.fidelity/<slug>/render.png

# 2. measure it against the Figma reference
python3 $S/compare.py --reference $P/.fidelity/<slug>/figma.png \
  --render $P/.fidelity/<slug>/render.png --out $P/.fidelity/<slug>
```

Then **read the diff image**, fix, and run both again. Repeat until it passes or
until you hit the stopping rule below.

## It did not match — read `triage.md` first

"It does not match" is four different situations — a browser limitation, a
missing input you should ask him for, a structural mistake of yours, or an
inconsistency in the design itself. They need opposite responses.
**`references/triage.md` is the decision table.** Do not improvise it.

## Reading the output before you start guessing

`compare.py` prints four things, in the order you should act on them:

**1. A vertical offset.** *"HTML content sits about 14px LOWER than Figma"* means
one wrong value near the top pushed everything down. One fix — usually a margin,
a line height, or a missing `margin:0` — collapses most of the diff. **Fix this
before touching anything else.** Chasing individual bands while a global offset
is in play means fixing thirty symptoms of one cause.

**2. A height delta.** The HTML being taller or shorter than the frame is almost
always line height (see `tokens.md`) or a wrapper's padding.

**3. The worst bands.** `y 180-210 → 41%` tells you which strip of the page to
open. Map it to the element by its position in the design.

**4. The shape of the difference** — `CONCENTRATED` or `DIFFUSE`. This matters
more than the percentage, because the percentage cannot tell a broken element
from noise:

- **`CONCENTRATED`** names a box and draws it in yellow on `diff.png`. One solid
  patch is a missing element, an unloaded image, or a wrong fill. Go straight
  there. A screen at 1.2% that is concentrated is *worse* than one at 2% that is
  diffuse.
- **`DIFFUSE`** means it is scattered with no solid patch. Check the font first —
  a substituted font produces exactly this signature across the whole page. Then
  gradients and antialiasing, which are usually not worth chasing.

**5. The number itself.** A stopping condition, not a verdict. Never report it to
him without the shape.

## What the number is blind to

The score is area-weighted, so a small element can be badly wrong and barely
move it. Every icon on a page redrawn at the wrong aspect ratio was worth
**0.019 points** — invisible against a 2.2% total, and obvious the moment anyone
looked at a chevron. A passing score is not evidence that the icons are right.

So two checks stand outside the loop, and both are required before handoff:
run `measure.py --icons` (see `assets.md`), and crop each icon and small control
out of both images at 4-6x and look at them side by side.

Then look at `diff.png` — differences are painted red over a dimmed reference. A
red *outline* around a shape is a 1px border or radius difference. A red *block*
is a wrong colour or a missing element. Red *text* is font, size, weight, spacing
or colour — check in that order.

## Capture rules that decide whether the number means anything

- **DPR 1, always.** `capture.py` pins it. A 2x capture gets rescaled and the
  resampling alone eats part of the budget.
- **Same width as the reference.** If the tool says it rescaled, you captured at
  the wrong width — fix that before believing the score.
- **Scrollbars hidden.** Already handled; a 15px scrollbar shifts an RTL layout
  sideways and reads as a total mismatch.
- **Reference at natural size.** `get_screenshot` defaults to `maxDimension:
  1024`. A downscaled reference makes text edges soft and puts a floor under the
  score you can never get below. See `extraction.md`.

## The stopping rule

**Pass:** `diff_pct ≤ 1.0` and `|height_delta| ≤ 2`. `compare.py` reports this as
`pass: true`.

**Keep going** while each round is still reducing the number meaningfully.

**Stop and report** when either:
- three consecutive rounds move the number by less than 0.2 points, or
- the remaining difference is something a browser cannot do (below).

Stopping is not failure. Stopping *and calling it a pass* is.

> The `notes.json` schema — `blockers` vs `deviations` vs `accepted`, and why
> the distinction matters — is in `triage.md`, with the decision it belongs to.

## The responsive pass — נאמן mode only

Only after the design width passes:

```bash
for w in 375 768; do
  python3 $S/capture.py --file $P/screens/<slug>.html --width $w \
    --out $P/.fidelity/<slug>/w$w.png
done
```

**Chrome will not open a window narrower than 500px.** Ask for 375 and you get
a 375px-wide screenshot of a layout that was laid out at 500 — every mobile
media query below 500 silently skipped, and a picture that looks fine.
`capture.py` and `measure.py` both handle this by rendering inside an iframe of
the exact width, and say so in their output. Never hand-roll a narrow capture.

Then confirm nothing overflows, rather than judging it by eye:

```bash
python3 $S/measure.py --file $P/screens/<slug>.html --width 375 --overflow
```

**If he supplied frames for these widths, this is not the pass to run** — go to
`responsive.md`, where each width is scored against its own reference. What
follows is only for a screen the intent gate settled as AS IS, where the small
widths exist so the page does not break rather than to match a design.

With no reference there is nothing to score, so **look**: horizontal overflow,
text clipped or overlapping, an element pushed off-screen, touch targets under
44px, a grid that has not collapsed. Say plainly in the handoff that these
widths were not designed and were not measured.

A screen that is perfect at 1440 and broken at 375 is not done. If a fix at 375
would cost fidelity at 1440, that is his call — show him both and ask.

## What he sees

Not the diff percentage on its own — it means nothing to him. Send him
`.fidelity/<slug>/side-by-side.png` (Figma | HTML | diff, labelled) and one
Hebrew line per screen.

**Order the batch by what he can act on**, not by screen order:

1. **חוסמים first** — what you need from him, and what it unblocks.
2. Then screens that need a decision from him (category 4, or a fidelity/
   responsive trade-off).
3. Then the ones that are simply done, in one line together.

> `3 מסכים תואמים. במסך התשלום הפונט המקורי לא מותקן — תשלח לי את קובץ הפונט
> ואסגור את זה. במסך הפרופיל הטקסט גולש מהתיבה גם בפיגמה עצמה — לתקן בעיצוב או
> להשאיר?`

For a screen that stopped short, lead with the cause, not the number. A number
without its shape and cause is not a report.
