"""Step 14: the virtual measurement. Builds the chip from step10_chip.py, exposes the eight
fiber ports, simulates the whole netlist in SAX with the PDK compact models, and plots what
the probe station would record: raw spectra with the coupler hump, and the ring bank alone
after subtracting the loopback. NB: the PDK ring-coupler model is marked incomplete by its
authors (see step 14 notes); absolute drop levels from it are not to be trusted."""
import sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, ".")
import gdsfactory as gf, sax, jax.numpy as jnp
src = open("step10_chip.py").read().replace("chip.show()", "").replace('chip.write_gds("gds/step10_chip.gds")', "")
src = src.replace("from step10_wdm_bank import c as bank", open("step10_wdm_bank.py").read().replace("c.show()", "").replace('c.write_gds("gds/step8_heated_bank.gds")', "").replace('c.write_gds("gds/step10_wdm_bank.gds")', "") + "\nbank = c\n")
exec(src)
# expose the fiber ports of the eight couplers as chip ports: in, d1..d4, thru, lb1, lb2
names = ["in", "d1", "d2", "d3", "d4", "thru", "lb1", "lb2"]
for n, g in zip(names, couplers):
    chip.add_port(n, port=g.ports["o2"])
net = chip.get_netlist(recursive=True)
tops = list(net.keys()); print("netlist cells:", len(tops))
# models: the PDK's SAX models. Cells without an optical model (heater path, vias, pads,
# metal wires, die frame, label) carry no light: drop them and their connections from the netlist.
models = dict(PDK.models)
import wdm_models; models.update(wdm_models.MODELS)   # step 15: our own waveguide + ring-coupler models
ELECTRICAL = ("via_stack", "pad", "straight_metal", "bend_metal", "wire_corner", "compass", "rectangle",
              "text_rectangular", "die", "Unnamed")
def is_optical_cell(name):
    return (name in models or name in net) and not any(name.startswith(e) for e in ELECTRICAL)
for k in [k for k in net if any(k.startswith(e) for e in ELECTRICAL)]:
    del net[k]                                   # their sub-netlists go too
dropped = set()
for cellname, n in net.items():
    keep = {k: v for k, v in n["instances"].items() if is_optical_cell(v["component"])}
    dropped |= {v["component"] for k, v in n["instances"].items() if k not in keep}
    n["instances"] = keep
    optical = lambda ref: ref.split(",")[0] in keep and not ref.split(",")[1].startswith("e") and not ref.split(",")[1].endswith(("_e", "_s"))
    n["connections"] = {a: b for a, b in n.get("connections", {}).items() if optical(a) and optical(b)}
    n["ports"] = {pn: ref for pn, ref in n.get("ports", {}).items() if optical(ref)}
    def ref_of(x):                       # a net endpoint is "inst,port" or {"instance":..., "port":...}
        return x if isinstance(x, str) else f'{x["instance"]},{x["port"]}'
    n["nets"] = [nt for nt in n.get("nets", []) if all(optical(ref_of(v)) for v in nt.values())]
print("non-optical cells dropped from the netlist:", sorted(dropped))
circuit, info = sax.circuit(net, models=models)
wl = jnp.linspace(1.535, 1.565, 3001)
S = circuit(wl=wl)
def dB(x): return 10*np.log10(np.abs(np.asarray(x))**2 + 1e-30)
lb = dB(S[("lb1", "lb2")]); 
fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
ax[0].plot(wl*1e3, lb, "k", label="loopback lb1->lb2 (two couplers + waveguide)")
for n in ["d1","d2","d3","d4","thru"]:
    ax[0].plot(wl*1e3, dB(S[("in", n)]), label=f"in->{n}")
ax[0].set_ylabel("transmission (dB)"); ax[0].legend(fontsize=8, ncol=2); ax[0].set_title("as measured: coupler hump included")
for n in ["d1","d2","d3","d4","thru"]:
    ax[1].plot(wl*1e3, dB(S[("in", n)]) - lb, label=f"in->{n} minus loopback")
ax[1].set_ylabel("ring bank alone (dB)"); ax[1].set_xlabel("wavelength (nm)"); ax[1].legend(fontsize=8, ncol=2); ax[1].set_ylim(-40, 3)
plt.tight_layout(); plt.savefig("img/step15b_spectra.png", dpi=120)
# report the drop peaks
for n in ["d1","d2","d3","d4"]:
    t = dB(S[("in", n)]) - lb; i = int(np.argmax(t)); print(f"{n}: peak {t[i]:.2f} dB at {float(wl[i])*1e3:.2f} nm")
print("loopback at 1550:", round(float(lb[np.argmin(abs(wl-1.55))]),2), "dB")
