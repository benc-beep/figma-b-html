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

BOARD_CSS = """
:root{--ink:#1e1e1e;--muted:#757575;--line:#e6e6e6;--bg:#f7f7f8;--card:#fff}
@media (prefers-color-scheme:dark){
  :root{--ink:#ededed;--muted:#9a9a9a;--line:#444;--bg:#1c1c1c;--card:#2c2c2c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
header{padding:28px 32px 10px;background:var(--card);border-bottom:1px solid var(--line)}
h1{margin:0 0 4px;font-size:20px;font-weight:650}
.sub{color:var(--muted);font-size:13px}
main{padding:24px 32px 64px;display:flex;flex-direction:column;gap:28px}
.comp{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.comp > h2{margin:0;padding:12px 16px;font-size:14px;font-weight:650;
  border-bottom:1px solid var(--line)}
.states{display:flex;flex-wrap:wrap;gap:0}
.state{border-inline-end:1px solid var(--line);border-block-end:1px solid var(--line);
  padding:16px;min-width:200px}
.state:last-child{border-inline-end:0}
.state > .label{font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);margin-bottom:10px;direction:ltr}
.state > .node{display:flex;align-items:center;justify-content:flex-start}
.note{padding:12px 16px;font-size:12px;color:var(--muted);border-top:1px solid var(--line)}
"""


def screen_styles(project, screen):
    """Every <style> block from the screen, so the board renders like the page."""
    path = os.path.join(project, "screens", screen + ".html")
    if not os.path.isfile(path):
        sys.stderr.write("no such screen: %s\n" % path)
        sys.exit(2)
    html = open(path, encoding="utf-8").read()
    blocks = re.findall(r"<style>(.*?)</style>", html, re.S)
    m = re.search(r'<html[^>]*\bdir="(rtl|ltr)"', html, re.I)
    lang = re.search(r'<html[^>]*\blang="([^"]+)"', html, re.I)
    # The board's own <title> follows the page anywhere it is published or
    # bundled, so it has to be the screen's human name — not the slug.
    t = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
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
        cells = ""
        for st in c.get("states") or ["default"]:
            node = (c["html"].replace('class="', 'class="%s ' % state_class(st).strip(), 1)
                    if state_class(st) else c["html"])
            cells += ('      <div class="state"><div class="label">%s</div>'
                      '<div class="node">%s</div></div>\n' % (st, rebase(node, "assets/")))
        blocks.append(
            '  <section class="comp">\n    <h2>%s</h2>\n    <div class="states">\n%s'
            '    </div>\n%s  </section>' % (
                c.get("name", "component"), cells,
                ('    <div class="note">%s</div>\n' % c["note"]) if c.get("note") else ""))

    board = """<!doctype html>
<html lang="%s" dir="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s — סטייטים</title>
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="base.css">
<style>%s</style>
<style>%s</style>
</head>
<body>
<header>
  <h1>%s — סטייטים</h1>
  <div class="sub">כל רכיב בכל מצב. המחלקות <code>is-*</code> הן וו לבדיקה בלבד —
    בקוד עצמו הסטייטים הם <code>:hover</code>, <code>:disabled</code> וכו'.</div>
</header>
<main>
%s
</main>
</body>
</html>
""" % (lang, direction, name, rebase(css, "assets/"), BOARD_CSS, name, "\n".join(blocks))

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
