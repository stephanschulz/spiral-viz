"""Analyse the rectangle-like drawings: how many per turn? Position distribution?"""
import fitz, math, json

PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
drawings = doc[0].get_drawings()

with open("processing/tmp/spiral_fit.json") as f:
    fit = json.load(f)
cx, cy = fit["center"]
a_idx, b_idx = fit["a_per_index"], fit["b_per_index"]
phi0 = fit["phi0_rad"]

# Rectangle-like drawings = 27..37 items (from earlier analysis)
rects = []
for d in drawings:
    n = len(d.get("items", []))
    if 27 <= n <= 37 and d.get("type") == "s":
        r = d["rect"]
        rx = (r.x0 + r.x1) / 2
        ry = (r.y0 + r.y1) / 2
        rects.append((rx, ry, (r.x1-r.x0), (r.y1-r.y0)))

print(f"rectangle candidates: {len(rects)}")

# For each rectangle, compute polar coords and figure out which TURN it's on
# k_index = (r - a_idx) / b_idx  (the corridor turn index)
turns_per_rect = []
for x, y, w, h in rects:
    th = math.atan2(y-cy, x-cx)
    r = math.hypot(x-cx, y-cy)
    k = (r - a_idx) / b_idx
    turns_per_rect.append((k, th, r, x, y, w, h))

turns_per_rect.sort(key=lambda t: t[0])
print("\nrectangles sorted by turn index k:")
print(f"{'idx':>4} {'k':>6} {'r':>7} {'theta_deg':>10} {'(x,y)':>16}")
for i, (k, th, r, x, y, w, h) in enumerate(turns_per_rect):
    print(f"  {i:>3} {k:6.2f} {r:7.2f} {math.degrees(th):10.2f}  ({x:7.2f},{y:7.2f})")

# Count rectangles per integer turn
from collections import Counter
turn_counter = Counter()
for k, *_ in turns_per_rect:
    turn_counter[round(k)] += 1
print("\nrectangles per (rounded) turn index:")
for ti in sorted(turn_counter):
    c = turn_counter[ti]
    circ_pts = 2 * math.pi * (a_idx + b_idx * ti)
    print(f"  turn {ti:>3}: {c:>2} rectangles, turn circumference = {circ_pts:7.2f} pts, "
          f"avg spacing = {(circ_pts / c if c else 0):7.2f} pts")
