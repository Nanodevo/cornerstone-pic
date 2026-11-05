"""MZI4: a thermo-optic 2x2 Mach-Zehnder switch and three unbalanced Mach-Zehnder
interferometers (delta L = 30, 60, 120 um) on one CORNERSTONE si220 die. Same conventions as the
WDM4 die: 2x2 MMI splitters, one fiber row of grating couplers at 127 um pitch, termination
tapers on the unused inputs, a reference loopback, probe pads, die frame and label."""
import math
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

PITCH = 127.0                                 # fiber array pitch
GC_Y = 300.0                                  # coupler row above the interferometers
DELTAS = (30.0, 60.0, 120.0)                  # arm length differences of the three passive MZIs (um)
HEATER_L = 320.0                              # PDK heater length in the switch's top arm
PAD_SIZE, PAD_Y = 70.0, 150.0                 # two pads north of the switch, straight wires up from the heater contacts
CELL = (5500.0, 4900.0)                       # the standard user cell of the 220 nm SOI MPW (design guidelines #45, section 5.1): 5.5 x 4.9 mm2
MARGIN = 100.0                                # the structures sit this far from the cell's lower-left corner; the rest of the cell is free
WITH_CELL = True                              # the cell0 assembly turns this off and draws one outline for both dies
X_IN = 30.0                                   # an MZI's west port sits this far east of its input coupler's column


@gf.cell
def heater_arm(length: float = HEATER_L, cross_section=None, **kw) -> gf.Component:
    """The PDK heater straight, wrapped so the MZI builder's cross_section argument is accepted."""
    c = gf.Component()
    h = c << cells.straight_heater_metal(length=length)
    for p in h.ports:
        c.add_port(p.name, port=p)
    return c


def switch_cell() -> gf.Component:
    """Balanced 2x2 MZI, heater on the top arm: the cross port carries the light at zero phase, the bar port at pi."""
    return gf.components.mzi2x2_2x2(delta_length=0.0, length_x=HEATER_L, length_y=20.0, straight_x_top=heater_arm, cross_section="strip")


def unbalanced_cell(delta_length: float) -> gf.Component:
    """2x2 MZI with the top arm longer by delta_length: a comb filter whose free spectral range gives the group index."""
    return gf.components.mzi2x2_2x2(delta_length=delta_length, length_x=20.0, length_y=20.0, cross_section="strip")


chip = gf.Component("mzi4_v1")
couplers, pads, names = [], [], []


def coupler_at(slot: int):
    g = chip.add_ref(cells.grating_coupler_rectangular())
    g.drotate(90)
    g.dmove((slot * PITCH, GC_Y))
    couplers.append(g)
    return g


def place_mzi(cell, tag: str, slot_in: int, slot_cross: int, slot_bar: int):
    """Place an MZI with its west port east of the input column, terminate the unused input,
    route input -> o1, o3 -> cross coupler, o4 -> bar coupler."""
    m = chip.add_ref(cell)
    m.dmove((slot_in * PITCH + X_IN - m.ports["o1"].dcenter[0], -m.ports["o1"].dcenter[1]))
    t = chip.add_ref(cells.taper(length=10.0, width2=0.35))   # unused input ends at the platform's 350 nm minimum feature (Table 2 of the guidelines); it only carries the MMI's own back-reflection
    t.connect("o1", m.ports["o2"])
    g_in, g_x, g_b = coupler_at(slot_in), coupler_at(slot_cross), coupler_at(slot_bar)
    gf.routing.route_bundle(chip, [m.ports["o1"]], [g_in.ports["o1"]], cross_section="strip", radius=10.0)
    gf.routing.route_bundle(chip, [m.ports["o3"], m.ports["o4"]], [g_x.ports["o1"], g_b.ports["o1"]], cross_section="strip", radius=10.0, sort_ports=True)
    names.extend([f"{tag}_in", f"{tag}_cross", f"{tag}_bar"])
    return m


# the switch: input at slot 0, its east ports fall between slots 4 and 5, outputs at slots 5 and 6
sw = place_mzi(switch_cell(), "sw", 0, 5, 6)
for k, pname in enumerate(("e1", "e2")):
    ep = sw.ports[pname]
    p = chip.add_ref(cells.pad(size=(PAD_SIZE, PAD_SIZE)))
    p.dcenter = (ep.dcenter[0], PAD_Y)
    gf.routing.route_single(chip, ep, p.ports["e4"], cross_section="metal_routing", port_type="electrical", allow_width_mismatch=True)
    pads.append(p)

# the three passive interferometers, each with one empty slot after its input column
mzis = [sw]
for j, dl in enumerate(DELTAS):
    s0 = 8 + 4 * j
    mzis.append(place_mzi(unbalanced_cell(dl), f"m{int(dl)}", s0, s0 + 2, s0 + 3))

# reference loopback: two more couplers joined by a plain waveguide
lb = [coupler_at(21), coupler_at(22)]
gf.routing.route_single(chip, lb[0].ports["o1"], lb[1].ports["o1"], cross_section="strip", radius=10.0)
names += ["lb1", "lb2"]

# label below, then the standard user cell outline (GDS layer 99) with the structures at its lower-left corner
label = chip.add_ref(cells.text_rectangular(text="EMRE ACAR MZI4 V1 2026", size=4.0, layer="WG"))
label.dmove((chip.dxmin - label.dxmin, chip.dymin - 60.0 - label.dymax))
x0, y0 = chip.dxmin - MARGIN, chip.dymin - MARGIN                     # lower-left corner of the cell
CONTENT = (round(chip.dxmax - chip.dxmin + 2 * MARGIN), round(chip.dymax - chip.dymin + 2 * MARGIN))   # the structures' footprint, drawn as the floor of the 3D model
DIE = CONTENT
if WITH_CELL:
    cell = chip.add_ref(cells.die(size=CELL))
    cell.dmove((x0 + CELL[0] / 2 - cell.dcenter[0], y0 + CELL[1] / 2 - cell.dcenter[1]))

for n, g in zip(names, couplers):
    chip.add_port(n, port=g.ports["o2"])

if __name__ == "__main__":
    print("user cell (um):", CELL, "| structures footprint (um):", CONTENT, "| couplers:", len(couplers), "| pads:", len(pads), "| ports:", names)
    chip.write_gds("gds/mzi_die.gds")
