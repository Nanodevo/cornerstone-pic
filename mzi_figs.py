"""Layout figures of the MZI4 report, drawn from the tape-out GDS: the die, the switch, the
30 um interferometer, and the switch's splitter at true scale. Run after mzi_die.py."""
import gdstk, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

lib = gdstk.read_gds("gds/mzi_die.gds"); top = [c for c in lib.cells if c.name == "mzi4_v1"][0].copy("f"); top.flatten()
COL = {(3, 0): ("#e0645c", 1.0), (6, 0): ("#5b8def", 0.9), (39, 0): ("#f5a25d", 0.9), (41, 0): ("#e9c46a", 0.9), (99, 0): ("none", 1.0)}

def draw(ax, xlim, ylim, title):
    for p in top.polygons:
        k = (p.layer, p.datatype)
        if k not in COL: continue
        bb = p.bounding_box()
        if bb[1][0] < xlim[0] or bb[0][0] > xlim[1] or bb[1][1] < ylim[0] or bb[0][1] > ylim[1]: continue
        col, al = COL[k]
        ax.add_patch(Polygon(p.points, closed=True, facecolor=col, edgecolor="#333" if col == "none" else col, lw=0.6 if col == "none" else 0.2, alpha=al, linestyle="--" if col == "none" else "-"))
    ax.set(xlim=xlim, ylim=ylim, xlabel="x (µm)", ylabel="y (µm)", title=title); ax.set_aspect("equal")

fig = plt.figure(figsize=(14, 9.2)); gs = fig.add_gridspec(2, 1, height_ratios=[1.55, 1])
ax = fig.add_subplot(gs[0]); draw(ax, (-250, 5450), (-400, 4800), "(a) the 5.5 × 4.9 mm user cell (dashed, GDS layer 99) with the MZI4 structures at its lower-left corner; the rest is free")
ax = fig.add_subplot(gs[1]); draw(ax, (-150, 2950), (-250, 750), "(b) the structures: the switch (left) with its two pads, three unbalanced interferometers, the reference loopback; fiber row at y = 300 µm")
fig.tight_layout(); fig.savefig("img/mzi/die.png", dpi=110); plt.close(fig)

fig, ax = plt.subplots(figsize=(12, 5.5))
draw(ax, (-80, 900), (-120, 360), "The switch: input from the left, splitter, two 320 µm arms with the heater (orange) on the upper one, combiner, two outputs; pads above")
fig.tight_layout(); fig.savefig("img/mzi/switch_zoom.png", dpi=110); plt.close(fig)

fig, ax = plt.subplots(figsize=(12, 5.5))
draw(ax, (950, 1500), (-140, 360), "The ΔL = 30 µm interferometer: short horizontal sections, the extra length in the upper arm's loop")
fig.tight_layout(); fig.savefig("img/mzi/mzi30_zoom.png", dpi=110); plt.close(fig)

fig = plt.figure(figsize=(11, 5.2))
gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], width_ratios=[1, 1])
ax = fig.add_subplot(gs[0, :])
si = [p for p in top.polygons if (p.layer, p.datatype) == (3, 0)]
for p in si:
    bb = p.bounding_box()
    if bb[1][0] < -10 or bb[0][0] > 130 or bb[1][1] < -12 or bb[0][1] > 12: continue
    ax.add_patch(Polygon(p.points, closed=True, facecolor="#e0645c", edgecolor="#7a2a24", lw=0.5))
ax.set(xlim=(-10, 130), ylim=(-8, 8), xlabel="x (µm)", ylabel="y (µm)", title="(a) the switch's splitter, top view, true scale"); ax.set_aspect("equal")
for txt, xy, xt in (("0.45 µm strip", (15, 0), (12, -6)), ("20 µm taper, 0.45 → 1.5 µm", (40, -0.3), (28, -6.5)), ("unused input: 10 µm termination taper, 0.45 → 0.35 µm", (26, 2), (30, 6)),
                    ("MMI body 42.5 × 6 µm", (71, 0), (66, -6.5)), ("two outputs, 2 µm apart, to the arms", (103, 1), (86, 6))):
    ax.annotate(txt, xy, xt, fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.7))
# cross-sections of one strip: as it is, and as the 3D model stretches it
for k, (zx, title) in enumerate(((1, "(b) a strip as it is: 450 nm wide, 220 nm thick"), (25, "(c) as the 3D model draws it: thickness ×25"))):
    a = fig.add_subplot(gs[1, k])
    a.add_patch(Polygon([(-3, -2), (3, -2), (3, 0), (-3, 0)], closed=True, facecolor="#dbe6f3", edgecolor="none"))          # buried oxide
    a.add_patch(Polygon([(-3, 0), (3, 0), (3, 0.22 * zx + 1.0), (-3, 0.22 * zx + 1.0)], closed=True, facecolor="#eef3fa", edgecolor="none"))   # cladding
    a.add_patch(Polygon([(-0.225, 0), (0.225, 0), (0.225, 0.22 * zx), (-0.225, 0.22 * zx)], closed=True, facecolor="#e0645c", edgecolor="#7a2a24", lw=0.6))
    a.set(xlim=(-3, 3), ylim=(-2, 0.22 * zx + 1.0), xlabel="width (µm)", ylabel="height (µm)", title=title, ); a.set_aspect("equal" if zx == 1 else "auto")
    a.text(0.6, 0.22 * zx / 2, "silicon" if zx == 1 else "silicon, drawn 5.5 µm tall", fontsize=8, va="center"); a.text(-2.9, -1.2, "buried oxide", fontsize=8); a.text(-2.9, 0.22 * zx + 0.5, "oxide cladding", fontsize=8)
fig.tight_layout(); fig.savefig("img/mzi/splitter_topview.png", dpi=130); plt.close(fig)
print("die.png switch_zoom.png mzi30_zoom.png splitter_topview.png")
