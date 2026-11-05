"""Compact models for the MZI die, on top of wdm_models (same strip waveguide, same femwell
indices). Added here: the 2x2 multimode interference coupler and the heated straight.

  mmi2x2   ideal 3 dB coupler with an excess loss: bar amplitude 1/sqrt2, cross amplitude -i/sqrt2,
           both times the phase of the MMI body and tapers; the 90 degree bar/cross phase difference
           is what makes two MMIs in series a switch (all light leaves the cross port when the arms
           are balanced, the bar port when they differ by pi).
  heater   a straight of the same length plus a phase dphi set from outside: dphi = pi at the
           heater's P_pi. The thermo-optic coefficient of silicon (1.8e-4 per K) and the heater's
           thermal efficiency only enter through P_pi, which is a placeholder until measured.
"""
import jax.numpy as jnp
import sax
import wdm_models as W

MMI_EXCESS_DB = 0.34         # the foundry's cascade measurements of this very coupler: 3.31 and 3.37 dB per stage for the two
                             # output arrangements, i.e. 0.31-0.37 dB above the 3 dB split (CORNERSTONE SOI components library, Mar 2023)
BEND_EXCESS_DB = 0.0136      # measured loss of the PDK's 90 degree bend, R = 5 um, 450 nm strip (same library)
MMI_IMBALANCE = 0.0          # power imbalance of the two outputs, 0 = ideal 50/50
P_PI_MW = 30.0               # the foundry qualifies every 220 nm SOI run on a strip MZI with its PDK heater at < 30 mW per pi (design guidelines #45, Table 3); the bound is used until measured


def mmi2x2(*, wl=W.WL0, length_mmi=42.5, length_taper=20.0, **kw) -> sax.SDict:
    """Ports: o1, o2 inputs (west), o3, o4 outputs (east); o1 <-> o4 and o2 <-> o3 are bar."""
    wl = jnp.asarray(wl)
    L = length_mmi + 2 * length_taper
    amp = 10 ** (-MMI_EXCESS_DB / 20) * jnp.exp(-2j * jnp.pi * W.neff(wl) * L / wl)
    bar = amp * jnp.sqrt(0.5 * (1 + MMI_IMBALANCE))
    cross = amp * (-1j) * jnp.sqrt(0.5 * (1 - MMI_IMBALANCE))
    return sax.reciprocal({("o1", "o4"): bar, ("o2", "o3"): bar, ("o1", "o3"): cross, ("o2", "o4"): cross})


def straight_heater_metal(*, wl=W.WL0, length=320.0, dphi=0.0, **kw) -> sax.SDict:
    """The heated arm: the PDK cell's optical ports are `length` apart (the contact stubs lie outside them),
    so its optical length equals a plain straight of the same length; dphi is the heater's phase."""
    wl = jnp.asarray(wl)
    s = W._prop(wl, length) * jnp.exp(-1j * dphi)
    return sax.reciprocal({("o1", "o2"): s})


def heater_arm(*, wl=W.WL0, length=320.0, dphi=0.0, **kw) -> sax.SDict:
    return straight_heater_metal(wl=wl, length=length, dphi=dphi)


def bend_euler(*, wl=W.WL0, length=7.85, loss_dB_cm=W.LOSS_DB_CM, **kw) -> sax.SDict:
    """The PDK bend: the strip's propagation loss plus the measured excess loss of a 90 degree bend."""
    wl = jnp.asarray(wl)
    s = W._prop(wl, length, loss_dB_cm) * 10 ** (-BEND_EXCESS_DB / 20)
    return sax.reciprocal({("o1", "o2"): s})


MODELS = dict(W.MODELS)
MODELS.update({"mmi2x2": mmi2x2, "straight_heater_metal": straight_heater_metal, "heater_arm": heater_arm, "bend_euler": bend_euler, "bend_euler_strip": bend_euler})
