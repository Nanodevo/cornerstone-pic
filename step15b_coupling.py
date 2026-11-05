"""Step 15b: kappa0 and the indices for wdm_models.py from a mode solver (femwell).

Cross-section: CORNERSTONE strip, 450 x 220 nm silicon, oxide above and below.
1. single strip at 1540/1550/1560 nm  -> n_eff, n_g
2. two strips at gaps 0.15 .. 0.35 um -> even/odd TE supermodes, split dn,
   kappa = pi dn / wl, fitted to kappa0 exp(-gamma (gap - 0.2))
Writes data/strip_450x220.json, which wdm_models.py reads when present.
Needs femwell, in its own environment (see README).
"""
import json, time, pathlib
import numpy as np
from femwell.maxwell.waveguide import compute_modes
from skfem import Basis, ElementTriP0, MeshTri

HERE = pathlib.Path(__file__).parent
N_SI, N_OX = 3.4757, 1.4440
W, T = 0.450, 0.220
GAPS = (0.15, 0.20, 0.25, 0.30, 0.35)
WLS = (1.540, 1.550, 1.560)


def grid(anchors, lo, hi, d0=0.010, n_out=26, n_in=10):
    pts = [np.array([lo, hi]), np.asarray(anchors, float)]
    for a, b in zip(anchors[:-1], anchors[1:]):
        pts.append(np.linspace(a, b, n_in))
    for a in anchors:
        for sign, span in ((-1.0, a - lo), (1.0, hi - a)):
            if span > d0:
                pts.append(a + sign * np.geomspace(d0, span, n_out))
    g = np.unique(np.concatenate(pts))
    return g[(g >= lo) & (g <= hi)]


def mesh_for(cores, half=3.0):
    """cores: list of (x_left, x_right) silicon strips, all of height T at y in [0, T]."""
    xa = sorted({x for c in cores for x in c})
    xs = grid(xa, -half, half); ys = grid([0.0, T], -half, half)
    return MeshTri.init_tensor(xs, ys).with_subdomains({
        "core": lambda x: sum(((x[0] >= a) & (x[0] <= b)) for a, b in cores) * (x[1] >= 0) * (x[1] <= T) > 0,
    })


def solve(mesh, wl, num_modes):
    basis0 = Basis(mesh, ElementTriP0())
    eps = basis0.zeros(dtype=complex); eps[:] = N_OX ** 2
    eps[basis0.get_dofs(elements="core")] = N_SI ** 2
    modes = compute_modes(basis0, eps, wavelength=wl, num_modes=num_modes, order=1)
    modes = [m for m in modes if N_OX < np.real(m.n_eff) < N_SI]
    return sorted(modes, key=lambda m: -np.real(m.n_eff))


t0 = time.time()
# 1. single strip: n_eff(wl) -> n_g
single = mesh_for([(-W / 2, W / 2)])
neffs = []
for wl in WLS:
    m = [m for m in solve(single, wl, 4) if m.te_fraction > 0.5][0]
    neffs.append(float(np.real(m.n_eff)))
    print(f"single strip {wl:.3f} um: n_eff {neffs[-1]:.4f} (TE fraction {m.te_fraction:.2f})")
n0 = neffs[1]; dn_dwl = (neffs[2] - neffs[0]) / (WLS[2] - WLS[0])
ng = n0 - WLS[1] * dn_dwl
print(f"n_eff0 {n0:.4f}, n_g {ng:.4f}   ({time.time()-t0:.0f} s)")

# 2. two strips: supermode split -> kappa(gap)
rows = []
for gap in GAPS:
    m = mesh_for([(-gap / 2 - W, -gap / 2), (gap / 2, gap / 2 + W)])
    te = [x for x in solve(m, 1.55, 6) if x.te_fraction > 0.5][:2]
    dn = abs(float(np.real(te[0].n_eff)) - float(np.real(te[1].n_eff)))
    kappa = np.pi * dn / 1.55
    rows.append((gap, dn, kappa))
    print(f"gap {gap:.2f} um: split dn {dn:.5f}, kappa {kappa:.4f} rad/um   ({time.time()-t0:.0f} s)")
g = np.array([r[0] for r in rows]); k = np.array([r[2] for r in rows])
slope, icpt = np.polyfit(g - 0.20, np.log(k), 1)
kappa0, gamma = float(np.exp(icpt)), float(-slope)
gamma_formula = 2 * np.pi / 1.55 * np.sqrt(n0 ** 2 - N_OX ** 2)
print(f"fit: kappa0 {kappa0:.4f} rad/um at 0.20 um, gamma {gamma:.2f}/um (formula gamma {gamma_formula:.2f}/um)")
out = dict(width=W, thickness=T, wl0=1.55, neff0=n0, ng=ng, kappa0=kappa0, g0=0.20, gamma=gamma,
           gamma_formula=gamma_formula, points=[dict(gap=a, dn=b, kappa=c) for a, b, c in rows])
(HERE / "data" / "strip_450x220.json").write_text(json.dumps(out, indent=1))
print("wrote data/strip_450x220.json")
