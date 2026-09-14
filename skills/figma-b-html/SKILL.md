---
name: figma-b-html
description: >-
  Convert Figma screens into standalone HTML that a developer can build from and
  a client can be shown, measured pixel-for-pixel against the Figma render.
  There are exactly two ways in. FIRST, the explicit command: "convert to HTML",
  "המר ל HTML", "המר ל-HTML", /convert-to-html, /המר-ל-html — with a Figma link,
  several links, or none. SECOND, a demand that HTML match a design exactly:
  "אחד לאחד כמו בפיגמה", "בדיוק כמו בפיגמה", "זהה לפיגמה", "מדויק לפיקסל",
  "pixel perfect", "1:1 with the design", "it has to look exactly like the
  Figma", "identical to the design" — any phrasing whose point is that the HTML
  must be indistinguishable from the Figma frame. That demand IS this skill's
  whole subject, so honour it whether it arrives alone, alongside a link, or as
  a correction to HTML already on the table. Everything else stays out. A
  figma.com link on its own is not a request to convert; neither is "implement
  this design from Figma", "build this screen", or "turn this into code" —
  answer those as asked and leave this skill alone, because guessing wrong
  starts a long expensive job nobody ordered. The one case that looks like entry
  and is not: pixel-exactness demanded for a screen inside an existing
  application codebase, where the output belongs in the repo's own components.
  That is design-to-code in the repo, not this.
---

# Figma → HTML

Turn Figma screens into static HTML files that stand on their own: no framework,
no build step, no repository. The output opens in a browser by double-clicking it.

**Who this is for.** A designer, who may not read code — report in the language
they wrote to you in, as a picture, a table, or one sentence. Never as a diff.
The HTML is for the developers they hand it to.

**Product-agnostic.** No brand, font or repo is baked in; every value comes
from the file being converted.

## Standing rules

1. **Nothing is written outside `~/Design/figma-html/<project>/` without
   asking.** Fill that folder freely once he has named it; a repo, his Desktop
   or a project you did not create this session needs a yes first.
2. **Never report fidelity you did not measure.** "נראה זהה" is not a result.
   The result is the number `compare.py` printed. If a screen was not compared,
   say `לא נבדק` in those words.
3. **A gap is disclosed, never absorbed.** Reporting a pass over a quiet
   approximation is the one unrecoverable failure here. Sort every gap in
   `notes.json`: a **blocker** he can fix, a permanent **deviation**, or a flaw
   in the design. `triage.md` decides which.
4. **Report blockers before numbers**, in Hebrew, one line per screen.
5. **End every completed task with `סיימתי אחי`.**

## The two modes

He decides per batch; when he does not say, use **נאמן**.

| | **נאמן** — default | **מדויק** |
|---|---|---|
| For | handing to developers | showing a client, nothing built behind it |
| Layout | flex / grid, real tags (`header`, `nav`, `button`, `ul`) | absolute positioning |
| Fidelity bar | **the same bar** — must match the Figma render at the design width | must match |

The bar does not soften in נאמן mode. If a layout genuinely cannot be both
semantic and exact, say so and let him choose — do not silently pick.

## The pipeline

### 1 — Orient

`figma.com/design/<fileKey>/<name>?node-id=1-2` → `fileKey`, `nodeId` = `1:2`.
No `node-id` → `get_metadata` on the `fileKey` alone lists the pages; show them
in Hebrew and let him pick. Then `get_metadata` on the page for the frame
inventory, shown as a Hebrew table. **Do not convert a whole page because he
pasted a page link** — twenty screens is an hour of tool calls.

Direction comes from the content, never an assumption: Hebrew or Arabic glyphs
→ `rtl`. Record it; it drives the whole layout.

### 2 — The intent gate

A link does not say whether he wants this frame copied faithfully or a
responsive, stateful component. **Ask once, before any conversion; never invent
what the answer needs.** `references/intent.md` has the question round, the
four-question cap, and where the answer is recorded.

### 3 — Create the project

```bash
python3 ~/.claude/skills/figma-b-html/scripts/new_project.py \
  --name "<his name for it>" --dir <rtl|ltr> --figma-url "<the link>"
```

It refuses to overwrite an existing project. If it refuses, **ask him** — that
folder holds work he may still need.

### 4 — Tokens, once per file

`get_variable_defs` on a representative frame, then write `tokens.css` —
details and the no-Variables fallback in `references/tokens.md`. Do this
**before** the first screen, or it gets hardcoded values nobody revisits.

### 5 — Per screen

Detail in `extraction.md`, `html-conventions.md`, `assets.md`. The shape:

1. `get_screenshot` with `maxDimension` = the frame's larger edge, or the
   reference is scaled down and every comparison is measured against a blur.
   Save to `.fidelity/<slug>/figma.png`.
2. Load the `figma-design-to-code` skill, then `get_design_context`. That skill
   is a **mandatory prerequisite** of the tool, not a suggestion.
3. **Font gate** — before writing any HTML, resolve the font (`html-conventions.md § Fonts`). If the font is proprietary, ask him for the files or a source HTML that already has them. Do not proceed without an answer.
4. `download_assets` → `assets/`. Icons as inline SVG, photos as files.
5. Write `screens/<slug>.html`.
6. **Verify** — `references/fidelity.md`; if it does not match, `triage.md`.
   Icons need a check of their own (`measure.py --icons`) — the score is
   area-weighted and cannot see a distorted one.
7. Breakpoints and states only if the gate asked for them: `responsive.md`,
   `states.md`. Otherwise confirm 375/768 merely do not break.

### 6 — Close the batch

```bash
python3 ~/.claude/skills/figma-b-html/scripts/build_index.py --project <path>
```

Write `README-dev.md`'s per-screen section (`references/handoff.md`), then:

```bash
open -a "Google Chrome" ~/Design/figma-html/<project>/index.html
```

**Give him that command, not a preview-pane screenshot** — his live editor
exists only in his real Chrome, and the pane renders local files as a static
snapshot where iframes and scripts do not run.

### 7 — Review gate (mandatory after every delivery)

Never close a batch on your own judgement that it looks right. Run the
three-question review round in `references/handoff.md`, and do not skip it
because the result looks good to you.

## The scripts

| | |
|---|---|
| `scripts/new_project.py` | scaffolds the project folder; refuses to clobber |
| `scripts/capture.py` | headless-Chrome screenshot at an exact width, 1:1 pixels |
| `scripts/compare.py` | reference vs render → diff %, heatmap, where it differs |
| `scripts/measure.py` | the real box of any selector, and what overflows a width |
| `scripts/build_index.py` | rebuilds the gallery from `screens/` |
| `scripts/states_board.py` | a board of every state, plus a probe page per state |
| `scripts/bundle.py` | folds one screen + its assets into a single sendable file |

Run `--help` on any. Three things they know so you need not: Chrome writes the
PNG then never exits; it will not open a window under 500px (narrow widths
render in an iframe); an absolute iframe in an RTL document anchors wrong.

## Files

| | |
|---|---|
| `references/intent.md` | **the gate** — what he actually wants, asked once |
| `references/extraction.md` | which Figma tool, in which order, and their limits |
| `references/tokens.md` | Variables → `tokens.css`; what to do when there are none |
| `references/fidelity.md` | the verification loop, the stopping rule, its blind spots |
| `references/triage.md` | **when it does not match** — the four causes and what to do |
| `references/html-conventions.md` | the two modes, RTL, fonts, semantics, responsive |
| `references/responsive.md` | breakpoints built from his frames, scored per width |
| `references/states.md` | states read from his variants, and how to measure one |
| `references/assets.md` | images and icons |
| `references/handoff.md` | what the developer receives |

## Maintenance

Budgets: this file ≤160 lines, each reference ≤200. At a cap, delete or split —
never raise the cap. When a conversion costs real time over something not
written here, add it to a reference; a trap that fires twice belongs above.
