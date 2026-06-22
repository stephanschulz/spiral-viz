"""Render an overlay PNG showing: original walls (light grey), the new
centreline (blue), the red start markers, and the blue end marker.  For
visual verification only."""
import fitz, math
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

# Load source PDF walls + colored markers
src = fitz.open("processing/Spiral_5m sections and spokes-grey dots.pdf")
page = src[0]
drawings = page.get_drawings()

# Load my centreline SVG points back from the SVG
import re
with open("processing/spiral_centerline.svg") as f:
    svg = f.read()
m = re.search(r'points="([^"]+)"', svg)
coords = m.group(1).split()
cp = [tuple(float(v) for v in c.split(",")) for c in coords]

reds, blues = [], []
for d in drawings:
    if d.get("type") == "f" and d.get("fill"):
        c = tuple(round(x, 3) for x in d["fill"])
        r = d["rect"]
        cd = ((r.x0+r.x1)/2, (r.y0+r.y1)/2, max(r.x1-r.x0, r.y1-r.y0))
        if c[0] > 0.9 and c[1] < 0.1: reds.append(cd)
        elif c[2] > 0.9 and c[0] < 0.1: blues.append(cd)

# Compute bbox to render
xs, ys = [], []
for d in drawings:
    if d.get("rect"):
        r = d["rect"]; xs += [r.x0, r.x1]; ys += [r.y0, r.y1]
bbox = (min(xs), min(ys), max(xs), max(ys))

PAD = 30; SCALE = 5.0
W = int((bbox[2]-bbox[0])*SCALE)+2*PAD
H = int((bbox[3]-bbox[1])*SCALE)+2*PAD
def xf(p): return (PAD+(p[0]-bbox[0])*SCALE, PAD+(p[1]-bbox[1])*SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

# Walls
for d in drawings:
    if d.get("type") != "s": continue
    polys = polylines_from_drawing(d.get("items", []))
    for p in polys:
        if len(p) > 100:
            draw.line([xf(q) for q in p], fill=(220,220,220), width=1)

# Centreline (blue)
draw.line([xf(q) for q in cp], fill=(20,100,255), width=2)

# Mark START (green) and END (purple) of polyline
sx, sy = xf(cp[0])
draw.ellipse([sx-9, sy-9, sx+9, sy+9], outline=(0,180,0), width=3)
draw.text((sx+12, sy-8), "START", fill=(0,180,0))
ex, ey = xf(cp[-1])
draw.ellipse([ex-9, ey-9, ex+9, ey+9], outline=(180,0,180), width=3)
draw.text((ex+12, ey-8), "END", fill=(180,0,180))

# Red & blue markers
for x, y, dia in reds:
    px, py = xf((x, y))
    draw.ellipse([px-6, py-6, px+6, py+6], fill=(255,0,0))
for x, y, dia in blues:
    px, py = xf((x, y))
    draw.ellipse([px-6, py-6, px+6, py+6], fill=(0,40,255))

img.save("processing/tmp/verify_overlay.png")
print("Wrote processing/tmp/verify_overlay.png", W, H)
