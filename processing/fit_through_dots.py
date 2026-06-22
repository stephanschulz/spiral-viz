"""Fit a continuous Archimedean spiral centreline that passes through the user-placed dots.

Each dot is on a different corridor turn at (approximately) the same angle phi_0,
so dot k satisfies r_k = a + b * (phi_0 + 2*pi*k).
We can do a clean linear fit r vs k.

We also derive the spiral centre by minimising the residuals.
"""
import json, math, statistics, fitz

# Reload dots from new PDF (more direct than file path)
PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
page = doc[0]
drawings = page.get_drawings()
dots = []
for d in drawings:
    if d.get("type") == "f" and d.get("fill"):
        f = d["fill"]
        if abs(f[0]-0.549) < 0.01 and abs(f[1]-0.549) < 0.01:
            r = d["rect"]
            dots.append(((r.x0+r.x1)/2, (r.y0+r.y1)/2))
print(f"loaded {len(dots)} dots")

# The previous centre estimate (387.86, 529.46) is approximate.  Refine the
# centre so the dots are most consistently spaced.  Treat the spiral as an
# Archimedean spiral and pick (cx, cy) that minimises residuals to the linear
# fit r vs k (radial index).
def fit(cx, cy):
    polar = []
    for x, y in dots:
        polar.append((math.atan2(y-cy, x-cx), math.hypot(x-cx, y-cy)))
    polar.sort(key=lambda t: t[1])  # by radius -> the user placed them ordered
    # All dots are near the same angle phi_0.  Each consecutive dot is one turn
    # outward, so k = 0..N-1.
    rs = [r for _, r in polar]
    ths = [t for t, _ in polar]
    # Quick check: median theta
    phi0 = statistics.median(ths)
    # Linear regression r = a + b * k  (using k = index in sorted order)
    n = len(rs)
    ks = list(range(n))
    mk = sum(ks)/n; mr = sum(rs)/n
    num = sum((k-mk)*(r-mr) for k, r in zip(ks, rs))
    den = sum((k-mk)**2 for k in ks)
    b = num/den; a = mr - b*mk
    res = [r - (a + b*k) for k, r in zip(ks, rs)]
    rss = sum(x*x for x in res)
    return rss, a, b, phi0, polar

# Coarse-then-fine grid search around (387.86, 529.46)
best = None
for cx in [387 + dx*0.5 for dx in range(-12, 13)]:
    for cy in [529 + dy*0.5 for dy in range(-12, 13)]:
        rss, a, b, phi0, polar = fit(cx, cy)
        if best is None or rss < best[0]:
            best = (rss, cx, cy, a, b, phi0)
rss, cx, cy, a, b, phi0 = best
print(f"refined centre: ({cx}, {cy})  rss={rss:.4f}")

# Finer search
for _ in range(3):
    cx0, cy0 = cx, cy
    for dx in [(-1+i*0.1) for i in range(21)]:
        for dy in [(-1+i*0.1) for i in range(21)]:
            cxn, cyn = cx0+dx*0.5, cy0+dy*0.5
            rss, a, b, phi0, polar = fit(cxn, cyn)
            if rss < best[0]:
                best = (rss, cxn, cyn, a, b, phi0)
                cx, cy = cxn, cyn
rss, cx, cy, a, b, phi0 = best
print(f"final centre: ({cx:.4f}, {cy:.4f})")
print(f"a={a:.4f}, b_per_turn={b:.4f}, phi0={math.degrees(phi0):.2f} deg")

# Per-turn radial pitch = b
print(f"\nspiral pitch: {b:.4f} pts per turn")
print(f"min r (innermost dot): {a:.2f} pts  (k=0)")
print(f"max r (outermost dot): {a + b*(len(dots)-1):.2f} pts")

# Refit with theta_total parameterisation (continuous spiral):
# theta_total = phi0 + 2*pi*k  ->  r = a + b*k = a + (b/(2*pi))*(theta_total - phi0)
# So r = a - phi0*(b/(2*pi)) + (b/(2*pi))*theta_total
b_per_rad = b / (2*math.pi)
a_continuous = a - phi0 * b_per_rad
print(f"\ncontinuous form: r(theta_total) = {a_continuous:.4f} + {b_per_rad:.4f} * theta_total")

# Determine where the spiral path STARTS and ENDS.
# Inner dot at k=0 is on the innermost turn.  The spiral path likely starts
# from the OUTERMOST entrance (k=N-1) and winds inward to the central plaza.
# Compute total arc length.
# Arc length integral for r = A + B*theta:
#  L = integral sqrt(r^2 + (dr/dtheta)^2) dtheta = integral sqrt((A+B*th)^2 + B^2) dth
# Closed form:
def arc_length(theta0, theta1, A, B):
    # antiderivative of sqrt((A+B*t)^2 + B^2) dt is
    #  (1/(2B)) * [ u*sqrt(u^2+B^2) + B^2*ln(u+sqrt(u^2+B^2)) ]  where u = A+B*t
    def F(t):
        u = A + B*t
        s = math.sqrt(u*u + B*B)
        return (u*s + B*B*math.log(u + s)) / (2*B)
    return F(theta1) - F(theta0)

# theta range of dots
theta_start = phi0  # k=0 (innermost)
theta_end = phi0 + 2*math.pi*(len(dots)-1)  # k = N-1 (outermost)
L_pts = arc_length(theta_start, theta_end, a_continuous, b_per_rad)
print(f"\narc length between innermost and outermost dot: {L_pts:.2f} pts")

# Save fit
with open("processing/tmp/spiral_fit.json", "w") as f:
    json.dump({
        "center": [cx, cy],
        "phi0_rad": phi0,
        "phi0_deg": math.degrees(phi0),
        "a_per_index": a, "b_per_index": b,
        "a_continuous": a_continuous, "b_per_rad": b_per_rad,
        "theta_start": theta_start, "theta_end": theta_end,
        "n_dots": len(dots),
        "arc_length_pts": L_pts,
        "dot_positions": dots,
    }, f, indent=2)
print("Wrote processing/tmp/spiral_fit.json")

# Suggest possible meter scales
print("\nIf total spiral arc length (between innermost & outermost dot) is:")
for total_m in [50, 100, 150, 200, 250, 300, 400, 500, 800, 1000, 1500]:
    s = total_m / L_pts
    od_m = (a + b*(len(dots)-1)) * 2 * s
    pitch_m = b * s
    print(f"   {total_m:5d} m  -> 1pt = {s:.5f} m, outer diameter = {od_m:5.2f} m, "
          f"spiral pitch = {pitch_m*100:5.1f} cm/turn")
