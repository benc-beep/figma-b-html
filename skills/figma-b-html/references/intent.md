# The intent gate

**Ask before converting, never in the middle.** A link on its own does not say
whether he wants a faithful copy of that one frame or a responsive, stateful
component. Both are legitimate; they are different jobs, and finding out after
the HTML is written means rewriting it.

**Nothing here is ever invented.** If he asks for breakpoints and the design has
no mobile frame, the answer is to ask him for it — not to make one up. Same for
states: no variants in the file means no states in the output until he supplies
them. That rule is why the gate exists at all.

## When to skip the gate

Skip it, silently, when:

- **His message already says.** "as is", "just convert this", "רק להעתיק" →
  AS IS. "with all the breakpoints", "כולל סטייטים" → that. Do not re-ask what
  he already told you.
- **`project.json` already records an intent** for this Figma file. One answer
  covers the whole batch — asking again on screen 7 of 12 is intolerable.
  He can change it any time by saying so; then update the file.

Otherwise ask, once, before step 2 of the pipeline.

## Read the link first

Pull the frame's width from `get_metadata` and name the form factor in the
question, so he is not asked a generic question about a specific thing:

| frame width | call it |
|---|---|
| ≥ 1200 | desktop |
| 700–1199 | tablet |
| < 700 | mobile |

A tablet link changes the wording: the missing widths are desktop *and* mobile,
not "the smaller ones".

## The questions — four, maximum

Ask them as one round, in Hebrew, using `AskUserQuestion` for the discrete
choices so he can click rather than type. Only ask what the previous answer
makes necessary.

**1 — always.** What should this become?

| option | meaning |
|---|---|
| **AS IS** (default) | a faithful copy of this one frame at its own width |
| **+ breakpoints** | one file that also matches his other widths |
| **+ states** | hover / selected / disabled from his component variants |
| **both** | both of the above |

If he picks AS IS the gate is over. One question, and the fast path stays fast.

**2 — only if breakpoints.** Name the widths already converted or linked, and
ask for the frames for the others. If he says none exist, say plainly that a
responsive build needs designs to build from, and offer: convert this width
only, or wait until the frames exist. Do not offer to infer them.

**3 — only if states.** Ask **before** going looking: *"תשלח לי את הקומפוננט
סטים, או שאחפש בעצמי?"* Hunting first is the expensive order — it costs several
tool calls and often dead-ends anyway, because a component set that lives in a
separate library cannot be enumerated through the MCP at all (`states.md`).
Pasting one link takes him seconds.

If he says search, search, then report what you found before asking anything
else. If a component has no variant for a state he wants, that is a request for
him, not a gap for you to fill.

**4 — reserve.** One screen-specific ambiguity, if a real one exists. Usually
it does not; do not manufacture one to fill the slot.

## Past four, stop asking

If a fifth question would be needed, the round has failed as a round. Switch
from asking to reporting: give him the current state and let him choose the
next move with the consequences visible.

> **איפה זה עומד:** דסקטופ 1440 הומר, 1.8% הפרש. מובייל 375 ממתין לקישור.
> סטייטים: מצאתי variants לכפתור הראשי בלבד — לכרטיסים אין.
> **אפשרויות:** (א) לסגור את הדסקטופ ולהמשיך כשיהיו מסגרות, (ב) להמיר גם את
> הסטייטים של הכפתור עכשיו ולהשאיר את הכרטיסים, (ג) משהו אחר.

Three things make that report work: what is **done** with its number, what is
**blocked** and on what, and **concrete options** rather than an open question.
Never present an option that requires inventing design.

## Record the answer

Write it into `project.json` so the rest of the batch inherits it:

```json
"intent": {
  "mode": "as-is",
  "breakpoints": [],
  "states": false,
  "asked": "2026-09-10"
}
```

`mode` is `as-is`, `responsive`, `states` or `full`. `breakpoints` lists the
widths he actually supplied frames for. Nothing goes in these fields on the
strength of an assumption — an empty list means he was asked and had none.

## What each answer commits you to

| answer | what has to be true before you start |
|---|---|
| AS IS | nothing beyond the one link |
| + breakpoints | a Figma frame per width, from him — see `responsive.md` |
| + states | a component set with variants, in his file — see `states.md` |

If a prerequisite is missing when you get there, it is a **blocker** in
`notes.json`, phrased as a request. It is never a licence to design.
