"""Flat widths, the ratios limited by AISI S100-24 Table B4.1-1 and the mid-line dimensions of Table 2.3.3-1.

Table B4.1-1 (pp. 25-26; notes a-f): w = flat width of the stiffened compression element (the
web, w = h), b = flat width of the edge-stiffened element (flange), bo = its out-to-out width,
d = flat width of the unstiffened element (lip), do = its out-to-out width, h = flat depth of the
web, R = inside bend radius. The limits are checked in domain/applicability.py (M3).

Table 2.3.3-1 note 1 (p. 2-12): b, d and h are mid-line dimensions, corners ignored, i.e. the
lengths of the sharp-cornered midline (b_mid, d_mid, h_mid).
"""
import math

from .geometry import Geometry


def element_widths(geometry: Geometry, B: float, D: float, t: float, R: float) -> dict[str, float]:
    """C and Z segments run lip, flange, web, flange, lip (geometry.py); both halves are equal."""
    d, b, h = geometry.flats[0], geometry.flats[1], geometry.flats[2]
    v = geometry.vertices
    return {"h": h, "b": b, "d": d, "w": h, "bo": B, "do": D,
            "h_t": h / t, "b_t": b / t, "d_t": d / t, "w_t": h / t, "R_t": R / t, "do_bo": D / B,
            "h_mid": math.dist(v[2], v[3]), "b_mid": math.dist(v[1], v[2]), "d_mid": math.dist(v[0], v[1])}
