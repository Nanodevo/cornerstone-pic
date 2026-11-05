"""Export the split die for the three.js showcase: polygons per layer (with the 2.5D
heights) plus the light paths (route centrelines and ring loops). Writes wdm4-3d.json,
or the path given as the first argument."""
import sys, json, math, pathlib
import numpy as np, gdstk
from shapely.geometry import Polygon
sys.path.insert(0, ".")
import gdsfactory as gf

ROUTES = {}      # name -> list of (x, y)
_rb, _rs = gf.routing.route_bundle, gf.routing.route_single
def _pts(route):
    """Backbone points of a route in micrometres. kfactory gives integer dbu points
    (1 dbu = 1 nm) or float DPoints; integers are converted, floats kept."""
    bb = getattr(route, "backbone", None)
    if bb is None: return []
    out = []
    for p in bb:
        x = getattr(p, "x", None); y = getattr(p, "y", None)
        if x is None: x, y = p[0], p[1]
        if isinstance(x, int) and isinstance(y, int):
            x, y = x / 1000.0, y / 1000.0
        out.append((float(x), float(y)))
    return out
def route_bundle(comp, p1, p2, **kw):
    rs = _rb(comp, p1, p2, **kw)
    for a, r in zip(p1, rs): ROUTES.setdefault("bundle", []).append((a.name, _pts(r)))
    return rs
def route_single(comp, p1, p2, **kw):
    r = _rs(comp, p1, p2, **kw); ROUTES.setdefault("single", []).append((p1.name, _pts(r))); return r
gf.routing.route_bundle, gf.routing.route_single = route_bundle, route_single

src = open("step16_chip_split.py").read().replace('if __name__ == "__main__":', "if True:").replace("chip.show()", "")
exec(src)
print("routes captured:", {k: len(v) for k, v in ROUTES.items()})
sample = ROUTES["bundle"][0]; print("sample route", sample[0], "points:", sample[1][:4], "...", len(sample[1]))

lib = gdstk.read_gds("gds/step16_chip_split.gds"); top = [c for c in lib.cells if c.name == chip.name][0].copy("f"); top.flatten()
Z = {(3, 0): ("si", 0.0, 0.22), (6, 0): ("grating", 0.15, 0.22), (39, 0): ("heater", 1.1, 1.8), (41, 0): ("metal", 1.8, 2.5), (99, 0): ("die", -0.05, 0.0)}
polys = []
cell_poly = [p for p in top.polygons if (p.layer, p.datatype) == (99, 0)]
(cx0, cy0), (cx1, cy1) = cell_poly[0].bounding_box()      # the floor IS the foundry's user cell, read from the GDS, so the picture shows the real boundary
top.remove(*cell_poly)
sb = [q.bounding_box() for q in top.polygons if (q.layer, q.datatype) in Z]
SPAN_BOX = [round(min(v[0][0] for v in sb), 2), round(min(v[0][1] for v in sb), 2), round(max(v[1][0] for v in sb), 2), round(max(v[1][1] for v in sb), 2)]   # true extent of the structures
polys.append({"l": "die", "z0": -0.05, "z1": 0.0, "p": [[round(cx0, 2), round(cy0, 2)], [round(cx1, 2), round(cy0, 2)], [round(cx1, 2), round(cy1, 2)], [round(cx0, 2), round(cy1, 2)]]})
for p in top.polygons:
    k = (p.layer, p.datatype)
    if k not in Z: continue
    pts = np.asarray(p.points)
    if len(pts) > 40:                                  # thin out curve sampling for the browser WITHOUT changing the outline
        # (an even-index pick cut the right lead off the heaters, 13.10.2026: shape-preserving simplification instead)
        sp = Polygon(pts).simplify(0.05, preserve_topology=True)
        pts = np.asarray(sp.exterior.coords)[:-1]
    polys.append({"l": Z[k][0], "z0": Z[k][1], "z1": Z[k][2], "p": [[round(float(x), 3), round(float(y), 3)] for x, y in pts]})
print("polygons:", len(polys), "| by layer:", {n: sum(1 for q in polys if q["l"] == n) for n in ("si", "grating", "heater", "metal", "die")})

# ring loops for the light animation: racetrack centreline per ring
rings = []
for j, gap in enumerate(GAPS):
    for i in range(4):
        # bank j ring i: bus input of the bank at (j*6*PITCH, 0); ring cx = that + i*PITCH + 12
        cx = j * 6 * PITCH + i * PITCH + 12.0; y_bend = 0.45 + gap + 10.0
        R, LX, LY = 10.0, 4.0, 0.6 + i * 0.066
        loop = []
        for t in np.linspace(0, 1, 120):
            # parametrise the racetrack counter-clockwise starting at the bottom-left of the bottom straight
            s = t * (2 * LX + 2 * LY + 2 * math.pi * R); segs = [("b", LX), ("arc", math.pi * R / 2), ("r", LY), ("arc", math.pi * R / 2), ("t", LX), ("arc", math.pi * R / 2), ("l", LY), ("arc", math.pi * R / 2)]
            loop.append(s)
        rings.append({"bank": j + 1, "ch": i + 1, "cx": cx, "cy": y_bend + LY / 2, "R": R, "LX": LX, "LY": LY, "gap": gap})
out = {"die": DIE, "cell": [CELL[0], CELL[1]], "span_box": SPAN_BOX, "span": [round(SPAN_BOX[2] - SPAN_BOX[0]), round(SPAN_BOX[3] - SPAN_BOX[1])], "pitch": PITCH, "gaps": list(GAPS), "polys": polys, "rings": rings,
       "routes": {k: [{"port": n, "pts": [[round(x, 2), round(y, 2)] for x, y in pts]} for n, pts in v] for k, v in ROUTES.items()},
       "couplers": [{"name": n, "x": round(g.dcenter[0], 2), "y": round(g.dcenter[1], 2)} for n, g in zip(names, couplers)],
       "pads": [{"x": round(p.dcenter[0], 2), "y": round(p.dcenter[1], 2)} for p in pads]}
dst = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "wdm4-3d.json")
dst.write_text(json.dumps(out, separators=(",", ":")))
print("wrote", dst, round(dst.stat().st_size / 1e6, 2), "MB")
