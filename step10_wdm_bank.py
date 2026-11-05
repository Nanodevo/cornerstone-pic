from step9_ring_add_drop import ring_add_drop_heater
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

CHANNEL_STEP_UM = 0.064  # 64nm step up on rings after the first on to have channel spacing of 1.6nm
SPACER_UM = 103          # bus length between rings 

c = gf.Component("ring_bank_4ch")
previous = None
for i in range(4):
    ring = c.add_ref(ring_add_drop_heater(length_y=0.6 + i * CHANNEL_STEP_UM, name=f"ring_ch{i+1}"))

    if previous is None:
        c.add_port("o1", port=ring.ports["o1"])   # bus input of the bank
    else:
        ring.connect("o1", previous.ports["o2"])

    c.add_port(f"drop{i+1}", port=ring.ports["drop"])
    c.add_port(f"add{i+1}", port=ring.ports["add"])
    c.add_port(f"l_e{i+1}", port=ring.ports["l_e"])
    c.add_port(f"r_e{i+1}", port=ring.ports["r_e"])
    c.add_port(f"l_s{i+1}", port=ring.ports["l_s"])
    c.add_port(f"r_s{i+1}", port=ring.ports["r_s"])

    if i < 3:                                      # a spacer after rings 1 to 3 only
        spacer = c.add_ref(cells.straight(length=SPACER_UM))
        spacer.connect("o1", ring.ports["o2"])
        previous = spacer
    else:                                          # ring 4 ends the bus
        previous = ring
c.add_port("o2", port=previous.ports["o2"])        # bus output (through port)


print("ports:", [p.name for p in c.ports])
print("size (um):", round(c.dxsize, 2), "x", round(c.dysize, 2))
c.write_gds("gds/step8_heated_bank.gds")
c.show()

