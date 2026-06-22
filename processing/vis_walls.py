"""Render specific wall polylines individually to understand structure."""
import json, math, fitz
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

doc = fitz.open("processing/Spiral_5m sections and spokes.pdf")
all_polys = []
for d in doc[0].get_drawings():
    all_polys.extend(polylines_from_drawing(d.get("items", [])))

cx, cy = 387.8637, 529.4637

def polar(p):
    return [(math.atan2(y-cy, x-cx), math.hypot(x-cx, y-cy)) for x,y in p]

walls = []
for idx, p in enumerate(all_polys):
    if len(p) >= 200:
        pol = polar(p)
        rs = [r for _, r in pol]
        walls.append({"idx": idx, "points": p, "r_mean": sum(rs)/len(rs)})
walls.sort(key=lambda w: w["r_mean"])

# Pick walls 0..15 and render each in distinct colour
import colorsys
img = Image.new("RGB", (1200, 1200), "white")
draw = ImageDraw.Draw(img)
PAD = 50
SCALE = 3.5
def xf(pt):
    return (PAD + (pt[0]-cx+200)*SCALE, PAD + (pt[1]-cy+200)*SCALE)

for i, w in enumerate(walls[:15]):
    h = (i / 15) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 0.85)
    col = (int(r*255), int(g*255), int(b*255))
    pts = [xf(q) for q in w["points"]]
    draw.line(pts, fill=col, width=1)
    # label start point
    draw.text(xf(w["points"][0]), str(i), fill=col)

draw.ellipse([xf((cx, cy))[0]-3, xf((cx,cy))[1]-3, xf((cx,cy))[0]+3, xf((cx,cy))[1]+3], outline="red")
img.save("processing/tmp/walls_15.png")
print("Wrote walls_15.png")

# Also test if walls[5] and walls[6] are duplicates (same wall drawn twice)
def compare(a, b):
    # Take many sample points from a, find nearest distance to b's polyline.
    # Returns max & mean distance.
    pts_b = b["points"]
    max_d = 0; sum_d = 0; n = 0
    step = max(1, len(a["points"]) // 100)
    for q in a["points"][::step]:
        d_min = min(math.hypot(q[0]-r[0], q[1]-r[1]) for r in pts_b[::max(1,len(pts_b)//200)])
        max_d = max(max_d, d_min); sum_d += d_min; n += 1
    return sum_d/n, max_d

mean_d, max_d = compare(walls[5], walls[6])
print(f"walls[5] vs walls[6] mean dist: {mean_d:.4f}, max: {max_d:.4f}")
mean_d, max_d = compare(walls[8], walls[9])
print(f"walls[8] vs walls[9] mean dist: {mean_d:.4f}, max: {max_d:.4f}")
mean_d, max_d = compare(walls[11], walls[12])
print(f"walls[11] vs walls[12] mean dist: {mean_d:.4f}, max: {max_d:.4f}")
mean_d, max_d = compare(walls[0], walls[1])
print(f"walls[0] vs walls[1] mean dist: {mean_d:.4f}, max: {max_d:.4f}")
