"""Classify the SMALL drawings to identify 5m markers, rectangles, spokes etc."""
import fitz, math
from collections import Counter

EPS = 0.01
def polylines_from_drawing(items):
    out = []; cur = []
    for op in items:
        if op[0] == 'l':
            a, b = op[1], op[2]
            if not cur:
                cur = [(a.x, a.y), (b.x, b.y)]
            else:
                last = cur[-1]
                if abs(last[0]-a.x) < EPS and abs(last[1]-a.y) < EPS:
                    cur.append((b.x, b.y))
                else:
                    out.append(cur); cur = [(a.x, a.y), (b.x, b.y)]
    if cur: out.append(cur)
    return out

doc = fitz.open("processing/Spiral_5m sections and spokes.pdf")
drawings = doc[0].get_drawings()
print(f"total drawings: {len(drawings)}")

cx, cy = 387.8637, 529.4637

# Classify each drawing by:
#  - number of items
#  - bbox size (small vs spans most of page)
#  - is it radial or tangential or rectangular?
size_counter = Counter()
samples_by_items = {}
for d in drawings:
    items = d.get("items", [])
    n = len(items)
    size_counter[n] += 1
    if n not in samples_by_items:
        samples_by_items[n] = []
    if len(samples_by_items[n]) < 5:
        samples_by_items[n].append(d)

print("\nDrawing item-count distribution:")
for n in sorted(size_counter):
    print(f"  {n:5d} items -> {size_counter[n]:5d} drawings")

# Look at samples with 2, 3, 4 items
for n in [2, 3, 4, 8, 27, 28, 30, 36]:
    if n not in samples_by_items: continue
    print(f"\n=== Sample drawings with {n} items ===")
    for k, d in enumerate(samples_by_items[n][:3]):
        items = d.get("items", [])
        r = d.get("rect")
        print(f"--- sample {k} rect={r}")
        for it in items:
            print("   ", it[0], "from", (round(it[1].x,2), round(it[1].y,2)), "to", (round(it[2].x,2), round(it[2].y,2)))

# Statistics of single-segment drawings:
# length and orientation (radial vs tangential vs other)
single_polys = []
for d in drawings:
    if len(d.get("items", [])) == 1 and d["items"][0][0] == 'l':
        a, b = d["items"][0][1], d["items"][0][2]
        single_polys.append(((a.x, a.y), (b.x, b.y)))

print(f"\nsingle-segment count: {len(single_polys)}")

# Compute length distribution & orientation
lens = []
radial_score = []  # cos(angle between segment dir and radial dir)
for (a, b) in single_polys:
    dx = b[0]-a[0]; dy = b[1]-a[1]
    L = math.hypot(dx, dy)
    lens.append(L)
    mx = (a[0]+b[0])/2 - cx; my = (a[1]+b[1])/2 - cy
    R = math.hypot(mx, my)
    if R > 0 and L > 0:
        # radial unit vec
        rx, ry = mx/R, my/R
        sx, sy = dx/L, dy/L
        radial_score.append(abs(rx*sx + ry*sy))
    else:
        radial_score.append(0)

# histogram
def hist(vals, bins):
    h = Counter()
    for v in vals:
        for i, b in enumerate(bins):
            if v < b:
                h[i] += 1
                break
        else:
            h[len(bins)] += 1
    return h

len_bins = [1, 2, 3, 4, 5, 8, 12, 20, 50, 100, 500]
print("single-seg lengths:", dict(hist(lens, len_bins)))
print(f"  edges: {len_bins}")

# Radial score (1 = pointing radially, 0 = perpendicular/tangential)
rad_bins = [0.1, 0.3, 0.6, 0.9, 1.01]
print("single-seg radial scores:", dict(hist(radial_score, rad_bins)))
print(f"  bin edges (radial = 1.0): {rad_bins}")
