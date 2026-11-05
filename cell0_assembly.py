"""The tape-out cell: both dies, WDM4 above MZI4, in one 5.5 x 4.9 mm user cell (CORNERSTONE
220 nm SOI MPW, design guidelines #45). Writes gds/cell0_wdm4_mzi4.gds with the top cell named as
the foundry asks, Cell0_<name>. Run: .venv/bin/python cell0_assembly.py"""
import sys
import gdsfactory as gf
from cspdk.si220.cband import PDK, cells
sys.path.insert(0, ".")
PDK.activate()

def build(script):
    src = open(script).read().replace('if __name__ == "__main__":', "if False:").replace("WITH_CELL = True", "WITH_CELL = False")
    ns = {}; exec(src, ns); return ns["chip"], ns["CONTENT"], ns["MARGIN"]

mzi, mzi_fp, margin = build("mzi_die.py")
wdm, wdm_fp, _ = build("step16_chip_split.py")
CELL = (5500.0, 4900.0)
GAP = 200.0                                  # between the two dies' footprints

top = gf.Component("Cell0_EmreAcar")
a = top.add_ref(mzi); a.dmove((margin - a.dxmin, margin - a.dymin))                      # MZI4 at the lower-left corner
b = top.add_ref(wdm); b.dmove((margin - b.dxmin, mzi_fp[1] + GAP - b.dymin))             # WDM4 above it
cell = top.add_ref(cells.die(size=CELL)); cell.dmove((CELL[0] / 2 - cell.dcenter[0], CELL[1] / 2 - cell.dcenter[1]))

if __name__ == "__main__":
    print("cell:", CELL, "| MZI4 footprint:", mzi_fp, "| WDM4 footprint:", wdm_fp, "| content bbox:", [round(v, 1) for v in (top.dxmin, top.dxmax, top.dymin, top.dymax)])
    top.write_gds("gds/cell0_wdm4_mzi4.gds")
