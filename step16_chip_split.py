"""Step 16: the die. Three ring banks with a gap split (0.22 / 0.27 / 0.32 um), one fiber
row of 20 couplers at 127 um pitch (6 per bank + 2 for the reference loopback), eight pads
per bank on the south edge, termination tapers on the add ports, die frame and label."""
import math
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells, tech
from step16_3wdm_banks import make_bank

PDK.activate()

PITCH = 127.0                          # fiber array pitch = ring pitch
GAPS = (0.22, 0.27, 0.32)              # the split: strong / design / weak coupling
GC_Y = 300.0                           # coupler row height above the banks
PAD_SIZE, PAD_Y, PAD_ROW_GAP = 70.0, -300.0, 150.0   # two staggered pad rows on the 127 um ring pitch, every pad straight under its via
CELL = (5500.0, 4900.0)                # the standard user cell of the 220 nm SOI MPW (design guidelines #45, section 5.1)
MARGIN = 100.0                         # the structures sit this far from the cell's lower-left corner
WITH_CELL = True                       # the cell0 assembly turns this off and draws one outline for both dies

chip = gf.Component("wdm4_split_v1")
couplers, pads, via_ports = [], [], []

for j, gap in enumerate(GAPS):
    b = chip.add_ref(make_bank(gap, f"g{int(round(gap * 1000))}"))
    b.dmove((j * 6 * PITCH, 0))                        # each bank owns six coupler slots

    drop_out = []
    for i in range(1, 5):
        bd = chip.add_ref(cells.bend_euler())
        bd.dmirror_y()
        bd.connect("o1", b.ports[f"drop{i}"])
        assert round(bd.ports["o2"].orientation) == 90
        drop_out.append(bd.ports["o2"])
    for i in range(1, 5):
        t = chip.add_ref(cells.taper(length=10.0, width2=0.35))   # the add port ends at the platform's 350 nm minimum feature (guidelines, Table 2)
        t.connect("o1", b.ports[f"add{i}"])

    x0 = drop_out[0].dcenter[0]
    cs = []
    for k in range(6):                                  # k = 0 input, 1-4 drops, 5 through
        g = chip.add_ref(cells.grating_coupler_rectangular())
        g.drotate(90)
        g.dmove((x0 + (k - 1) * PITCH, GC_Y))
        cs.append(g)
    gf.routing.route_bundle(chip, [b.ports["o1"]] + drop_out + [b.ports["o2"]],
                            [g.ports["o1"] for g in cs], cross_section="strip", radius=10.0, sort_ports=True)
    couplers += cs

    # this bank's eight pads in two rows, each pad exactly under its via: left vias -> upper row,
    # right vias -> lower row. Every wire is then a straight line, no bends at all.
    ps = []
    for i in range(1, 5):
        for side, row_y in (("l_s", PAD_Y), ("r_s", PAD_Y - PAD_ROW_GAP)):
            vp = b.ports[f"{side}{i}"]
            p = chip.add_ref(cells.pad(size=(PAD_SIZE, PAD_SIZE)))
            p.dcenter = (vp.dcenter[0], row_y)
            gf.routing.route_single(chip, vp, p.ports["e2"], cross_section="metal_routing", port_type="electrical", allow_width_mismatch=True)
            ps.append(p); via_ports.append(vp)
    pads += ps

# reference loopback: two more couplers on the row, joined by a plain waveguide
x_last = couplers[-1].ports["o1"].dcenter[0]
lb = []
for k in (1, 2):
    g = chip.add_ref(cells.grating_coupler_rectangular())
    g.drotate(90)
    g.dmove((x_last + k * PITCH, GC_Y))
    lb.append(g)
gf.routing.route_single(chip, lb[0].ports["o1"], lb[1].ports["o1"], cross_section="strip", radius=10.0)
couplers += lb

# label below the pad row, then the die sized from the content plus the keep-out
label = chip.add_ref(cells.text_rectangular(text="EMRE ACAR WDM4 SPLIT V1 2026", size=4.0, layer="WG"))
label.dmove((chip.dxmin - label.dxmin, chip.dymin - 60.0 - label.dymax))
x0, y0 = chip.dxmin - MARGIN, chip.dymin - MARGIN
CONTENT = (round(chip.dxmax - chip.dxmin + 2 * MARGIN), round(chip.dymax - chip.dymin + 2 * MARGIN))   # the structures' footprint, the floor of the 3D model
DIE = CONTENT
if WITH_CELL:
    cell = chip.add_ref(cells.die(size=CELL))
    cell.dmove((x0 + CELL[0] / 2 - cell.dcenter[0], y0 + CELL[1] / 2 - cell.dcenter[1]))

# the fiber ports, named, so the prediction script can address them
names = []
for j in range(len(GAPS)):
    names += [f"b{j+1}_in", f"b{j+1}_d1", f"b{j+1}_d2", f"b{j+1}_d3", f"b{j+1}_d4", f"b{j+1}_thru"]
names += ["lb1", "lb2"]
for n, g in zip(names, couplers):
    chip.add_port(n, port=g.ports["o2"])

if __name__ == "__main__":
    print("user cell (um):", CELL, "| structures footprint (um):", CONTENT, "| couplers:", len(couplers), "| pads:", len(pads))
    chip.write_gds("gds/step16_chip_split.gds")
    chip.show()
    
