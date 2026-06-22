"""Render small drawings color-coded by type to identify rectangles vs ticks vs spokes."""
import fitz, math
from PIL import Image, ImageDraw

doc = fitz.open("processing/Spiral_5m sections and spokes.pdf")
drawings = doc[0].get_drawings()

cx, cy = 387.8637, 529.4637

# Compute bbox of strokes
xs, ys = [], []
for d in drawings:
    r = d.get("rect")
    if r is None: continue
    xs += [r.x0, r.x1]; ys += [r.y0, r.y1]
bbox = (min(xs), min(ys), max(xs), max(ys))

PAD = 30; SCALE = 4.0
W = int((bbox[2]-bbox[0])*SCALE)+2*PAD
H = int((bbox[3]-bbox[1])*SCALE)+2*PAD
def xf(pt): return (PAD+(pt[0]-bbox[0])*SCALE, PAD+(pt[1]-bbox[1])*SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

# Draw all walls (long polylines) in faint gray for reference
def polylines_from_drawing(items):
    out = []; cur = []
    for op in items:
        if op[0] == 'l':
            a, b = op[1], op[2]
            if not cur:
                cur = [(a.x, a.y), (b.x, b.y)]
            else:
                last = cur[-1]
                if abs(last[0]-a.x) < 0.01 and abs(last[1]-a.y) < 0.01:
                    cur.append((b.x, b.y))
                else:
                    out.append(cur); cur = [(a.x, a.y), (b.x, b.y)]
    if cur: out.append(cur)
    return out

for d in drawings:
    polys = polylines_from_drawing(d.get("items", []))
    for p in polys:
        if len(p) > 100:
            draw.line([xf(q) for q in p], fill=(220,220,220), width=1)

# Now overlay small drawings color-coded by item count
colors = {1: (220,200,200), 2: (255,0,0), 3: (255,140,0), 4: (0,180,0),
          8: (255,0,255), 27: (0,140,140), 28: (0,140,140), 29: (0,140,140),
          30: (0,140,140), 31: (0,140,140), 32: (0,140,140), 33: (0,140,140),
          34: (0,140,140), 35: (0,140,140), 36: (0,140,140), 37: (0,140,140),
          64: (0,0,255), 65: (0,0,255), 66: (0,0,255)}

for d in drawings:
    n = len(d.get("items", []))
    if n in colors:
        c = colors[n]
        polys = polylines_from_drawing(d["items"])
        for p in polys:
            if len(p) < 2: continue
            w = 1 if n in (1, 2) else 2
            draw.line([xf(q) for q in p], fill=c, width=w)

img.save("processing/tmp/marks_classified.png")
print("Wrote marks_classified.png", W, H)
print("Legend: gray=walls, light-pink=1-item, RED=2-item, ORANGE=3-item, GREEN=4-item, MAGENTA=8-item, TEAL=27-37 items, BLUE=64-66 items")
