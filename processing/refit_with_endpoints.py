"""Refit the Archimedean spiral using all anchors:
   - START at the BIGGEST RED dot   (r_red, theta_red)
   - END   at the BLUE dot           (r_blue, theta_blue)
   - PASSES through (or near) the 41 grey dots
The path winds CCW (in PDF y-down: math theta decreasing).

Parameterise by signed turn count tau in [0, T], where T is the total CCW
turns from red to blue.  The number of full turns N is an integer; we sweep N
and pick the value that best matches the grey dots.

At parameter tau:
    theta(tau) = theta_red - 2*pi*tau                 (CCW visual)
    r(tau)    = r_red + (r_blue - r_red) * tau / T
with T such that:
    theta(T) ≡ theta_blue  (mod 2*pi)
i.e.  T = (theta_red - theta_blue) / (2*pi)  +  N
"""
import fitz, math, json

PDF = "processing/Spiral_5m sections and spokes-grey dots.pdf"
doc = fitz.open(PDF)
drawings = doc[0].get_drawings()

grey, red, blue = [], [], []
for d in drawings:
    if d.get("type") == "f" and d.get("fill"):
        c = tuple(round(x, 3) for x in d["fill"])
        r = d["rect"]
        cd = ((r.x0 + r.x1)/2, (r.y0 + r.y1)/2)
        diam = max(r.x1-r.x0, r.y1-r.y0)
        if abs(c[0]-0.549) < 0.01:
            grey.append(cd)
        elif c[0] > 0.9 and c[1] < 0.1 and c[2] < 0.1:
            red.append((*cd, diam))
        elif c[2] > 0.9 and c[0] < 0.1:
            blue.append(cd)
red.sort(key=lambda t: -t[2])
print(f"grey={len(grey)} red={len(red)} blue={len(blue)}")

with open("processing/tmp/spiral_fit.json") as f:
    prev = json.load(f)
cx, cy = prev["center"]

def polar(p):
    return (math.atan2(p[1]-cy, p[0]-cx), math.hypot(p[0]-cx, p[1]-cy))

red_th, red_r = polar(red[0][:2])
blue_th, blue_r = polar(blue[0])
print(f"red1: theta={math.degrees(red_th):.2f}, r={red_r:.3f}")
print(f"blue: theta={math.degrees(blue_th):.2f}, r={blue_r:.3f}")

# Direct CCW arc from red to blue (math theta decreasing).
# CCW arc length in turns = (theta_red - theta_blue) / (2*pi)  (must be positive)
direct = (red_th - blue_th) / (2 * math.pi)
while direct < 0:
    direct += 1.0
print(f"direct CCW arc (red -> blue): {direct:.4f} turns ({direct*360:.2f} deg)")

# For each candidate N (number of additional full CCW turns), compute spiral
# parameters and evaluate fit to grey dots.
def angular_residual(theta_actual, theta_pred):
    d = (theta_actual - theta_pred) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d

best = None
for N in range(30, 55):
    T = direct + N                        # total CCW turns
    pitch = (blue_r - red_r) / T          # pts per turn (radial)
    # Predict theta at each grey dot from its radius, then compare to actual theta
    # turns_from_red = (r - red_r) / pitch
    # theta_pred = red_th - 2*pi * turns_from_red
    rss = 0.0
    n_used = 0
    for gx, gy in grey:
        gth, gr = polar((gx, gy))
        if gr < red_r or gr > blue_r:
            continue
        tau = (gr - red_r) / pitch
        th_pred = red_th - 2 * math.pi * tau
        d = angular_residual(gth, th_pred)
        rss += d * d
        n_used += 1
    if n_used == 0:
        continue
    rms = math.sqrt(rss / n_used)
    if best is None or rms < best[0]:
        best = (rms, N, T, pitch)
    print(f"  N={N:2d}  T={T:.4f} turns  pitch={pitch:.4f} pts/turn  rms_theta={math.degrees(rms):6.2f} deg")

rms, N_best, T_best, pitch_best = best
print(f"\nBEST: N={N_best}, total turns T={T_best:.4f}, pitch={pitch_best:.4f}, rms={math.degrees(rms):.3f} deg")

# Save updated fit anchored to red + blue
result = {
    "center": [cx, cy],
    "red_xy": list(red[0][:2]),
    "red_theta_rad": red_th,
    "red_r": red_r,
    "blue_xy": list(blue[0]),
    "blue_theta_rad": blue_th,
    "blue_r": blue_r,
    "N_extra_turns": N_best,
    "total_turns": T_best,
    "pitch_pts_per_turn": pitch_best,
    "n_grey": len(grey),
    "grey_dots": grey,
}
with open("processing/tmp/spiral_fit2.json", "w") as f:
    json.dump(result, f, indent=2)
print("Wrote processing/tmp/spiral_fit2.json")
