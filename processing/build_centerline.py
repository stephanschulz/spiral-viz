"""Build a clean Archimedean centerline through the spiral corridor.

The PDF has corridor walls (pairs of close arcs at radii r, r+wall_thickness)
with corridors between them.  Detect wall pairs at many angles, find the
mid-corridor radii, fit a continuous Archimedean spiral r = a + b*theta_total
(theta_total accumulates across turns), and dump the centreline polyline.
"""
import fitz, math, json

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
all_polys = []
for d in doc[0].get_drawings():
    all_polys.extend(polylines_from_drawing(d.get("items", [])))

cx, cy = 387.8637, 529.4637

def crossings_at_angle(polys, theta):
    rd = (math.cos(theta), math.sin(theta))
    out = []
    for p in polys:
        if len(p) < 100: continue  # walls only
        for i in range(1, len(p)):
            a = (p[i-1][0]-cx, p[i-1][1]-cy)
            b = (p[i][0]-cx, p[i][1]-cy)
            ap = a[0]*rd[1]-a[1]*rd[0]
            bp = b[0]*rd[1]-b[1]*rd[0]
            if ap*bp > 0: continue
            denom = bp - ap
            if abs(denom) < 1e-9: continue
            u = -ap/denom
            ix = a[0] + u*(b[0]-a[0]); iy = a[1] + u*(b[1]-a[1])
            t = ix*rd[0] + iy*rd[1]
            if t > 1: out.append(t)
    return sorted(out)

def cluster_walls(rs, dup_eps=1.0, wall_eps=3.0):
    """Deduplicate near-duplicate lines (within dup_eps), then group into wall
    pairs (two lines within wall_eps form a wall).  Return list of wall centre
    radii."""
    deduped = []
    for r in rs:
        if deduped and r - deduped[-1] < dup_eps:
            continue
        deduped.append(r)
    walls = []
    i = 0
    while i < len(deduped):
        if i+1 < len(deduped) and deduped[i+1] - deduped[i] < wall_eps:
            walls.append((deduped[i]+deduped[i+1]) / 2)
            i += 2
        else:
            walls.append(deduped[i])
            i += 1
    return walls

def corridor_centres(walls, wall_eps=3.0, max_corr=12.0):
    """Mid-points between consecutive walls — corridors."""
    centres = []
    for i in range(len(walls)-1):
        d = walls[i+1] - walls[i]
        if d > wall_eps and d < max_corr:
            centres.append((walls[i]+walls[i+1])/2)
    return centres

# Sample many angles
N_ANGLES = 720
samples = []  # (theta, [r1, r2, ...])
for k in range(N_ANGLES):
    th = (k * 2*math.pi) / N_ANGLES
    rs = crossings_at_angle(all_polys, th)
    rs = [r for r in rs if r > 10]
    walls = cluster_walls(rs)
    centres = corridor_centres(walls)
    samples.append((th, centres))

# Diagnostics
nc = [len(c) for _, c in samples]
print(f"corridors per angle: min={min(nc)} max={max(nc)} mean={sum(nc)/len(nc):.1f}")

# Build (theta_unwrapped, r) pairs for every corridor centre
# At each angle θ, the i-th centre is on the spiral at parameter θ + 2π*i (continuing inward to outward)
spiral_points = []  # (theta_unwrapped, r)
for th, centres in samples:
    for i, r in enumerate(centres):
        spiral_points.append((th + 2*math.pi*i, r))

# Linear regression r = a + b * theta_unwrapped
N = len(spiral_points)
Sx = sum(t for t,_ in spiral_points); Sy = sum(r for _,r in spiral_points)
Sxx = sum(t*t for t,_ in spiral_points); Sxy = sum(t*r for t,r in spiral_points)
b = (N*Sxy - Sx*Sy) / (N*Sxx - Sx*Sx)
a = (Sy - b*Sx) / N
print(f"\nArchimedean fit: r = {a:.4f} + {b:.6f} * theta  (b = {b*2*math.pi:.4f} pts/turn)")

# Compute fit residuals
res = [r - (a + b*t) for t,r in spiral_points]
import statistics
print(f"residual stdev: {statistics.pstdev(res):.4f} pts")

# Determine the angular range
thetas = [t for t,_ in spiral_points]
theta_min, theta_max = min(thetas), max(thetas)
print(f"theta range: {theta_min:.2f} -> {theta_max:.2f} rad  ({math.degrees(theta_min):.1f} to {math.degrees(theta_max):.1f} deg)")
print(f"num turns: {(theta_max-theta_min)/(2*math.pi):.2f}")

# Sample the fitted spiral and write SVG and polyline JSON
# Use finer parameterisation
STEPS = 8000
pts = []
for k in range(STEPS+1):
    t = theta_min + (theta_max-theta_min) * k / STEPS
    r = a + b * t
    x = cx + r * math.cos(t)
    y = cy + r * math.sin(t)
    pts.append((x, y))

# Arc length
total = 0
for i in range(1, len(pts)):
    total += math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1])
print(f"total arc length: {total:.2f} pts")
print(f"if 1pt = 0.0353 m (1:100 scale)  -> {total*0.0353:.1f} m")
print(f"if 5m sections at that scale     -> {total*0.0353/5:.1f} sections")

# Save centerline polyline
with open("processing/tmp/centerline.json", "w") as f:
    json.dump({
        "center": [cx, cy],
        "a": a, "b": b,
        "theta_min": theta_min, "theta_max": theta_max,
        "total_arc_pts": total,
        "polyline": pts,
        "bbox": [min(x for x,y in pts), min(y for x,y in pts),
                 max(x for x,y in pts), max(y for x,y in pts)],
    }, f)
print("Wrote processing/tmp/centerline.json")
