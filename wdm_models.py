"""Step 15: our own compact models for the WDM chip, replacing the PDK's ring coupler.

Formulas:
  waveguide  S = exp(-a L/2) exp(-i 2 pi n_eff(wl) L / wl),  n_eff(wl) = n0 + (n0 - ng)(wl - wl0)/wl0
  coupler    lossless 2x2: through sqrt(1-K), cross -i sqrt(K)
  K(gap)     = sin^2( kappa0 exp(-gamma (gap - g0)) l_eff ),  gamma = k0 sqrt(n_eff^2 - n_ox^2)
  l_eff      = length_x + 2 * integral of exp(-gamma y(s)) ds along one ring corner, where y(s) is
               the distance the corner has moved away from the bus. The kit's ring corners are
               Euler bends (curvature growing from zero), which stay near the bus longer than a
               quarter circle: for R = 10 um the integral gives l_eff = 9.4 um, where the
               quarter-circle formula length_x + sqrt(2 pi R / gamma) gives 6.7 um.
  ring       corner length and corner shape are read from the kit's own bend (16.64 um for the
               10 um Euler bend, against 15.71 um for a quarter circle).
kappa0 defaults to a placeholder (scaled from 6.6% per pass at a 200 nm gap) until the femwell
supermode calculation on CORNERSTONE's 450 x 220 nm strip replaces it.
"""
import functools, json, pathlib
import numpy as np
import jax.numpy as jnp
import sax

WL0 = 1.55
N_OX = 1.444
LOSS_DB_CM = 3.0
# Loss per 90 degree bend of the 450 nm strip, from the cut-back slopes in CORNERSTONE's SOI
# standard components library (Mar 2023, page "SOI220nm_1550nm_TE_STRIP_90_Degree_Bend"):
# 0.0136 dB per bend at R = 5 um, 0.0116 dB per bend at R = 10 um. A cut-back slope is the whole
# loss of one bend, propagation along it included, so a bend is charged this figure and nothing else.
# The library does not say whether its bends are circular or Euler.
RING_BEND_DB = 0.0116        # each of the ring's four corners (R = 10 um)
BEND_DB = 0.0136             # each routing bend (R = 5 um figure, also used for the 10 um routing bends: the larger of the two)
# Defaults are the PDK's strip values and a placeholder coupling; step15b_coupling.py writes
# data/strip_450x220.json from femwell, and those numbers take over when the file exists.
NEFF0, NG = 2.38, 4.30
G0, KAPPA0, GAMMA = 0.20, 0.0379, None      # kappa0 in rad/um at the reference gap; GAMMA None -> formula
_data = pathlib.Path(__file__).parent / "data" / "strip_450x220.json"
if _data.exists():
    _d = json.loads(_data.read_text())
    NEFF0, NG, G0, KAPPA0, GAMMA = _d["neff0"], _d["ng"], _d["g0"], _d["kappa0"], _d["gamma"]
    SOURCE = f"femwell ({_data.name})"
else:
    SOURCE = "placeholder"


def neff(wl):
    return NEFF0 + (NEFF0 - NG) * (wl - WL0) / WL0


def gamma(wl):
    if GAMMA is not None:                      # fitted decay from the mode solver
        return GAMMA
    return 2 * jnp.pi / wl * jnp.sqrt(neff(wl) ** 2 - N_OX ** 2)


def _prop(wl, length, loss_db_cm=LOSS_DB_CM):
    """Amplitude transfer of a waveguide piece."""
    amp = 10 ** (-loss_db_cm * length * 1e-4 / 20)          # dB/cm -> amplitude over length in um
    return amp * jnp.exp(-2j * jnp.pi * neff(wl) * length / wl)


def straight(*, wl=WL0, length=10.0, loss_dB_cm=LOSS_DB_CM, **kw) -> sax.SDict:
    wl = jnp.asarray(wl)
    s = _prop(wl, length, loss_dB_cm)
    return sax.reciprocal({("o1", "o2"): s})


def bend_euler(*, wl=WL0, length=10.0, loss_dB_cm=LOSS_DB_CM, **kw) -> sax.SDict:
    """A 90 degree bend: its phase, and the foundry's measured loss per bend."""
    wl = jnp.asarray(wl)
    s = _prop(wl, length, 0.0) * 10 ** (-BEND_DB / 20)
    return sax.reciprocal({("o1", "o2"): s})


def taper(*, wl=WL0, length=10.0, **kw) -> sax.SDict:
    return straight(wl=wl, length=length, loss_dB_cm=0.0)


@functools.lru_cache(maxsize=None)
def ring_corner(radius, g):
    """One corner of the kit's ring: its path length, and the coupling integral
    of exp(-g y) along it, y being the distance the corner has left the bus."""
    import gdsfactory as gf
    pts = gf.path.euler(radius=radius, angle=90, p=0.5, use_eff=True, npoints=4000).points
    ds = np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1]))
    y = np.abs(pts[:, 1]); ym = 0.5 * (y[1:] + y[:-1])
    return float(ds.sum()), float(np.sum(np.exp(-g * ym) * ds))


def _g0():
    """Decay constant as a plain number for the corner integral."""
    return float(GAMMA) if GAMMA is not None else float(2 * np.pi / WL0 * np.sqrt(NEFF0 ** 2 - N_OX ** 2))


def l_eff(radius, length_x):
    return length_x + 2 * ring_corner(float(radius), _g0())[1]


def coupling(wl, gap, radius, length_x):
    """Power crossing per pass, K(gap) = sin^2(kappa(gap) l_eff)."""
    g = gamma(wl)
    kappa = KAPPA0 * jnp.exp(-g * (gap - G0))
    return jnp.sin(kappa * l_eff(radius, length_x)) ** 2


def coupler_ring(*, wl=WL0, gap=0.31, radius=10.0, length_x=4.0, length_extension=10.0, **kw) -> sax.SDict:
    """Bus-to-ring coupler, PDK port convention: o1 bus in, o4 bus out, o2/o3 the ring ends
    after the two corner bends. Lossless coupling plus the phases and losses of the paths."""
    wl = jnp.asarray(wl)
    K = coupling(wl, gap, radius, length_x)
    t, k = jnp.sqrt(1 - K), -1j * jnp.sqrt(K)
    bus = _prop(wl, length_x + 2 * length_extension)          # o1 -> o4 straight path
    arc = _prop(wl, ring_corner(float(radius), _g0())[0], 0.0) * 10 ** (-RING_BEND_DB / 20)   # one ring corner: phase, and the measured loss per bend
    ring = _prop(wl, length_x) * arc * arc                     # o2 -> o3 through the coupler section
    ext = _prop(wl, length_extension)                          # bus extension either side
    return sax.reciprocal({
        ("o1", "o4"): bus * t,
        ("o2", "o3"): ring * t,
        ("o1", "o3"): ext * _prop(wl, length_x) * arc * k,     # bus in -> ring right end
        ("o2", "o4"): arc * _prop(wl, length_x) * ext * k,     # ring left end -> bus out
    })


MODELS = {"straight": straight, "straight_strip": straight, "bend_euler": bend_euler,
          "bend_euler_strip": bend_euler, "taper": taper, "coupler_ring": coupler_ring}
