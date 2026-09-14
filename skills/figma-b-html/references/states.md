# States, taken from his variants

Only after the intent gate returned `+ states`. **States are read out of the
Figma file, never invented.** A hover colour you chose because it looked
reasonable is a design decision taken by the wrong person, and it will be
measured against nothing.

## Ask for the links before you go looking

The gate already put this to him (`intent.md`): supply the component sets, or
have you search. Take him up on the first whenever he offers, because the
search has a hard limit —

**A component set that lives in a separate library cannot be read through the
MCP.** `search_design_system` will confirm a component is a `component_set` and
hand back a `componentKey`; `get_libraries` will name the library and give a
`libraryKey`. Neither is a **fileKey**, and `get_metadata` needs one — so the
variant list stays out of reach. Seen for real on a shared design-system
library — the normal case, since that is where production components live.

Nor can the variant list be inferred from `get_design_context`: the union type
it generates (`property1?: "Default" | "active"`) lists only the values used in
that export, not every variant the set defines. A single-value union is not
evidence that only one variant exists.

What breaks the deadlock is one link from him — open the component set in
Figma, *Copy link to selection*. Then everything below works.

## Find what actually exists

In Figma a component's states live as **variants** in a component set —
`state=default | hover | pressed | disabled`, or the designer's own names.

1. `get_metadata` on an instance on the screen gives its component id.
2. `get_metadata` on the component set lists the variant children and their
   property names.
3. `get_screenshot` each variant at its natural size → the reference per state.
4. `get_design_context` on a variant → what actually changes in it.

**Report what you found before asking anything.** "I found variants for the
main button (default / hover / disabled) and none for the cards" is a useful
sentence; "which states do you want?" is not. A component with no variant for
a state he wants is a request to him, recorded as a blocker.

Often only one or two properties change between variants — a fill, a border, an
elevation. Take those; do not restyle the whole component from the variant's
full context.

## Write the state twice

A `:hover` rule never appears in a screenshot, which is why states were
previously unverifiable here. Every state rule is therefore written twice — the
real pseudo-class, and a forced class the board can set:

```css
.btn--primary:hover,
.btn--primary.is-hover { background: var(--main-primary-dark); }

.btn--primary:disabled,
.btn--primary.is-disabled { background: var(--greayscale-gray-2); }
```

Use the real mechanism wherever one exists — `:hover`, `:active`,
`:focus-visible`, `:disabled` on a real `<button>`, `[aria-selected="true"]`
for selection. `.is-*` is only ever the second selector, never the only one.

**Say this in the handoff.** `.is-hover` is an inspection hook so the state can
be photographed; it is not part of the component's API and nothing should ship
markup that sets it.

## The board

Describe the components once in `states.json` at the project root:

```json
{
  "screen": "charging-station",
  "components": [
    {
      "name": "כפתור ראשי",
      "html": "<button class=\"btn btn--primary\" type=\"button\">רכישה</button>",
      "states": ["default", "hover", "disabled"],
      "figma": {"hover": "7518:4412", "disabled": "7518:4413"}
    }
  ]
}
```

`html` is the component's markup exactly as it appears in the screen; `figma`
records which variant each state came from, so a reference can be traced back.

```bash
python3 ~/.claude/skills/figma-b-html/scripts/states_board.py --project <path>
```

That writes two things from one spec:

- **`states.html`** — every component × every state, labelled, using the
  screen's own stylesheet. This is what he and the developer look at.
- **`.fidelity/states/NN-<component>-<state>.html`** — one page holding only
  that component in that state, so it can be captured and scored.

## Measure each state

```bash
python3 $S/capture.py --file "$P/.fidelity/states/01-כפתור-ראשי-hover.html" \
  --width 400 --out /tmp/hover.png
python3 $S/compare.py --reference $P/.fidelity/states/figma-btn-hover.png \
  --render /tmp/hover.png --out /tmp/h
```

The probe page pads the component by 24px, so crop the Figma variant
screenshot to the same padding, or compare the component's own box. A state
with a reference gets a number in `notes.json` like any screen; a state with no
reference says `לא נבדק`.

**But do not read that percentage as the state's fidelity.** The variant in the
library is not the instance on the screen — it carries placeholder content
(`Button name`, a different photo, two chevrons the screen does not use). A
real run scored 6–11% per state on pure content difference while every state
was exactly right. Chasing that number means editing the screen's real content
to match a placeholder.

**The check that decides is the state's own delta:** sample the pixel that the
variant changes — fill, border, text colour, opacity — in the Figma render and
in the probe, and compare the two values. Nine of nine matching is a result;
`6.3%` is not. Report the colour comparison, and give the percentage only with
the reason it is nonzero beside it.

**If every state renders identically on the board, that is the answer, not a
bug in the board** — it means no `.is-*` rules were written. Check that before
reporting the board as done.

## What not to do

- Do not derive a hover from the token palette because the design has none.
- Do not add `:hover` transitions the design does not specify. Motion is a
  design decision; `get_motion_context` exists if the file has any.
- Do not put states on things the design never shows as interactive.
