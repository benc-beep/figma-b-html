---
name: figma-b-html
description: >-
  Convert Figma screens into standalone HTML that a developer can build from and
  a client can be shown, measured pixel-for-pixel against the Figma render. This
  skill is COMMAND-INVOKED ONLY. Use it when, and only when, the user writes one
  of these exact commands: "convert to HTML", "המר ל HTML", "המר ל-HTML", or the
  slash command /convert-to-html. The command may carry a Figma link, several
  links, or none. Do NOT use this skill for a figma.com link on its own, for
  "implement this design from Figma", for "build this screen", for "turn this
  into code", or for any other phrasing however close in meaning — a link
  without the command is not a request to convert, and guessing wrong starts a
  long expensive job the user did not ask for. If a Figma link arrives with no
  command, do the ordinary thing the message asks for and leave this skill
  alone. Also do NOT use it for implementing a design inside an existing
  application codebase; that is design-to-code in the repo, not this.
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

After the Chrome command, ask these three questions with `AskUserQuestion`
(multiSelect: false on each, one round):

1. **התוצאה טובה?** — כן, נראה מדויק / לא, יש פערים
2. **דורש סיבוב נוסף?** — כן, תתקן / לא, מספיק טוב לעכשיו
3. **תרצה שאעבור סקשן סקשן ותאשר כל אחד בנפרד?** — כן / לא

If answer 1 = "לא" or answer 2 = "כן" → ask him to describe the gaps, then
fix and re-deliver. If answer 3 = "כן" → walk through each section sequentially.
For each section, ask him to supply **two things before comparing**:
- צילום מסך של הסקשן מה-HTML (Cmd+Shift+4 על הסקשן)
- קישור Figma MCP לנוד של אותו סקשן (לחיצה ימנית על הפריים בפיגמה → Copy link to selection)

Only after receiving both, call `get_design_context` on the node and list the
gaps as bullets. Do not skip the gate even if the result looks good to you.

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
