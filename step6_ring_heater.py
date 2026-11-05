import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

GAP, RADIUS, LENGTH_X = 0.27, 10.0, 4.0
WG_WIDTH = 0.45        # CORNERSTONE strip width, measured in step 4
STUB = 12.0            # heater lead length from the ring out to the via stack
TURN = 3.0             # bend radius of the heater leads


def ring_with_heater(length_y: float, name: str) -> gf.Component:
    """A CORNERSTONE ring_single plus a metal heater over its top three sides.
    The coupling side stays bare so the metal does not disturb the coupler.
    Two via stacks at the lead ends are the electrical ports."""
    c = gf.Component(name)
    ring = c.add_ref(cells.ring_single(gap=GAP, radius=RADIUS, length_x=LENGTH_X, length_y=length_y))
    ring.dmove((-ring.ports["o1"].dcenter[0], -ring.ports["o1"].dcenter[1]))   # put the bus input at (0, 0)
    c.add_port("o1", port=ring.ports["o1"])
    c.add_port("o2", port=ring.ports["o2"])

    # where the ring sits, from its parameters (same arithmetic as the ruler check)
    cx = 0.5 * (ring.ports["o1"].dcenter[0] + ring.ports["o2"].dcenter[0])   # ring centre, x
    y_bend = WG_WIDTH + GAP + RADIUS                                          # centre height of the lower bends
    x_left = cx - LENGTH_X / 2 - RADIUS                                       # centreline of the left straight
    x_right = cx + LENGTH_X / 2 + RADIUS                                      # centreline of the right straight

    # the heater as a path: lead in, up the left side, over the top, down the right side, lead out
    p = gf.Path()
    p.append(gf.path.straight(STUB))          # lead, heading east
    p.append(gf.path.arc(TURN, 90))           # turn north onto the left straight
    p.append(gf.path.straight(length_y))      # the left straight
    p.append(gf.path.arc(RADIUS, -90))        # top-left bend, now heading east
    p.append(gf.path.straight(LENGTH_X))      # the top straight
    p.append(gf.path.arc(RADIUS, -90))        # top-right bend, now heading south
    p.append(gf.path.straight(length_y))      # the right straight
    p.append(gf.path.arc(TURN, 90))           # turn east onto the lead
    p.append(gf.path.straight(STUB))          # lead out
    heater = c.add_ref(gf.path.extrude(p, cross_section="heater_metal"))
    # the path starts at (0, 0); its north-going segment begins at (STUB + TURN, TURN): put that on the ring
    heater.dmove((x_left - (STUB + TURN), y_bend - TURN))

    # via stacks at the two lead ends; their outward-facing ports become the cell's electrical ports
    for side, x in (("l", x_left - TURN - STUB), ("r", x_right + TURN + STUB)):
        via = c.add_ref(cells.via_stack_heater_mtop())
        via.dcenter = (x, y_bend - TURN)
        wanted = 180 if side == "l" else 0
        for port in via.ports:
            if port.port_type == "electrical" and round(port.orientation) == wanted:
                c.add_port(f"{side}_e", port=port)
                break
    return c


if __name__ == "__main__":
    r = ring_with_heater(length_y=0.6, name="ring_heater_ch1")
    print("ports:", [(p.name, p.port_type) for p in r.ports])
    print("size (um):", round(r.dxsize, 2), "x", round(r.dysize, 2))
    print("layers used:", r.layers)
    r.write_gds("gds/step6_ring_heater.gds")
    r.show()
