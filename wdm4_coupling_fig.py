"""Coupling figure for the WDM4 report: the coupling rate from the mode solver, the shape of the
ring's corner next to the bus, and the power crossing per pass for the three banks.
Run after step15b_coupling.py: .venv/bin/python wdm4_coupling_fig.py"""
import json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import gdsfactory as gf
from cspdk.si220.cband import PDK; PDK.activate()
import wdm_models as m
from step16_chip_split import GAPS

d = json.load(open("data/strip_450x220.json")); g = d["gamma"]
gp = np.array([p["gap"] for p in d["points"]]); kp = np.array([p["kappa"] for p in d["points"]])
gaps = np.linspace(0.14, 0.40, 200); kappa = d["kappa0"] * np.exp(-g * (gaps - d["g0"]))
eul = gf.path.euler(radius=10, angle=90, p=0.5, use_eff=True, npoints=2000).points
cir = gf.path.arc(radius=10, angle=90, npoints=2000).points
l_euler = m.l_eff(10.0, 4.0); l_circle = 4.0 + np.sqrt(2 * np.pi * 10.0 / g)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
ax[0].semilogy(gaps * 1e3, kappa, "C0", label=f"fit: {d['kappa0']:.4f} · exp(−{g:.2f} (gap − 0.20))")
ax[0].semilogy(gp * 1e3, kp, "ko", label="mode solver (supermode split)")
ax[0].set(xlabel="gap (nm)", ylabel="coupling rate κ (rad/µm)", title="Coupling rate between two 450 nm strips"); ax[0].legend(fontsize=8)

ax[1].plot(eul[:, 0], np.abs(eul[:, 1]) * 1e3, "C3", label=f"Euler corner of the kit's ring: l_eff = {l_euler:.1f} µm")
ax[1].plot(cir[:, 0], np.abs(cir[:, 1]) * 1e3, "C7", ls="--", label=f"quarter circle, for comparison: l_eff = {l_circle:.1f} µm")
ax[1].axhline(1e3 / g, color="k", lw=0.6); ax[1].text(0.1, 1e3 / g + 8, "coupling has fallen to 1/e", fontsize=8)
ax[1].set(xlim=(0, 4), ylim=(0, 600), xlabel="distance along the bus from the end of the straight (µm)", ylabel="extra gap (nm)",
          title="How fast the ring's corner leaves the bus"); ax[1].legend(fontsize=8, loc="upper left")

ax[2].plot(gaps * 1e3, 100 * np.sin(kappa * l_euler) ** 2, "C3", label="Euler corner (the layout)")
ax[2].plot(gaps * 1e3, 100 * np.sin(kappa * l_circle) ** 2, "C7", ls="--", label="quarter circle")
for j, gap in enumerate(GAPS, start=1):
    K = 100 * float(m.coupling(1.55, gap, 10.0, 4.0)); ax[2].plot(gap * 1e3, K, "ko")
    ax[2].annotate(f"bank {j}\n{gap:.2f} µm, {K:.1f} %", (gap * 1e3, K), textcoords="offset points", xytext=(8, 6), fontsize=8)
ax[2].set(xlabel="gap (nm)", ylabel="power crossing per pass (%)", xlim=(130, 440), ylim=(0, 45), title="Coupling per pass, K = sin²(κ · l_eff)"); ax[2].legend(fontsize=8)
fig.tight_layout(); fig.savefig("img/wdm4_coupling.png", dpi=120)
print("l_eff Euler %.2f, circle %.2f; wrote img/wdm4_coupling.png" % (l_euler, l_circle))
