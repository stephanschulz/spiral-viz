"""Generate a preview SVG of the centreline fit, overlaid on the original walls
and showing the user's grey dots.  This is the verification step before we
emit the final split-by-5 m SVG.
"""
import fitz, math, json, os

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

PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
page = doc[0]
page_w, page_h = page.rect.width, page.rect.height
drawings = page.get_drawings()

with open("processing/tmp/spiral_fit.json") as f:
    fit = json.load(f)
cx, cy = fit["center"]
phi0 = fit["phi0_rad"]
a_idx, b_idx = fit["a_per_index"], fit["b_per_index"]
N_dots = fit["n_dots"]

# Sample the Archimedean spiral going through the dots.
# Index space: float k = 0..N-1, theta = phi0 + 2*pi*k.
# We extend slightly: from the OUTERMOST dot to the INNERMOST dot (the path
# starts outside and winds in, the natural direction for a spiral walk).
SAMPLES_PER_TURN = 360
total_samples = int(SAMPLES_PER_TURN * (N_dots - 1)) + 1
spiral_pts = []
for s in range(total_samples):
    k = (N_dots - 1) - s * (N_dots - 1) / (total_samples - 1)  # outer -> inner
    th = phi0 + 2 * math.pi * k
    r = a_idx + b_idx * k
    x = cx + r * math.cos(th)
    y = cy + r * math.sin(th)
    spiral_pts.append((x, y))

# Compute arc length
total_arc = 0
for i in range(1, len(spiral_pts)):
    total_arc += math.hypot(spiral_pts[i][0]-spiral_pts[i-1][0],
                            spiral_pts[i][1]-spiral_pts[i-1][1])
print(f"sampled centerline arc length: {total_arc:.2f} pts ({total_samples} samples)")

# Emit SVG -- preserve PDF coordinate system (y-down).
out_path = "processing/spiral_centerline_preview.svg"
def pt(p): return f"{p[0]:.3f},{p[1]:.3f}"

svg = []
svg.append(f'<?xml version="1.0" encoding="UTF-8"?>')
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="0 0 {page_w:.2f} {page_h:.2f}" '
           f'width="{page_w:.2f}pt" height="{page_h:.2f}pt">')
svg.append('  <title>Spiral centreline preview (through user dots)</title>')

# Background walls (light gray)
svg.append('  <g id="walls" stroke="#dddddd" fill="none" stroke-width="0.35">')
for d in drawings:
    if d.get("type") != "s":
        continue
    polys = polylines_from_drawing(d.get("items", []))
    for p in polys:
        if len(p) < 2: continue
        svg.append('    <polyline points="' + ' '.join(pt(q) for q in p) + '"/>')
svg.append('  </g>')

# Dots (red, with index)
svg.append('  <g id="dots" fill="#dd2222" stroke="none" font-family="Arial" font-size="3">')
for i, (x, y) in enumerate(fit["dot_positions"]):
    svg.append(f'    <circle cx="{x:.3f}" cy="{y:.3f}" r="1.4"/>')
svg.append('  </g>')

# Centerline (blue)
svg.append('  <g id="centerline" stroke="#1a66ff" fill="none" stroke-width="0.8">')
svg.append('    <polyline points="' + ' '.join(pt(q) for q in spiral_pts) + '"/>')
svg.append('  </g>')

# Spiral centre marker
svg.append(f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="1.0" fill="#22aa00"/>')

svg.append('</svg>')

with open(out_path, "w") as f:
    f.write('\n'.join(svg))
print(f"wrote {out_path}")
print(f"page size: {page_w} x {page_h} pts")
