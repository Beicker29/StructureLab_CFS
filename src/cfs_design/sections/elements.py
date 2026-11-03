"""Flat widths and the ratios limited by AISI S100-24 Table B4.1-1 (pp. 25-26; notes a-f).

The limits themselves are checked in domain/applicability.py (M3); here only the variables:
w = flat width of the stiffened compression element (the web, w = h), b = flat width of the
edge-stiffened element (flange), bo = its out-to-out width, d = flat width of the unstiffened
element (lip), do = its out-to-out width, h = flat depth of the web, R = inside bend radius.
"""
from .geometry import Geometry


def element_widths(geometry: Geometry, B: float, D: float, t: float, R: float) -> dict[str, float]:
    """C and Z segments run lip, flange, web, flange, lip (geometry.py); both halves are equal."""
    d, b, h = geometry.flats[0], geometry.flats[1], geometry.flats[2]
    return {"h": h, "b": b, "d": d, "w": h, "bo": B, "do": D,
            "h_t": h / t, "b_t": b / t, "d_t": d / t, "w_t": h / t, "R_t": R / t, "do_bo": D / B}
