"""AISI S100-24 Appendix 2, Elastic Buckling Analysis of Members (pp. 2-1 to 2-18), analytical solutions 2.3.

Units: N, mm, MPa. Shear buckling (2.3.4) is not here: it moves to milestone M5 with Section G2.3 (D9).
Equations that look alike are kept apart when the Specification states them separately
(e.g. Eq. 2.3.3.1-5 has a term that Eq. 2.3.3.2-6 lacks).
"""
import math
from dataclasses import dataclass

E = 203_000.0
"""2.3.1, p. 2-3: modulus of elasticity of steel (MPa)."""
G = 78_000.0
"""2.3.1, p. 2-3: shear modulus of steel (MPa)."""
MU = 0.30
"""Symbols, p. xxxii: Poisson's ratio of steel."""


# --- 2.3.1 Global buckling -----------------------------------------------------------------------------------------

def flexural_buckling_force(inertia: float, kl: float) -> float:
    """Eqs. 2.3.1-1, 2.3.1-2 (Pex, Pey) and 2.3.1.1.1-1, pp. 2-3 and 2-5: π²EI/(KL)²."""
    return math.pi**2 * E * inertia / kl**2


def torsional_buckling_force(ro: float, j_torsion: float, cw: float, kt_lt: float) -> float:
    """Eq. 2.3.1-3, p. 2-3: Pt = [GJ + π²ECw/(KtLt)²] / ro²."""
    return (G * j_torsion + math.pi**2 * E * cw / kt_lt**2) / ro**2


def beta_flexural_torsional(xo: float, ro: float, kt_lt: float, kx_lx: float) -> float:
    """Eq. 2.3.1-4, p. 2-3: β = 1 − (xo/ro)²(KtLt/KxLx)²."""
    return 1 - (xo / ro) ** 2 * (kt_lt / kx_lx) ** 2


def flexural_torsional_force(p_ex: float, p_t: float, beta: float) -> float:
    """Eq. 2.3.1.1.2-1, p. 2-6: singly-symmetric section, x the axis of symmetry."""
    return ((p_ex + p_t) - math.sqrt((p_ex + p_t) ** 2 - 4 * beta * p_ex * p_t)) / (2 * beta)


def mcre_symmetric_axis(cb: float, ro: float, p_ey: float, p_t: float) -> float:
    """Eq. 2.3.1.2.1-1, p. 2-7: bending about the symmetric x-axis, Mcre = Cb ro √(Pey Pt)."""
    return cb * ro * math.sqrt(p_ey * p_t)


def mcre_non_symmetric_axis(cb: float, p_ex: float, cs: int, j_asym: float, ro: float, p_t: float) -> float:
    """Eq. 2.3.1.2.2-1, p. 2-8: singly-symmetric section bending about the y-axis perpendicular to the symmetric
    x-axis, Mcre = Cb Pex (Cs|j| + √(j² + ro² Pt/Pex)); Cs = +1 with compression on the shear-centre side."""
    return cb * p_ex * (cs * abs(j_asym) + math.sqrt(j_asym**2 + ro**2 * p_t / p_ex))


def mcre_point_symmetric(cb: float, ro: float, p_ey: float, p_t: float) -> float:
    """Eq. 2.3.1.2.3-1, p. 2-8: point-symmetric Z bending about the x-axis perpendicular to the web,
    Mcre = (Cb ro / 2) √(Pey Pt)."""
    return cb * ro / 2 * math.sqrt(p_ey * p_t)


# --- 2.3.2 Local buckling --------------------------------------------------------------------------------------------

def plate_buckling_stress(k: float, t: float, w: float) -> float:
    """Eqs. 2.3.2.1-2 and 2.3.2.2-2, p. 2-10: Fcr = k π²E/[12(1 − μ²)] (t/w)²."""
    return k * math.pi**2 * E / (12 * (1 - MU**2)) * (t / w) ** 2


# --- 2.3.3 Distortional buckling -----------------------------------------------------------------------------------

@dataclass(frozen=True)
class FlangeProperties:
    """Table 2.3.3-1 (p. 2-12): flange plus lip, axes at the flange centroid, x toward the lip, y down."""

    Af: float
    Jf: float
    Ixf: float
    Iyf: float
    Ixyf: float
    Cwf: float
    xof: float
    xhf: float
    yhf: float
    yof: float


def flange_properties_c(b: float, d: float, t: float) -> FlangeProperties:
    """Table 2.3.3-1, C-section column (p. 2-12); b, d mid-line dimensions, corner radius ignored."""
    s = b + d
    y = -d**2 / (2 * s)
    return FlangeProperties(
        Af=s * t, Jf=b * t**3 / 3 + d * t**3 / 3,
        Ixf=t * (t**2 * b**2 + 4 * b * d**3 + t**2 * b * d + d**4) / (12 * s),
        Iyf=t * (b**4 + 4 * d * b**3) / (12 * s),
        Ixyf=t * b**2 * d**2 / (4 * s), Cwf=0.0,
        xof=b**2 / (2 * s), xhf=-(b**2 + 2 * d * b) / (2 * s), yhf=y, yof=y)


def flange_properties_z(b: float, d: float, t: float, theta: float) -> FlangeProperties:
    """Table 2.3.3-1, Z-section column (p. 2-12); b, d mid-line dimensions, θ lip angle (rad), corners ignored."""
    s = b + d
    c, sn = math.cos(theta), math.sin(theta)
    y = -d**2 * sn / (2 * s)
    return FlangeProperties(
        Af=s * t, Jf=b * t**3 / 3 + d * t**3 / 3,
        Ixf=t * (t**2 * b**2 + 4 * b * d**3 - 4 * b * d**3 * c**2 + t**2 * b * d + d**4 - d**4 * c**2) / (12 * s),
        Iyf=t * (b**4 + 4 * d * b**3 + 6 * d**2 * b**2 * c + 4 * d**3 * b * c**2 + d**4 * c**2) / (12 * s),
        Ixyf=t * b * d**2 * sn * (b + d * c) / (4 * s), Cwf=0.0,
        xof=(b**2 - d**2 * c) / (2 * s), xhf=-(b**2 + 2 * d * b + d**2 * c) / (2 * s), yhf=y, yof=y)


def _warping_term(f: FlangeProperties) -> float:
    """Cwf + Ixf (xof − xhf)² (1 − Ixyf²/(Ixf Iyf)), common bracket of Eqs. 2.3.3.1-3, -7, 2.3.3.2-4 and -8."""
    return f.Cwf + f.Ixf * (f.xof - f.xhf) ** 2 * (1 - f.Ixyf**2 / (f.Ixf * f.Iyf))


def k_phi_fe(f: FlangeProperties, ld: float) -> float:
    """Eq. 2.3.3.1-3, p. 2-13 (also used by 2.3.3.2): elastic rotational stiffness provided by the flange."""
    return (math.pi / ld) ** 4 * E * _warping_term(f) + (math.pi / ld) ** 2 * G * f.Jf


def lcrd_compression(f: FlangeProperties, t: float, ho: float) -> float:
    """Eq. 2.3.3.1-7, p. 2-14."""
    return math.pi * ho * (6 * (1 - MU**2) / (t**3 * ho**3) * _warping_term(f)) ** 0.25


def k_phi_we_compression(t: float, ho: float) -> float:
    """Eq. 2.3.3.1-4, p. 2-13: Et³/[12(1 − μ²)] (2/ho)."""
    return E * t**3 / (12 * (1 - MU**2)) * (2 / ho)


def k_phi_fg_compression(f: FlangeProperties, ld: float) -> float:
    """Eq. 2.3.3.1-5, p. 2-13 (includes the (xof − xhf)²(Ixyf/Iyf)² term)."""
    r = f.Ixyf / f.Iyf
    bracket = f.xhf**2 + f.yof**2 - 2 * f.yof * (f.xof - f.xhf) * r + (f.xof - f.xhf) ** 2 * r**2
    return (math.pi / ld) ** 2 * (f.Ixf + f.Iyf + f.Af * bracket)


def k_phi_wg_compression(t: float, ho: float, ld: float) -> float:
    """Eq. 2.3.3.1-6, p. 2-13: (π/Ld)² t ho³ / 60."""
    return (math.pi / ld) ** 2 * t * ho**3 / 60


def fcrd_compression(k_fe: float, k_we: float, k_phi: float, k_fg: float, k_wg: float) -> float:
    """Eq. 2.3.3.1-2, p. 2-13."""
    return (k_fe + k_we + k_phi) / (k_fg + k_wg)


def lcrd_flexure_perpendicular(f: FlangeProperties, t: float, ho: float) -> float:
    """Eq. 2.3.3.2-4, p. 2-15: bending about the axis perpendicular to the web."""
    return math.pi * ho * (4 * (1 - MU**2) / (t**3 * ho**3) * _warping_term(f) + 1 / 720) ** 0.25


def k_phi_we_flexure_perpendicular(t: float, ho: float, ld: float) -> float:
    """Eq. 2.3.3.2-5, p. 2-15."""
    r = math.pi * ho / ld
    return E * t**3 / (12 * (1 - MU**2)) * (3 / ho) * (1 + 2 / 15 * r**2 + r**4 / 720)


def k_phi_fg_flexure(f: FlangeProperties, ld: float) -> float:
    """Eq. 2.3.3.2-6, p. 2-15 (no (Ixyf/Iyf)² term; the bracket also enters Eq. 2.3.3.2-10)."""
    bracket = f.xhf**2 + f.yof**2 - 2 * f.yof * (f.xof - f.xhf) * (f.Ixyf / f.Iyf)
    return (math.pi / ld) ** 2 * (f.Ixf + f.Iyf + f.Af * bracket)


def k_phi_wg_flexure_perpendicular(t: float, ho: float, ld: float, xi_web: float) -> float:
    """Eq. 2.3.3.2-7, p. 2-15; xi_web = (f1 − f2)/f1 over the web."""
    r = math.pi * ho / ld
    return (math.pi / ld) ** 2 * t * ho**3 / 240 * (1110 + 810 * (1 - xi_web) + 8 * r**2 + r**4) / (420 + 28 * r**2 + r**4)


def he_parallel(f: FlangeProperties) -> float:
    """Eq. 2.3.3.2-11, p. 2-16: he = 3.5 √(Iyf/Af + xhf²)."""
    return 3.5 * math.sqrt(f.Iyf / f.Af + f.xhf**2)


def lcrd_flexure_parallel(f: FlangeProperties, t: float, he: float) -> float:
    """Eq. 2.3.3.2-8, p. 2-16: bending about the axis parallel to the web, web in tension."""
    return math.pi * he * (6 * (1 - MU**2) / (t**3 * he**3) * _warping_term(f) + 1 / 120) ** 0.25


def k_phi_we_flexure_parallel(t: float, he: float, ld: float) -> float:
    """Eq. 2.3.3.2-9, p. 2-16."""
    r = math.pi * he / ld
    return E * t**3 / (12 * (1 - MU**2)) * (2 / he) * (1 + r**2 / 6 + r**4 / 120)


def k_phi_fg_flexure_parallel(f: FlangeProperties, ld: float, psi_f: float, xi_f: float) -> float:
    """Eq. 2.3.3.2-10, p. 2-16; k̃φwg = 0 in this case."""
    return k_phi_fg_flexure(f, ld) * psi_f + (math.pi / ld) ** 2 * f.Iyf * xi_f


def fcrd_flexure(beta: float, k_fe: float, k_we: float, k_phi: float, k_fg: float, k_wg: float) -> float:
    """Eq. 2.3.3.2-2, p. 2-14."""
    return beta * (k_fe + k_we + k_phi) / (k_fg + k_wg)
