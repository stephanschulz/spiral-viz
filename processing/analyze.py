"""Chain segments into polylines, classify them, find centerline."""
import fitz, math, json
from collections import defaultdict, Counter

PDF = "processing/Spiral_5m sections and spokes.pdf"

doc = fitz.open(PDF)
page = doc[0]
drawings = page.get_drawings()

# Bounding box of page strokes
xs, ys = [], []
for d in drawings:
    r = d.get("rect")
    if r is None:
        continue
    xs += [r.x0, r.x1]
    ys += [r.y0, r.y1]
print("Drawings bbox: x=[%.2f, %.2f] y=[%.2f, %.2f]" % (min(xs), max(xs), min(ys), max(ys)))

# Each "drawing" item is already a continuous polyline (its line ops chain end-to-end).
# Build polylines per-drawing first, splitting if items don't chain.
EPS = 0.01

def to_polylines_from_drawing(items):
    polylines = []
    cur = []
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
                    polylines.append(cur)
                    cur = [(a.x, a.y), (b.x, b.y)]
        elif op[0] == 'c':
            # cubic bezier; sample 8 points
            p0, p1, p2, p3 = op[1], op[2], op[3], op[4]
            pts = []
            for t in [i/8 for i in range(1, 9)]:
                u = 1 - t
                x = u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x
                y = u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y
                pts.append((x, y))
            if not cur:
                cur = [(p0.x, p0.y)]
            elif abs(cur[-1][0]-p0.x) > EPS or abs(cur[-1][1]-p0.y) > EPS:
                polylines.append(cur)
                cur = [(p0.x, p0.y)]
            cur.extend(pts)
    if cur:
        polylines.append(cur)
    return polylines

all_polys = []
for d in drawings:
    polys = to_polylines_from_drawing(d.get("items", []))
    all_polys.extend(polys)

print("Raw polylines (per drawing chained):", len(all_polys))

# Classify each polyline by:
#  - length (sum of segments)
#  - number of points
#  - radial vs tangential
def poly_length(p):
    s = 0.0
    for i in range(1, len(p)):
        dx = p[i][0]-p[i-1][0]
        dy = p[i][1]-p[i-1][1]
        s += math.hypot(dx, dy)
    return s

lens = [poly_length(p) for p in all_polys]
npts = [len(p) for p in all_polys]
print("len stats: min=%.2f max=%.2f median=%.2f" % (min(lens), max(lens), sorted(lens)[len(lens)//2]))
print("npts stats: min=%d max=%d" % (min(npts), max(npts)))

# Histogram of #points
bucket = Counter()
for n in npts:
    if n <= 2: bucket['1 segment'] += 1
    elif n <= 5: bucket['short'] += 1
    elif n <= 30: bucket['medium'] += 1
    elif n <= 100: bucket['longish'] += 1
    elif n <= 1000: bucket['long'] += 1
    else: bucket['huge'] += 1
print("size buckets:", bucket)

# Center estimate from full strokes bbox (note: bbox may be biased; refine later)
cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
print("approx center:", cx, cy)

# For each polyline, compute centroid radius
def avg_radius(p):
    return sum(math.hypot(x-cx, y-cy) for x,y in p)/len(p)

# Find the LONG polylines (walls)
long_polys = [(i, p) for i,p in enumerate(all_polys) if len(p) > 100]
print("Long polylines:", len(long_polys))
for i, p in long_polys[:5]:
    print("  #%d  npts=%d  len=%.1f  avg_r=%.1f" % (i, len(p), poly_length(p), avg_radius(p)))

# Save chained polylines for later steps
with open("processing/tmp/polylines.json", "w") as f:
    json.dump({
        "polylines": all_polys,
        "bbox": [min(xs), min(ys), max(xs), max(ys)],
        "center": [cx, cy],
    }, f)
print("Wrote processing/tmp/polylines.json")
