"""Plot the user's grey dots over the spiral walls and analyze their positions."""
import fitz, math, json
from PIL import Image, ImageDraw

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
drawings = page.get_drawings()

# Collect dots (filled grey small circles)
dots = []
for d in drawings:
    if d.get("type") == "f" and d.get("fill"):
        f = d["fill"]
        if abs(f[0]-0.549) < 0.01 and abs(f[1]-0.549) < 0.01:
            r = d["rect"]
            cx_dot = (r.x0+r.x1)/2
            cy_dot = (r.y0+r.y1)/2
            dots.append((cx_dot, cy_dot))

print(f"found {len(dots)} dots")

# Compute polar about provisional centre, ordered by angle/radius
cx, cy = 387.8637, 529.4637
polar_dots = []
for (dx, dy) in dots:
    th = math.atan2(dy-cy, dx-cx)
    r = math.hypot(dx-cx, dy-cy)
    polar_dots.append((th, r, dx, dy))

# Sort by r (so we go from inner dot to outer dot)
polar_dots.sort(key=lambda t: t[1])
print("\nDots sorted by radius:")
for i, (th, r, x, y) in enumerate(polar_dots):
    print(f"  [{i:2d}] r={r:7.2f}  theta={math.degrees(th):7.2f}  ({x:.2f}, {y:.2f})")

# Render: walls in gray, dots in red labeled by sorted index
xs, ys = [], []
all_polys = []
for d in drawings:
    polys = polylines_from_drawing(d.get("items", []))
    all_polys.extend(polys)
    if d.get("rect"):
        r = d["rect"]
        xs += [r.x0, r.x1]; ys += [r.y0, r.y1]
bbox = (min(xs), min(ys), max(xs), max(ys))

PAD = 30; SCALE = 5.0
W = int((bbox[2]-bbox[0])*SCALE)+2*PAD
H = int((bbox[3]-bbox[1])*SCALE)+2*PAD
def xf(pt): return (PAD+(pt[0]-bbox[0])*SCALE, PAD+(pt[1]-bbox[1])*SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)
for d in drawings:
    if d.get("type") != "s":
        continue
    polys = polylines_from_drawing(d.get("items", []))
    for p in polys:
        if len(p) > 100:  # walls
            draw.line([xf(q) for q in p], fill=(190,190,190), width=1)

for i, (th, r, x, y) in enumerate(polar_dots):
    px, py = xf((x, y))
    draw.ellipse([px-5, py-5, px+5, py+5], fill=(255,0,0), outline=(120,0,0))
    draw.text((px+7, py-6), str(i), fill=(180,0,0))

# Spiral centre
ccx, ccy = xf((cx, cy))
draw.ellipse([ccx-4, ccy-4, ccx+4, ccy+4], outline=(0,0,255), width=2)

img.save("processing/tmp/dots_over_walls.png")
print(f"\nWrote processing/tmp/dots_over_walls.png  ({W}x{H})")

# Save raw dot positions for next stage
with open("processing/tmp/dots.json", "w") as f:
    json.dump({"center": [cx, cy], "dots": dots,
               "polar_by_radius": [(t,r,x,y) for t,r,x,y in polar_dots]}, f, indent=2)
