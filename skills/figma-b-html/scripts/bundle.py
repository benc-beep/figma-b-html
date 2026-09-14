#!/usr/bin/env python3
"""Fold a converted screen and everything it references into one HTML file.

    python3 bundle.py screens/home.html home-standalone.html
    python3 bundle.py screens/home.html fragment.html --fragment
    python3 bundle.py screens/home.html small.html --max-image 1600

--max-image caps the longest edge of each raster and re-encodes photographs as
JPEG. Figma hands back source images far larger than the box they render in — a
card photo displayed at 392x212 can arrive as 1568x1176 — so a bundle can run to
tens of megabytes for a page that looks identical at a fraction of that. The
project folder keeps the originals; only the single sendable file is reduced.
Always re-measure the bundled file: the point is a smaller file that still
scores the same.
"""
import argparse, base64, io, mimetypes, os, re, sys

MIME = {".ttf":"font/ttf",".woff":"font/woff",".woff2":"font/woff2",
        ".svg":"image/svg+xml",".png":"image/png",".jpg":"image/jpeg",
        ".jpeg":"image/jpeg",".webp":"image/webp",".gif":"image/gif"}

def shrink(path, cap, q=82):
    """Return (bytes, mime) for a raster, capped and re-encoded. None if untouched."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(path)
    except Exception:
        return None
    if max(im.size) <= cap and im.mode != "P":
        # small already: only worth re-encoding if it is an opaque PNG
        if os.path.splitext(path)[1].lower() != ".png":
            return None
    if max(im.size) > cap:
        ratio = cap / float(max(im.size))
        im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))),
                       Image.LANCZOS)
    buf = io.BytesIO()
    has_alpha = im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255
    if has_alpha:
        im.save(buf, "PNG", optimize=True)
        return buf.getvalue(), "image/png"
    im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    return buf.getvalue(), "image/jpeg"


def data_uri(path, cap=0, q=82):
    ext = os.path.splitext(path)[1].lower()
    if cap and ext in (".png", ".jpg", ".jpeg", ".webp"):
        out = shrink(path, cap, q)
        if out:
            return "data:%s;base64,%s" % (out[1], base64.b64encode(out[0]).decode())
    mime = MIME.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())

def inline_refs(text, base_dir, missing, cap=0, q=82):
    """Rewrite url(...) and src="..." that point at local files."""
    def repl_url(m):
        raw = m.group(2).strip()
        if raw.startswith(("data:", "http:", "https:", "#")):
            return m.group(0)
        p = os.path.normpath(os.path.join(base_dir, raw))
        if not os.path.isfile(p):
            missing.append(raw); return m.group(0)
        return "url(%s)" % data_uri(p, cap, q)
    text = re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", repl_url, text)

    def repl_src(m):
        raw = m.group(2)
        if raw.startswith(("data:", "http:", "https:", "#")):
            return m.group(0)
        p = os.path.normpath(os.path.join(base_dir, raw))
        if not os.path.isfile(p):
            missing.append(raw); return m.group(0)
        return '%s="%s"' % (m.group(1), data_uri(p, cap, q))
    return re.sub(r'\b(src)=(?:")([^"]+)(?:")', repl_src, text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--fragment", action="store_true",
                    help="emit only <title>/<style>/body for an Artifact publish")
    ap.add_argument("--max-image", type=int, default=0, dest="cap",
                    help="cap each raster's longest edge and re-encode photos as JPEG")
    ap.add_argument("--quality", type=int, default=82,
                    help="JPEG quality for --max-image (default 82)")
    args = ap.parse_args()
    src, out, body_only, cap, q = args.src, args.out, args.fragment, args.cap, args.quality
    src = os.path.abspath(src); d = os.path.dirname(src)
    html = open(src, encoding="utf-8").read()
    missing = []

    # pull each linked stylesheet in, resolving its own url()s from ITS folder
    def repl_link(m):
        href = m.group(1)
        p = os.path.normpath(os.path.join(d, href))
        if not os.path.isfile(p):
            missing.append(href); return m.group(0)
        css = open(p, encoding="utf-8").read()
        return "<style>\n/* %s */\n%s\n</style>" % (os.path.basename(p),
                                                    inline_refs(css, os.path.dirname(p), missing, cap, q))
    html = re.sub(r'<link\s+rel="stylesheet"\s+href="([^"]+)"\s*/?>', repl_link, html)
    html = inline_refs(html, d, missing, cap, q)

    if body_only:
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        styles = re.findall(r"<style>.*?</style>", html, re.S)
        body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)
        parts = ["<title>%s</title>" % (title.group(1) if title else "screen")]
        parts += styles
        # The host page owns <html>, so the document's own direction has to be
        # carried on the body instead. Read it — hardcoding rtl silently mirrors
        # every LTR page, and the flip is invisible in a centred layout until a
        # split section lands the wrong way round.
        m = re.search(r'<html[^>]*\bdir="(rtl|ltr)"', html, re.I)
        direction = m.group(1).lower() if m else "ltr"
        lang = re.search(r'<html[^>]*\blang="([^"]+)"', html, re.I)
        parts.append("<style>body{direction:%s}</style>" % direction)
        if lang:
            parts.append("<!-- source document: lang=%s dir=%s -->" % (lang.group(1), direction))
        parts.append(body)
        html = "\n".join(parts)

    open(out, "w", encoding="utf-8").write(html)
    kb = os.path.getsize(out) / 1024.0
    print("%s  %.0f KB" % (out, kb))
    if missing:
        print("MISSING (left as-is): %s" % sorted(set(missing)))

main()
