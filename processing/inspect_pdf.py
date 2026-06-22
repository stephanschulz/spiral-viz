"""Inspect the spiral PDF drawings: counts, types, bbox, sample paths."""
import fitz
from collections import Counter

PDF = "processing/Spiral_5m sections and spokes.pdf"

doc = fitz.open(PDF)
page = doc[0]
print("page size pts:", page.rect)

drawings = page.get_drawings()
print("total drawings:", len(drawings))

type_counter = Counter()
item_counter = Counter()
for d in drawings:
    type_counter[d.get("type")] += 1
    for it in d.get("items", []):
        item_counter[it[0]] += 1

print("drawing types:", type_counter)
print("item op types:", item_counter)

# Print first few drawings with details
for i, d in enumerate(drawings[:8]):
    print(f"\n--- drawing #{i} ---")
    print("type:", d.get("type"), "rect:", d.get("rect"))
    print("stroke:", d.get("color"), "fill:", d.get("fill"), "width:", d.get("width"))
    for it in d.get("items", [])[:6]:
        print(" ", it)

# Page-wide bbox of all drawings
xs, ys = [], []
for d in drawings:
    r = d.get("rect")
    if r is None:
        continue
    xs += [r.x0, r.x1]
    ys += [r.y0, r.y1]
print("\nAll drawings bbox: x=[%.2f, %.2f] y=[%.2f, %.2f]" % (min(xs), max(xs), min(ys), max(ys)))

# Distribution: items per drawing
size_counter = Counter()
for d in drawings:
    size_counter[len(d.get("items", []))] += 1
print("\nItems-per-drawing distribution (size -> count):")
for size in sorted(size_counter):
    print(f"  {size:6d} items -> {size_counter[size]} drawings")

# Find big drawings (likely the long spiral runs)
big = sorted(drawings, key=lambda d: -len(d.get("items", [])))[:5]
for i, d in enumerate(big):
    print(f"\nBig drawing #{i}: {len(d.get('items',[]))} items, rect={d.get('rect')}, width={d.get('width')}")
    items = d.get("items", [])
    print("  first 3:", items[:3])
    print("  last  3:", items[-3:])

