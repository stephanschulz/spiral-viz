"""Find the new red (start) and blue (end) marker dots in the updated PDF."""
import fitz
from collections import Counter

PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
page = doc[0]
drawings = page.get_drawings()
print(f"total drawings: {len(drawings)}")

fills = Counter()
filled = []
for d in drawings:
    if d.get("type") == "f" and d.get("fill") is not None:
        c = tuple(round(x, 3) for x in d["fill"])
        fills[c] += 1
        filled.append((c, d))

print("\nfill colours of filled drawings:")
for c, n in fills.most_common():
    print(f"  {c} -> {n}")

# Print non-grey filled (likely the new red/blue markers)
print("\nnon-grey filled drawings:")
for c, d in filled:
    if abs(c[0]-0.549) > 0.01 or abs(c[1]-0.549) > 0.01 or abs(c[2]-0.549) > 0.01:
        r = d["rect"]
        diam = max(r.x1-r.x0, r.y1-r.y0)
        cx_dot = (r.x0+r.x1)/2
        cy_dot = (r.y0+r.y1)/2
        print(f"  fill={c} centre=({cx_dot:.2f}, {cy_dot:.2f}) diameter={diam:.3f}")
