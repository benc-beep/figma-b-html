# figma-b-html

Turn Figma screens into standalone HTML — then **measure the result against the
Figma render** and iterate until it matches.

No framework, no build step, no repository. The output opens in a browser by
double-clicking it. It is what you hand a developer, and what you keep editing.

Works for any product or client: no brand, font, palette or repo is baked in.
Every value is read out of the Figma file being converted.

## Install

```
/plugin marketplace add benc-beep/figma-b-html
/plugin install figma-b-html@figma-b-html
```

Restart Claude Code. Type `/` and `/convert-to-html` should be there.

## Use

The skill is **command-invoked only**. Pasting a Figma link does nothing on its
own — deliberately, so a link dropped in conversation never starts a long
conversion nobody asked for.

```
convert to HTML   https://www.figma.com/design/…?node-id=1234-5678
```

Also: `המר ל HTML` · `/convert-to-html` · `/המר-ל-html`

Before converting anything it asks **once** what the link is for — a faithful
copy of that frame, or breakpoints and/or component states as well — and
records the answer per Figma file, so it does not ask again on screen 7 of 12.

## What you get

```
~/Design/figma-html/<project>/
  index.html          gallery — every screen with its measured fidelity
  tokens.css          the design system, read from the file's own Variables
  screens/*.html      one file per screen
  states.html         every component in every state (only if you asked)
  .fidelity/          the proof: Figma reference, render, pixel diff, report
  README-dev.md       the handoff note for the developer
```

Nothing is written outside that folder without asking.

## What makes it different

**It reports the number it measured, and says so plainly when it measured
nothing.** Each screen is compared pixel-for-pixel against Figma's own render;
the report says how far off it is, where the difference sits, and why. A gap is
disclosed, never absorbed.

**It never invents.** Ask for breakpoints when the file has no mobile frame and
it asks you for the frame — it will not make one up. Same for states with no
variants. A missing input becomes a blocker phrased as a request.

**It knows the traps, because it hit them.** Figma's padding includes the
stroke. Figma cap-height-trims text boxes, so a layer's box is shorter than the
text it draws — reproduced with `text-box: trim-both cap alphabetic`. Icons
export at the glyph's own size with `preserveAspectRatio="none"`, so sizing the
`<img>` stretches every chevron. Chrome will not open a window narrower than
500px, which silently skips every media query below it.

**Two checks sit outside the score**, because the score is area-weighted and
blind to small things: every icon is verified against its own aspect ratio, and
component states are rendered onto probe pages — so a `:hover` that never
appears in a screenshot can still be compared against its Figma variant.

## Requirements

| | why |
|---|---|
| **Python 3.8+**, Pillow, numpy | `pip install Pillow numpy` |
| **Chrome 133+** | rendering, and `text-box: trim`. On an older Chrome every text block sits a few pixels off. Chromium and Edge work too. |
| **Figma MCP** | Figma desktop → Preferences → Enable local MCP server |

If your browser lives somewhere unusual: `CHROME=/path/to/browser`.

## Notes

- The interface reports in Hebrew.
- macOS, Windows and Linux are all handled; only macOS has been run in anger.

## License

MIT
