"""Build the spiral centerline from the wall polylines and split it into 5 m sections.

Strategy
--------
1. Find a precise centre by fitting a circle to all "long" polylines (the wall arcs).
2. Convert each long polyline to (angle, radius) about that centre.
3. Sort the polylines by their mean radius. Pair consecutive arcs as
   (inner_wall, outer_wall) of one spiral revolution.
4. For each revolution, build a centerline by sampling angles and averaging the
   inner & outer wall radii at each angle.
5. Concatenate revolutions head-to-tail to produce the full continuous spiral
   centerline.
6. Find the scale (pts -> metres) from the bbox of the spiral and known
   diameters, OR from the 5 m tick marks themselves.
7. Resample the centerline at 5 m intervals and emit each segment as its own
   polyline in an SVG file.
"""
import fitz, math, json, statistics
from collections import defaultdict

PDF = "processing/Spiral_5m sections and spokes.pdf"

# ------------------------------------------------------------------
# Step 0: Load polylines exactly as analyze.py did
# ------------------------------------------------------------------
EPS = 0.01
def polylines_from_drawing(items):
    out = []
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
                    out.append(cur); cur = [(a.x, a.y), (b.x, b.y)]
        elif op[0] == 'c':
            p0,p1,p2,p3 = op[1], op[2], op[3], op[4]
            if not cur:
                cur = [(p0.x, p0.y)]
            elif abs(cur[-1][0]-p0.x) > EPS or abs(cur[-1][1]-p0.y) > EPS:
                out.append(cur); cur = [(p0.x, p0.y)]
            for t in [i/12 for i in range(1, 13)]:
                u = 1-t
                x = u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x
                y = u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y
                cur.append((x, y))
    if cur:
        out.append(cur)
    return out

doc = fitz.open(PDF)
page = doc[0]
all_polys = []
for d in page.get_drawings():
    all_polys.extend(polylines_from_drawing(d.get("items", [])))

print("polylines:", len(all_polys))

def poly_len(p):
    return sum(math.hypot(p[i][0]-p[i-1][0], p[i][1]-p[i-1][1]) for i in range(1, len(p)))

# ------------------------------------------------------------------
# Step 1: estimate centre by fitting a circle to a long arc with many points
# ------------------------------------------------------------------
def fit_circle(points):
    # Algebraic circle fit: minimize sum (x^2+y^2 - 2a x - 2b y - c)^2
    n = len(points)
    Sx = sum(p[0] for p in points); Sy = sum(p[1] for p in points)
    Sxx = sum(p[0]*p[0] for p in points); Syy = sum(p[1]*p[1] for p in points)
    Sxy = sum(p[0]*p[1] for p in points)
    Sxxx = sum(p[0]**3 for p in points); Syyy = sum(p[1]**3 for p in points)
    Sxyy = sum(p[0]*p[1]*p[1] for p in points); Sxxy = sum(p[0]*p[0]*p[1] for p in points)
    A = [[Sxx, Sxy, Sx], [Sxy, Syy, Sy], [Sx, Sy, n]]
    B = [-(Sxxx + Sxyy), -(Sxxy + Syyy), -(Sxx + Syy)]
    # Solve 3x3 via Cramer
    def det3(M):
        return (M[0][0]*(M[1][1]*M[2][2]-M[1][2]*M[2][1])
              - M[0][1]*(M[1][0]*M[2][2]-M[1][2]*M[2][0])
              + M[0][2]*(M[1][0]*M[2][1]-M[1][1]*M[2][0]))
    D = det3(A)
    if abs(D) < 1e-9:
        return None
    def replace(col, vec):
        return [[vec[i] if j==col else A[i][j] for j in range(3)] for i in range(3)]
    a = det3(replace(0, B))/D
    b = det3(replace(1, B))/D
    c = det3(replace(2, B))/D
    cx = -a/2; cy = -b/2
    r = math.sqrt(cx*cx + cy*cy - c)
    return (cx, cy, r)

# The drawing is a real spiral (variable radius), so fitting a circle to a
# whole arc gives a biased centre.  Instead pick polylines whose points lie on
# a near-perfect circle (tight radius range relative to mean) and fit those.
candidates = []
for p in all_polys:
    if len(p) < 30:
        continue
    # use crude centroid as provisional centre to compute radii
    mx = sum(q[0] for q in p)/len(p); my = sum(q[1] for q in p)/len(p)
    rs = [math.hypot(q[0]-mx, q[1]-my) for q in p]
    spread = (max(rs)-min(rs)) / (sum(rs)/len(rs) + 1e-9)
    candidates.append((spread, p))
candidates.sort(key=lambda t: t[0])
print("best 5 circular candidates by spread:")
for s, p in candidates[:5]:
    print(f"  spread={s:.4f} npts={len(p)}")

cxs, cys = [], []
for s, p in candidates[:30]:  # use the 30 most circular polylines
    f = fit_circle(p)
    if f is None:
        continue
    # discard absurd fits
    if f[2] < 1 or f[2] > 1000:
        continue
    cxs.append(f[0]); cys.append(f[1])
cx = statistics.median(cxs); cy = statistics.median(cys)
print(f"centre: ({cx:.4f}, {cy:.4f})  (from {len(cxs)} fits)")

# ------------------------------------------------------------------
# Step 2: characterise polylines
# ------------------------------------------------------------------
def polar(p):
    return [(math.atan2(y-cy, x-cx), math.hypot(x-cx, y-cy)) for (x,y) in p]

def angle_span(angs):
    # compute total angular range traversed by the polyline by unwrapping
    if len(angs) < 2:
        return 0.0
    unwrapped = [angs[0]]
    for a in angs[1:]:
        d = a - unwrapped[-1]
        while d > math.pi: d -= 2*math.pi
        while d < -math.pi: d += 2*math.pi
        unwrapped.append(unwrapped[-1] + d)
    return unwrapped[-1] - unwrapped[0], unwrapped

# Pull out the LONG wall polylines and characterise each one
walls = []  # list of dicts
for idx, p in enumerate(all_polys):
    if len(p) < 200:
        continue
    pol = polar(p)
    rs = [r for _, r in pol]
    angs = [a for a, _ in pol]
    span, unwrapped = angle_span(angs)
    walls.append({
        "idx": idx,
        "points": p,
        "polar": pol,
        "unwrapped": unwrapped,
        "r_mean": sum(rs)/len(rs),
        "r_min": min(rs),
        "r_max": max(rs),
        "span_rad": span,
    })

print(f"wall arcs: {len(walls)}")
walls.sort(key=lambda w: w["r_mean"])
for i, w in enumerate(walls):
    print(f"  [{i:3d}] r_mean={w['r_mean']:7.2f} r_range=[{w['r_min']:7.2f},{w['r_max']:7.2f}] "
          f"npts={len(w['points']):5d} span_deg={math.degrees(w['span_rad']):8.2f}")

# ------------------------------------------------------------------
# Save for next step (interactive)
# ------------------------------------------------------------------
import os
os.makedirs("processing/tmp", exist_ok=True)
with open("processing/tmp/walls.json", "w") as f:
    json.dump({
        "center": [cx, cy],
        "walls": [
            {
                "idx": w["idx"],
                "r_mean": w["r_mean"],
                "r_min": w["r_min"], "r_max": w["r_max"],
                "span_rad": w["span_rad"],
                "npts": len(w["points"]),
            } for w in walls
        ],
    }, f, indent=2)
print("Wrote walls.json")
