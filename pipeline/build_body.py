"""Thylacine drawn to a measured proportion sheet (3 reference agents, ~25 usable images).

Units: SH = shoulder (withers) height = 1. x runs from the nose (0) toward the tail,
y is height above the ground. Head outline from pipeline/head_profile.json.
Sheet (live photos / mounts / skeletons, reconciled):
  body chest->tail root 1.45, depth 0.445, backline level (rump 1.0), head 0.42 pitched
  ~18 deg nose-down, ear ~0.11, tail 1.0 stiff and thick at the root, carried ~18 deg down,
  14 stripes from ~1/4 back from the withers to the tail root, short in front, long and
  wide over the rump, wrapping back onto the thigh; none on head, neck, shoulder, legs.
  Legs (rig): fore 0.31/0.315/0.11 from shoulder joint 0.68; hind 0.38/0.41/0.17 from hip 0.84.
Encoding per grid cell: 0 empty, 1..191 tone (pale..dark), 255 dark mark (eye, nose, gape).
"""
import json, base64, math, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DATA_JS = os.path.join(ROOT, "roto-data.js")
import numpy as np
from PIL import Image, ImageDraw

SHG = 80                       # grid units per shoulder height
X0, YTOP = -0.06, 1.30         # grid origin in SH units
W, H = 256, 106
LEGCUT = 0.13
GY = round((YTOP - LEGCUT) * SHG)   # ground row: legs ~15% shorter than the measured sheet (panel r12)
SS = 4                         # supersampling for coverage

def G(x, y): return ((x - X0) * SHG, (YTOP - y) * SHG)

# ---------------------------------------------------------------- head
hp = json.load(open(os.path.join(HERE, "head_profile.json"), encoding="utf-8"))
HL, PITCH = 0.51, math.radians(18)
OCC = (0.43, 0.845)             # crown ~0.08 SH below the withers (critic C, r35/r49)
NX = OCC[0] - HL * math.cos(PITCH); NY = OCC[1] - HL * math.sin(PITCH)
def head_pt(u, v):             # head frame -> body frame (head faces -x, rear tilted up)
    c, s = math.cos(PITCH), math.sin(PITCH)
    return (NX + HL * (u * c - v * s), NY + HL * (u * s + v * c))
# ears: live photos read bigger than the shrunken taxidermy ears the outline came from -> x1.5 tall, x1.25 wide
EAR = {"ear_front_edge", "ear_tip_front", "ear_tip", "ear_tip_back", "ear_back_edge"}
EAR_PTS = [(0.85, 0.14), (0.86, 0.28), (0.88, 0.36), (0.92, 0.41), (0.975, 0.42), (1.02, 0.39), (1.05, 0.32), (1.07, 0.23), (1.08, 0.14)]   # rounded triangle ~3 wide x 4 tall   # short, broad, rounded (~3x3 cells)   # rounded triangle, ~0.25 L tall, 1-cell tip
def ear_pt(p):
    if p["name"] not in EAR: return (p["x"], p["y"])
    return (0.95 + (p["x"] - 0.95) * 1.25, 0.22 + (p["y"] - 0.22) * 1.2)   # broad-based, rounded, erect
OUT = []
for p in hp["outline"]:
    if p["name"] == "ear_front_edge": OUT += EAR_PTS
    elif p["name"] not in EAR: OUT.append((p["x"], p["y"]))
# a deeper cranium and jaw: the back half of the head is a box, not a cone (critic, r06/r34)
OUT = [(u, v * (1 + 0.32 * max(0.0, min(1.0, (u - 0.25) / 0.5))) if v < 0 else v) for u, v in OUT]
OUT = [(u, v * (1 + 0.30 * max(0.0, 1 - u / 0.40))) for u, v in OUT]   # blunt square muzzle tip   # blunt muzzle, only a slight taper
head_poly = [head_pt(u, v) for u, v in OUT]

# ---------------------------------------------------------------- trunk (clockwise from the nape)
# nape dips behind the ears, rises to slightly low withers; backline climbs to a high, rounded rump
SQ = lambda x: x if x < 0.72 else 0.72 + (x - 0.72) * 0.93   # trunk 12% shorter behind the shoulder (critic: 1.7x SH nose->tail root)
top = [(0.40, 0.825), (0.47, 0.84), (0.55, 0.875), (0.63, 0.925), (0.70, 0.945), (0.82, 0.952), (0.92, 0.952), (1.12, 0.952),   # nape dips behind the ears, then rises to the withers
       (1.35, 0.952), (1.50, 0.952), (1.62, 0.951), (1.70, 0.946), (1.78, 0.932), (1.86, 0.914), (1.92, 0.900)]   # croup rounds off into the tail
rear = [(1.95, 0.84), (1.96, 0.75), (1.92, 0.64), (1.85, 0.55), (1.76, 0.50)]   # tail root widens into the buttock: no notch
# deep chest (0.46 SH), loin tucked up to ~0.28 SH deep just before the stifle; throat notch under the jaw
under = [(1.70, 0.50), (1.62, 0.56), (1.52, 0.70), (1.42, 0.725), (1.28, 0.68), (1.12, 0.57), (0.92, 0.495),
         (0.80, 0.485), (0.68, 0.53), (0.60, 0.61), (0.54, 0.66), (0.50, 0.69), (0.45, 0.705), (0.38, 0.70), (0.33, 0.71)]   # neck front sits behind the jaw angle: throat notch
trunk_poly = [(SQ(x), y) for x, y in top + rear + under]

def catmull(pts, closed=True, n=8):
    out = []; m = len(pts)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0, p1, p2, p3 = pts[(i - 1) % m], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out

# ---------------------------------------------------------------- tail: stiff rod, thick for its first third
# top edge continues the backline from the top of the rump: root centre = rump top - root radius
TA, TLEN = math.radians(7), 1.12      # walking carriage, ~0.95-1.05 SH (critic C, measurements)
TR0, TR1 = 0.11, 0.022
T0 = (SQ(1.74), 0.951 - 0.05 - TR0)        # tail top edge starts at the croup top
def tail_c(t):
    return (T0[0] + TLEN * t * math.cos(TA), T0[1] - TLEN * t * math.sin(TA))
def tail_r(t): return (TR0 - 0.085 * np.asarray(t)) * np.minimum(1.0, (np.clip(1 - np.asarray(t), 0, 1) / 0.12) ** 0.6)   # ~5 rows at the root, steady taper, pointed tip

# ---------------------------------------------------------------- rasterise
def raster(draw_fn):
    im = Image.new("L", (W * SS, H * SS), 0); d = ImageDraw.Draw(im)
    draw_fn(d, lambda x, y: tuple(c * SS for c in G(x, y)))
    a = np.asarray(im, dtype=np.float32) / 255
    return a.reshape(H, SS, W, SS).mean(axis=(1, 3))
def poly_fn(pts): return lambda d, P: d.polygon([P(*p) for p in pts], fill=255)
def tail_fn(d, P):
    for t in np.linspace(0, 1, 120):
        cx, cy = P(*tail_c(t)); r = tail_r(t) * SHG * SS
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)

cov_head = raster(poly_fn(head_poly))
# far ear: a cell behind and lower than the near one, a tone darker (two ears, not a horn)
cov_fe = raster(poly_fn([head_pt(u + 0.27, v - 0.05) for u, v in EAR_PTS + [(1.05, 0.12)]]))
# far ear dropped (all 3 critics: reads as a horn/tab on the neck)
cov_fe = cov_fe * 0
cov_trunk = raster(poly_fn(catmull(trunk_poly)))
cov_tail = raster(tail_fn)
cov = np.clip(cov_head + cov_trunk, 0, 1)   # tail drawn live by the page (ROTO.tailA)        # sum, not max: no sliver gaps where two shapes meet
M = cov >= 0.5

# ---------------------------------------------------------------- coat tone (0 pale .. 1 dark)
YY, XX = np.mgrid[0:H, 0:W]
xs = X0 + (XX + 0.5) / SHG; ys = YTOP - (YY + 0.5) / SHG
# dorsal-ventral position per column: 0 at the belly edge, 1 at the backline
d = np.zeros((H, W))
for c in range(W):
    rr = np.nonzero(M[:, c])[0]
    if len(rr): d[rr, c] = (rr.max() - rr) / max(1, rr.max() - rr.min())
sm = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
tone = 0.0 + 0.46 * sm(0.18, 0.90, d) + 0.30 * sm(0.86, 1.0, d)                    # coat stays light-to-mid: the stripes alone carry the dark (value separation)                     # pale belly -> darker greyish-brown back (photos: darker overall)
tone += 0.025 * (np.sin(xs * 23.0 + ys * 9.0) * np.sin(xs * 7.0 - ys * 17.0))   # faint fur variation
# head, in its own frame
c, s = math.cos(PITCH), math.sin(PITCH)
hu = ((xs - NX) * c + (ys - NY) * s) / HL; hv = (-(xs - NX) * s + (ys - NY) * c) / HL
inH = cov_head >= 0.5
ht = 0.04 + 0.46 * sm(-0.05, 0.28, hv)                      # pale lips and cheek, darker bridge and crown
ex, ey = 0.57, 0.07               # eye at 0.62 L, just below the brow (head_profile)
ring = np.hypot(hu - ex, hv - ey)
ht = np.where((ring < 0.20), ht - 0.24, ht)               # pale patch round the eye
earz = (hu > 0.80) & (hv > 0.22)
ht = np.where(earz, 0.30, ht)                             # ear: paler inside ...
eb = earz.copy()                                          # ... darker rim (cells touching the outside)
inHb = cov_head >= 0.5
rim = inHb & ~(np.roll(inHb, 1, 0) & np.roll(inHb, -1, 0) & np.roll(inHb, 1, 1) & np.roll(inHb, -1, 1)
               & np.roll(inHb, 2, 0) & np.roll(inHb, 2, 1) & np.roll(inHb, -2, 1))
ht = np.where(earz & rim, 0.78, ht)
fe_only = (cov_fe >= 0.5) & ~(raster(poly_fn(head_poly)) >= 0.5)
ht = np.where(fe_only, 0.72, ht)
wh = np.where(inH, 1 - sm(0.70, 1.02, hu), 0) * np.where(hv > 0.2, 1, 1)   # blend head into neck: no seam
wh = np.where(inH & earz, 1, wh)
tone = tone * (1 - wh) + ht * wh
# tail: the coat colour of the rump, darkening toward the tip
tt = np.clip(((xs - T0[0]) * math.cos(TA) - (ys - T0[1]) * math.sin(TA)) / TLEN, 0, 1)
inT = (cov_tail >= 0.5) & (cov_trunk < 0.5)
# tail: dorsal shading continues from the rump (top edge darker), darkening toward the tip
tcd = -((xs - T0[0]) * math.sin(TA) + (ys - T0[1]) * math.cos(TA)) / np.maximum(tail_r(tt) , 1e-3)   # -1 top .. +1 underside
tone = np.where(inT, 0.40 + 0.18 * np.clip(-tcd, 0, 1) - 0.12 * np.clip(tcd, 0, 1) + 0.16 * tt ** 1.5, tone)
tone = np.clip(tone, 0, 1)
v = (1 + np.round(tone * 190)).astype(np.int32)

# ---------------------------------------------------------------- face marks
def disc(cx, cy, r): gx, gy = G(cx, cy); return (XX + 0.5 - gx) ** 2 + (YY + 0.5 - gy) ** 2 <= (r * SHG) ** 2
eye = disc(*head_pt(ex, ey), 0.013)                       # one cell, set in a pale ring
nose = inH & (hu < 0.045) & (hv > -0.06)                  # one dark nose pad
gape = np.zeros_like(M)
ml = hp["features"]["mouth_line"]
for (u0, v0), (u1, v1) in zip(ml, ml[1:]):
    for t in np.linspace(0, 1, 40):
        u_ = u0 + (u1 - u0) * t
        if 0.10 < u_ < 0.68: gape |= disc(*head_pt(u_, v0 + (v1 - v0) * t), 0.010)
XS0, XS1 = SQ(1.30), SQ(1.84)            # stripe span (also used for the bars below)
zw = sm(XS0 - 0.12, XS0 + 0.05, xs) * (1 - sm(XS1 + 0.05, XS1 + 0.2, xs)) * sm(0.25, 0.5, d) * (1 - 0.5 * sm(0.80, 1.0, d)) * (cov_trunk >= 0.5) * ~inT   # soft-edged
v = np.where((v > 0) & (v < 255), np.maximum(1, np.round(v - 60 * zw)).astype(np.int32), v)
v[gape & M] = 191                                         # mouth line: dark, runs to below the eye
# eye and nose are placed by the renderer as exactly one cell each (meta eye/nose): never two, never lost
v[~M] = 0

# ---------------------------------------------------------------- stripes as vector bars [xTop,yTop,xBot,yBot,width] (grid)
def back_y(x):                 # backline height at x (from the mask)
    col = int(round((x - X0) * SHG)); rr = np.nonzero(M[:, col])[0]
    return YTOP - rr.min() / SHG
def belly_y(x):
    col = int(round((x - X0) * SHG)); rr = np.nonzero(cov_trunk[:, col] >= 0.5)[0]
    return YTOP - (rr.max() + 1) / SHG
bars = []
# 13 bars from ~35% of the way withers->rump to just ahead of the tail root (refs: mid-back start, r16/r49/r58)
N = 9
XP = []
for i in range(N):
    f = i / (N - 1)                                         # 0 front .. 1 tail root
    JIT = [0, 0.12, -0.1, 0.12, -0.08, 0.1, -0.1, 0.06, 0]
    x = XS0 + (XS1 - XS0) * (f ** 0.92 + JIT[i] / (N - 1) * 0.8)   # crowd onto the rump, uneven gaps
    XP.append(x)
    yt = back_y(x) - 0.012                                   # start inside the coat: a stripe never lifts the backline
    length = (0.12 + 0.30 * f ** 1.4)                        # SH: 2 rows at the front, ~0.43 SH over the hip, onto the thigh
    length = min(length, (0.20 + 0.40 * f) * (back_y(x) - belly_y(x)))
    lean = 0.0                                              # vertical: any lean snaps into broken dashes at this cell size                # near-upright: leaning bars become cell staircases (hatching)
    width = 0.03 + 0.04 * f ** 1.2
    gx0, gy0 = G(x, yt); gx1, gy1 = G(x + lean * length, yt - length)
    bars.append([round(gx0, 2), round(gy0, 2), round(gx1, 2), round(gy1, 2), round(width * SHG, 2)])
# two bands across the tail root
for tq in (0.13, 0.23, 0.33):
    (cx_, cy_), r_ = tail_c(tq), tail_r(tq)
    gx0, gy0 = G(cx_, cy_ + r_ - 0.01)
    gx1, gy1 = G(cx_, cy_ - r_ * 0.25)
    bars.append([round(gx0, 2), round(gy0, 2), round(gx1, 2), round(gy1, 2), round(0.05 * SHG, 2)])

# ---------------------------------------------------------------- rig (grid units)
def gl(xy): return [round(c, 2) for c in G(*xy)]
k = SHG
legs = {
    # legs about twice as thick as before (critic: 0.10-0.12 SH in r35); broad thigh wedge at the hip
    "fore": {"root": gl((0.74, 0.68)), "L": [0.24 * k, 0.25 * k, 0.09 * k], "R": [0.068 * k, 0.05 * k, 0.04 * k, 0.045 * k]},
    "hind": {"root": gl((SQ(1.66), 0.74)), "L": [0.23 * k, 0.22 * k, 0.27 * k], "R": [0.15 * k, 0.065 * k, 0.034 * k, 0.045 * k]},
}
for i, b in enumerate(bars):          # per-bar clearance to its nearest neighbour (grid units): renderer widens a band only where a gap still fits
    if i < N:
        nb = [abs(XP[i] - XP[j]) for j in (i - 1, i + 1) if 0 <= j < N]
        b.append(round(min(nb) * SHG, 2))
    else:
        b.append(round(0.08 * SHG, 2))
meta = {"tailA": [round(G(*T0)[0], 3), round(G(*T0)[1], 3), round(TA, 5), round(TLEN * SHG, 3), [round(float(tail_r(t)) * SHG, 3) for t in np.linspace(0, 1, 33)]], "ntail": 3, "tail": [round(c, 2) for c in G(*T0)] + [round(TLEN * SHG, 2)], "eye": [round(c, 2) for c in G(*head_pt(ex, ey))], "nose": [round(c, 2) for c in G(*head_pt(0.025, 0.02))], "sgap": round((XS1 - XS0) / (N - 1), 4), "stripes": bars, "legs": legs, "w": W, "h": H, "ax": round(G(1.2, 0)[0], 2), "gy": GY, "sh": SHG,
        "src": "drawn to a proportion sheet measured from ~25 reference images (live photos, mounts, skeletons)"}
with open(DATA_JS, "w", encoding="utf-8") as fo:
    fo.write("// Thylacine drawn to a measured proportion sheet (live photos, museum mounts, skeletons).\n")
    fo.write("const ROTO = " + json.dumps(meta) + ";\nROTO.frames = " + json.dumps([base64.b64encode(v.astype(np.uint8).tobytes()).decode()]) + ";\n")

# preview: body + stripes + legs at rest, 6x
P = 6
prev = Image.new("RGB", (W * P, H * P), (255, 255, 255)); dr = ImageDraw.Draw(prev)
for y in range(H):
    for x in range(W):
        if v[y, x] == 255: col = (30, 22, 16)
        elif v[y, x]: t_ = (v[y, x] - 1) / 190; col = tuple(int(a + (b - a) * t_) for a, b in zip((240, 226, 196), (140, 100, 62)))
        else: continue
        dr.rectangle([x * P, y * P, x * P + P - 1, y * P + P - 1], fill=col)
for b in bars:
    dr.line([b[0] * P, b[1] * P, b[2] * P, b[3] * P], fill=(50, 34, 24), width=max(1, int(b[4] * P)))
for nm, Lg in legs.items():
    rx, ry = Lg["root"]
    dr.ellipse([rx * P - 4, ry * P - 4, rx * P + 4, ry * P + 4], outline=(200, 0, 0))
dr.line([0, GY * P, W * P, GY * P], fill=(180, 180, 180))
prev.save(os.path.join(HERE, "preview.png"))
print("grid", W, H, "bars", len(bars), "bytes", os.path.getsize(DATA_JS))
