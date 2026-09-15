# The intent gate

**Ask before converting, never in the middle.** A link on its own does not say
whether they want a faithful copy of that one frame or a responsive, stateful
component. Both are legitimate; they are different jobs, and finding out after
the HTML is written means rewriting it.

**Nothing here is ever invented.** If they ask for breakpoints and the design has
no mobile frame, the answer is to ask them for it — not to make one up. Same for
states: no variants in the file means no states in the output until they supply
them. That rule is why the gate exists at all.

## When to skip the gate

Skip it, silently, when:

- **Their message already says.** "as is", "just convert this", "רק להעתיק" →
  AS IS. "with all the breakpoints", "כולל סטייטים" → that. Do not re-ask what
  they already told you.
- **`project.json` already records an intent** for this Figma file. One answer
  covers the whole batch — asking again on screen 7 of 12 is intolerable.
  They can change it any time by saying so; then update the file.

Otherwise ask, once, before step 2 of the pipeline.

## Read the link first

Pull the frame's width from `get_metadata` and name the form factor in the
question, so they are not asked a generic question about a specific thing:

| frame width | call it |
|---|---|
| ≥ 1200 | desktop |
| 700–1199 | tablet |
| < 700 | mobile |

A tablet link changes the wording: the missing widths are desktop *and* mobile,
not "the smaller ones".

## The questions — four, maximum

Ask them as one round, using `AskUserQuestion` for the discrete choices so they
can click rather than type. Only ask what the previous answer makes necessary.

**Ask in the language they opened the conversation in** — see the language rule
in `SKILL.md`. The Hebrew below is an example of a question, not the question.

**1 — always.** What should this become?

| option | meaning |
|---|---|
| **AS IS** (default) | a faithful copy of this one frame at its own width |
| **+ breakpoints** | one file that also matches their other widths |
| **+ states** | hover / selected / disabled from their component variants |
| **both** | both of the above |

If they pick AS IS the gate is over. One question, and the fast path stays fast.

**2 — only if breakpoints.** Name the widths already converted or linked, and
ask for the frames for the others. If they say none exist, say plainly that a
responsive build needs designs to build from, and offer: convert this width
only, or wait until the frames exist. Do not offer to infer them.

**3 — only if states.** Ask **before** going looking — *"Will you send me the
component sets, or should I search for them myself?"* / *"תשלח לי את הקומפוננט
סטים, או שאחפש בעצמי?"* Hunting first is the expensive order — it costs several
tool calls and often dead-ends anyway, because a component set that lives in a
separate library cannot be enumerated through the MCP at all (`states.md`).
Pasting one link takes them seconds.

If they say search, search, then report what you found before asking anything
else. If a component has no variant for a state they want, that is a request for
them, not a gap for you to fill.

**4 — reserve.** One screen-specific ambiguity, if a real one exists. Usually
it does not; do not manufacture one to fill the slot.

## Past four, stop asking

If a fifth question would be needed, the round has failed as a round. Switch
from asking to reporting: give them the current state and let them choose the
next move with the consequences visible.

> **Where this stands:** desktop 1440 converted, 1.8% diff. Mobile 375 is
> waiting on a link. States: I found variants for the main button only — the
> cards have none.
> **Options:** (a) close the desktop and continue when the frames exist,
> (b) convert the button's states now and leave the cards, (c) something else.

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
widths they actually supplied frames for. Nothing goes in these fields on the
strength of an assumption — an empty list means they were asked and had none.

## What each answer commits you to

| answer | what has to be true before you start |
|---|---|
| AS IS | nothing beyond the one link |
| + breakpoints | a Figma frame per width, from them — see `responsive.md` |
| + states | a component set with variants, in their file — see `states.md` |

If a prerequisite is missing when you get there, it is a **blocker** in
`notes.json`, phrased as a request. It is never a licence to design.
