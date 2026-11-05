"""Step 2: one foundry cell from the CORNERSTONE PDK, written to GDS."""
from cspdk.si220.cband import PDK, cells

PDK.activate()
c = cells.grating_coupler_rectangular()   # the foundry's own C-band grating coupler
c.write_gds("gds/step2_grating_coupler.gds")
c.show()
print("wrote gds/step2_grating_coupler.gds")
print("size (um):", round(c.dxsize, 2), "x", round(c.dysize, 2))
print("ports:", [p.name for p in c.ports])
print("layers used:", c.layers)
