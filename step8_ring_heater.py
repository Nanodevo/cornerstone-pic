import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

GAP, RADIUS, LENGTH_X = 0.27, 10.0, 4.0
WG_WIDTH = 0.45
STUB = 8.0             # lead length from the ring out to the via
TURN = 3.0             # bend radius of the leads
CLIMB = 15.0           # the right lead climbs this much before its via
VIA = (10.0, 10.0)     # narrower via stacks (check against the design manual)


def ring_with_heater(length_y: float, name: str) -> gf.Component:
    """ring_single + heater over the top three sides. Left via low, right via
    high, so neighbouring rings' vias stack vertically instead of colliding."""
    c = gf.Component(name)
    ring = c.add_ref(cells.ring_single(gap=GAP, radius=RADIUS, length_x=LENGTH_X, length_y=length_y))
    ring.dmove((-ring.ports["o1"].dcenter[0], -ring.ports["o1"].dcenter[1]))
    c.add_port("o1", port=ring.ports["o1"])
    c.add_port("o2", port=ring.ports["o2"])

    cx = 0.5 * (ring.ports["o1"].dcenter[0] + ring.ports["o2"].dcenter[0])
    y_bend = WG_WIDTH + GAP + RADIUS
    x_left = cx - LENGTH_X / 2 - RADIUS
    x_right = cx + LENGTH_X / 2 + RADIUS

    p = gf.Path()
    p.append(gf.path.straight(STUB))          # left lead, heading east
    p.append(gf.path.arc(TURN, 90))           # turn north onto the left straight
    p.append(gf.path.straight(length_y))
    p.append(gf.path.arc(RADIUS, -90))        # top-left bend
    p.append(gf.path.straight(LENGTH_X))      # top straight
    p.append(gf.path.arc(RADIUS, -90))        # top-right bend, heading south
    p.append(gf.path.straight(length_y))      # right straight, heading south
    p.append(gf.path.arc(TURN, 90))           # turn east
    p.append(gf.path.arc(TURN, 90))           # turn north again: a U-turn right beside the ring
    p.append(gf.path.straight(CLIMB))         # climb, so this via sits above the neighbour's low via
    heater = c.add_ref(gf.path.extrude(p, cross_section="heater_metal"))
    heater.dmove((x_left - (STUB + TURN), y_bend - TURN))

    left_via = c.add_ref(cells.via_stack_heater_mtop(size=VIA))
    left_via.dcenter = (x_left - TURN - STUB, y_bend - TURN)
    right_via = c.add_ref(cells.via_stack_heater_mtop(size=VIA))
    right_via.dcenter = (x_right + 2 * TURN, y_bend - TURN + CLIMB)
    for via, side, wanted in ((left_via, "l", 180), (right_via, "r", 90)):
        for port in via.ports:
            if port.port_type == "electrical" and round(port.orientation) == wanted:
                c.add_port(f"{side}_e", port=port)
                break
    return c


if __name__ == "__main__":
    r = ring_with_heater(length_y=0.6, name="ring_heater_ch1")
    print("ports:", [(p.name, p.port_type) for p in r.ports])
    print("size (um):", round(r.dxsize, 2), "x", round(r.dysize, 2))
    r.write_gds("gds/step8_ring_heater.gds")
    r.show()
