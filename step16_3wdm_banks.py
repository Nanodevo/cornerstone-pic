from step9_ring_add_drop import ring_add_drop_heater
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

CHANNEL_STEP_UM = 0.069  # each ring's two side straights are 69 nm longer than the previous ring's: 138 nm of circumference, 1.6 nm of channel spacing on the 75.7 um ring
SPACER_UM = 103          # bus length between rings 

def make_bank(gap: float, tag: str) -> gf.Component:
    """Four add-drop rings on one bus, ring pitch = fiber pitch. gap sets the coupling."""
    c = gf.Component(f"ring_bank_{tag}")
    previous = None
    for i in range(4):
        ring = c.add_ref(ring_add_drop_heater(length_y=round(0.6 + i * CHANNEL_STEP_UM, 3),
                                              name=f"ring_{tag}_ch{i+1}", gap=gap))
        if previous is None:
            c.add_port("o1", port=ring.ports["o1"])
        else:
            ring.connect("o1", previous.ports["o2"])
        for n in ("drop", "add", "l_e", "r_e", "l_s", "r_s"):
            c.add_port(f"{n}{i+1}", port=ring.ports[n])
        if i < 3:
            spacer = c.add_ref(cells.straight(length=SPACER_UM))
            spacer.connect("o1", ring.ports["o2"])
            previous = spacer
        else:
            previous = ring
    c.add_port("o2", port=previous.ports["o2"])
    return c


if __name__ == "__main__":
    c = make_bank(0.31, "g310")
    print("ports:", [p.name for p in c.ports])
    print("size (um):", round(c.dxsize, 2), "x", round(c.dysize, 2))
    c.write_gds("gds/step10_wdm_bank.gds")
    c.show()