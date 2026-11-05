import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

GAP, RADIUS, LENGTH_X = 0.27, 10.0, 4.0
WG_WIDTH = 0.45
TURN = 3.0             # bend radius of the leads
VIA_Y = -8.0           # both vias sit on one line 8 um below the bus: the leads cross the bus as 2.5 um strips
LEFT_VIA_DX = 20.5     # left via this far west of the ring's left side ...
RIGHT_VIA_DX = 43.0    # ... right via this far east of it: 63.5 um apart, half a ring pitch, so the pad rows interleave; the via square stays 10 um from the lead's bend
VIA = (10.0, 10.0)     # the guidelines ask for at least 10 um of heater under pad metal

def ring_add_drop_heater(length_y: float, name: str, gap: float = GAP) -> gf.Component:
    """ring_double + heater over the top three sides. Each lead continues the
    ring's straight side downward, crosses the bus and turns outward below it, so
    the heater has no S-bend: the guidelines' 10 um heater spacing then holds
    inside the polygon as well (an S-bend of 3 um radius next to the 10 um ring
    bend fails it)."""
    c = gf.Component(name)
    ring = c.add_ref(cells.ring_double(gap=gap, radius=RADIUS, length_x=LENGTH_X, length_y=length_y))
    ring.dmove((-ring.ports["o1"].dcenter[0], -ring.ports["o1"].dcenter[1]))
    c.add_port("o1", port=ring.ports["o1"])
    c.add_port("o2", port=ring.ports["o2"])
    c.add_port("drop", port=ring.ports["o3"])    # top-left: the caught channel leaves here
    c.add_port("add", port=ring.ports["o4"])     # top-right: unused, stays as a port
    cx = 0.5 * (ring.ports["o1"].dcenter[0] + ring.ports["o2"].dcenter[0])
    y_bend = WG_WIDTH + GAP + RADIUS
    x_left = cx - LENGTH_X / 2 - RADIUS
    x_right = cx + LENGTH_X / 2 + RADIUS

    drop = y_bend - VIA_Y - TURN                # vertical lead from the ring side down to the turn below the bus
    p = gf.Path()
    p.append(gf.path.straight(LEFT_VIA_DX - TURN))  # left lead, heading east from its via
    p.append(gf.path.arc(TURN, 90))           # turn north, below the bus
    p.append(gf.path.straight(drop))          # up across the bus onto the left straight
    p.append(gf.path.straight(length_y))
    p.append(gf.path.arc(RADIUS, -90))        # top-left bend
    p.append(gf.path.straight(LENGTH_X))      # top straight
    p.append(gf.path.arc(RADIUS, -90))        # top-right bend, heading south
    p.append(gf.path.straight(length_y))      # right straight, heading south
    p.append(gf.path.straight(drop))          # down across the bus
    p.append(gf.path.arc(TURN, 90))           # turn east, below the bus
    p.append(gf.path.straight(RIGHT_VIA_DX - LENGTH_X - 2 * RADIUS - TURN))  # right lead to its via
    heater = c.add_ref(gf.path.extrude(p, cross_section="heater_metal"))
    heater.dmove((x_left - LEFT_VIA_DX, VIA_Y))

    left_via = c.add_ref(cells.via_stack_heater_mtop(size=VIA))
    left_via.dcenter = (x_left - LEFT_VIA_DX, VIA_Y)
    right_via = c.add_ref(cells.via_stack_heater_mtop(size=VIA))
    right_via.dcenter = (x_left + RIGHT_VIA_DX, VIA_Y)
    for via, side, wanted in ((left_via, "l", 180), (right_via, "r", 90)):
        for port in via.ports:
            if port.port_type != "electrical":
                continue
            if round(port.orientation) == wanted:
                c.add_port(f"{side}_e", port=port)
            elif round(port.orientation) == 270:
                c.add_port(f"{side}_s", port=port)
                break
    return c


if __name__ == "__main__":
    r = ring_add_drop_heater(length_y=0.6, name="ring_add_drop_ch1")
    print("ports:", [(p.name, p.port_type) for p in r.ports])
    print("size (um):", round(r.dxsize, 2), "x", round(r.dysize, 2))
    r.write_gds("gds/step9_ring_add_drop.gds")
    r.show()
