import gdsfactory as gf
from cspdk.si220.cband import PDK, cells, tech
from step10_wdm_bank import c as bank

PDK.activate()

DIE = (2000.0, 1600.0)   # placeholder until the design manual gives the real cell size
EDGE = 150.0             # keep-out from the die edge to couplers and pads, also a placeholder

PITCH = 127.0        # fiber array pitch
GC_Y = 300.0         # coupler row height above the bank
PAD_PITCH = 150.0    # probe-card pitch, the fixed interface
PAD_Y = -300.0       # pad row on the south edge, opposite the fibers

chip = gf.Component("wdm_chip_v1")
b = chip.add_ref(bank)

# a bend at every drop port, so the route leaves north instead of running west into the neighbour's top bus
drop_out = []
for i in range(1, 5):
    bd = chip.add_ref(cells.bend_euler())
    bd.dmirror_y()
    bd.connect("o1", b.ports[f"drop{i}"])
    assert round(bd.ports["o2"].orientation) == 90   # stop here if a drop does not leave northward
    drop_out.append(bd.ports["o2"])

for i in range(1, 5):
    t = chip.add_ref(cells.taper(length=20.0, width2=0.1))
    t.connect("o1", b.ports[f"add{i}"])

x0 = drop_out[0].dcenter[0]                       # coupler grid anchored on drop 1
couplers = []
for k in range(8):
    g = chip.add_ref(cells.grating_coupler_rectangular())
    g.drotate(90)
    g.dmove((x0 + (k - 1) * PITCH, GC_Y))         # k=0 input, 1-4 drops, 5 through
    couplers.append(g)

# along the fiber row, left to right: input, drop 1 to 4, through
bank_ports = [b.ports["o1"]] + drop_out + [b.ports["o2"]]
gc_ports = [g.ports["o1"] for g in couplers]
gf.routing.route_bundle(chip, bank_ports, [g.ports["o1"] for g in couplers[:6]], cross_section="strip", radius=10.0, sort_ports=True)
gf.routing.route_single(chip, couplers[6].ports["o1"], couplers[7].ports["o1"], cross_section="strip", radius=10.0)

via_ports = []
for i in range(1, 5):
    via_ports += [b.ports[f"l_s{i}"], b.ports[f"r_s{i}"]]
xc = 0.5 * (min(p.dcenter[0] for p in via_ports) + max(p.dcenter[0] for p in via_ports))
pads = []
for k in range(8):
    p = chip.add_ref(cells.pad())                        # 90 x 90 um, the PDK default
    p.dcenter = (xc + (k - 3.5) * PAD_PITCH, PAD_Y)      # eight pads centred under the bank
    pads.append(p)
tech.route_bundle_metal(chip, via_ports, [p.ports["e2"] for p in pads], sort_ports=True, separation=10.0)

top_y = max(g.dymax for g in couplers) + EDGE                  # coupler tips sit EDGE below the top edge
die = chip.add_ref(cells.die(size=DIE))
die.dmove((chip.dxmin + chip.dxsize / 2 - die.dxsize / 2 - die.dxmin, top_y - die.dymax))
label = chip.add_ref(cells.text_rectangular(text="EMRE ACAR WDM4 V1 2026", size=4.0, layer="WG"))
label.dmove((die.dxmin + EDGE - label.dxmin, die.dymin + EDGE - label.dymin))

print("size (um):", round(chip.dxsize, 1), "x", round(chip.dysize, 1))
chip.write_gds("gds/step10_chip.gds")
chip.show()