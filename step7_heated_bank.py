from step8_ring_heater import ring_with_heater
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells

PDK.activate()

CHANNEL_STEP_UM = 0.064  # 64nm step up on rings after the first on to have channel spacing of 1.6nm
SPACER_UM = 30          # bus length between rings 

c= gf.Component("ring_bank_4ch")
previous = None
for i in range(4):
    ring = c.add_ref(ring_with_heater(length_y=0.6+i*CHANNEL_STEP_UM, name= f"ring_ch{i+1}"))

    spacer = c.add_ref(cells.straight(length=SPACER_UM ))
    if previous is None:
        c.add_port("o1", port=ring.ports["o1"])   #bus input of the bank
    else:
        ring.connect("o1", previous.ports["o2"])
    spacer.connect("o1", ring.ports["o2"])
    previous = spacer
c.add_port("o2", port=previous.ports["o2"])         #bus output(through port)


print("ports:", [p.name for p in c.ports])
print("size (um):", round(c.dxsize, 2), "x", round(c.dysize, 2))
c.write_gds("gds/step8_heated_bank.gds")
c.show

