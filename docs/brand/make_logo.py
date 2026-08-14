#!/usr/bin/env python3
"""Draw the comfy-preflight wordmark and favicons, deterministically.

    python docs/brand/make_logo.py <outdir>

⚠ **THE SHIPPED WORDMARK IS NOT THIS SCRIPT'S OUTPUT.** The mark in the brand repo and in the
README is the **Director's own file**, kept beside this script as `docs/brand/readme.png`. It is
this construction with the type block balanced, and it won — which is the armature precedent
holding for a second time: that repo's commit records its generated rounds losing to the
Director's render, and the same happened here against a drawn one.

What this script still owns is **the favicon set**, which is a purpose-drawn second drawing
rather than a downscale (see `build_favicon`). `build_wordmark` is kept because it documents the
construction the shipped mark uses and because `check_composition` measures ANY candidate
against the reference — including the Director's, which it passes: 83.3% of canvas height,
margins 44/45, left 228, vertical centre 269.0 against 270.0.

**Not part of the package.** It needs Pillow, which `comfy-preflight` deliberately does not
depend on, and it lives outside `src/` so it never reaches a wheel. It is committed because a
brand asset nobody can regenerate is one nobody can correct — this repo's whole standard.

## The form is the `armature` wordmark's, matched by measurement rather than by eye

Every constant below was read off `mcp-tool-shop-org/brand/logos/armature/readme.png` with PIL:
canvas 1600x540, a vertical background gradient from (44,45,51) to (29,30,35), name text
(231,225,219), tagline (141,141,149), a 2px rule at (86,88,96), the subject occupying the left
third, and the rule drawn to the TAGLINE's width rather than the name's.

The type is flat **Segoe UI Semilight, tracked out**, exactly as the armature commit records:
the original heavy-grotesque treatment with bevel and gloss "was fighting the delicacy of the
wire", so the copper is the only thing carrying dimension. Nothing here has a bevel, a gloss or
a drop shadow.

## Why the subject is drawn rather than generated

The armature mark's own commit records that generation was **tried and lost**: the Director's
render was "better than anything the generated rounds produced." A node graph is worse for
diffusion than a figure was — it is clean geometry with exact topology, which is precisely what
a diffusion model approximates into mush. Drawing it also makes the mark reproducible and
costs nothing.

## What the subject is, and why this one

A node graph in copper wire, because that is literally what the product operates on. **One link
leaves a node and curves back into that same node** — the self-link, the founding defect: a
hand-retyped payload with `VAEDecode.samples = ["14", 0]` that a provider's `dry_run` returned
`status: validated` on. The mark carries the case the product exists for, and the offending
wire is the one lit brightest.
"""

from __future__ import annotations

import math
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

# ---- measured off logos/armature/readme.png --------------------------------------------------
W, H = 1600, 540
BG_TOP = (44, 45, 51)
BG_BOTTOM = (29, 30, 35)
NAME_RGB = (231, 225, 219)
TAGLINE_RGB = (141, 141, 149)
RULE_RGB = (86, 88, 96)

TEXT_X = 648          # armature's name/rule/tagline all start at 643-650
NAME_BASELINE = 305   # armature's name bbox bottom
RULE_Y = 340
TAGLINE_TOP = 376

COPPER_LIT = (206, 168, 150)
COPPER_MID = (168, 118, 96)
COPPER_DARK = (104, 70, 58)

SEMILIGHT = "C:/Windows/Fonts/segoeuisl.ttf"
REGULAR = "C:/Windows/Fonts/segoeui.ttf"

NAME = "comfy-preflight"
# The line the landing page leads on, so the two front doors say the same thing. An earlier
# draft read "It will run. But is it the graph you meant?" and was cut for the reason it was
# cut from the hero: it is a riddle whose "it" has no antecedent, and it makes a reader work out
# the stake instead of being told it. A completed cloud job is billed whether or not the graph
# was the one you meant, and that is the sentence worth putting on the mark.
TAGLINE = "The wrong graph bills the same."


def background() -> Image.Image:
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row
    return im


def _tracked(draw: ImageDraw.ImageDraw, xy, text, font, fill, tracking: float):
    """Draw text with letter-spacing. PIL has no tracking, so glyphs are placed one at a time."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += draw.textlength(ch, font=font) + tracking
    return x


def _tracked_width(draw: ImageDraw.ImageDraw, text, font, tracking: float) -> float:
    return sum(draw.textlength(c, font=font) for c in text) + tracking * (len(text) - 1)


def shade(t: float) -> tuple[int, int, int]:
    """Copper along a lit->dark ramp. `t` is 0 at the lit end, 1 at the dark end.

    This is the only dimension in the mark, which is the armature form's rule: flat type, and
    the copper carries the light.
    """
    if t < 0.5:
        a, b, u = COPPER_LIT, COPPER_MID, t / 0.5
    else:
        a, b, u = COPPER_MID, COPPER_DARK, (t - 0.5) / 0.5
    return tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))


def draw_graph(im: Image.Image, cx: int, cy: int, scale: float, ss: int = 4) -> None:
    """The copper node graph, supersampled so the wire keeps the armature's delicacy.

    Two drafts were thrown away here and both failures are worth the lines, because both look
    like "the curve is wrong" and neither is:

    1. Colouring each segment separately to fake an along-wire gradient produced a hairy, dotted
       wire — PIL leaves a gap at every joint when consecutive segments differ in colour.
    2. Drawing one polyline with `joint="curve"` and 120 points produced a *subtler* version of
       the same fuzz: `joint="curve"` stamps an ellipse at every interior joint, and 120 stamps
       along a short curve survive the downsample as texture rather than dissolving into it.

    So: few points (segments are long), one flat tone per wire, and no overdraw. Dimension comes
    from the tone chosen per wire and per node, which is the armature form's rule anyway — flat
    type, and the copper carries the light.
    """
    box = int(430 * scale)
    canvas = Image.new("RGBA", (box * ss, box * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    S = ss
    unit = box / 100.0  # work in a 0-100 space, then scale

    def P(pt):
        return (pt[0] * unit * S, pt[1] * unit * S)

    wire = max(2, int(round(2.3 * unit * S)))

    nw, nh = 26.0, 14.5
    # A VERTICAL spine, and the orientation is a measured decision rather than a taste one.
    # armature's figure is portrait - 344 wide by 427 tall - which is how it fills 79% of the
    # canvas height. The first layout here fanned left-to-right and was landscape, so it could
    # only ever fill ~59% before its right edge collided with the text column at x=648. A wide
    # subject in this form floats no matter how it is scaled; a tall one does not.
    #
    # Load and encode feed a sampler, which feeds the decoder, which feeds the save. The DECODER
    # is the node that links to itself, because node 14 in the recorded incident was the
    # VAEDecode.
    nodes = {
        "in":   (28, 8),
        "in2":  (72, 8),
        "mid":  (50, 34),
        "self": (50, 62),
        "out":  (50, 90),
    }

    def rect(c):
        return (c[0] - nw / 2, c[1] - nh / 2, c[0] + nw / 2, c[1] + nh / 2)

    def bez(p0, p1, p2, p3, steps=26):
        pts = []
        for i in range(steps + 1):
            u = i / steps
            pts.append((
                (1 - u) ** 3 * p0[0] + 3 * (1 - u) ** 2 * u * p1[0]
                + 3 * (1 - u) * u ** 2 * p2[0] + u ** 3 * p3[0],
                (1 - u) ** 3 * p0[1] + 3 * (1 - u) ** 2 * u * p1[1]
                + 3 * (1 - u) * u ** 2 * p2[1] + u ** 3 * p3[1],
            ))
        return pts

    def stroke(pts, base):
        """One continuous wire in one flat tone. Few joints, so the joint stamps disappear."""
        d.line([P(p) for p in pts], fill=base, width=wire, joint="curve")

    def link(a, b):
        """Bottom port of `a` to top port of `b`, with vertical control handles."""
        ax, ay = nodes[a][0], nodes[a][1] + nh / 2
        bx, by = nodes[b][0], nodes[b][1] - nh / 2
        dy = max(7.0, (by - ay) * 0.55)
        return bez((ax, ay), (ax, ay + dy), (bx, by - dy), (bx, by))

    # ---- the ordinary links, drawn first so nodes sit over them ---------------------------
    stroke(link("in", "mid"), shade(0.34))
    stroke(link("in2", "mid"), shade(0.62))
    stroke(link("mid", "self"), shade(0.26))
    stroke(link("mid", "out"), shade(0.66))

    # ---- THE SELF-LINK -------------------------------------------------------------------
    # Out of the node's RIGHT port, up and over, and back down into its own LEFT port. It is
    # drawn brightest and it is the only closed path in the mark, because it is the defect the
    # product exists for: `VAEDecode.samples = ["14", 0]`, which a provider's dry_run returned
    # `status: validated` on.
    sx, sy = nodes["self"]
    # A near-closed CIRCLE tangent to the node's right edge — standard graph notation for a
    # self-edge, and the third attempt at this shape. A wide arc over the top read as a speech
    # balloon; a short two-control bezier off the right edge collapsed into a cramped stub that
    # looked like a drawing defect rather than a loop. A circle reads as "returns to itself" at
    # any size, which matters because this is the one element carrying the mark's meaning.
    r = 14.0
    ccx, ccy = sx + nw / 2 + r * 0.72, sy
    # Sweep the LONG way round: 150 degrees down through 0 to -150, which is 300 degrees of arc
    # and leaves a clean opening where the loop meets the node. Getting this wrong is easy and
    # silent — an earlier version interpolated start -> end the SHORT way and drew a 34-degree
    # stub that rendered as a scribble beside the node rather than as a loop.
    start, sweep = math.radians(150), math.radians(-300)
    steps = 40
    loop = [
        (ccx + r * math.cos(start + sweep * i / steps),
         ccy + r * math.sin(start + sweep * i / steps))
        for i in range(steps + 1)
    ]
    stroke(loop, COPPER_LIT)

    # The arrowhead, landing back on the node it left. Its direction is taken from the path's
    # own final tangent rather than hard-coded, so it stays correct if the arc is ever retuned.
    (px_, py_), (tipx, tipy) = loop[-2], loop[-1]
    vx, vy = tipx - px_, tipy - py_
    n = math.hypot(vx, vy) or 1.0
    vx, vy = vx / n, vy / n
    head = 7.0
    for a in (math.radians(140), math.radians(-140)):
        bx = tipx + head * (vx * math.cos(a) - vy * math.sin(a))
        by = tipy + head * (vx * math.sin(a) + vy * math.cos(a))
        d.line([P((bx, by)), P((tipx, tipy))], fill=COPPER_LIT, width=wire, joint="curve")

    # ---- nodes ---------------------------------------------------------------------------
    for name, c in nodes.items():
        x0, y0, x1, y1 = rect(c)
        t = 0.06 if name == "self" else 0.30 + 0.42 * (c[1] / 100.0)
        d.rounded_rectangle(
            [P((x0, y0)), P((x1, y1))], radius=3.4 * unit * S, outline=shade(t), width=wire
        )
        for py_ in (y0, y1):
            d.ellipse(
                [P((c[0] - 1.7, py_ - 1.7)), P((c[0] + 1.7, py_ + 1.7))],
                fill=shade(max(0.0, t - 0.10)),
            )

    canvas = canvas.resize((box, box), Image.LANCZOS)

    # Crop to the DRAWN content and paste that centred, rather than centring the drawing box.
    # The box is not the picture: the self-loop and the port pips push the ink off-centre inside
    # it, which is how two earlier passes ended up 22px and then 42px above the canvas centre
    # while every constant in the file looked correct. Measuring removes the guess permanently.
    bbox = canvas.getbbox()
    if bbox:
        content = canvas.crop(bbox)
        im.paste(content, (cx - content.width // 2, cy - content.height // 2), content)


def build_wordmark() -> Image.Image:
    im = background()
    draw = ImageDraw.Draw(im)

    # The subject sits where armature's figure does: centred near x=400 in the left third.
    # Measured against the reference rather than eyeballed. armature's content fills 79.1% of
    # the canvas height with margins of 55/57 and a vertical centre of 268.5 against a canvas
    # centre of 270. An earlier pass here filled 59.3% with margins of 88/131 and sat 22px high,
    # which is what "floating in the canvas" looks like as a number.
    draw_graph(im, cx=395, cy=270, scale=1.06)

    # ---- the name: flat, tracked out, no bevel and no shadow -----------------------------
    size, tracking = 96, 6.0
    font = ImageFont.truetype(SEMILIGHT, size)
    # Fit the name inside the right column, shrinking rather than overflowing. "comfy-preflight"
    # is 15 characters against armature's 8, so the same point size would run off the canvas —
    # the form's proportions are what is being matched, not its absolute type size.
    while _tracked_width(draw, NAME, font, tracking) > (W - TEXT_X - 110) and size > 60:
        size -= 2
        font = ImageFont.truetype(SEMILIGHT, size)
    _tracked(draw, (TEXT_X, NAME_BASELINE), NAME, font, NAME_RGB, tracking)

    # ---- the tagline, and the rule drawn to ITS width (armature's rule matches the tagline)
    tag_font = ImageFont.truetype(REGULAR, 30)
    tag_track = 0.6
    tag_w = _tracked_width(draw, TAGLINE, tag_font, tag_track)
    draw.rectangle([TEXT_X - 5, RULE_Y, TEXT_X - 5 + tag_w, RULE_Y + 1], fill=RULE_RGB)
    _tracked(draw, (TEXT_X, TAGLINE_TOP + 26), TAGLINE, tag_font, TAGLINE_RGB, tag_track)

    return im


def build_favicon(px: int) -> Image.Image:
    """A purpose-drawn SECOND DRAWING, not a downscale and not the wordmark's idea shrunk.

    The armature record measured this failure and it repeated here exactly: a detailed wire mark
    at 32px "turns to a copper smudge, and thickening the strokes by dilation just makes it a
    gingerbread man." The first attempt at this icon was the wordmark's self-linking node scaled
    down, and at 16-64px it read unmistakably as a **hamburger** — a bun over a patty. Looked at
    rather than assumed, which is the only way that gets caught.

    So the icon draws a different idea from the same product: **a wire arriving at a gate and
    stopping short of it.** Three strokes, no enclosed shapes to fill in at small size, and the
    gap is the meaning — the run that did not proceed. It is the product in one glyph, and it
    cannot collapse into food.
    """
    ss = 8
    size = px * ss
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size * 0.22, fill=(36, 37, 43, 255))

    mid = size * 0.52
    w = max(2, int(size * 0.095))

    # The gate: a full-height bar, the brightest thing in the icon.
    bar_x = size * 0.70
    d.rounded_rectangle(
        [bar_x - w / 2, size * 0.20, bar_x + w / 2, size * 0.80],
        radius=w / 2, fill=COPPER_LIT,
    )

    # The wire, arriving from the left and STOPPING. The gap before the bar is the whole idea,
    # so it is sized generously — at 16px a subtle gap closes up and the glyph becomes a plus.
    d.rounded_rectangle(
        [size * 0.18, mid - w / 2, size * 0.50, mid + w / 2], radius=w / 2, fill=COPPER_MID
    )
    # One node on the wire, upstream, so it reads as a graph rather than an arrow.
    d.ellipse(
        [size * 0.13, mid - w * 1.15, size * 0.13 + w * 2.3, mid + w * 1.15], fill=COPPER_MID
    )

    return im.resize((px, px), Image.LANCZOS)


# The reference's own composition, measured off logos/armature/readme.png. These are what the
# output is CHECKED against, not just what it was built from — see `check_composition`.
REFERENCE = {
    "fills_height_pct": 79.1,
    "margin_top": 55,
    "margin_bottom": 57,
    "margin_left": 228,
    "v_centre": 268.5,
}
TOLERANCE = {"fills_height_pct": 8.0, "margin_balance": 12, "v_centre": 12, "margin_left": 45}


def check_composition(mark: Image.Image) -> list[str]:
    """Measure the OUTPUT against the reference and report what is off.

    This exists because of a defect that reached a public surface. The reference was measured to
    BUILD this mark and never re-measured to CHECK it, so a version shipped that filled 59.3% of
    the canvas height against the reference's 79.1%, with margins of 88/131 against 55/57, and
    sat 22px above centre. Every constant in this file looked correct; the composition was not.
    A person reading the rendered README caught it.

    The instrument already existed. It was simply never pointed at my own output. So it is
    pointed at it here, on every run, and the numbers are printed whether they pass or fail.
    """
    import numpy as np  # local: only the checker needs it, and only when this script runs

    a = np.asarray(mark.convert("RGB")).astype(int)
    height, width, _ = a.shape
    bg = a[:, :5, :].mean(axis=1, keepdims=True)
    ys, xs = np.where(np.abs(a - bg).sum(2) > 40)

    fills = 100 * (ys.max() - ys.min()) / height
    top, bottom, left = int(ys.min()), int(height - 1 - ys.max()), int(xs.min())
    centre = (ys.min() + ys.max()) / 2

    print(
        f"  composition: fills {fills:.1f}% tall (ref {REFERENCE['fills_height_pct']}%) | "
        f"margins T{top}/B{bottom} (ref {REFERENCE['margin_top']}/{REFERENCE['margin_bottom']}) | "
        f"L{left} (ref {REFERENCE['margin_left']}) | "
        f"v-centre {centre:.1f} (canvas {height / 2:.1f})"
    )

    problems = []
    if abs(fills - REFERENCE["fills_height_pct"]) > TOLERANCE["fills_height_pct"]:
        problems.append(
            f"fills {fills:.1f}% of canvas height; the reference fills "
            f"{REFERENCE['fills_height_pct']}% - the mark floats"
        )
    if abs(top - bottom) > TOLERANCE["margin_balance"]:
        problems.append(f"vertical margins are unbalanced: {top} top vs {bottom} bottom")
    if abs(centre - height / 2) > TOLERANCE["v_centre"]:
        problems.append(f"content centre {centre:.1f} is off the canvas centre {height / 2:.1f}")
    if abs(left - REFERENCE["margin_left"]) > TOLERANCE["margin_left"]:
        problems.append(f"left margin {left} against the reference's {REFERENCE['margin_left']}")
    return problems


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)

    mark = build_wordmark()
    mark.save(out / "readme.png")
    print(f"wrote {out / 'readme.png'}  {mark.size[0]}x{mark.size[1]}")

    problems = check_composition(mark)
    if problems:
        print("\nCOMPOSITION CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        print("\nThe asset was written but should NOT be pushed to the brand repo as-is.")
        return 1

    for px in (16, 32, 64, 180, 512):
        icon = build_favicon(px)
        icon.save(out / f"favicon-{px}.png")
    build_favicon(180).save(out / "apple-touch-icon.png")
    ico = build_favicon(64)
    ico.save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"wrote favicons + favicon.ico into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
