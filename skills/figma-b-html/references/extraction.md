# Getting the design out of Figma

Five tools, and the order matters. Calling them in the wrong order costs
round-trips and, on a big file, rate limits.

## Parsing the link

```
https://figma.com/design/<fileKey>/<AnyName>?node-id=12-345
                         ^fileKey                    ^ nodeId, as 12:345
```

- Dashes become colons: `12-345` → `12:345`.
- Branch links — `…/design/<fileKey>/branch/<branchKey>/<name>` — use the
  **branchKey** as the fileKey.
- `/board/` is FigJam and `/slides/` is Slides. Neither is convertible here;
  say so rather than trying.
- No `node-id` at all → do not guess one. Call `get_metadata` with just the
  `fileKey`; it returns the top-level pages, and they pick.

## The order

### 1. `get_metadata` — the inventory

Node IDs, layer names, types, positions, sizes. Nothing else, which is exactly
what you want for choosing what to convert. Cheap relative to everything below.

Use it on the page node to list frames. **Record each frame's width and height
from here** — the fidelity loop needs both, and re-reading them later means
another call.

### 2. `get_variable_defs` — the design system

Once per file, on a frame that uses the system broadly (a full screen, not an
icon). Returns a name → value map. → `tokens.md`

### 3. `get_screenshot` — the reference image

**This is the ground truth every later number is measured against, so get it right:**

- `maxDimension` defaults to **1024** and silently scales the render down. Pass
  the frame's longer edge instead. A 1440×3200 frame needs `maxDimension: 3200`.
- The response reports `width`/`height` (what you got) alongside
  `original_width`/`original_height` (the node's true size). **Compare them.** If
  they differ, you are holding a scaled image — re-request before comparing
  anything against it.
- It returns a short-lived URL plus a curl line by default. Use that; it costs a
  fraction of the tokens of an inline image. Download to
  `.fidelity/<slug>/figma.png` immediately — the URL expires.
- `enableBase64Response` exists for sandboxes with no shell. You have a shell.

### 4. `get_design_context` — the structure

**Load the `figma-design-to-code` skill before the first call.** The tool states
this as a hard prerequisite and it is not decorative — without it you get code
that ignores the design system you just extracted. Pass
`skillNames: "figma-design-to-code"` and `clientLanguages: "html,css"`,
`clientFrameworks: "none"`.

What comes back is **reference code, not the answer.** It is generated for a
generic React-ish target. Read it for structure, measurements, colours and text;
then write your own HTML against the conventions in `html-conventions.md`.
Pasting it through unedited produces div soup with inline hex values — the exact
thing this tool exists to stop.

`excludeScreenshot: true` is worth passing here, since step 3 already got a
better one at full resolution.

On a large node the tool may return metadata instead of code because the output
is too big. That is a signal to convert the frame's **sections** one at a time
and assemble, not to pass `forceCode` and hope.

### 5. `download_assets` — the pictures

→ `assets.md`. Note the caps: **20 raw images and 20 SVGs per call**. A screen
that exceeds either needs to be pulled per section. The URLs are temporary;
download in the same turn.

## `get_metadata` on a node is the argument-ender

When the render disagrees with the reference and you cannot see why, call
`get_metadata` on **that node**, not on the page. It returns every descendant's
exact x / y / width / height. Read it next to `measure.py`'s output for the same
selectors and the wrong number names itself.

Do this the moment you are about to guess a value from the reference code.
Deriving heights from `get_design_context`'s Tailwind is guesswork; the metadata
is the measurement.

## Hebrew and Arabic can come back reversed

`get_design_context` sometimes returns an RTL string in **visual** order — the
characters reversed. On the first real conversion `עקבו אחרינו` arrived as
`ונירחא ובקע`, which reads exactly like a designer having pasted text backwards.

**It was not.** The Figma render showed it correctly; only the tool's
serialization was reversed. Crop that area out of the reference screenshot and
look before reporting a reversed string as a design bug — a false bug report
costs more than the check.

## Rate limits

A big batch will hit them. When it happens: stop, tell them in one Hebrew
sentence how many screens are done and how many remain, and offer to continue
later. Do not retry in a tight loop — that extends the block.

`whoami` reports the account and its plans; use it when a file that should be
reachable returns a permission error, before assuming the link is wrong.

## When the frame is not a frame

Components and instances convert fine. A **group** often has no clear bounds and
produces a screenshot with unexpected padding. If the reference image looks
padded, check the node type in `get_metadata` — and prefer converting the
enclosing frame.
