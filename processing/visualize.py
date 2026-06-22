"""Render polylines color-coded by size to understand which ones are walls/spokes/marks."""
import json, math
from PIL import Image, ImageDraw

with open("processing/tmp/polylines.json") as f:
    data = json.load(f)

polys = data["polylines"]
bbox = data["bbox"]
cx, cy = data["center"]

# Map to image
PAD = 20
SCALE = 4.0  # pts -> px
W = int((bbox[2]-bbox[0])*SCALE) + 2*PAD
H = int((bbox[3]-bbox[1])*SCALE) + 2*PAD

def xf(pt):
    return (PAD + (pt[0]-bbox[0])*SCALE, PAD + (pt[1]-bbox[1])*SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

def poly_len(p):
    s = 0
    for i in range(1, len(p)):
        s += math.hypot(p[i][0]-p[i-1][0], p[i][1]-p[i-1][1])
    return s

# Color code: huge=blue, long=green, longish=orange, medium=purple, short=gray, single=lightgray
colors = []
buckets = {"single": (220,220,220), "short": (160,160,160), "medium": (180,120,180),
           "longish": (255,160,0), "long": (0,180,0), "huge": (0,0,200)}
for p in polys:
    n = len(p)
    if n <= 2: c = buckets["single"]
    elif n <= 5: c = buckets["short"]
    elif n <= 30: c = buckets["medium"]
    elif n <= 100: c = buckets["longish"]
    elif n <= 1000: c = buckets["long"]
    else: c = buckets["huge"]
    colors.append(c)

# Draw in order: small ones first (so big ones overlay)
order = sorted(range(len(polys)), key=lambda i: len(polys[i]))
for i in order:
    p = polys[i]
    if len(p) < 2: continue
    pts = [xf(q) for q in p]
    draw.line(pts, fill=colors[i], width=2)

# Draw center
ccx, ccy = xf((cx, cy))
draw.ellipse([ccx-6, ccy-6, ccx+6, ccy+6], outline="red", width=2)

img.save("processing/tmp/classified.png")
print("Wrote processing/tmp/classified.png", W, H)
