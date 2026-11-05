"""The virtual measurement of the MZI4 die: spectra of the three unbalanced interferometers
(cross and bar, minus the loopback), the group index from their free spectral ranges, and the
switch's transfer against heater phase. Run: .venv/bin/python mzi_predict.py"""
import sys, json, re
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import gdsfactory as gf, sax, jax.numpy as jnp
sys.path.insert(0, ".")
src = open("mzi_die.py").read().replace('if __name__ == "__main__":', "if False:")
exec(src)                                      # builds `chip` with its named fiber ports
from cspdk.si220.cband import PDK
import mzi_models, wdm_models

net = chip.get_netlist(recursive=True)
models = dict(PDK.models); models.update(mzi_models.MODELS)
ELECTRICAL = ("via_stack", "pad", "straight_metal", "bend_metal", "wire_corner", "compass", "rectangle",
              "text_rectangular", "die", "Unnamed", "straight_heater_metal", "heater_arm")   # the last two become leaves with our model
for k in [k for k in net if any(k.startswith(e) for e in ELECTRICAL)]:
    del net[k]
def is_optical_cell(name):
    return (name in models or name in net) and not any(name.startswith(e) for e in ELECTRICAL if e not in ("straight_heater_metal", "heater_arm"))
for cellname, n in net.items():
    keep = {k: v for k, v in n["instances"].items() if is_optical_cell(v["component"])}
    n["instances"] = keep
    optical = lambda ref: ref.split(",")[0] in keep and re.match(r"^o\d+$", ref.split(",")[1]) is not None   # optical ports only: o1, o2, ...
    n["connections"] = {a: b for a, b in n.get("connections", {}).items() if optical(a) and optical(b)}
    n["ports"] = {pn: ref for pn, ref in n.get("ports", {}).items() if optical(ref)}
    ref_of = lambda x: x if isinstance(x, str) else f'{x["instance"]},{x["port"]}'
    n["nets"] = [nt for nt in n.get("nets", []) if all(optical(ref_of(v)) for v in nt.values())]
top = net[chip.name]
print("top-level instances:", sorted(set(v["component"] for v in top["instances"].values())))
sw_cell = [k for k in net if k.startswith("mzi2x2_2x2") and "DL0" in k]
print("switch cell:", sw_cell, "| its instances:", sorted(set(v["component"] for v in net[sw_cell[0]]["instances"].values())) if sw_cell else None)

circuit, info = sax.circuit(net, models=models)
dB = lambda x: 10 * np.log10(np.abs(np.asarray(x)) ** 2 + 1e-30)
lin = lambda x: np.abs(np.asarray(x)) ** 2

# ---- spectra of the passive interferometers, and the switch at rest --------------------------
wl = jnp.linspace(1.50, 1.60, 4001); w = np.asarray(wl) * 1e3
S0 = circuit(wl=wl, dphi=0.0)
lb = dB(S0[("lb1", "lb2")])
out = {"p_pi_mw": mzi_models.P_PI_MW, "neff0": wdm_models.NEFF0, "ng": wdm_models.NG, "mzis": {}}
fig, axes = plt.subplots(4, 1, figsize=(9, 11), sharex=True)
for ax, (tag, dl) in zip(axes, [("sw", 0.0)] + [(f"m{int(d)}", d) for d in DELTAS]):
    cross, bar = dB(S0[(f"{tag}_in", f"{tag}_cross")]) - lb, dB(S0[(f"{tag}_in", f"{tag}_bar")]) - lb
    ax.plot(w, cross, label="cross port (o3)"); ax.plot(w, bar, label="bar port (o4)")
    ax.set_ylim(-40, 2); ax.set_ylabel("interferometer alone (dB)")
    entry = {"delta_length_um": dl, "wl_nm": [round(float(v), 3) for v in w[::10]], "cross_db": [round(float(v), 3) for v in cross[::10]], "bar_db": [round(float(v), 3) for v in bar[::10]]}
    if dl > 0:
        i = np.where((cross[1:-1] > cross[:-2]) & (cross[1:-1] > cross[2:]) & (cross[1:-1] > -3))[0] + 1   # transmission maxima
        peaks = w[i]; fsr = float(np.mean(np.diff(peaks))) if len(peaks) > 1 else float("nan")
        ng = 1.55e3 ** 2 / (fsr * dl * 1e3) if fsr == fsr else float("nan")   # n_g = lambda^2 / (FSR dL), lambda and FSR in nm, dL in nm
        er = float(np.max(cross) - np.min(cross))
        entry.update({"fsr_nm": round(fsr, 3), "ng_from_fsr": round(ng, 4), "extinction_db": round(er, 1), "peaks_nm": [round(float(p), 2) for p in peaks]})
        ax.set_title(f"delta L = {dl:.0f} um: FSR {fsr:.2f} nm -> n_g = {ng:.3f} (model {wdm_models.NG:.3f}); extinction {er:.0f} dB")
        for p in peaks: ax.axvline(p, color="gray", ls=":", lw=0.6)
    else:
        ax.set_title("balanced switch at rest (heater off): the cross port carries the light over the whole band")
    out["mzis"][tag] = entry
axes[-1].set_xlabel("wavelength (nm)")
h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=2, frameon=False)
plt.tight_layout(rect=[0, 0.03, 1, 1]); plt.savefig("img/mzi/spectra.png", dpi=120); plt.close()

# ---- the switch against heater phase, at 1550 nm, ideal MMIs and with a 5 % imbalance ---------
phi = np.linspace(0, 2 * np.pi, 361)
def transfer(imbalance):
    mzi_models.MMI_IMBALANCE = imbalance
    circ, _ = sax.circuit(net, models=models)
    S1 = circ(wl=jnp.array([1.55]), dphi=0.0)
    lb1 = lin(S1[("lb1", "lb2")])[0]
    pc, pb = [], []
    for f in phi:
        S = circ(wl=jnp.array([1.55]), dphi=float(f))
        pc.append(lin(S[("sw_in", "sw_cross")])[0] / lb1); pb.append(lin(S[("sw_in", "sw_bar")])[0] / lb1)
    return np.array(pc), np.array(pb)
pc0, pb0 = transfer(0.0); pc1, pb1 = transfer(0.007); pc5, pb5 = transfer(0.05); mzi_models.MMI_IMBALANCE = 0.0
P = phi / np.pi * mzi_models.P_PI_MW
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(P, pc0, label="cross, ideal MMIs"); ax[0].plot(P, pb0, label="bar, ideal MMIs")
ax[0].plot(P, pc1, "--", label="cross, 0.7 % imbalance (foundry data)"); ax[0].plot(P, pb1, "--", label="bar, 0.7 % imbalance")
ax[0].plot(P, pc5, ":", label="cross, 5 % imbalance"); ax[0].plot(P, pb5, ":", label="bar, 5 % imbalance")
ax[0].set(xlabel=f"heater power (mW), P_pi = {mzi_models.P_PI_MW:.0f} mW, the foundry's bound", ylabel="transmission (linear)", title="(a) the two outputs against heater power")
ax[1].plot(P, 10 * np.log10(pc0 + 1e-12), label="cross, ideal"); ax[1].plot(P, 10 * np.log10(pb0 + 1e-12), label="bar, ideal")
ax[1].plot(P, 10 * np.log10(pc1 + 1e-12), "--", label="cross, 0.7 %"); ax[1].plot(P, 10 * np.log10(pb1 + 1e-12), "--", label="bar, 0.7 %")
ax[1].plot(P, 10 * np.log10(pc5 + 1e-12), ":", label="cross, 5 %"); ax[1].plot(P, 10 * np.log10(pb5 + 1e-12), ":", label="bar, 5 %")
ax[1].set(xlabel="heater power (mW)", ylabel="transmission (dB)", ylim=(-50, 2), title="(b) in decibels: the floor set by the MMI imbalance")
h, l = ax[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=9)
plt.tight_layout(rect=[0, 0.11, 1, 1]); plt.savefig("img/mzi/switch.png", dpi=120); plt.close()
er_ideal = 10 * np.log10(pc0[0] / (pb0[0] + 1e-12)); er_1 = 10 * np.log10(pc1[0] / (pb1[0] + 1e-12)); er_5 = 10 * np.log10(pc5[0] / (pb5[0] + 1e-12))
il = -10 * np.log10(pc0[0])
out["switch"] = {"phi": [round(float(v), 4) for v in phi], "p_cross": [round(float(v), 5) for v in pc0], "p_bar": [round(float(v), 5) for v in pb0],
                 "p_cross_imb5": [round(float(v), 5) for v in pc5], "p_bar_imb5": [round(float(v), 5) for v in pb5],
                 "er_ideal_db": round(float(er_ideal), 1), "er_imb07_db": round(float(er_1), 1), "er_imb5_db": round(float(er_5), 1), "insertion_loss_db": round(float(il), 2)}
json.dump(out, open("img/mzi/sim.json", "w"), separators=(",", ":"))
print(f"switch at rest: cross {10*np.log10(pc0[0]):.2f} dB, bar {10*np.log10(pb0[0]+1e-12):.1f} dB; at pi: cross {10*np.log10(pc0[180]+1e-12):.1f} dB, bar {10*np.log10(pb0[180]):.2f} dB")
print(f"extinction ideal {er_ideal:.1f} dB, with 0.7 % imbalance {er_1:.1f} dB, with 5 % {er_5:.1f} dB; insertion loss at rest {il:.2f} dB")
for tag, e in out["mzis"].items():
    if "fsr_nm" in e: print(f"{tag}: FSR {e['fsr_nm']} nm, n_g {e['ng_from_fsr']}, extinction {e['extinction_db']} dB, peaks {e['peaks_nm'][:4]}...")
print("wrote img/mzi/spectra.png img/mzi/switch.png img/mzi/sim.json")
