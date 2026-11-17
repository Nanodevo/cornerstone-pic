"""Step 18: the mode solver on the WDM4 strip, shown. femwell (finite elements) on the
CORNERSTONE 450 x 220 nm strip in oxide: the fundamental TE and TM mode fields, the even
and odd supermodes of the bus-ring pair at the design gap (the origin of the coupling),
and the effective index versus strip width (where the strip stops being single-mode).
Run with the cpo-pic environment (it has femwell):
  ~/Documents/claude/Projects/cpo-pic/.venv/bin/python step18_modes.py
"""
import time, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from femwell.maxwell.waveguide import compute_modes
from skfem import Basis, ElementTriP0, MeshTri

N_SI, N_OX, T, WL = 3.4757, 1.4440, 0.220, 1.55
GAP = 0.31
L_EFF = 9.4          # effective coupling length of the ring's coupler, integrated along its Euler corners (wdm_models.l_eff)

def grid(anchors, lo, hi, d0=0.010, n_out=26, n_in=10):
    pts = [np.array([lo, hi]), np.asarray(anchors, float)]
    for a, b in zip(anchors[:-1], anchors[1:]): pts.append(np.linspace(a, b, n_in))
    for a in anchors:
        for sign, span in ((-1.0, a - lo), (1.0, hi - a)):
            if span > d0: pts.append(a + sign * np.geomspace(d0, span, n_out))
    g = np.unique(np.concatenate(pts)); return g[(g >= lo) & (g <= hi)]

def mesh_for(cores, half=2.5):
    xa = sorted({x for c in cores for x in c})
    xs = grid(xa, -half, half); ys = grid([0.0, T], -half, half)
    return MeshTri.init_tensor(xs, ys).with_subdomains({
        "core": lambda x: sum(((x[0] >= a) & (x[0] <= b)) for a, b in cores) * (x[1] >= 0) * (x[1] <= T) > 0})

def solve(mesh, wl=WL, num_modes=4):
    basis0 = Basis(mesh, ElementTriP0()); eps = basis0.zeros(dtype=complex); eps[:] = N_OX ** 2
    eps[basis0.get_dofs(elements="core")] = N_SI ** 2
    modes = [m for m in compute_modes(basis0, eps, wavelength=wl, num_modes=num_modes, order=1) if N_OX < np.real(m.n_eff) < N_SI]
    return sorted(modes, key=lambda m: -np.real(m.n_eff))

def field_on_grid(mode, xs, ys):
    """|E| sampled on a regular grid for plotting."""
    from skfem import ElementTriP1
    basis = mode.basis; E = mode.E
    # interpolate the transverse field magnitude with the basis' own probes
    X, Y = np.meshgrid(xs, ys); pts = np.vstack([X.ravel(), Y.ravel()])
    try:
        (Ex, Ey), Ez = basis.split(E)
        probes_t = Ex.basis.probes(pts) if hasattr(Ex, "basis") else None
    except Exception:
        probes_t = None
    # robust path: use the mode's own interpolation helper on a fine element set
    ex = mode.basis.interpolator(np.real(mode.E))(pts) if False else None
    return None

t0 = time.time()
# 1. single strip: fundamental TE and TM
W = 0.45
m = mesh_for([(-W/2, W/2)])
modes = solve(m, num_modes=4)
te = [x for x in modes if x.te_fraction > 0.5][0]; tm = [x for x in modes if x.te_fraction <= 0.5][0]
print(f"strip {W*1e3:.0f} x {T*1e3:.0f} nm: TE0 n_eff {np.real(te.n_eff):.4f} (TE fraction {te.te_fraction:.2f}), TM0 n_eff {np.real(tm.n_eff):.4f} (TE fraction {tm.te_fraction:.2f})   [{time.time()-t0:.0f} s]")

# 2. supermodes at the design gap
m2 = mesh_for([(-GAP/2 - W, -GAP/2), (GAP/2, GAP/2 + W)])
sm = [x for x in solve(m2, num_modes=6) if x.te_fraction > 0.5][:2]
dn = np.real(sm[0].n_eff) - np.real(sm[1].n_eff)
print(f"pair at gap {GAP} um: even n_eff {np.real(sm[0].n_eff):.5f}, odd {np.real(sm[1].n_eff):.5f}, split {dn:.5f} -> kappa {np.pi*dn/WL:.4f} rad/um   [{time.time()-t0:.0f} s]")

# 3. n_eff vs width: where the strip stops being single-mode (second TE mode appears)
widths = np.arange(0.30, 0.80, 0.05); rows = []
for w in widths:
    ms = solve(mesh_for([(-w/2, w/2)]), num_modes=5)
    tes = [x for x in ms if x.te_fraction > 0.5]; tms = [x for x in ms if x.te_fraction <= 0.5]
    rows.append((w, np.real(tes[0].n_eff) if tes else np.nan, np.real(tes[1].n_eff) if len(tes) > 1 else np.nan, np.real(tms[0].n_eff) if tms else np.nan))
    print(f"  width {w*1e3:.0f} nm: TE0 {rows[-1][1]:.4f}  TE1 {rows[-1][2] if not np.isnan(rows[-1][2]) else float('nan'):.4f}  TM0 {rows[-1][3]:.4f}")
rows = np.array(rows)

# ---- figure: mode fields via femwell's own plotting, plus the width sweep
fig = plt.figure(figsize=(12, 7.5))
ax1 = fig.add_subplot(2, 3, 1); te.plot_intensity(ax=ax1, colorbar=False); ax1.set_title(f"TE0, n_eff = {np.real(te.n_eff):.3f}"); ax1.set_xlim(-1, 1); ax1.set_ylim(-0.7, 0.9)
ax2 = fig.add_subplot(2, 3, 2); tm.plot_intensity(ax=ax2, colorbar=False); ax2.set_title(f"TM0, n_eff = {np.real(tm.n_eff):.3f}"); ax2.set_xlim(-1, 1); ax2.set_ylim(-0.7, 0.9)
ax3 = fig.add_subplot(2, 3, 3)
ax3.plot(rows[:, 0]*1e3, rows[:, 1], "o-", label="TE0"); ax3.plot(rows[:, 0]*1e3, rows[:, 3], "s-", label="TM0"); ax3.plot(rows[:, 0]*1e3, rows[:, 2], "^-", label="TE1 (second mode)")
ax3.axvline(450, color="k", ls="--", lw=.8); ax3.text(455, N_OX + 0.03, "design width", fontsize=8)
ax3.axhline(N_OX, color="gray", lw=.8); ax3.set_xlabel("strip width (nm)"); ax3.set_ylabel("effective index at 1550 nm"); ax3.legend(fontsize=8); ax3.set_title("Single-mode range of the 220 nm strip")
ax4 = fig.add_subplot(2, 3, 4); sm[0].plot_intensity(ax=ax4, colorbar=False); ax4.set_title(f"even supermode, n_eff = {np.real(sm[0].n_eff):.4f}"); ax4.set_xlim(-1.4, 1.4); ax4.set_ylim(-0.7, 0.9)
ax5 = fig.add_subplot(2, 3, 5); sm[1].plot_intensity(ax=ax5, colorbar=False); ax5.set_title(f"odd supermode, n_eff = {np.real(sm[1].n_eff):.4f}"); ax5.set_xlim(-1.4, 1.4); ax5.set_ylim(-0.7, 0.9)
ax6 = fig.add_subplot(2, 3, 6); ax6.axis("off")
ax6.text(0, 0.95, f"Bus-ring pair at the design gap ({GAP:.2f} µm)", fontsize=11, weight="bold", va="top")
ax6.text(0, 0.80, f"index split Δn = {dn:.5f}\nκ = πΔn/λ = {np.pi*dn/WL:.4f} rad/µm\nfull transfer length π/(2κ) = {np.pi/(2*np.pi*dn/WL):.0f} µm\n\nOver the ring's effective coupling length of {L_EFF} µm\nthe power crossing per pass is sin²(κ·l_eff) = {100*np.sin(np.pi*dn/WL*L_EFF)**2:.1f} %.\n\nThe two waveguides are one system with two modes;\nlight launched in the bus is a superposition of both,\nand their phase difference moves power across the gap.", fontsize=9.5, va="top", linespacing=1.5)
fig.suptitle("Mode solver on the WDM4 strip: CORNERSTONE 450 × 220 nm silicon in oxide, femwell finite elements, λ = 1550 nm", fontsize=12)
plt.tight_layout(); plt.savefig("img/step18_modes.png", dpi=130); print("wrote img/step18_modes.png   [%.0f s]" % (time.time()-t0))
