#!/usr/bin/env python3
"""Measure a page's real layout boxes in the browser, or find what overflows.

    python3 measure.py --file screens/home.html --width 1440 .hero .card .card__title
    python3 measure.py --file screens/home.html --width 375 --overflow

This is the tool that ends arguments. A pixel diff says *that* something is
wrong and roughly where; this says the box is 92px when Figma says 90, which is
a fix rather than another guess. Reach for it as soon as a comparison plateaus,
and always before changing a value you are not sure about.

Pair it with `get_metadata` on the same Figma node: that returns every child's
exact x/y/w/h, so the two lists can be read side by side.

--overflow lists the elements sticking out past the viewport, innermost first.
It is the fastest way to find what breaks a narrow layout.
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MIN_WINDOW = 500   # Chrome will not open a narrower window; see capture.py


# Written into the page ahead of the measuring script. In the narrow-width path
# the page is inside an iframe and Chrome's --dump-dom only serializes the OUTER
# document, so writing the result to this document's own title is not enough:
# it has to be pushed up to the parent. Same-origin holds because both are
# file:// under --allow-file-access-from-files.
EMIT_JS = """
<script>
/* Measure only after the web fonts are in. Without this the script can run
   during the font-block period and report fallback metrics — two runs of the
   same page then disagree, which makes every number here untrustworthy.
   (The screenshot path in capture.py does not have this problem: it was
   verified deterministic across runs.) */
function ready(fn){
  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(fn); }
  else { fn(); }
}
function emit(o){
  var p = 'M:' + JSON.stringify(o);
  document.title = p;
  try { if (window.parent && window.parent !== window) window.parent.document.title = p; }
  catch (e) {}
}
</script>
"""

MEASURE_JS = """
<script>
ready(function(){
  var sels = %s, out = [];
  sels.forEach(function(s){
    document.querySelectorAll(s).forEach(function(el, i){
      var r = el.getBoundingClientRect();
      out.push([s + '[' + i + ']', Math.round(r.x), Math.round(r.y + window.scrollY),
                Math.round(r.width * 100) / 100, Math.round(r.height * 100) / 100]);
    });
  });
  emit({mode: 'measure', rows: out});
});
</script>
"""

# getComputedStyle, not offsetWidth and not getBoundingClientRect: offset* round
# to whole pixels (a 10.83px glyph reads as 11 and looks 4% stretched), and the
# bounding rect includes transforms (a rotated icon would read as its rotated
# box). The computed style is the fractional, untransformed layout size.
ICONS_JS = """
<script>
ready(function(){
  var out = [];
  document.querySelectorAll('img').forEach(function(el){
    var cs = getComputedStyle(el);
    out.push([el.getAttribute('src') || '',
              parseFloat(cs.width) || 0, parseFloat(cs.height) || 0]);
  });
  emit({mode: 'icons', rows: out});
});
</script>
"""

OVERFLOW_JS = """
<script>
ready(function(){
  var vw = document.documentElement.clientWidth, bad = [];
  document.querySelectorAll('*').forEach(function(el){
    var r = el.getBoundingClientRect();
    if (r.width > vw + 1 || r.right > vw + 1) {
      // report only the innermost offender: if a child also overflows, the
      // parent is just carrying it and naming both is noise
      var childOver = Array.prototype.slice.call(el.children).some(function(c){
        var q = c.getBoundingClientRect();
        return q.width > vw + 1 || q.right > vw + 1;
      });
      if (!childOver) {
        var cls = (el.className || '').toString().split(' ').filter(Boolean).slice(0, 3).join('.');
        bad.push([el.tagName.toLowerCase() + (cls ? '.' + cls : ''),
                  Math.round(r.width), Math.round(r.right)]);
      }
    }
  });
  emit({mode: 'overflow', vw: vw, sw: document.documentElement.scrollWidth,
        rows: bad.slice(0, 20)});
});
</script>
"""


# Chrome lives in a different place on every platform, and this skill gets
# shared between machines. Resolution order: --chrome, then $CHROME (the escape
# hatch when it is installed somewhere unusual), then the platform's own
# defaults, then anything on PATH.
def chrome_candidates():
    if sys.platform == "darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    if os.name == "nt":
        roots = [os.environ.get(v) for v in
                 ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rel = [r"Google\Chrome\Application\chrome.exe",
               r"Chromium\Application\chrome.exe",
               r"Microsoft\Edge\Application\msedge.exe"]
        return [os.path.join(root, r) for root in roots if root for r in rel]
    return [
        "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium", "/usr/bin/chromium-browser",
        "/snap/bin/chromium", "/usr/bin/microsoft-edge",
    ]


PATH_NAMES = ("google-chrome", "google-chrome-stable", "chromium",
              "chromium-browser", "chrome", "msedge")


def platform_name():
    return ("macOS" if sys.platform == "darwin"
            else "Windows" if os.name == "nt" else "Linux")


def find_chrome(explicit=None):
    for given in (explicit, os.environ.get("CHROME")):
        if not given:
            continue
        given = os.path.expanduser(given)
        if os.path.isfile(given) and os.access(given, os.X_OK):
            return given
        sys.stderr.write("not executable: %s\n" % given)
        sys.exit(2)
    for path in chrome_candidates():
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    for name in PATH_NAMES:
        found = shutil.which(name)
        if found:
            return found
    sys.stderr.write(
        "No Chrome/Chromium found on this %s machine.\n"
        "Install Google Chrome 133 or newer and re-run. If it is installed\n"
        "somewhere unusual, point at it with --chrome <path> or $CHROME.\n"
        % platform_name())
    sys.exit(2)


def run(chrome, path, width, height, script):
    """Inject `script`, load the page, and read the result back out of <title>."""
    html = open(path, encoding="utf-8").read()
    if "</body>" in html:
        html = html.replace("</body>", EMIT_JS + script + "</body>", 1)
    else:
        html += EMIT_JS + script
    tmp = os.path.join(os.path.dirname(os.path.abspath(path)), "_measure_tmp.html")
    open(tmp, "w", encoding="utf-8").write(html)

    narrow = width < MIN_WINDOW
    target = tmp
    wrapper = None
    if narrow:
        # same iframe trick capture.py uses, so the media queries are real
        wrapper = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                              encoding="utf-8")
        wrapper.write(
            "<!doctype html><meta charset='utf-8'>"
            "<style>html,body{margin:0}iframe{display:block;border:0;width:%dpx;height:%dpx}"
            "</style><iframe src=\"file://%s\" scrolling=\"no\"></iframe>"
            % (width, height, tmp))
        wrapper.close()
        target = wrapper.name

    prof = tempfile.mkdtemp(prefix="figma2html-m-")
    proc = subprocess.Popen(
        [chrome, "--headless", "--disable-gpu", "--allow-file-access-from-files",
         "--force-device-scale-factor=1", "--hide-scrollbars", "--no-first-run",
         "--virtual-time-budget=3000", "--user-data-dir=" + prof,
         "--window-size=%d,%d" % (max(width, MIN_WINDOW), height),
         "--dump-dom", "file://" + target],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        dom = proc.communicate(timeout=60)[0].decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        proc.kill()
        dom = proc.communicate()[0].decode("utf-8", "replace")

    shutil.rmtree(prof, ignore_errors=True)
    os.remove(tmp)
    if wrapper:
        os.remove(wrapper.name)

    # In the narrow path the measured page is inside the iframe, so its own
    # <title> is not the document title Chrome dumps — but --dump-dom includes
    # the iframe's serialized document, so the marker is still findable.
    m = re.search(r"M:(\{.*?\})</title>", dom, re.S)
    if not m:
        sys.stderr.write("no measurement came back — the injected script did not run\n")
        sys.exit(1)
    return json.loads(m.group(1).replace("&quot;", '"'))


SVG_SIZE = re.compile(r'<svg[^>]*?\bwidth="([0-9.]+)"[^>]*?\bheight="([0-9.]+)"', re.I)


def report_icons(rows, base_dir, tol):
    """Compare each local SVG's own dimensions against the box it renders in.

    Figma exports icons at the glyph's natural size and stamps
    preserveAspectRatio="none" on them, so an SVG forced into a box of a
    different shape is stretched — silently, and with almost no effect on the
    pixel score, because an icon is a few hundred pixels in a page of millions.
    The comparison loop cannot see this class of bug; this can.
    """
    checked = bad = 0
    for src, w, h in rows:
        head, name = None, src
        if src.startswith("data:image/svg+xml;base64,"):
            # a bundled page carries its icons inline; decode enough to read the
            # <svg> header so the check still works after bundle.py
            try:
                head = base64.b64decode(src.split(",", 1)[1][:4000] + "==").decode(
                    "utf-8", "replace")
            except Exception:
                continue
            name = "inline svg #%d" % (checked + 1)
        elif src.lower().endswith(".svg") and not src.startswith(("data:", "http")):
            path = os.path.normpath(os.path.join(base_dir, src))
            if not os.path.isfile(path):
                print("  ? %-44s (file not found)" % src)
                continue
            head = open(path, encoding="utf-8", errors="replace").read(4000)
            name = os.path.basename(src)
        else:
            continue
        m = SVG_SIZE.search(head)
        if not m or not w or not h:
            continue
        checked += 1
        nat_w, nat_h = float(m.group(1)), float(m.group(2))
        if nat_h == 0 or h == 0:
            continue
        want, got = nat_w / nat_h, float(w) / float(h)
        err = abs(got - want) / want
        if err > tol:
            bad += 1
            print("  STRETCHED %-34s natural %.5g x %.5g  rendered %.5g x %.5g  (%.0f%% off)"
                  % (name, nat_w, nat_h, w, h, err * 100))
    if bad:
        print("%d of %d SVGs are being stretched. Give each one its natural size "
              "inside a box that carries the layout size." % (bad, checked))
        return 1
    if not checked:
        # "all clear" over an empty check is the exact failure this tool exists
        # to prevent — say nothing was checked, and fail.
        print("NOTHING CHECKED — found no SVG this script could size. "
              "Wrong page, or the icons are not <img> elements. Not a pass.")
        return 2
    print("%d SVGs checked, all at their natural aspect ratio" % checked)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=4000,
                    help="window height; make it taller than the page")
    ap.add_argument("--overflow", action="store_true",
                    help="list what sticks out past the viewport instead")
    ap.add_argument("--icons", action="store_true",
                    help="flag SVGs rendered at the wrong aspect ratio")
    ap.add_argument("--tolerance", type=float, default=0.02,
                    help="allowed relative aspect-ratio error for --icons")
    ap.add_argument("--chrome", default=None)
    ap.add_argument("selectors", nargs="*", help="CSS selectors to measure")
    args = ap.parse_args()

    path = os.path.abspath(os.path.expanduser(args.file))
    if not os.path.isfile(path):
        sys.stderr.write("no such file: %s\n" % path)
        sys.exit(2)
    if not args.overflow and not args.icons and not args.selectors:
        sys.stderr.write("give some selectors, or pass --overflow / --icons\n")
        sys.exit(2)

    chrome = find_chrome(args.chrome)
    if args.overflow:
        script = OVERFLOW_JS
    elif args.icons:
        script = ICONS_JS
    else:
        script = MEASURE_JS % json.dumps(args.selectors)
    data = run(chrome, path, args.width, args.height, script)

    if data["mode"] == "icons":
        sys.exit(report_icons(data["rows"], os.path.dirname(path), args.tolerance))

    if data["mode"] == "overflow":
        print("viewport %spx   scrollWidth %spx" % (data["vw"], data["sw"]))
        if not data["rows"]:
            print("nothing overflows")
        for name, w, right in data["rows"]:
            print("  %-50s w=%-7s right=%s" % (name, w, right))
    else:
        for name, x, y, w, h in data["rows"]:
            print("%-40s x=%-7s y=%-7s w=%-9s h=%s" % (name, x, y, w, h))


if __name__ == "__main__":
    main()
