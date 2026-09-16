#!/usr/bin/env python3
"""Render every component state so it can be looked at — and measured.

    python3 states_board.py --project ~/Design/figma-html/acme --screen home

Reads `states.json` from the project and writes two things:

  states.html                        one board, every component x every state,
                                     labelled — this is what the developer and
                                     the designer look at
  .fidelity/states/<comp>-<state>.html
                                     one tiny page per state, holding only that
                                     component, so capture.py can shoot it and
                                     compare.py can score it against the Figma
                                     variant screenshot

A `:hover` rule never appears in a screenshot, which is why states used to be
unverifiable here. The convention that fixes it: every state rule is written
twice, once as the real pseudo-class and once as a forced class —

    .btn:hover, .btn.is-hover { ... }

The page ships the real behaviour; the board sets `.is-hover` so the state can
be rendered at rest. Say so in the handoff: `.is-*` is a inspection hook, not
part of the component's API.

states.json:

    {
      "screen": "home",
      "components": [
        {
          "name": "Main button",
          "html": "<button class=\\"btn\\">Book now</button>",
          "states": ["default", "hover", "disabled"],
          "figma": {"hover": "3:41", "disabled": "3:42"}
        }
      ]
    }

`html` is the component's markup exactly as it appears in the screen. `figma`
is optional and records which variant node each state came from, so the
reference images can be traced back.
"""

import argparse
import html
import json
import os
import re
import sys

# The probe must land at a known origin so the crop is deterministic. An
# inline-block in an RTL document sits at the RIGHT edge, which silently makes
# every state measurement compare the wrong pixels — and only in RTL, so it
# passes unnoticed on an LTR project. Pin it to the top-left; the component
# inside still inherits the document's own direction.
CELL_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; }
.probe { position: absolute; top: 0; left: 0; padding: 24px; }
"""

# Every user-facing string in one place, matching build_index.py. The board
# speaks one language at a time; swapping this dict translates it.
T = {
    "suffix": "סטייטים",
    "lede": "כל רכיב במסך, בכל אחד מהמצבים שלו — כפי שהם מוגדרים בקומפוננט סטס "
            "בפיגמה. שום מצב כאן לא הומצא.",
    "live": "אפשר לרחף עם העכבר על הרכיבים — הכללים כאן אמיתיים, לא צילום.",
    "hook": "בקוד עצמו הסטייטים הם <code>:hover</code>, <code>:disabled</code> "
            "ודומיהם. המחלקות <code>is-*</code> קיימות רק כדי לצלם מצב שאי אפשר "
            "לראות במנוחה — הן לא חלק מה-API ואין לשלוח אותן לפרודקשן.",
    "back": "חזרה לגלריה",
    "variant": "וריאנט",
    "default_label": "ברירת מחדל",
}

BOARD_CSS = """
:root{
  --bg:#F4F5F7; --card:#FFFFFF; --line:#E3E5E9; --line-2:#CFD3DA;
  --ink:#16181D; --ink-2:#5A616E; --ink-3:#8B93A1;
  --accent:#1F4E79; --accent-bg:#E8F0F8; --hover:#F2F4F7;
  --shadow:0 1px 2px rgba(16,20,28,.05), 0 4px 12px rgba(16,20,28,.05);
}
@media (prefers-color-scheme:dark){
  :root{ --bg:#15171B; --card:#1E2126; --line:#2E333A; --line-2:#3C434C;
         --ink:#ECEEF1; --ink-2:#A7AEBA; --ink-3:#79818E;
         --accent:#8FC0EC; --accent-bg:#17273A; --hover:#262A30;
         --shadow:0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(0,0,0,.25); }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  -webkit-font-smoothing:antialiased}

.sb-head{padding:26px 32px 20px;background:var(--card);
  border-bottom:1px solid var(--line)}
.sb-title{margin:0 0 6px;font-size:22px;font-weight:680;letter-spacing:-.01em}
.sb-lede{margin:0;max-width:74ch;color:var(--ink-2);font-size:13.5px}
.sb-live{margin:12px 0 0;display:inline-flex;align-items:center;gap:7px;
  padding:6px 11px;border-radius:999px;background:var(--accent-bg);
  color:var(--accent);font-size:12.5px;font-weight:600}
.sb-live::before{content:"";width:7px;height:7px;border-radius:50%;
  background:currentColor;flex:none}
/* The hook rule is the one thing a developer must not miss: .is-* is for
   photographing a state, never for shipping. */
.sb-hook{margin:14px 0 0;padding-top:13px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--ink-2);max-width:82ch}
.sb-hook code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  direction:ltr;display:inline-block;font-size:11.5px;
  background:var(--hover);padding:1px 5px;border-radius:4px}
.sb-back{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;
  margin-top:14px;border:1px solid var(--line-2);border-radius:9px;
  background:var(--card);color:var(--ink);font-size:12.5px;font-weight:600;
  text-decoration:none}
.sb-back:hover{background:var(--hover);border-color:var(--ink-3)}
.sb-back svg{width:14px;height:14px;opacity:.75}

.sb-main{padding:24px 32px 72px;display:flex;flex-direction:column;gap:22px;
  width:auto;margin:0;max-width:none}
.sb-comp{background:var(--card);border:1px solid var(--line);border-radius:12px;
  overflow:hidden;box-shadow:var(--shadow)}
.sb-comp-title{margin:0;padding:13px 18px;font-size:15px;font-weight:650;
  border-bottom:1px solid var(--line)}
/* auto-FILL, not auto-fit: a component with a single state should sit in a
   normal-sized cell, not stretch across the whole row looking broken. The
   separators are drawn per cell rather than by the grid's own background —
   otherwise every unused track shows up as a grey block. */
.sb-states{display:grid;gap:1px;background:var(--card);
  grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.sb-state{background:var(--card);padding:18px;
  box-shadow:0 0 0 1px var(--line)}
.sb-state>.sb-label{display:flex;align-items:baseline;gap:8px;margin-bottom:12px}
.sb-state>.sb-label b{font-size:13px;font-weight:650;letter-spacing:0}
.sb-state>.sb-label .sb-src{font-size:11px;color:var(--ink-3);direction:ltr}
.sb-node{display:flex;align-items:center;justify-content:flex-start;
  min-height:56px}
.sb-note{padding:12px 18px;font-size:12.5px;color:var(--ink-2);
  border-top:1px solid var(--line)}
@media (max-width:640px){
  .sb-head{padding:20px} .sb-main{padding:18px 20px 56px}
  .sb-states{grid-template-columns:1fr}
}
"""


def screen_styles(project, screen):
    """Every <style> block from the screen, so the board renders like the page."""
    path = os.path.join(project, "screens", screen + ".html")
    if not os.path.isfile(path):
        sys.stderr.write("no such screen: %s\n" % path)
        sys.exit(2)
    src = open(path, encoding="utf-8").read()
    blocks = re.findall(r"<style>(.*?)</style>", src, re.S)
    m = re.search(r'<html[^>]*\bdir="(rtl|ltr)"', src, re.I)
    lang = re.search(r'<html[^>]*\blang="([^"]+)"', src, re.I)
    # The board's own <title> follows the page anywhere it is published or
    # bundled, so it has to be the screen's human name — not the slug.
    t = re.search(r"<title>(.*?)</title>", src, re.I | re.S)
    name = t.group(1).strip() if t else screen
    return ("\n".join(blocks), (m.group(1) if m else "ltr"),
            (lang.group(1) if lang else "en"), name)


def rebase(text, prefix):
    """The screen lives in screens/, so its asset paths are ../assets/. The
    board sits at the project root and the probes two levels down — rewrite
    rather than leaving broken references that render as blank icons."""
    return text.replace("../assets/", prefix)


def state_class(state):
    return "" if state == "default" else " is-" + state


def slug(text):
    """Keep Unicode letters. Stripping to [a-z0-9] turns every Hebrew component
    name into the same empty string, and the probe pages then overwrite each
    other silently — reported as written, not actually there."""
    return re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-") or "component"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--screen", default=None,
                    help="screen slug; defaults to states.json's own 'screen'")
    args = ap.parse_args()

    project = os.path.abspath(os.path.expanduser(args.project))
    spec_path = os.path.join(project, "states.json")
    if not os.path.isfile(spec_path):
        sys.stderr.write(
            "no states.json in %s — the agent writes it from the Figma variants "
            "(see references/states.md)\n" % project)
        sys.exit(2)
    spec = json.load(open(spec_path, encoding="utf-8"))
    screen = args.screen or spec.get("screen")
    if not screen:
        sys.stderr.write("no screen named, and states.json has no 'screen'\n")
        sys.exit(2)

    comps = spec.get("components") or []
    if not comps:
        sys.stderr.write("states.json lists no components — nothing to render\n")
        sys.exit(2)

    css, direction, lang, name = screen_styles(project, screen)

    # ---- the board -------------------------------------------------------
    blocks = []
    for c in comps:
        figma = c.get("figma") or {}
        cells = ""
        for st in c.get("states") or ["default"]:
            node = (c["html"].replace('class="', 'class="%s ' % state_class(st).strip(), 1)
                    if state_class(st) else c["html"])
            # naming the variant each state came from is what lets a developer
            # trace a colour back to the design instead of taking it on trust
            src = ('<span class="sb-src">%s %s</span>'
                   % (T["variant"], html.escape(str(figma[st])))) if figma.get(st) else ""
            label = T["default_label"] if st == "default" else st
            cells += ('      <div class="sb-state">\n'
                      '        <div class="sb-label"><b>%s</b>%s</div>\n'
                      '        <div class="sb-node">%s</div>\n'
                      '      </div>\n'
                      % (html.escape(label), src, rebase(node, "assets/")))
        blocks.append(
            '  <div class="sb-comp">\n    <div class="sb-comp-title">%s</div>\n'
            '    <div class="sb-states">\n%s    </div>\n%s  </div>' % (
                html.escape(c.get("name", "component")), cells,
                ('    <div class="sb-note">%s</div>\n' % c["note"]) if c.get("note") else ""))

    back = ""
    if os.path.isfile(os.path.join(project, "index.html")):
        back = ('<a class="sb-back" href="index.html"><svg viewBox="0 0 14 14" '
                'fill="none" stroke="currentColor" stroke-width="1.3" '
                'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                '<rect x="1.5" y="2" width="4.5" height="4.5" rx="1"/>'
                '<rect x="8" y="2" width="4.5" height="4.5" rx="1"/>'
                '<rect x="1.5" y="7.5" width="4.5" height="4.5" rx="1"/>'
                '<rect x="8" y="7.5" width="4.5" height="4.5" rx="1"/>'
                '</svg>%s</a>' % T["back"])

    board = """<!doctype html>
<html lang="%s" dir="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s — %s</title>
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="base.css">
<style>%s</style>
<style>%s</style>
</head>
<body>
<div class="sb-head">
  <div class="sb-title">%s — %s</div>
  <p class="sb-lede">%s</p>
  <p class="sb-live">%s</p>
  <p class="sb-hook">%s</p>
  %s
</div>
<div class="sb-main">
%s
</div>
</body>
</html>
""" % (lang, direction, name, T["suffix"], rebase(css, "assets/"), BOARD_CSS,
       name, T["suffix"], T["lede"], T["live"], T["hook"], back,
       "\n".join(blocks))

    board_path = os.path.join(project, "states.html")
    open(board_path, "w", encoding="utf-8").write(board)

    # ---- one probe page per state, for measuring -------------------------
    probe_dir = os.path.join(project, ".fidelity", "states")
    os.makedirs(probe_dir, exist_ok=True)
    made = []
    for i, c in enumerate(comps, 1):
        for st in c.get("states") or ["default"]:
            node = (c["html"].replace('class="', 'class="%s ' % state_class(st).strip(), 1)
                    if state_class(st) else c["html"])
            node = rebase(node, "../../assets/")
            page = ("""<!doctype html>
<html lang="%s" dir="%s"><head><meta charset="utf-8">
<link rel="stylesheet" href="../../tokens.css">
<link rel="stylesheet" href="../../base.css">
<style>%s</style><style>%s</style></head>
<body><div class="probe">%s</div></body></html>
""" % (lang, direction, rebase(css, "../../assets/"), CELL_CSS, node))
            # index prefix so two components can never collide, whatever the
            # script their names are written in
            name = "%02d-%s-%s.html" % (i, slug(c.get("name", "component")), slug(st))
            open(os.path.join(probe_dir, name), "w", encoding="utf-8").write(page)
            made.append(name)

    print("%s" % board_path)
    print("%d probe pages in %s" % (len(made), probe_dir))


if __name__ == "__main__":
    main()
