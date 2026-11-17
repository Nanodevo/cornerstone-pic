"""Step 19: how much the strip's effective index moves per nanometre of silicon thickness.
femwell on the CORNERSTONE 450 nm strip in oxide, TE0 at 1550 nm, thickness 210 to 230 nm
(same mesh recipe and indices as step 18). Used by the test station's die model.
Run with the cpo-pic environment:
  ~/Documents/claude/Projects/cpo-pic/.venv/bin/python step19_thickness.py
"""
import json, numpy as np
from femwell.maxwell.waveguide import compute_modes
from skfem import Basis, ElementTriP0, MeshTri

N_SI, N_OX, W, WL = 3.4757, 1.4440, 0.45, 1.55

def grid(anchors, lo, hi, d0=0.010, n_out=26, n_in=10):
    pts = [np.array([lo, hi]), np.asarray(anchors, float)]
    for a, b in zip(anchors[:-1], anchors[1:]): pts.append(np.linspace(a, b, n_in))
    for a in anchors:
        for sign, span in ((-1.0, a - lo), (1.0, hi - a)):
            if span > d0: pts.append(a + sign * np.geomspace(d0, span, n_out))
    g = np.unique(np.concatenate(pts)); return g[(g >= lo) & (g <= hi)]

def te0(t, w=W, wl=WL, half=2.5):
    xs = grid([-w/2, w/2], -half, half); ys = grid([0.0, t], -half, half)
    mesh = MeshTri.init_tensor(xs, ys).with_subdomains({
        "core": lambda x: (x[0] >= -w/2) & (x[0] <= w/2) & (x[1] >= 0) & (x[1] <= t)})
    b0 = Basis(mesh, ElementTriP0()); eps = b0.zeros(dtype=complex); eps[:] = N_OX ** 2
    eps[b0.get_dofs(elements="core")] = N_SI ** 2
    modes = [m for m in compute_modes(b0, eps, wavelength=wl, num_modes=4, order=1) if m.te_fraction > 0.5]
    return max(np.real(m.n_eff) for m in modes)

ts = [0.210, 0.215, 0.219, 0.220, 0.221, 0.225, 0.230]
ne = [te0(t) for t in ts]
for t, n in zip(ts, ne): print(f"thickness {t*1e3:.0f} nm: TE0 n_eff {n:.5f}")
d1 = (ne[4] - ne[2]) / 2.0           # per nm, from 219 and 221 nm
d10 = (ne[6] - ne[0]) / 20.0         # per nm, from 210 and 230 nm
dw = (te0(0.220, w=0.451) - te0(0.220, w=0.449)) / 2.0
print(f"dn_eff/dt = {d1:.5f} per nm (219-221 nm), {d10:.5f} per nm (210-230 nm)")
print(f"check, dn_eff/dw = {dw:.5f} per nm (449-451 nm); step 18 sweep gave 0.00219")
json.dump({"thickness_um": ts, "n_eff": ne, "dneff_dt_per_nm": d1, "dneff_dt_per_nm_wide": d10, "dneff_dw_per_nm": dw},
          open("data_step19_thickness.json", "w"), indent=1)
