"""Emit the final single-polyline spiral centreline as SVG and PDF.

Uses the Archimedean fit through the user's 42 grey dots:
    r(k) = a + b*k        where k is the corridor-turn index (0 = innermost)
    theta(k) = phi0 + 2*pi*k
The path is traced continuously from outermost dot inward to the innermost
dot (the natural walking direction for entering a spiral pavilion).
"""
import json, math, fitz

with open("processing/tmp/spiral_fit.json") as f:
    fit = json.load(f)

cx, cy = fit["center"]
phi0 = fit["phi0_rad"]
a_idx = fit["a_per_index"]
b_idx = fit["b_per_index"]
N = fit["n_dots"]

PDF_SRC = "processing/Spiral_5m sections and spokes-grey dots.pdf"
src = fitz.open(PDF_SRC)
page = src[0]
PAGE_W, PAGE_H = page.rect.width, page.rect.height

# Find the start (biggest red dot) and end (blue dot) markers in the PDF
red, blue = [], []
for d in src[0].get_drawings():
    if d.get("type") == "f" and d.get("fill"):
        c = tuple(round(x, 3) for x in d["fill"])
        r = d["rect"]
        cx_d = (r.x0+r.x1)/2; cy_d = (r.y0+r.y1)/2
        diam = max(r.x1-r.x0, r.y1-r.y0)
        if c[0] > 0.9 and c[1] < 0.1 and c[2] < 0.1:
            red.append((cx_d, cy_d, diam))
        elif c[2] > 0.9 and c[0] < 0.1:
            blue.append((cx_d, cy_d, diam))
red.sort(key=lambda t: -t[2])  # biggest first = start
start_x, start_y, _ = red[0]
end_x, end_y, _ = blue[0]
start_r = math.hypot(start_x - cx, start_y - cy)
end_r = math.hypot(end_x - cx, end_y - cy)

# Find the k value on the fitted spiral whose (x,y) is CLOSEST to each marker.
# Matching just r gives a wrong angular position (off by half a turn), so we
# need to honour both r and theta together.
def spiral_xy(k):
    th = phi0 - 2 * math.pi * k
    r = a_idx + b_idx * k
    return cx + r * math.cos(th), cy + r * math.sin(th)

def find_closest_k(target_x, target_y, k_min=-5.0, k_max=42.0):
    best_k, best_d = None, float("inf")
    n = int((k_max - k_min) * 720) + 1  # 720 samples per turn
    for i in range(n):
        k = k_min + (k_max - k_min) * i / (n - 1)
        x, y = spiral_xy(k)
        d2 = (x - target_x)**2 + (y - target_y)**2
        if d2 < best_d:
            best_d = d2; best_k = k
    # refine
    for _ in range(5):
        step = (k_max - k_min) / n
        for delta in [-step, -step/2, step/2, step]:
            k = best_k + delta
            x, y = spiral_xy(k)
            d2 = (x - target_x)**2 + (y - target_y)**2
            if d2 < best_d:
                best_d = d2; best_k = k
        n *= 4
    return best_k, math.sqrt(best_d)

k_start, d_start = find_closest_k(start_x, start_y)
k_end, d_end = find_closest_k(end_x, end_y)
print(f"k_start (red): {k_start:.4f}  (distance to red marker: {d_start:.2f} pt)")
print(f"k_end (blue):  {k_end:.4f}  (distance to blue marker: {d_end:.2f} pt)")
print(f"total turns: {k_end - k_start:.4f}")

# Walk inner -> outer (k from k_start UP to k_end).  Theta uses MINUS sign so
# decreasing math-angle = visually counter-clockwise in the PDF y-down frame.
SAMPLES_PER_TURN = 720
n_steps = max(2, int(SAMPLES_PER_TURN * abs(k_end - k_start))) + 1

pts = []
for s in range(n_steps):
    k = k_start + (k_end - k_start) * s / (n_steps - 1)
    th = phi0 - 2 * math.pi * k
    r = a_idx + b_idx * k
    x = cx + r * math.cos(th)
    y = cy + r * math.sin(th)
    pts.append((x, y))

# Arc length report
arc_len = 0.0
for i in range(1, len(pts)):
    arc_len += math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1])

print(f"samples: {len(pts)}")
print(f"arc length: {arc_len:.2f} pts")
print(f"start (red, inner): ({pts[0][0]:.2f}, {pts[0][1]:.2f})  r={a_idx+b_idx*k_start:.2f}  (red marker at ({start_x:.2f}, {start_y:.2f}))")
print(f"end (blue, outer):  ({pts[-1][0]:.2f}, {pts[-1][1]:.2f})  r={a_idx+b_idx*k_end:.2f}  (blue marker at ({end_x:.2f}, {end_y:.2f}))")

# ---------------- SVG output ----------------
svg_path = "processing/spiral_centerline.svg"
def fmt(p):
    return f"{p[0]:.3f},{p[1]:.3f}"

with open(svg_path, "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {PAGE_W:.2f} {PAGE_H:.2f}" '
            f'width="{PAGE_W:.2f}pt" height="{PAGE_H:.2f}pt">\n')
    f.write('  <title>Spiral path centreline</title>\n')
    f.write('  <polyline fill="none" stroke="#000000" stroke-width="0.5" '
            'stroke-linecap="round" stroke-linejoin="round"\n')
    f.write('    points="')
    f.write(' '.join(fmt(p) for p in pts))
    f.write('"/>\n')
    f.write('</svg>\n')
print(f"wrote {svg_path}")

# ---------------- PDF output ----------------
pdf_path = "processing/spiral_centerline.pdf"
out_doc = fitz.open()
out_page = out_doc.new_page(width=PAGE_W, height=PAGE_H)
shape = out_page.new_shape()

# Use a single open polyline so PyMuPDF doesn't add a closing edge.
shape.draw_polyline([fitz.Point(*p) for p in pts])
shape.finish(color=(0, 0, 0), width=0.5, lineCap=1, lineJoin=1, closePath=False)
shape.commit()
out_doc.save(pdf_path)
out_doc.close()
print(f"wrote {pdf_path}")
