from cspdk.si220.cband import PDK, cells

PDK.activate()
r= cells.ring_single(gap=0.27, radius= 10.0, length_x=4.0)
print("ports:", [p.name for p in r.ports])
r.show()
