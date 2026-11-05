"""Layout figures for the WDM4 report after the foundry's guidelines: the structures on the
standard user cell, and the assembled tape-out cell with both dies. Run after step16 and cell0_assembly."""
import gdstk, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
COL = {(3, 0): ("#e0645c", 1.0), (6, 0): ("#5b8def", 0.9), (39, 0): ("#f5a25d", 0.9), (41, 0): ("#e9c46a", 0.9), (99, 0): ("none", 1.0)}
def flat(path, name):
    lib = gdstk.read_gds(path); top = [c for c in lib.cells if c.name == name][0].copy("f"); top.flatten(); return top
def draw(ax, top, xlim, ylim, title):
    for p in top.polygons:
        k = (p.layer, p.datatype)
        if k not in COL: continue
        bb = p.bounding_box()
        if bb[1][0] < xlim[0] or bb[0][0] > xlim[1] or bb[1][1] < ylim[0] or bb[0][1] > ylim[1]: continue
        col, al = COL[k]
        ax.add_patch(Polygon(p.points, closed=True, facecolor=col, edgecolor="#333" if col == "none" else col, lw=0.6 if col == "none" else 0.2, alpha=al, linestyle="--" if col == "none" else "-"))
    ax.set(xlim=xlim, ylim=ylim, xlabel="x (µm)", ylabel="y (µm)", title=title); ax.set_aspect("equal")
w = flat("gds/step16_chip_split.gds", "wdm4_split_v1")
fig, ax = plt.subplots(figsize=(14, 7.5))
draw(ax, w, (-150, 2650), (-650, 900), "WDM4 structures: three ring banks on one bus each, twenty couplers on the 127 µm row, 24 pads in two rows per bank, the label; on the foundry's 5.5 × 4.9 mm user cell")
fig.tight_layout(); fig.savefig("img/wdm4_die.png", dpi=110); plt.close(fig)
c = flat("gds/cell0_wdm4_mzi4.gds", "Cell0_EmreAcar")
fig, ax = plt.subplots(figsize=(12, 10.7))
draw(ax, c, (-150, 5650), (-150, 5050), "The tape-out cell, 5.5 × 4.9 mm (dashed, layer 99): MZI4 at the bottom, WDM4 above it; the rest is free")
fig.tight_layout(); fig.savefig("img/cell0.png", dpi=110); plt.close(fig)
fig, ax = plt.subplots(figsize=(9, 5.5))
draw(ax, w, (-45, 125), (-25, 45), "One ring cell: racetrack (red) on its bus, heater (orange) over the top three sides,\nleads straight down across the bus to 10 × 10 µm vias, add taper ending at 350 nm")
fig.tight_layout(); fig.savefig("img/wdm4_ring.png", dpi=120); plt.close(fig)
fig, ax = plt.subplots(figsize=(11, 6))
draw(ax, w, (-80, 560), (-520, 60), "Bank 1's electrical side: left vias to the upper pad row, right vias to the lower row,\nevery wire straight and 23.5 µm from the neighbouring pads")
fig.tight_layout(); fig.savefig("img/wdm4_pads.png", dpi=110); plt.close(fig)
print("img/wdm4_die.png img/cell0.png img/wdm4_ring.png img/wdm4_pads.png")
