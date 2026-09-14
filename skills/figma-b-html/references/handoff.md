# What the developer receives

The folder is the handoff. No separate document, no Slack thread that gets lost:
a developer who opens `~/Design/figma-html/<project>/` should be able to start
without asking anyone a question.

`new_project.py` writes the skeleton of `README-dev.md`. You add the parts that
only exist after the screens do.

## Add to README-dev.md

### A screen table

| Screen | File | Design width | Fidelity | Notes |
|---|---|---|---|---|
| מסך הבית | `screens/home.html` | 1440 | 0.4% ✓ | הצל הפנימי בכרטיס מקורב |
| תשלום | `screens/checkout.html` | 1440 | 2.1% | הפונט X לא היה מותקן |

Fidelity comes from `.fidelity/<slug>/report.json`. **Copy the measured number.**
A screen with no report says `לא נבדק` — never a guess.

### The design system in one paragraph

Where the tokens came from (Figma Variables, or reconstructed from the values in
use — say which), how many there are, and the naming convention. If you merged
near-duplicate values, list what you merged; that is the one decision a developer
cannot reverse-engineer from the file.

### What is inferred rather than designed

The honest section, and the most useful one:

- states you derived rather than found in Figma (hover, focus, disabled)
- responsive behaviour at 375 and 768 that was not in the design
- content that was invented to fill a slot
- any accessibility fix applied on top of the design, with its reason
- anything the designer should look at again

A developer who knows which decisions were the designer's and which were yours
will ask about the right ones.

### Deviations, collected

Every `deviations` entry across the batch, in one list. They are already on the
gallery cards; repeat them here because the README is what gets read first.

Mark screens the designer **accepted** as accepted, with their reason and the
real number. A developer reading `2.05%, אושר — ההפרש הוא בצל בלבד` knows not
to re-open it.

### Open blockers

If any screen still has `blockers`, the batch is not finished — say so at the top
of the README, not at the bottom:

> **לא סגור:** מסך התשלום ממתין לקובץ הפונט של המותג. עד שהוא יגיע, הטקסט
> באותו מסך מוצג בפונט חלופי ואינו מייצג את העיצוב.

A developer who builds from a screen whose font was substituted will reproduce
the substitution. That one sentence prevents it.

## What the folder must not contain

- No `node_modules`, no build config, no framework. If it needs a build step to
  open, it is not this deliverable.
- No screen that was never rendered. An HTML file nobody captured has not been
  proven to open at all.
- No `.fidelity/` entry for a screen that no longer exists. Deleting a screen
  means deleting its folder and re-running `build_index.py`.

## Sending one screen on its own

The folder is the handoff, but "send me the link" and "email this to a developer"
both want one file. `bundle.py` inlines the stylesheets, fonts and images as
data URIs and writes a single self-contained HTML:

```bash
python3 ~/.claude/skills/figma-b-html/scripts/bundle.py \
  <project>/screens/<slug>.html <project>/<slug>-standalone.html
```

**Capture and compare the bundled file before sending it.** It should score
0.000% against the folder version — anything else means an asset did not inline.
The script also prints anything it could not resolve; that list must be empty.

Add `--fragment` for an Artifact publish: it strips the document wrapper the
host supplies and carries the document's own `direction` on the body instead.

**A page of photographs will not fit as-is.** Figma hands back source images far
larger than the box they render in — a card photo shown at 392x212 can arrive at
1568x1176 — so one real page bundled to **36MB**, well past the 16MB an Artifact
accepts. `--max-image 1600 --quality 92` brought the same page to 7.5MB and cost
0.19% against the folder version. Measure that cost, don't assume it: compare the
bundled file to the folder render and report the number if it is not zero.

## Handing it over

Rebuild the gallery last — it reads the reports, so it must run after the final
comparison:

```bash
python3 ~/.claude/skills/figma-b-html/scripts/build_index.py --project <path>
```

Then give him the command, not a screenshot:

```bash
open -a "Google Chrome" ~/Design/figma-html/<project>/index.html
```

**His real Chrome, specifically.** His live design-editing extension only exists
there, and the agent preview pane renders local files as a static snapshot: the
gallery's iframes do not load and its script does not run, so the page looks
broken when it is not. That snapshot behaviour has already caused one false bug
report — do not repeat it.

## The summary he reads

Hebrew, one line per screen, deviations before numbers:

> `4 מסכים הומרו. שלושה תואמים מתחת ל-1%. במסך התשלום הפונט המקורי לא מותקן ולכן
> הטקסט מוצג בפונט חלופי — צריך ממני את קובץ הפונט כדי לסגור את זה.`

Then the `open` command. Then `סיימתי אחי`.

## The review gate — after every delivery

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
