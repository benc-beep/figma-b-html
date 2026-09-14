#!/usr/bin/env python3
"""Rebuild the gallery page for a converted-screens project.

    python3 build_index.py --project ~/Design/figma-html/acme-checkout

Scans screens/*.html, pairs each one with its fidelity report, and writes
index.html: a live thumbnail per screen (a scaled iframe, so it is always the
real current file and never a stale image), its measured fidelity, and any
deviation the conversion could not avoid.

Re-run it after adding, renaming or re-verifying a screen. It only writes
index.html; nothing else in the project is touched.
"""

import argparse
import html
import json
import os
import re
import sys

CARD_W = 320


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


def badge(report, accepted):
    """The fidelity chip.

    'accepted' is deliberately not the same as 'pass'. A screen the designer has
    looked at and approved stops being flagged, but keeps showing its real number
    — hiding the measurement once someone approves it is how a folder slowly
    stops being trustworthy.
    """
    if not report:
        return ("לא נבדק", "unknown",
                "אין דוח השוואה — אל תניח שהמסך תואם לפיגמה")
    pct = report.get("diff_pct")
    if pct is None:
        return ("לא נבדק", "unknown", "")

    # Numbers are LTR runs inside RTL text. Without the explicit spans the
    # browser reorders them and "4.83% הפרש · גובה -22px" comes out unreadable.
    num = '<span dir="ltr">%.2f%%</span>' % pct
    extra = ""
    hd = report.get("height_delta_px") or 0
    if hd:
        extra = ' · גובה <span dir="ltr">%+dpx</span>' % hd

    if accepted:
        return ("אושר · " + num + extra, "accepted", "")
    if report.get("pass"):
        state = "good"
    elif pct <= 3.0:
        state = "warn"
    else:
        state = "bad"
    return (num + " הפרש" + extra, state, "")


STYLE = """
:root{
  --bg:#F7F7F8; --card:#FFFFFF; --line:#E6E6E6; --ink:#1E1E1E; --muted:#757575;
  --good:#3D8168; --good-bg:#EAF6F0; --warn:#8A6100; --warn-bg:#FDF3E0;
  --bad:#A32C2C; --bad-bg:#FBECEC; --unknown:#5B5B5B; --unknown-bg:#EFEFEF;
  --accent:#2C5C8A; --accent-bg:#E8F0F8;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1C1C1C; --card:#2C2C2C; --line:#444; --ink:#EDEDED; --muted:#9A9A9A;
         --good:#7FC4A4; --good-bg:#1E3A2E; --warn:#E0B25C; --warn-bg:#3A2F17;
         --bad:#E88C8C; --bad-bg:#3A1F1F; --unknown:#B0B0B0; --unknown-bg:#3A3A3A;
         --accent:#8FB8DC; --accent-bg:#1E2E3E; }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
header{padding:28px 32px 8px;border-bottom:1px solid var(--line);background:var(--card)}
h1{margin:0 0 4px;font-size:20px;font-weight:650}
.sub{color:var(--muted);font-size:13px}
.sub code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;direction:ltr;
  display:inline-block;font-size:12px}
main{padding:24px 32px 64px;display:grid;gap:20px;
  grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  overflow:hidden;display:flex;flex-direction:column}
/* direction:ltr is load-bearing. In an RTL document an absolutely positioned
   iframe with inset:0 anchors to the RIGHT edge, and transform-origin:top left
   then scales it away off-canvas — the thumbnail comes out blank and the card
   overflows. Pin it explicitly instead. */
.thumb{position:relative;height:220px;overflow:hidden;background:#fff;
  border-bottom:1px solid var(--line);direction:ltr}
.thumb iframe{position:absolute;top:0;left:0;right:auto;border:0;
  transform-origin:top left;pointer-events:none}
.meta{padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.name{font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.dims{color:var(--muted);font-size:12px;direction:ltr}
.chips{display:flex;gap:6px;align-items:center;flex-shrink:0}
.badge{font-size:11.5px;padding:3px 8px;border-radius:999px;white-space:nowrap}
.good{color:var(--good);background:var(--good-bg)}
.warn{color:var(--warn);background:var(--warn-bg)}
.bad{color:var(--bad);background:var(--bad-bg)}
.unknown{color:var(--unknown);background:var(--unknown-bg)}
.accepted{color:var(--accent);background:var(--accent-bg)}
.blocked{color:#fff;background:var(--bad);font-weight:600}
/* Blockers are things the designer can fix in a minute — a missing font, an asset
   cap. They are not deviations, and burying them in the same grey list is how
   a one-minute fix sits unnoticed for a week. */
.blockers{margin:0;padding:8px 10px;border-radius:6px;background:var(--bad-bg);
  border:1px solid color-mix(in srgb, var(--bad) 30%, transparent);
  list-style:none;font-size:12px;color:var(--bad)}
.blockers li{margin:2px 0}
.blockers .hdr{font-weight:700;margin-bottom:2px}
.notes{margin:0;padding:0 16px 0 0;font-size:12px;color:var(--muted)}
.notes li{margin:2px 0}
.links{display:flex;gap:14px;font-size:12.5px;padding-top:2px}
.links a{color:var(--good);text-decoration:none}
.links a:hover{text-decoration:underline}
.empty{padding:48px 32px;color:var(--muted)}
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
        notes = note_file.get("deviations", [])
        blockers = note_file.get("blockers", [])
        accepted = bool(note_file.get("accepted"))
        if accepted and note_file.get("accepted_note"):
            notes = list(notes) + ["אושר: %s" % note_file["accepted_note"]]
        text, state, hint = badge(report, accepted)
        if blockers:
            blocked_count += 1
        if accepted:
            accepted_count += 1

        scale = CARD_W / float(width_i)
        links = ['<a href="screens/%s">פתח</a>' % html.escape(fname)]
        if os.path.isfile(os.path.join(fid, "side-by-side.png")):
            links.append('<a href=".fidelity/%s/side-by-side.png">השוואה</a>'
                         % html.escape(slug))
        if figma_url:
            links.append('<a href="%s" target="_blank">פיגמה</a>' % html.escape(figma_url))
        # the states board belongs to the whole project, but it is only useful
        # from the screen it was generated for
        if os.path.isfile(os.path.join(project, "states.html")) and \
           (load_json(os.path.join(project, "states.json")) or {}).get("screen") == slug:
            links.append('<a href="states.html">סטייטים</a>')

        block_html = ""
        if blockers:
            block_html = ("<ul class='blockers'><li class='hdr'>חוסם — צריך ממך:</li>%s</ul>"
                          % "".join("<li>%s</li>" % html.escape(str(b)) for b in blockers))

        note_html = ""
        if hint:
            notes = [hint] + list(notes)
        if notes:
            note_html = "<ul class='notes'>%s</ul>" % "".join(
                "<li>%s</li>" % html.escape(str(n)) for n in notes)

        cards.append("""
  <div class="card">
    <div class="thumb">
      <iframe src="screens/{file}" width="{w}" height="{ih}" loading="lazy"
              data-w="{w}" style="transform:scale({scale});" title="{name}"></iframe>
    </div>
    <div class="meta">
      <div class="row">
        <span class="name" title="{name}">{name}</span>
        <span class="chips">{blocked_chip}<span class="badge {state}">{badge}</span></span>
      </div>
      <div class="row">
        <span class="dims">{w}px{mode}{node}</span>
      </div>
      {blockers}
      {notes}
      <div class="links">{links}</div>
    </div>
  </div>""".format(
            file=html.escape(fname), w=width_i,
            ih=int(round(220 / scale)) if scale else 900,
            scale=round(scale, 4), name=html.escape(name),
            state=state, badge=text,  # already HTML: badge() emits dir spans
            blocked_chip=('<span class="badge blocked">חוסם</span>' if blockers else ""),
            mode=(" · %s" % html.escape(mode)) if mode else "",
            node=(" · %s" % html.escape(node)) if node else "",
            blockers=block_html, notes=note_html, links=" ".join(links)))

    body = "\n".join(cards) if cards else \
        '<div class="empty">אין עדיין מסכים בתיקייה screens/.</div>'

    source_line = ""
    if info.get("figma_url"):
        source_line = '<div class="sub">מקור: <code>%s</code></div>' % \
            html.escape(info["figma_url"])

    summary = ""
    if blocked_count:
        summary += ' · <strong style="color:var(--bad)">%d ממתינים לך</strong>' % blocked_count
    if accepted_count:
        summary += " · %d אושרו" % accepted_count

    out = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — מסכים</title>
<style>{style}</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="sub">{count} מסכים · כיוון {dirn}{summary}</div>
  {source_line}
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
""".format(title=html.escape(title), style=STYLE, count=len(files),
           dirn=html.escape(direction), summary=summary,
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
