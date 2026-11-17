"""Step 17: the virtual measurement of the split die. Same method as step 14, on the
three banks of step16_chip_split.py: for each bank, input -> four drops and through,
minus the shared loopback, side by side. Run: python3 step17_predict_split.py"""
import sys
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import gdsfactory as gf, sax, jax.numpy as jnp
sys.path.insert(0, ".")
src = open("step16_chip_split.py").read().replace('if __name__ == "__main__":', "if False:")
exec(src)                                    # builds `chip` with its named fiber ports
from cspdk.si220.cband import PDK
import wdm_models

net = chip.get_netlist(recursive=True)
models = dict(PDK.models); models.update(wdm_models.MODELS)
ELECTRICAL = ("via_stack", "pad", "straight_metal", "bend_metal", "wire_corner", "compass", "rectangle",
              "text_rectangular", "die", "Unnamed")
def is_optical_cell(name):
    return (name in models or name in net) and not any(name.startswith(e) for e in ELECTRICAL)
for k in [k for k in net if any(k.startswith(e) for e in ELECTRICAL)]:
    del net[k]
for cellname, n in net.items():
    keep = {k: v for k, v in n["instances"].items() if is_optical_cell(v["component"])}
    n["instances"] = keep
    optical = lambda ref: ref.split(",")[0] in keep and not ref.split(",")[1].startswith("e") and not ref.split(",")[1].endswith(("_e", "_s"))
    n["connections"] = {a: b for a, b in n.get("connections", {}).items() if optical(a) and optical(b)}
    n["ports"] = {pn: ref for pn, ref in n.get("ports", {}).items() if optical(ref)}
    ref_of = lambda x: x if isinstance(x, str) else f'{x["instance"]},{x["port"]}'
    n["nets"] = [nt for nt in n.get("nets", []) if all(optical(ref_of(v)) for v in nt.values())]

circuit, info = sax.circuit(net, models=models)
wl = jnp.linspace(1.542, 1.562, 10001)                # 2 pm steps
S = circuit(wl=wl)
dB = lambda x: 10 * np.log10(np.abs(np.asarray(x)) ** 2 + 1e-30)
lb = dB(S[("lb1", "lb2")])
w = np.asarray(wl) * 1e3

fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
for j, (ax, gap) in enumerate(zip(axes, GAPS), start=1):
    for n in ("d1", "d2", "d3", "d4", "thru"):
        ax.plot(w, dB(S[(f"b{j}_in", f"b{j}_{n}")]) - lb, label=n)
    ax.set_ylim(-45, 2); ax.set_ylabel("ring bank alone (dB)")
    ax.set_title(f"bank {j}: gap {gap:.2f} um, coupling {100*float(wdm_models.coupling(1.55, gap, 10.0, 4.0)):.1f}% per pass")
    ax.legend(fontsize=8, ncol=5, loc="lower right")
axes[-1].set_xlabel("wavelength (nm)")
plt.tight_layout(); plt.savefig("img/step17_split_spectra.png", dpi=120)

# numbers per bank: drop peak, its 3 dB width, and the neighbour leaking into it
for j, gap in enumerate(GAPS, start=1):
    t2 = dB(S[(f"b{j}_in", f"b{j}_d2")]) - lb
    i = int(np.argmax(t2)); peak = t2[i]
    lo = i
    while lo > 0 and t2[lo - 1] > peak - 3: lo -= 1
    hi = i
    while hi < len(t2) - 1 and t2[hi + 1] > peak - 3: hi += 1
    fwhm = w[hi] - w[lo]                                   # contiguous 3 dB width around this peak only
    t1_at_2 = (dB(S[(f"b{j}_in", f"b{j}_d1")]) - lb)[i]
    print(f"bank {j} (gap {gap:.2f}): drop2 peak {peak:.2f} dB at {w[i]:.2f} nm, 3 dB width {fwhm:.3f} nm, neighbour d1 at that wavelength {t1_at_2:.1f} dB")
    peaks = []
    for n in ("d1", "d2", "d3", "d4"):
        t = dB(S[(f"b{j}_in", f"b{j}_{n}")]) - lb
        sel = (w > 1548.0) & (w < 1555.0); peaks.append(w[sel][int(np.argmax(t[sel]))])
    others = sum(10 ** ((dB(S[(f"b{j}_in", f"b{j}_d1")]) - lb)[np.argmin(abs(w - p))] / 10) for p in peaks[1:])
    print(f"   drop peaks {[round(p, 2) for p in peaks]} nm, spacings {[round(b - a, 2) for a, b in zip(peaks, peaks[1:])]} nm; "
          f"channels 2-4 together in drop 1: {10 * np.log10(others):.1f} dB")
print("wrote img/step17_split_spectra.png")

# the design bank as the probe station would record it: coupler hump included, then loopback subtracted
fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
ax[0].plot(w, lb, "k", label="loopback (two couplers + waveguide)")
for n in ("d1", "d2", "d3", "d4", "thru"):
    ax[0].plot(w, dB(S[("b2_in", f"b2_{n}")]), label=f"in to {n}")
    ax[1].plot(w, dB(S[("b2_in", f"b2_{n}")]) - lb, label=f"in to {n}, minus loopback")
ax[0].set_ylabel("transmission (dB)"); ax[0].set_ylim(-60, 0); ax[0].legend(fontsize=8, ncol=3, loc="lower right"); ax[0].set_title(f"bank 2 (gap {GAPS[1]:.2f} um) as it would be recorded: couplers included")
ax[1].set_ylabel("ring bank alone (dB)"); ax[1].set_xlabel("wavelength (nm)"); ax[1].set_ylim(-45, 3); ax[1].legend(fontsize=8, ncol=3, loc="lower right")
plt.tight_layout(); plt.savefig("img/step17_bank2_recorded.png", dpi=120); print("wrote img/step17_bank2_recorded.png")
