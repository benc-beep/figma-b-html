#!/usr/bin/env python3
"""Rebuild the gallery page for a converted-screens project.

    python3 build_index.py --project ~/Design/figma-html/acme-checkout

Scans screens/*.html, pairs each one with its fidelity report, and writes
index.html: a live thumbnail per screen (a scaled iframe, so it is always the
real current file and never a stale image), its measured fidelity, and any
deviation the conversion could not avoid.

The page is opened by people who did not run the conversion — a developer, a
client, the designer a week later. So it has to explain itself: what a card is,
what the percentage means, and what each action does. Anything that needs a
sentence of spoken context is a bug in this file.

Re-run it after adding, renaming or re-verifying a screen. It only writes
index.html; nothing else in the project is touched.
"""

import argparse
import html
import json
import os
import re
import sys

CARD_W = 340

# Every user-facing string, in one place. The gallery speaks one language at a
# time; swapping this dict is the whole job of translating it.
T = {
    "title_suffix": "מסכים",
    "lede": "כל כרטיס כאן הוא מסך שהומר מפיגמה ל-HTML עצמאי — נפתח בדפדפן בלחיצה, "
            "בלי שרת ובלי התקנה. האחוז שליד כל מסך הוא כמה הרינדור בדפדפן שונה "
            "מהעיצוב המקורי, נמדד פיקסל מול פיקסל.",
    "legend": [("good", "עד 1% — תואם"),
               ("warn", "1%–3% — פערים קטנים"),
               ("bad", "מעל 3% — כדאי להסתכל"),
               ("unknown", "לא נבדק")],
    "screens": "מסכים",
    "direction": "כיוון",
    "waiting": "ממתינים לך",
    "approved": "אושרו",
    "source": "מקור",
    "empty": "אין עדיין מסכים בתיקייה screens/.",
    "open": "פתח את המסך",
    "compare": "השוואה לפיגמה",
    "figma": "פתח בפיגמה",
    "states": "סטייטים",
    "blocked_chip": "חוסם",
    "blocked_title": "חסום — צריך ממך",
    "notes_one": "הערה טכנית אחת",
    "notes_many": "%d הערות טכניות",
    "unmeasured": "לא נבדק",
    "unmeasured_hint": "אין דוח השוואה — אל תניח שהמסך תואם לפיגמה",
    "approved_prefix": "אושר",
    "approved_note": "אושר: %s",
    "words": {"good": "תואם לעיצוב",
              "warn": "פערים קטנים",
              "bad": "כדאי להסתכל",
              "accepted": "אושר על ידך",
              "unknown": "לא נמדד"},
    "height_delta": "הפרש גובה",
}

# At 14px an icon either says something instantly or it is noise. The Figma
# brand mark is four overlapping shapes and turns to mush at this size, so the
# icons describe the *action* instead: a window opens, a split panel compares,
# an arrow leaves the page, layers are states.
ICONS = {
    "open": '<rect x="1.5" y="2.5" width="11" height="9" rx="1.5"/>'
            '<path d="M1.5 5.2h11"/>',
    "compare": '<rect x="1.5" y="2.5" width="11" height="9" rx="1.5"/>'
               '<path d="M7 2.5v9"/><path d="M1.5 4h5.5M1.5 6h5.5M1.5 8h5.5" '
               'opacity=".55"/>',
    "figma": '<path d="M6.5 2.5H2.5v9h9v-4"/><path d="M8.75 1.75h3.75v3.75"/>'
             '<path d="M12.5 1.75L7 7.25"/>',
    "states": '<path d="M7 1.5l5.5 3L7 7.5 1.5 4.5z"/><path d="M1.5 9.5L7 12.5l5.5-3"/>',
}


def icon(name):
    return ('<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" '
            'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">%s</svg>' % ICONS[name])


def read(path):
    with open(path, "r", errors="replace") as fh:
        return fh.read()


def meta(source, name, default=""):
    m = re.search(
        r'<meta\s+name=["\']%s["\']\s+content=["\'](.*?)["\']' % re.escape(name),
        source, re.I | re.S)
    return m.group(1).strip() if m else default


def screen_title(source, fallback):
    m = re.search(r"<title>(.*?)</title>", source, re.I | re.S)
    return m.group(1).strip() if m else fallback


def load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def score(report, accepted):
    """The fidelity readout: a number, a state, and a phrase in plain words.

    The number alone means nothing to someone meeting this page for the first
    time — 2.34% reads as a failure until you know the scale. So every card
    carries the plain-language verdict beside it, and the header carries the
    scale itself.

    'accepted' is deliberately not the same as 'pass'. A screen the designer has
    looked at and approved stops being flagged, but keeps showing its real
    number — hiding the measurement once someone approves it is how a folder
    slowly stops being trustworthy.
    """
    if not report or report.get("diff_pct") is None:
        return ("—", "unknown", T["words"]["unknown"], "", T["unmeasured_hint"])

    pct = report["diff_pct"]
    num = '<span dir="ltr">%.2f%%</span>' % pct
    hd = report.get("height_delta_px") or 0
    extra = ('%s <span dir="ltr">%+dpx</span>' % (T["height_delta"], hd)) if hd else ""

    if accepted:
        return (num, "accepted", T["words"]["accepted"], extra, "")
    if report.get("pass") or pct <= 1.0:
        state = "good"
    elif pct <= 3.0:
        state = "warn"
    else:
        state = "bad"
    return (num, state, T["words"][state], extra, "")


STYLE = """
:root{
  --bg:#F4F5F7; --card:#FFFFFF; --line:#E3E5E9; --line-2:#CFD3DA;
  --ink:#16181D; --ink-2:#5A616E; --ink-3:#8B93A1;
  --good:#1F6F4F; --good-bg:#E6F5EE;
  --warn:#8A5A00; --warn-bg:#FDF1DC;
  --bad:#A32020; --bad-bg:#FBEAEA;
  --unknown:#555B66; --unknown-bg:#EDEEF1;
  --accent:#1F4E79; --accent-bg:#E8F0F8; --accent-ink:#FFFFFF;
  --hover:#F2F4F7;
  --shadow:0 1px 2px rgba(16,20,28,.05), 0 4px 12px rgba(16,20,28,.05);
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#15171B; --card:#1E2126; --line:#2E333A; --line-2:#3C434C;
         --ink:#ECEEF1; --ink-2:#A7AEBA; --ink-3:#79818E;
         --good:#7ED3A8; --good-bg:#12301F;
         --warn:#E4B65F; --warn-bg:#332713;
         --bad:#F09393; --bad-bg:#3A1C1C;
         --unknown:#AFB6C1; --unknown-bg:#2A2E34;
         --accent:#8FC0EC; --accent-bg:#17273A; --accent-ink:#0E1620;
         --hover:#262A30;
         --shadow:0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(0,0,0,.25); }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  -webkit-font-smoothing:antialiased}

header{padding:26px 32px 20px;background:var(--card);
  border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:22px;font-weight:680;letter-spacing:-.01em}
.lede{margin:0;max-width:74ch;color:var(--ink-2);font-size:13.5px}

/* The scale is the missing context: without it a number is just a number. */
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:16px 0 0;padding:0;
  list-style:none;font-size:12.5px;color:var(--ink-2)}
.legend li{display:flex;align-items:center;gap:7px}
.dot{width:9px;height:9px;border-radius:50%;flex:none}
.dot.good{background:var(--good)} .dot.warn{background:var(--warn)}
.dot.bad{background:var(--bad)}   .dot.unknown{background:var(--ink-3)}

.facts{margin-top:14px;padding-top:13px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--ink-2);overflow-wrap:anywhere}
.facts .waiting{color:var(--bad);font-weight:650}
.facts code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  direction:ltr;display:inline-block;font-size:11.5px;color:var(--ink-3)}

main{padding:24px 32px 72px;display:grid;gap:22px;
  grid-template-columns:repeat(auto-fill,minmax(340px,1fr));align-items:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
  overflow:hidden;box-shadow:var(--shadow)}

/* direction:ltr is load-bearing. In an RTL document an absolutely positioned
   iframe with inset:0 anchors to the RIGHT edge, and transform-origin:top left
   then scales it away off-canvas — the thumbnail comes out blank and the card
   overflows. Pin it explicitly instead. */
.thumb{position:relative;display:block;height:208px;overflow:hidden;
  background:#fff;border-bottom:1px solid var(--line);direction:ltr}
.thumb iframe{position:absolute;top:0;left:0;right:auto;border:0;
  transform-origin:top left;pointer-events:none}
.thumb::after{content:"";position:absolute;inset:0;
  box-shadow:inset 0 -28px 24px -24px rgba(16,20,28,.10)}
a.thumb:hover::after{box-shadow:inset 0 0 0 2px var(--accent)}

.meta{padding:14px 16px 16px;display:flex;flex-direction:column;gap:12px}
.name{margin:0;font-size:15.5px;font-weight:650;line-height:1.3}
.dims{margin-top:3px;color:var(--ink-3);font-size:12px;direction:ltr;
  text-align:start}

/* The score is the card's headline, so it reads as one: big number, plain
   words beside it, and the colour carries the verdict. */
.score{display:flex;align-items:center;gap:10px;padding:9px 12px;
  border-radius:9px;border:1px solid transparent}
.score .pct{font-size:19px;font-weight:700;line-height:1;letter-spacing:-.02em}
.score .word{font-size:13px;font-weight:600}
.score .extra{margin-inline-start:auto;font-size:11.5px;opacity:.85}
.score.good{background:var(--good-bg);color:var(--good)}
.score.warn{background:var(--warn-bg);color:var(--warn)}
.score.bad{background:var(--bad-bg);color:var(--bad)}
.score.unknown{background:var(--unknown-bg);color:var(--unknown)}
.score.accepted{background:var(--accent-bg);color:var(--accent)}

.actions{display:flex;flex-wrap:wrap;gap:8px}
.btn{display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 13px;
  border:1px solid var(--line-2);border-radius:9px;background:var(--card);
  color:var(--ink);font-size:12.5px;font-weight:600;text-decoration:none;
  white-space:nowrap;transition:background .12s,border-color .12s}
.btn:hover{background:var(--hover);border-color:var(--ink-3)}
.btn svg{width:14px;height:14px;flex:none;opacity:.75}
.btn--primary{background:var(--accent);border-color:var(--accent);
  color:var(--accent-ink)}
.btn--primary:hover{background:var(--accent);filter:brightness(1.08)}
.btn--primary svg{opacity:.9}

/* Blockers are things the designer can fix in a minute — a missing font, an
   asset cap. They are not deviations, and burying them in the same grey list
   is how a one-minute fix sits unnoticed for a week. */
.blockers{padding:11px 13px;border-radius:9px;background:var(--bad-bg);
  border-inline-start:3px solid var(--bad);font-size:12.5px;color:var(--bad);
  line-height:1.5}
.blockers .hdr,.blockers>summary{font-weight:700;margin-bottom:5px}
.blockers>summary{cursor:pointer;list-style:none;user-select:none;margin:0}
.blockers>summary::-webkit-details-marker{display:none}
.blockers[open]>summary{margin-bottom:6px}
.blockers .n{opacity:.7;font-weight:600}
.blockers ul{margin:0;padding-inline-start:16px;list-style:disc}
.blockers li+li{margin-top:5px}
/* free text with no length contract — keep the card from running away */
.blockers ul,details.notes ul{max-height:230px;overflow:auto;overscroll-behavior:contain}

details.notes{font-size:12.5px;color:var(--ink-2)}
details.notes>summary{cursor:pointer;list-style:none;display:inline-flex;
  align-items:center;gap:6px;color:var(--ink-2);font-weight:600;
  padding:3px 0;user-select:none}
details.notes>summary::-webkit-details-marker{display:none}
details.notes>summary::before{content:"";width:0;height:0;
  border-block:4px solid transparent;
  border-inline-start:5px solid currentColor;transition:transform .15s}
details.notes[open]>summary::before{transform:rotate(90deg)}
[dir="rtl"] details.notes>summary::before{transform:scaleX(-1)}
[dir="rtl"] details.notes[open]>summary::before{transform:scaleX(-1) rotate(90deg)}
details.notes ul{margin:8px 0 0;padding-inline-start:16px}
details.notes li{margin:4px 0}

.empty{padding:56px 32px;color:var(--ink-2)}
@media (max-width:640px){
  header{padding:20px}
  main{padding:18px 20px 56px;grid-template-columns:1fr}
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args()

    project = os.path.abspath(os.path.expanduser(args.project))
    screens_dir = os.path.join(project, "screens")
    if not os.path.isdir(screens_dir):
        sys.stderr.write("not a converted-screens project (no screens/): %s\n" % project)
        sys.exit(1)

    info = load_json(os.path.join(project, "project.json")) or {}
    title = info.get("title") or os.path.basename(project)
    direction = info.get("direction", "ltr")

    files = sorted(f for f in os.listdir(screens_dir) if f.endswith(".html"))
    cards = []
    blocked_count = 0
    accepted_count = 0
    for fname in files:
        slug = fname[:-5]
        source = read(os.path.join(screens_dir, fname))
        name = screen_title(source, slug)
        width = meta(source, "design-width", "1440")
        try:
            width_i = int(re.sub(r"[^\d]", "", width) or 1440)
        except ValueError:
            width_i = 1440
        node = meta(source, "figma:node")
        figma_url = meta(source, "figma:url")
        mode = meta(source, "conversion-mode", "")

        fid = os.path.join(project, ".fidelity", slug)
        report = load_json(os.path.join(fid, "report.json"))
        note_file = load_json(os.path.join(fid, "notes.json")) or {}
        notes = list(note_file.get("deviations", []))
        blockers = note_file.get("blockers", [])
        accepted = bool(note_file.get("accepted"))
        if accepted and note_file.get("accepted_note"):
            notes.append(T["approved_note"] % note_file["accepted_note"])
        num, state, word, extra, hint = score(report, accepted)
        if hint:
            notes = [hint] + notes
        if blockers:
            blocked_count += 1
        if accepted:
            accepted_count += 1

        scale = CARD_W / float(width_i)

        acts = ['<a class="btn btn--primary" href="screens/%s">%s%s</a>'
                % (html.escape(fname), icon("open"), T["open"])]
        if os.path.isfile(os.path.join(fid, "side-by-side.png")):
            acts.append('<a class="btn" href=".fidelity/%s/side-by-side.png">%s%s</a>'
                        % (html.escape(slug), icon("compare"), T["compare"]))
        if figma_url:
            acts.append('<a class="btn" href="%s" target="_blank" rel="noopener">%s%s</a>'
                        % (html.escape(figma_url), icon("figma"), T["figma"]))
        # the states board belongs to the whole project, but it is only useful
        # from the screen it was generated for
        if os.path.isfile(os.path.join(project, "states.html")) and \
           (load_json(os.path.join(project, "states.json")) or {}).get("screen") == slug:
            acts.append('<a class="btn" href="states.html">%s%s</a>'
                        % (icon("states"), T["states"]))

        # A blocker must stay visible — it is the one thing on the card someone
        # has to act on. But it is free text, and one screen's blockers ran to
        # a dozen paragraphs: rendered flat, that card grew to 1400px and tore a
        # hole in the grid. Short ones stay open; long ones collapse to a line
        # that still says how many there are.
        block_html = ""
        if blockers:
            items = "".join("<li>%s</li>" % html.escape(str(b)) for b in blockers)
            bulk = sum(len(str(b)) for b in blockers)
            if len(blockers) <= 2 and bulk <= 220:
                block_html = ('<div class="blockers"><div class="hdr">⚠ %s</div>'
                              '<ul>%s</ul></div>' % (T["blocked_title"], items))
            else:
                block_html = (
                    '<details class="blockers"><summary>⚠ %s <span class="n">(%d)</span>'
                    '</summary><ul>%s</ul></details>'
                    % (T["blocked_title"], len(blockers), items))

        note_html = ""
        if notes:
            label = T["notes_one"] if len(notes) == 1 else T["notes_many"] % len(notes)
            note_html = ('<details class="notes"><summary>%s</summary><ul>%s</ul></details>'
                         % (label,
                            "".join("<li>%s</li>" % html.escape(str(n)) for n in notes)))

        bits = [b for b in ("%spx" % width_i, mode, node) if b]
        cards.append("""
  <article class="card">
    <a class="thumb" href="screens/{file}">
      <iframe src="screens/{file}" width="{w}" height="{ih}" loading="lazy"
              scrolling="no" data-w="{w}" style="transform:scale({scale});"
              title="{name}" tabindex="-1"></iframe>
    </a>
    <div class="meta">
      <div>
        <h2 class="name">{name}</h2>
        <div class="dims">{dims}</div>
      </div>
      <div class="score {state}">
        <span class="pct">{num}</span>
        <span class="word">{word}</span>
        {extra}
      </div>
      <div class="actions">{actions}</div>
      {blockers}
      {notes}
    </div>
  </article>""".format(
            file=html.escape(fname), w=width_i,
            ih=int(round(208 / scale)) if scale else 900,
            scale=round(scale, 4), name=html.escape(name),
            dims=html.escape(" · ".join(bits)),
            state=state, num=num, word=word,
            extra=('<span class="extra">%s</span>' % extra) if extra else "",
            actions="".join(acts), blockers=block_html, notes=note_html))

    body = "\n".join(cards) if cards else '<div class="empty">%s</div>' % T["empty"]

    source_line = ""
    if info.get("figma_url"):
        source_line = " · %s: <code>%s</code>" % (
            T["source"], html.escape(info["figma_url"]))

    summary = ""
    if blocked_count:
        summary += ' · <span class="waiting">%d %s</span>' % (blocked_count, T["waiting"])
    if accepted_count:
        summary += " · %d %s" % (accepted_count, T["approved"])

    legend = "".join('<li><span class="dot %s"></span>%s</li>' % (cls, text)
                     for cls, text in T["legend"])

    out = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — {suffix}</title>
<style>{style}</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p class="lede">{lede}</p>
  <ul class="legend">{legend}</ul>
  <div class="facts">{count} {screens} · {dirlabel} {dirn}{summary}{source_line}</div>
</header>
<main>
{body}
</main>
<script>
/* Cards stretch to fill the grid, so the baked-in scale is only a starting
   point. Recompute it from the real card width — and again on resize. Without
   JS the baked value still renders a usable thumbnail. */
(function () {{
  function fit() {{
    document.querySelectorAll('.thumb iframe').forEach(function (f) {{
      var w = parseInt(f.dataset.w, 10) || 1440;
      var box = f.parentElement;
      var s = box.clientWidth / w;
      f.style.transform = 'scale(' + s + ')';
      f.height = Math.round(box.clientHeight / s);
    }});
  }}
  window.addEventListener('resize', fit);
  window.addEventListener('load', fit);
  fit();
}})();
</script>
</body>
</html>
""".format(title=html.escape(title), suffix=T["title_suffix"], style=STYLE,
           lede=T["lede"], legend=legend, count=len(files), screens=T["screens"],
           dirlabel=T["direction"], dirn=html.escape(direction), summary=summary,
           source_line=source_line, body=body)

    index_path = os.path.join(project, "index.html")
    with open(index_path, "w") as fh:
        fh.write(out)

    if info:
        info["screens"] = [f[:-5] for f in files]
        with open(os.path.join(project, "project.json"), "w") as fh:
            json.dump(info, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print("%s (%d screens)" % (index_path, len(files)))


if __name__ == "__main__":
    main()
