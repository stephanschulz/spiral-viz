"""Find the user-placed grey dots in the new PDF."""
import fitz
from collections import Counter

PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
page = doc[0]
drawings = page.get_drawings()
print(f"total drawings: {len(drawings)}")

# Group by colour / fill
type_counter = Counter()
fill_counter = Counter()
stroke_counter = Counter()
for d in drawings:
    type_counter[d.get("type")] += 1
    f = d.get("fill")
    s = d.get("color")
    fill_counter[f] += 1
    stroke_counter[s] += 1

print("\ndraw types:", type_counter)
print("\nfill colours (top 10):")
for k, n in fill_counter.most_common(10):
    print(f"  {k} -> {n}")
print("\nstroke colours (top 10):")
for k, n in stroke_counter.most_common(10):
    print(f"  {k} -> {n}")

# Look for filled drawings (likely the dots)
fills = [d for d in drawings if d.get("type") == "f" or (d.get("fill") is not None and d.get("type") != "s")]
print(f"\nfilled drawings: {len(fills)}")

# Show first few filled
for i, d in enumerate(fills[:5]):
    print(f"\n--- filled drawing {i} ---")
    print("  type:", d.get("type"), "fill:", d.get("fill"), "rect:", d.get("rect"))
    for it in d.get("items", [])[:6]:
        print("   ", it)
