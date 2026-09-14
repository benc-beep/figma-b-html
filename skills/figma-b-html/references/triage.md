# When it does not match

Read this the moment a screen fails to reach the bar, before deciding what to do
about it. "It does not match" is four different situations that need opposite
responses, and treating them alike is how a session turns into twenty pointless
rounds.

| | How you recognise it | What you do |
|---|---|---|
| **1. The browser cannot do it** | small, does not improve, on the list below | record in `deviations`, move on |
| **2. Something is missing on this machine** | `DIFFUSE` across all text, or a solid block where an image should be | **`blockers`** — they can fix it in a minute, so ask |
| **3. You have not solved it yet** | the number drops, then plateaus | change tactic, below. Do not repeat the same round |
| **4. The design itself is inconsistent** | one sharp, local difference where the HTML looks *more* correct | **tell them.** Do not reproduce the flaw |

## Category 2 — ask, don't work around

The common ones: a font that is not installed, a Figma permission error, more
than 20 images or 20 SVGs in one node, a component whose source lives in a
library file they have not shared.

Each of these has a one-minute fix on their side and no good workaround on yours.
Substituting a font and tuning the spacing until the score looks acceptable
produces a file that is wrong in a way nobody can see — and it breaks the moment
the real font arrives. Put it in `blockers`, keep converting the other screens,
and tell them what you need at the top of the report.

## Category 4 — the one nobody plans for

Text overflowing its box. A 1px misalignment. Two "identical" cards that differ
by 3px. A text layer clipped in Figma. A spacing value that is 13px where every
sibling is 12px.

The browser lays these out correctly and the comparison calls it a miss. **Do not
reproduce the flaw to win the score** — that puts a bug into the developer's
starting point, and it is the one kind of error that survives all the way to
production looking intentional.

Say what you found, in Hebrew, with the coordinates, and offer both readings:

> `בכרטיס השני הכותרת גולשת מהתיבה — זה קורה גם בפיגמה עצמה, ב-HTML זה נראה נכון.
> לתקן בעיצוב, או שאשחזר את זה כמו שזה?`

They are the designer. A tool that finds problems in their file is doing them a
favour, as long as it says so plainly instead of working around it. Whatever they
answers, record the decision in `deviations` so the developer sees it too.

## What a browser genuinely cannot reproduce

Do not burn rounds on these. Recognise, record, move on:

- **Layer blend modes** beyond what `mix-blend-mode` supports, and blends
  interacting with Figma's own background handling.
- **Inner shadow** — `inset` box-shadow is close but the spread maths differs.
- **Background blur / layer blur** on overlapping content — `backdrop-filter`
  approximates it and differs by browser.
- **Text on a path**, and Figma's per-character overrides.
- **Non-uniform corner smoothing** (Figma's "squircle" corner smoothing has no
  CSS equivalent).
- **Gradient interpolation** — Figma and CSS interpolate differently, so a
  multi-stop gradient will show a faint band in the diff. Below about 0.3% this
  is not worth chasing.
- **Font rendering**, where the real font is unavailable. Say which font is
  missing rather than describing it as an approximation.

## Category 3 — tactics when the loop plateaus

Three rounds moving the number by less than 0.2 points each means the approach is
wrong, not that the effort was insufficient. Change something structural:

- **Isolate.** Crop both images to the worst band and compare only that. The
  whole-page percentage hides which of three changes actually helped.
- **Rebuild, don't patch.** A section that has resisted three rounds is usually
  built on a wrong structural assumption — flex where the design is grid,
  absolute where it should be flow. Rewrite it from the Figma measurements
  instead of nudging values.
- **Re-read the source.** Call `get_design_context` on that one child node.
  Section-level detail often contradicts what you inferred from the parent.
- **Split the mode.** One stubborn section can be absolutely positioned while the
  rest of the screen stays semantic. Note it in the handoff — a developer needs
  to know that one block is a placeholder rather than a pattern.

## `notes.json` — the record of everything the number does not say

One file per screen at `.fidelity/<slug>/notes.json`. The gallery reads it.

```json
{
  "blockers": [
    "פונט המותג לא מותקן — הטקסט מוצג בפונט חלופי. צריך ממך את קובץ הפונט."
  ],
  "deviations": [
    "הצל הפנימי בכרטיס מקורב — CSS לא מייצר inner shadow זהה לפיגמה"
  ],
  "accepted": false,
  "accepted_note": ""
}
```

**`blockers` and `deviations` are not the same thing, and mixing them is the
mistake this field exists to prevent.**

- A **blocker** is something *they* can resolve, usually in a minute: a font file,
  a Figma permission, an asset cap, a decision about an inconsistency in the
  design. It gets a red chip on the card, a red box with the text, and a count
  in the gallery header — *"1 ממתינים לך"*. Phrase it as a request: what you
  need, and what it will fix.
- A **deviation** is permanent and nobody can fix it. Grey text on the card.

Every entry is in Hebrew and says **what** differs. "מינור" and "כמעט זהה" are
not deviations; they are refusals to say anything.

**`accepted`** is their decision, never yours. Set it only when they have looked at a
screen and said it is good enough. The card then shows `אושר · 2.05%` in neutral
blue instead of red — flagged as settled, but **still showing the real number**.
Hiding the measurement once someone approves it is how a folder quietly stops
being trustworthy. `accepted_note` records why, and appears on the card.

Never set `accepted` to make a batch look finished. An unreviewed screen is
`לא נבדק`, and that is a perfectly good thing to report.

> The list of effects a browser genuinely cannot reproduce lives in
> `triage.md`, next to the decision about what to do with them.

## When the diff plateaus, stop looking at pixels and measure

```bash
python3 $S/measure.py --file $P/screens/<slug>.html --width 1440 .card .card__title
```

It prints each selector's real box. Put that next to `get_metadata` on the same
Figma node (`extraction.md`) and the wrong number is obvious — a box that is 92px
where Figma says 90 is a fix, not another guess. **Reach for this the second a
round fails to improve the score.** Diffing pixels tells you where; this tells
you what.

## After triage

Whatever the category, the screen ends in one of three honest states, and every
one of them is an acceptable outcome:

| | |
|---|---|
| passes | `pass: true`, nothing more to say |
| stopped short, cause recorded | `deviations`, and `blockers` if they can help |
| they looked at it and approved | `accepted: true` with their reason, real number still shown |

The unacceptable outcome is a screen reported as matching that was never
measured, or one whose gap was absorbed silently.
