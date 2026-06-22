"""Visualise the grey + red + blue dots together with the spiral walls."""
import fitz, math, json
from PIL import Image, ImageDraw

EPS = 0.01
def polylines_from_drawing(items):
    out = []; cur = []
    for op in items:
        if op[0] == 'l':
            a, b = op[1], op[2]
            if not cur: cur = [(a.x, a.y), (b.x, b.y)]
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

grey, red, blue = [], [], []
for d in drawings:
    if d.get("type") == "f" and d.get("fill"):
        c = tuple(round(x,3) for x in d["fill"])
        r = d["rect"]
        cx_d = (r.x0+r.x1)/2; cy_d = (r.y0+r.y1)/2
        diam = max(r.x1-r.x0, r.y1-r.y0)
        if abs(c[0]-0.549) < 0.01:
            grey.append((cx_d, cy_d, diam))
        elif c[0] > 0.9 and c[1] < 0.1 and c[2] < 0.1:
            red.append((cx_d, cy_d, diam))
        elif c[2] > 0.9 and c[0] < 0.1:
            blue.append((cx_d, cy_d, diam))
print(f"grey {len(grey)} red {len(red)} blue {len(blue)}")
print("red dots (sorted by diameter, biggest first):")
red.sort(key=lambda t: -t[2])
for r in red:
    print(f"  ({r[0]:.2f}, {r[1]:.2f}) d={r[2]:.3f}")
print("blue dot:")
for b in blue:
    print(f"  ({b[0]:.2f}, {b[1]:.2f}) d={b[2]:.3f}")

with open("processing/tmp/spiral_fit.json") as f:
    fit = json.load(f)
cx, cy = fit["center"]

# Compute polar of red & blue relative to fit centre
print("\npolar coords about spiral centre:")
for x, y, d in red:
    th = math.atan2(y-cy, x-cx); r = math.hypot(x-cx, y-cy)
    print(f"  red d={d:.3f}: r={r:7.3f} theta={math.degrees(th):8.2f} deg")
for x, y, d in blue:
    th = math.atan2(y-cy, x-cx); r = math.hypot(x-cx, y-cy)
    print(f"  blue d={d:.3f}: r={r:7.3f} theta={math.degrees(th):8.2f} deg")

# Render zoomed image of central area with all dots
xs = [x for x,y,d in grey+red+blue]; ys = [y for x,y,d in grey+red+blue]
# Focus on a window that includes red dots + inner grey dots + spiral centre
PAD = 30
xmin, xmax = cx-60, cx+60
ymin, ymax = cy-60, cy+60
SCALE = 30
W = int((xmax-xmin)*SCALE)+2*PAD
H = int((ymax-ymin)*SCALE)+2*PAD
def xf(pt): return (PAD+(pt[0]-xmin)*SCALE, PAD+(pt[1]-ymin)*SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)
for d in drawings:
    if d.get("type") != "s": continue
    polys = polylines_from_drawing(d.get("items", []))
    for p in polys:
        if len(p) > 100:
            draw.line([xf(q) for q in p], fill=(200,200,200), width=1)

for x, y, dia in grey:
    px, py = xf((x, y))
    draw.ellipse([px-5, py-5, px+5, py+5], fill=(120,120,120))
for i, (x, y, dia) in enumerate(red):
    px, py = xf((x, y))
    s = 4 + i * 4  # exaggerate sizes for visibility
    draw.ellipse([px-s, py-s, px+s, py+s], fill=(255,0,0), outline=(120,0,0))
    draw.text((px+s+2, py-6), f"R{i+1}", fill=(180,0,0))
for x, y, dia in blue:
    px, py = xf((x, y))
    draw.ellipse([px-7, py-7, px+7, py+7], fill=(0,40,255))
    draw.text((px+9, py-6), "BLUE", fill=(0,0,180))

ccx, ccy = xf((cx, cy))
draw.line([ccx-8, ccy, ccx+8, ccy], fill=(0,160,0), width=2)
draw.line([ccx, ccy-8, ccx, ccy+8], fill=(0,160,0), width=2)
img.save("processing/tmp/centre_dots.png")
print(f"\nWrote processing/tmp/centre_dots.png ({W}x{H})")
