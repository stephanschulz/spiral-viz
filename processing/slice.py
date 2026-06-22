"""Take a radial slice through the spiral at a fixed angle and list the wall crossings."""
import fitz, math
from collections import defaultdict

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

# For a fixed angle theta_0, find each polyline segment that crosses the
# infinite ray from centre.  Return r-values.
def crossings(polys, theta_0):
    """Return radii where wall polylines cross the ray at angle theta_0 (in rad)."""
    # The ray is parametric: (cx + t*cos(theta), cy + t*sin(theta)), t > 0.
    # For each segment (p0, p1) test intersection with the ray.
    rd = (math.cos(theta_0), math.sin(theta_0))
    out = []
    for p in polys:
        if len(p) < 2: continue
        for i in range(1, len(p)):
            a = (p[i-1][0]-cx, p[i-1][1]-cy)
            b = (p[i][0]-cx, p[i][1]-cy)
            # cross-products to know which side of ray
            ax_perp = a[0]*rd[1] - a[1]*rd[0]
            bx_perp = b[0]*rd[1] - b[1]*rd[0]
            if ax_perp * bx_perp > 0:
                continue
            # segment crosses ray line. Compute t (radius) of intersection
            denom = bx_perp - ax_perp
            if abs(denom) < 1e-9: continue
            u = -ax_perp / denom
            ix = a[0] + u*(b[0]-a[0])
            iy = a[1] + u*(b[1]-a[1])
            t = ix*rd[0] + iy*rd[1]
            if t > 1:  # discard centre singularities
                out.append(t)
    return sorted(out)

# Try a few angles
for theta_deg in [0, 45, 90, 135, 180]:
    rs = crossings(all_polys, math.radians(theta_deg))
    rs = [r for r in rs if r > 10]  # skip near centre noise
    # Cluster very close ones (within 1 pt) — they're duplicated CAD lines
    clustered = []
    last = -10
    for r in rs:
        if r - last < 1.0:
            continue
        clustered.append(r); last = r
    print(f"angle={theta_deg:3d}: {len(clustered)} wall crossings")
    diffs = [clustered[i] - clustered[i-1] for i in range(1, len(clustered))]
    for i, r in enumerate(clustered):
        d = "" if i == 0 else f"  Δ={diffs[i-1]:.2f}"
        print(f"   r={r:8.3f}{d}")
    print()
