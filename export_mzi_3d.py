"""Export the MZI4 die for the three.js showcase: polygons per layer with the 2.5D heights, the
routes, the arm centrelines of every interferometer, the MMI port positions, couplers, pads and
the simulated curves. Writes mzi-3d.json, or the path given as the first argument."""
import sys, json, math, pathlib, re
import numpy as np, gdstk
from shapely.geometry import Polygon
sys.path.insert(0, ".")
import gdsfactory as gf

ROUTES = []      # list of point lists (um), orientation as routed
_rb, _rs = gf.routing.route_bundle, gf.routing.route_single
def _pts(route):
    bb = getattr(route, "backbone", None)
    if bb is None: return []
    out = []
    for p in bb:
        x = getattr(p, "x", None); y = getattr(p, "y", None)
        if x is None: x, y = p[0], p[1]
        if isinstance(x, int) and isinstance(y, int): x, y = x / 1000.0, y / 1000.0
        out.append((float(x), float(y)))
    return out
def route_bundle(comp, p1, p2, **kw):
    rs = _rb(comp, p1, p2, **kw); ROUTES.extend(_pts(r) for r in rs); return rs
def route_single(comp, p1, p2, **kw):
    r = _rs(comp, p1, p2, **kw); ROUTES.append(_pts(r)); return r
gf.routing.route_bundle, gf.routing.route_single = route_bundle, route_single

src = open("mzi_die.py").read().replace('if __name__ == "__main__":', "if True:")
exec(src)
print("routes captured:", len(ROUTES))

lib = gdstk.read_gds("gds/mzi_die.gds"); top = [c for c in lib.cells if c.name == chip.name][0].copy("f"); top.flatten()
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
    if len(pts) > 40:   # shape-preserving thinning (an even-index pick can cut shapes, 13.10.2026)
        pts = np.asarray(Polygon(pts).simplify(0.05, preserve_topology=True).exterior.coords)[:-1]
    polys.append({"l": Z[k][0], "z0": Z[k][1], "z1": Z[k][2], "p": [[round(float(x), 3), round(float(y), 3)] for x, y in pts]})
print("polygons:", len(polys), "| by layer:", {n: sum(1 for q in polys if q["l"] == n) for n in ("si", "grating", "heater", "metal", "die")})

# ---- arm centrelines: walk the MZI cell's instances port to port ------------------------------
def bezier(a, c, b, n=10):
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t ** 2 * b[0], (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t ** 2 * b[1]) for t in np.linspace(0, 1, n)]
def corner(p, q):
    """Intersection of the tangent lines through two bend ports (each: x, y, orientation in degrees)."""
    (x1, y1, a1), (x2, y2, a2) = p, q
    d1 = (math.cos(math.radians(a1)), math.sin(math.radians(a1))); d2 = (math.cos(math.radians(a2)), math.sin(math.radians(a2)))
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9: return ((x1 + x2) / 2, (y1 + y2) / 2)
    t = ((x2 - x1) * d2[1] - (y2 - y1) * d2[0]) / den
    return (x1 + d1[0] * t, y1 + d1[1] * t)

def mzi_geometry(ref, tag, dl):
    cell = ref.cell
    off = (ref.ports["o1"].dcenter[0] - cell.ports["o1"].dcenter[0], ref.ports["o1"].dcenter[1] - cell.ports["o1"].dcenter[1])
    insts = []
    for inst in cell.insts:
        name = inst.cell.name
        ports = [(p.name, p.dcenter[0] + off[0], p.dcenter[1] + off[1], float(p.orientation)) for p in inst.ports if re.match(r"^o\d+$", p.name)]
        insts.append({"kind": "mmi" if name.startswith("mmi2x2") else "bend" if name.startswith("bend") else "straight", "ports": ports})
    mmis = sorted([i for i in insts if i["kind"] == "mmi"], key=lambda i: min(p[1] for p in i["ports"]))
    splitter, combiner = mmis[0], mmis[1]
    def port(inst, n): return next((x, y) for (nm, x, y, a) in inst["ports"] if nm == n)
    def walk(start, stop):
        """From a splitter output to a combiner input, through bends and straights."""
        pts = [start]; cur = start; used = set()
        for _ in range(60):
            if math.hypot(cur[0] - stop[0], cur[1] - stop[1]) < 0.01: break
            nxt = None
            for k, i in enumerate(insts):
                if i["kind"] == "mmi" or k in used: continue
                for (nm, x, y, a) in i["ports"]:
                    if math.hypot(x - cur[0], y - cur[1]) < 0.01:
                        other = [(nm2, x2, y2, a2) for (nm2, x2, y2, a2) in i["ports"] if nm2 != nm][0]
                        if i["kind"] == "bend":
                            c = corner((x, y, a), (other[1], other[2], other[3])); pts.extend(bezier((x, y), c, (other[1], other[2]))[1:])
                        else:
                            pts.append((other[1], other[2]))
                        cur = (other[1], other[2]); used.add(k); nxt = i; break
                if nxt: break
            if nxt is None: break
        return [[round(x, 3), round(y, 3)] for x, y in pts]
    top_arm = walk(port(splitter, "o3"), port(combiner, "o2"))
    bot_arm = walk(port(splitter, "o4"), port(combiner, "o1"))
    P = lambda i: {n: [round(v, 3) for v in port(i, n)] for n in ("o1", "o2", "o3", "o4")}
    return {"tag": tag, "delta_length": dl, "splitter": P(splitter), "combiner": P(combiner), "arm_top": top_arm, "arm_bot": bot_arm,
            "ports": {n: [round(v, 3) for v in ref.ports[n].dcenter] for n in ("o1", "o2", "o3", "o4")}}

geo = [mzi_geometry(mzis[0], "sw", 0.0)] + [mzi_geometry(m, f"m{int(d)}", d) for m, d in zip(mzis[1:], DELTAS)]
for g in geo: print(g["tag"], "arm points:", len(g["arm_top"]), len(g["arm_bot"]))
heater_ports = {n: [round(v, 2) for v in mzis[0].ports[n].dcenter] for n in ("e1", "e2")}

sim = json.load(open("img/mzi/sim.json"))
out = {"die": DIE, "cell": [CELL[0], CELL[1]], "span_box": SPAN_BOX, "span": [round(SPAN_BOX[2] - SPAN_BOX[0]), round(SPAN_BOX[3] - SPAN_BOX[1])], "pitch": PITCH, "gc_y": GC_Y, "polys": polys,
       "routes": [[[round(x, 2), round(y, 2)] for x, y in r] for r in ROUTES if len(r) > 1],
       "mzis": geo, "heater": heater_ports,
       "couplers": [{"name": n, "x": round(g.dcenter[0], 2), "y": round(g.dcenter[1], 2), "port": [round(v, 2) for v in g.ports["o1"].dcenter]} for n, g in zip(names, couplers)],
       "pads": [{"x": round(p.dcenter[0], 2), "y": round(p.dcenter[1], 2)} for p in pads], "sim": sim}
dst = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "mzi-3d.json")
dst.write_text(json.dumps(out, separators=(",", ":")))
print("wrote", dst, round(dst.stat().st_size / 1e6, 2), "MB")
