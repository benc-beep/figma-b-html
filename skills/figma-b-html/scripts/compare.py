#!/usr/bin/env python3
"""Pixel-compare a rendered HTML screenshot against the Figma reference.

The point of this script is to replace "looks about right" with a number, and —
more usefully — to say *where* and *what kind* of difference it found, so the
next fix is targeted instead of a guess.

    python3 compare.py --reference figma.png --render browser.png --out .fidelity/home

Writes into --out:
    diff.png        red heatmap of the differing pixels
    side-by-side.png  reference | render | diff, labelled
    report.json     the numbers

Prints a short human summary and the JSON path. Exit code is always 0 — a low
score is a finding, not a crash.
"""

import argparse
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(
        "compare.py needs Pillow and numpy: python3 -m pip install pillow numpy\n"
        "(%s)\n" % exc
    )
    sys.exit(2)


PAD = (255, 0, 255)  # magenta: padding is never a real colour, so it reads as "missing"


def load_rgb(path):
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def normalise_scale(ref, render):
    """Bring the render to the reference's width.

    A Browser-pane screenshot on a Retina display comes back at 2x, and the
    Figma render is capped by maxDimension. Neither is a design difference, so
    scale it away before measuring — but say that we did.
    """
    note = None
    if render.width != ref.width:
        ratio = ref.width / float(render.width)
        new_h = max(1, int(round(render.height * ratio)))
        render = render.resize((ref.width, new_h), Image.LANCZOS)
        note = "render rescaled by %.3f to match reference width %dpx" % (ratio, ref.width)
    return render, note


def pad_to(img, width, height):
    if img.width == width and img.height == height:
        return img
    canvas = Image.new("RGB", (width, height), PAD)
    canvas.paste(img, (0, 0))
    return canvas


def best_vertical_offset(a, b, limit=40):
    """Find the vertical shift that best aligns b onto a.

    This exists because a single wrong margin near the top of the page shifts
    everything below it, and the raw score then reports dozens of unrelated
    differences. Knowing "it is all 14px low" is one fix, not thirty.

    Works on a downscaled greyscale so it stays cheap.
    """
    scale = max(1, a.shape[1] // 320)
    ga = a[::scale, ::scale].astype(np.float32).mean(axis=2)
    gb = b[::scale, ::scale].astype(np.float32).mean(axis=2)
    limit_s = max(1, limit // scale)

    best_off, best_err = 0, None
    for off in range(-limit_s, limit_s + 1):
        if off >= 0:
            top_a, top_b = ga[off:], gb[: len(gb) - off if off else len(gb)]
        else:
            top_a, top_b = ga[: len(ga) + off], gb[-off:]
        n = min(len(top_a), len(top_b))
        if n < 8:
            continue
        err = float(np.abs(top_a[:n] - top_b[:n]).mean())
        if best_err is None or err < best_err:
            best_off, best_err = off * scale, err
    return best_off, best_err


def largest_region(mask, block=8, fill=0.25):
    """The biggest *contiguous* patch of difference, as a pixel box.

    This is the number that decides whether a mismatch matters. A total of 1.2%
    spread evenly is antialiasing on text and a gradient band; the same 1.2%
    concentrated in one 200x300 box is a missing image or a wrong colour. The
    percentage alone cannot tell those apart, so measure the shape too.

    Works on a coarse grid: a block counts as different only when a quarter of
    its pixels are, which drops isolated antialiasing pixels before they can
    chain unrelated areas together.
    """
    h, w = mask.shape
    bh, bw = h // block, w // block
    if bh < 1 or bw < 1:
        return None
    grid = mask[: bh * block, : bw * block]
    grid = grid.reshape(bh, block, bw, block).mean(axis=(1, 3)) >= fill
    if not grid.any():
        return None

    seen = np.zeros_like(grid, dtype=bool)
    best = None
    for sy in range(bh):
        for sx in range(bw):
            if not grid[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = True
            cells = 0
            y0 = y1 = sy
            x0 = x1 = sx
            while stack:
                cy, cx = stack.pop()
                cells += 1
                if cy < y0: y0 = cy
                if cy > y1: y1 = cy
                if cx < x0: x0 = cx
                if cx > x1: x1 = cx
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < bh and 0 <= nx < bw and grid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if best is None or cells > best[0]:
                best = (cells, y0, y1, x0, x1)

    cells, y0, y1, x0, x1 = best
    return {
        "x": x0 * block,
        "y": y0 * block,
        "w": (x1 - x0 + 1) * block,
        "h": (y1 - y0 + 1) * block,
        "area_px": cells * block * block,
        "pct_of_page": round(cells * block * block / float(h * w) * 100.0, 3),
    }


def band_report(mask, bands, height):
    """Worst horizontal strips, so the agent knows where to look."""
    rows = []
    step = max(1, height // bands)
    for start in range(0, height, step):
        strip = mask[start : start + step]
        if strip.size == 0:
            continue
        pct = float(strip.mean()) * 100.0
        rows.append({"y_from": start, "y_to": min(start + step, height), "diff_pct": round(pct, 2)})
    rows.sort(key=lambda r: -r["diff_pct"])
    return rows


def label(img, text):
    out = Image.new("RGB", (img.width, img.height + 24), (255, 255, 255))
    out.paste(img, (0, 24))
    ImageDraw.Draw(out).text((6, 7), text, fill=(20, 20, 20))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True, help="PNG exported from Figma")
    ap.add_argument("--render", required=True, help="PNG screenshot of the HTML")
    ap.add_argument("--out", required=True, help="directory for diff.png / report.json")
    ap.add_argument("--tolerance", type=int, default=12,
                    help="per-channel difference below this is not counted (anti-aliasing)")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="diff_pct at or below this counts as a pass")
    ap.add_argument("--bands", type=int, default=20)
    args = ap.parse_args()

    for p in (args.reference, args.render):
        if not os.path.isfile(p):
            sys.stderr.write("no such file: %s\n" % p)
            sys.exit(2)

    os.makedirs(args.out, exist_ok=True)

    ref = load_rgb(args.reference)
    render = load_rgb(args.render)
    render, scale_note = normalise_scale(ref, render)

    height_delta = render.height - ref.height
    canvas_h = max(ref.height, render.height)
    ref_p = pad_to(ref, ref.width, canvas_h)
    ren_p = pad_to(render, ref.width, canvas_h)

    a = np.asarray(ref_p, dtype=np.int16)
    b = np.asarray(ren_p, dtype=np.int16)

    delta = np.abs(a - b)
    per_pixel = delta.max(axis=2)
    mask = per_pixel > args.tolerance

    diff_pct = float(mask.mean()) * 100.0
    mae = float(delta.mean())

    offset, _ = best_vertical_offset(a, b)
    if offset < 0:
        offset_hint = "HTML content sits about %dpx LOWER than Figma" % abs(offset)
    elif offset > 0:
        offset_hint = "HTML content sits about %dpx HIGHER than Figma" % offset
    else:
        offset_hint = "no global vertical offset"

    total_diff_px = int(mask.sum())
    region = largest_region(mask)
    if total_diff_px == 0:
        shape, shape_hint = "none", "no difference to locate"
    elif region is None:
        # differences exist but no block is a quarter different — that is the
        # signature of noise scattered across the whole page, not a broken element
        shape = "diffuse"
        shape_hint = ("the difference is scattered across the page with no solid "
                      "patch anywhere — almost always a substituted font or "
                      "antialiasing. Confirm the font is loading before anything else.")
    elif region["area_px"] >= 2000 and region["area_px"] >= 0.30 * total_diff_px:
        shape = "concentrated"
        shape_hint = ("the difference is concentrated in one %dx%d box at x=%d y=%d — "
                      "look there first. A block this solid is usually a missing "
                      "element, an unloaded image, or a wrong fill."
                      % (region["w"], region["h"], region["x"], region["y"]))
    else:
        shape = "diffuse"
        shape_hint = ("the difference is spread out rather than in one place — "
                      "typically text antialiasing, a gradient, or a substituted font. "
                      "Check the font before chasing individual elements.")

    # heatmap: dim the reference, paint the differences red
    heat = (np.asarray(ref_p, dtype=np.float32) * 0.25).astype(np.uint8)
    heat[mask] = (255, 40, 40)
    diff_img = Image.fromarray(heat)
    if region and shape == "concentrated":
        ImageDraw.Draw(diff_img).rectangle(
            [region["x"], region["y"],
             region["x"] + region["w"] - 1, region["y"] + region["h"] - 1],
            outline=(255, 220, 0), width=3)
    diff_path = os.path.join(args.out, "diff.png")
    diff_img.save(diff_path)

    panels = [label(ref_p, "FIGMA"), label(ren_p, "HTML"), label(diff_img, "DIFF")]
    gap = 12
    sbs = Image.new("RGB",
                    (sum(p.width for p in panels) + gap * (len(panels) - 1), panels[0].height),
                    (245, 245, 245))
    x = 0
    for p in panels:
        sbs.paste(p, (x, 0))
        x += p.width + gap
    sbs_path = os.path.join(args.out, "side-by-side.png")
    sbs.save(sbs_path)

    report = {
        "reference": os.path.abspath(args.reference),
        "render": os.path.abspath(args.render),
        "reference_size": [ref.width, ref.height],
        "render_size": [render.width, render.height],
        "height_delta_px": height_delta,
        "diff_pct": round(diff_pct, 3),
        "mean_abs_error": round(mae, 3),
        "tolerance": args.tolerance,
        "threshold": args.threshold,
        "pass": diff_pct <= args.threshold and abs(height_delta) <= 2,
        "likely_vertical_offset_px": offset,
        "offset_hint": offset_hint,
        "diff_shape": shape,
        "diff_shape_hint": shape_hint,
        "largest_region": region,
        "worst_bands": band_report(mask, args.bands, canvas_h)[:5],
        "scale_note": scale_note,
        "diff_image": os.path.abspath(diff_path),
        "side_by_side": os.path.abspath(sbs_path),
    }
    report_path = os.path.join(args.out, "report.json")
    with open(report_path, "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print("diff %.3f%%  (pass<=%.2f%%)   mae %.2f" % (diff_pct, args.threshold, mae))
    if height_delta:
        print("height: HTML is %+dpx vs Figma" % height_delta)
    if offset:
        print("NOTE: %s — fix that first, one wrong margin near the top "
              "inflates every number below it" % report["offset_hint"])
    if scale_note:
        print("NOTE: %s" % scale_note)
        print("      resampling adds a difference of its own. Capture the render at "
              "the reference's own pixel width for a clean reading.")
    if shape != "none":
        print("shape: %s — %s" % (shape.upper(), shape_hint))
    bands = [b for b in report["worst_bands"] if b["diff_pct"] > 0]
    if bands:
        print("worst bands (y-range, % differing):")
        for band in bands:
            print("  %5d-%-5d  %6.2f%%" % (band["y_from"], band["y_to"], band["diff_pct"]))
    print(report_path)


if __name__ == "__main__":
    main()
