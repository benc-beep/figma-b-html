#!/usr/bin/env python3
"""Screenshot a local HTML file with headless Chrome, at an exact width and 1:1 pixels.

    python3 capture.py --file screens/home.html --width 1440 --out .fidelity/home/render.png

Why this and not the agent's browser pane: the pane renders local files as a
static snapshot — iframes do not load, scripts do not run, and the capture comes
back at the display's device pixel ratio. Every one of those makes a pixel
comparison meaningless. Chrome here is pinned to scale factor 1, given the exact
viewport width, and told to hide scrollbars (a 15px scrollbar shifts an entire
RTL layout sideways and shows up as a total mismatch).

Height: pass --height to capture exactly that box, which is what you want when
comparing against a Figma frame of known height. Omit it and the script captures
tall, then trims the empty background below the content and reports the real
height — that is how you find out a screen came out longer than the design.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    sys.stderr.write("capture.py needs Pillow and numpy (%s)\n" % exc)
    sys.exit(2)

TALL = 6000

# Chrome refuses to make a window narrower than this. Ask for --window-size=375
# and you get a 500px viewport — and a 375px-wide screenshot of a layout that
# was laid out at 500. The picture looks plausible and every mobile media query
# below 500 is silently skipped, which is the worst kind of wrong. Below this
# width the page is rendered inside an iframe of the exact size instead; an
# iframe has a viewport of its own, so the media queries are real.
MIN_WINDOW = 500


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


def shoot(chrome, url, width, height, out, dpr, wait_ms, deadline_s=60):
    """Render one screenshot.

    Chrome is given its own throwaway profile so a capture can never touch the
    user's real browser data. The catch, measured on macOS: with a fresh
    --user-data-dir, Chrome writes the PNG in a few seconds and then **never
    exits** — subprocess.run() waits forever on a job that is already done. So
    wait for the *file* to appear and stop growing, then kill the process. That
    also makes the script immune to any other reason Chrome might not exit.
    """
    if os.path.exists(out):
        os.remove(out)
    profile = tempfile.mkdtemp(prefix="figma2html-")
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--force-device-scale-factor=%g" % dpr,
        "--virtual-time-budget=%d" % wait_ms,
        "--user-data-dir=%s" % profile,
        "--window-size=%d,%d" % (width, height),
        "--screenshot=%s" % out,
        url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    deadline = time.time() + deadline_s
    last_size, stable = -1, 0
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if os.path.isfile(out):
            size = os.path.getsize(out)
            if size > 0 and size == last_size:
                stable += 1
                if stable >= 2:  # unchanged across ~0.6s — the write is done
                    break
            else:
                stable = 0
            last_size = size
        time.sleep(0.3)

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    shutil.rmtree(profile, ignore_errors=True)

    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        err = proc.stderr.read().decode("utf-8", "replace")[-1500:] if proc.stderr else ""
        sys.stderr.write("Chrome produced no screenshot for %s\n%s\n" % (url, err))
        sys.exit(1)
    try:
        Image.open(out).load()
    except Exception as exc:
        sys.stderr.write("screenshot is not a readable PNG (%s)\n" % exc)
        sys.exit(1)


def narrow_wrapper(url, width, height):
    """A page holding nothing but an iframe of the exact target width."""
    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#fff}"
        "iframe{display:block;border:0;width:%dpx;height:%dpx}</style>"
        "<iframe src=\"%s\" scrolling=\"no\"></iframe>" % (width, height, url)
    )
    fh = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    fh.write(html)
    fh.close()
    return fh.name


def content_height(path):
    """Height of the real content: everything above the empty background tail."""
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    if arr.shape[0] < 2:
        return arr.shape[0], False
    bottom = arr[-1]
    # a row is "empty" when every pixel matches the very bottom row
    same = (np.abs(arr - bottom).max(axis=2) <= 2).all(axis=1)
    last = arr.shape[0]
    while last > 1 and same[last - 1]:
        last -= 1
    truncated = last >= arr.shape[0] - 1
    return last, truncated


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="path to a local .html file")
    src.add_argument("--url", help="any URL Chrome can open")
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, default=0,
                    help="exact capture height; omit to auto-detect the content height")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpr", type=float, default=1.0)
    ap.add_argument("--wait", type=int, default=3000, help="render budget in ms")
    ap.add_argument("--chrome", default=None)
    args = ap.parse_args()

    chrome = find_chrome(args.chrome)
    if args.file:
        path = os.path.abspath(os.path.expanduser(args.file))
        if not os.path.isfile(path):
            sys.stderr.write("no such file: %s\n" % path)
            sys.exit(2)
        url = "file://" + path
    else:
        url = args.url

    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    narrow = args.width < MIN_WINDOW
    wrapper = None
    note = ""
    if narrow:
        note = ("rendered inside a %dpx iframe — Chrome will not open a window "
                "narrower than %dpx" % (args.width, MIN_WINDOW))

    def render(height):
        """Shoot at `height`, honouring the narrow-width iframe path."""
        nonlocal wrapper
        if not narrow:
            shoot(chrome, url, args.width, height, out, args.dpr, args.wait)
            return
        wrapper = narrow_wrapper(url, args.width, height)
        shoot(chrome, "file://" + wrapper, MIN_WINDOW, height, out, args.dpr, args.wait)
        os.remove(wrapper)
        wrapper = None
        # the iframe sits at the origin; keep only its box
        img = Image.open(out)
        img.crop((0, 0, min(args.width, img.width), img.height)).save(out)

    if args.height:
        render(args.height)
        img = Image.open(out)
        print("%s  %dx%d%s" % (out, img.width, img.height, "  [%s]" % note if note else ""))
        return

    render(TALL)
    height, truncated = content_height(out)
    img = Image.open(out)
    img.crop((0, 0, img.width, max(1, height))).save(out)
    img = Image.open(out)
    print("%s  %dx%d%s" % (out, img.width, img.height, "  [%s]" % note if note else ""))
    if truncated:
        print("WARNING: content reaches the bottom of a %dpx capture — the page is "
              "probably taller. Re-run with an explicit --height." % TALL)


if __name__ == "__main__":
    main()
