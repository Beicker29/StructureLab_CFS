"""Elastic critical loads of C_LIPPED and Z_LIPPED members by AISI S100-24 Appendix 2.3 (analytical).

Selection only; formulas live in codes/aisi_s100_24/appendix_2.py and appendix_1.py. Decisions
D5-D11 are in docs/chapter-appendix-2.md. Each quantity is computed independently: missing data
(lengths, Cb, Lm) or a case outside the analytical solutions blocks only that quantity.
Internal units N, mm, MPa; reported forces in kN, moments in kN·m, stresses in MPa, lengths in mm.
"""
import math
from collections.abc import Callable
from typing import Any

from ..codes.aisi_s100_24 import appendix_1 as a1
from ..codes.aisi_s100_24 import appendix_2 as a2
from ..errors import BLOCKING_ERRORS, IncompleteDataError, RuleNotImplementedError
from ..models import MemberInput
from ..sections import SectionProperties, section_geometry
from ..sections.geometry import Line

Stress = Callable[[float, float], float]  # (x, y) -> stress, compression positive


def _blocked(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return fn()
    except BLOCKING_ERRORS as error:
        return {"error": error.to_dict()}


def _need(**values: float | None) -> dict[str, float]:
    missing = [k for k, v in values.items() if v is None]
    if missing:
        raise IncompleteDataError(f"elastic buckling needs {', '.join(missing)}", details={"missing": missing})
    return {k: float(v) for k, v in values.items() if v is not None}


class _Member:
    """Section, geometry and member data shared by the buckling quantities."""

    def __init__(self, member: MemberInput, section: SectionProperties):
        self.member, self.section = member, section
        self.p, self.dims = section.properties, section.dimensions
        self.t, self.H, self.B = self.dims["t"], self.dims["H"], self.dims["B"]
        self.is_c = section.shape == "C_LIPPED"
        geometry = section_geometry(section.shape, self.H, self.B, self.dims["D"], self.t, self.dims["R"], self.dims["lip_angle"])
        lines = [e for e in geometry.midline if isinstance(e, Line)]
        # top half: lip (p = tip, q = bend), flange, web; flat widths from geometry.flats
        self.elements = [("lip", lines[0], geometry.flats[0]), ("flange", lines[1], geometry.flats[1]),
                         ("web", lines[2], geometry.flats[2])]
        self.xc = self.p["xcent"] if self.is_c else 0.0   # C: web outer face at x = 0; Z: web midline at x = 0
        el = section.elements
        if self.is_c:
            self.flange = a2.flange_properties_c(el["b_mid"], el["d_mid"], self.t)
        else:
            self.flange = a2.flange_properties_z(el["b_mid"], el["d_mid"], self.t, math.radians(self.dims["lip_angle"]))
        self.junction_x = geometry.vertices[2][0]           # flange/web junction of the mid-line (Table 2.3.3-1)
        lengths, factors = member.lengths, member.factors
        self.kxlx = None if lengths.Lx is None else factors.Kx * lengths.Lx
        self.kyly = None if lengths.Ly is None else factors.Ky * lengths.Ly
        self.ktlt = None if lengths.Lz is None else factors.Kt * lengths.Lz
        self.cb = member.flexure.Cb if member.flexure else None
        self.k_phi = member.buckling.k_phi if member.buckling.k_phi is not None else 0.0
        self.lm = member.buckling.Lm

    def pt(self, ktlt: float) -> float:
        return a2.torsional_buckling_force(self.p["ro"], self.p["J"], self.p["Cw"], ktlt)

    def ld(self, lcrd: float) -> tuple[float, float]:
        """Ld = min(Lcrd, Lm); with continuous rotational restraint (k_phi > 0) and no Lm, Lm = Lcrd (2.3.3.1, 2.3.3.2)."""
        lm = self.lm
        if lm is None:
            if self.k_phi > 0:
                lm = lcrd
            else:
                raise IncompleteDataError("distortional buckling needs Lm (distance between discrete restraints)",
                                          details={"missing": ["Lm"]})
        return min(lcrd, lm), lm


# --- global ----------------------------------------------------------------------------------------------------------

def _compression_global(m: _Member) -> dict[str, Any]:
    v = _need(KxLx=m.kxlx, KyLy=m.kyly, KtLt=m.ktlt)
    p = m.p
    modes = {"flexural_x": a2.flexural_buckling_force(p["Ix"], v["KxLx"]),
             "flexural_y": a2.flexural_buckling_force(p["Iy"], v["KyLy"])}
    if m.is_c:
        beta = a2.beta_flexural_torsional(p["xo"], p["ro"], v["KtLt"], v["KxLx"])
        modes["flexural_torsional"] = a2.flexural_torsional_force(modes["flexural_x"], m.pt(v["KtLt"]), beta)
        equation = "2.3.1.1.1-1; 2.3.1.1.2-1"
    else:
        modes["torsional"] = m.pt(v["KtLt"])
        modes["flexural_minor_principal"] = a2.flexural_buckling_force(p["I2"], max(v["KxLx"], v["KyLy"]))
        equation = "2.3.1.1.1-1; 2.3.1.1.3"
    mode = min(modes, key=lambda k: modes[k])
    pcre = modes[mode]
    return {"value": pcre / 1e3, "stress_MPa": pcre / p["A"], "mode": mode, "equation": f"Eq. {equation}; 2.3.1.1-1",
            "modes_kN": {k: val / 1e3 for k, val in modes.items()}}


def _flexure_global(m: _Member, axis: str, compression_at_tips: bool) -> dict[str, Any]:
    p = m.p
    if axis == "x":
        v = _need(KyLy=m.kyly, KtLt=m.ktlt, Cb=m.cb)
        p_ey, p_t = a2.flexural_buckling_force(p["Iy"], v["KyLy"]), m.pt(v["KtLt"])
        if m.is_c:
            mcre, eq, sfc = a2.mcre_symmetric_axis(v["Cb"], p["ro"], p_ey, p_t), "2.3.1.2.1-1", p["Sx"]
        else:
            mcre, eq, sfc = a2.mcre_point_symmetric(v["Cb"], p["ro"], p_ey, p_t), "2.3.1.2.3-1", p["Sx"]
    else:
        if not m.is_c:
            raise RuleNotImplementedError("Mcre of the Z about the y-axis needs Appendix 2.3.1.2.5 or a numerical solution (D8)",
                                          details={"decision": "D8"})
        v = _need(KxLx=m.kxlx, KtLt=m.ktlt, Cb=m.cb)
        compression_side = 1 if compression_at_tips else -1          # +x is toward the tips
        cs = 1 if compression_side * p["xo"] > 0 else -1             # shear centre on the compression side
        p_ex = a2.flexural_buckling_force(p["Ix"], v["KxLx"])
        mcre, eq = a2.mcre_non_symmetric_axis(v["Cb"], p_ex, cs, p["j_asym"], p["ro"], m.pt(v["KtLt"])), "2.3.1.2.2-1"
        sfc = p["Sy_tip"] if compression_at_tips else p["Sy_web"]
    return {"value": mcre / 1e6, "stress_MPa": mcre / sfc, "equation": f"Eq. {eq}; 2.3.1.2-1", "Cb": v["Cb"]}


# --- local -----------------------------------------------------------------------------------------------------------

def _element_stress(m: _Member, kind: str, line: Line, w: float, f: Stress, f_ext: float) -> tuple[float, float, str] | None:
    """Local buckling stress of one element referred to the extreme compression fiber (D11), or None if in tension."""
    fp, fq = f(*line.p), f(*line.q)
    f1, f2 = max(fp, fq), min(fp, fq)
    if f1 <= 0:
        return None
    if kind == "lip":                                  # unstiffened; q is the supported (bend) end
        f_sup, f_free = fq, fp
        if f2 < 0:
            raise RuleNotImplementedError("lip under stress gradient with tension is not implemented",
                                          details={"element": "lip"})
        if math.isclose(f_sup, f_free, rel_tol=1e-9):
            k, eq = a1.K_UNSTIFFENED, "1.2.1"
        elif f_free < f_sup:
            k, eq = a1.k_unstiffened_decreasing_to_free_edge(f_free / f_sup), "Eq. 1.2.2-2"
        else:
            k, eq = a1.k_unstiffened_increasing_to_free_edge(f_sup / f_free), "Eq. 1.2.2-3"
    elif f2 < 0:
        k, eq = a1.k_web_compression_tension(abs(f2 / f1)), "Eq. 1.1.2-2"
    elif math.isclose(f1, f2, rel_tol=1e-9):
        k, eq = a1.K_STIFFENED, "1.1"
    else:
        k, eq = a1.k_stiffened_both_compression(f2 / f1), "Eq. 1.1.2-8"
    fcr = a2.plate_buckling_stress(k, m.t, w)
    return fcr * f_ext / f1, k, eq


def _local(m: _Member, f: Stress, f_ext: float, sfc_or_area: float, to_unit: float, equation: str) -> dict[str, Any]:
    results = {}
    for kind, line, w in m.elements:
        r = _element_stress(m, kind, line, w, f, f_ext)
        if r is not None:
            results[kind] = r
    governing = min(results, key=lambda k: results[k][0])
    fcr = results[governing][0]
    return {"value": sfc_or_area * fcr / to_unit, "stress_MPa": fcr, "governing_element": governing, "equation": equation,
            "elements": {k: {"Fcr_MPa": r[0], "k": r[1], "k_source": r[2]} for k, r in results.items()}}


# --- distortional ----------------------------------------------------------------------------------------------------

def _compression_distortional(m: _Member) -> dict[str, Any]:
    f, t, ho = m.flange, m.t, m.H
    lcrd = a2.lcrd_compression(f, t, ho)
    ld, lm = m.ld(lcrd)
    fcrd = a2.fcrd_compression(a2.k_phi_fe(f, ld), a2.k_phi_we_compression(t, ho), m.k_phi,
                               a2.k_phi_fg_compression(f, ld), a2.k_phi_wg_compression(t, ho, ld))
    return {"value": m.p["A"] * fcrd / 1e3, "stress_MPa": fcrd, "Lcrd_mm": lcrd, "Lm_mm": lm, "Ld_mm": ld,
            "equation": "Eqs. 2.3.3.1-1 to 2.3.3.1-7; Table 2.3.3-1"}


def _flexure_x_distortional(m: _Member, f_web: tuple[float, float]) -> dict[str, Any]:
    f, t, ho = m.flange, m.t, m.H
    lcrd = a2.lcrd_flexure_perpendicular(f, t, ho)
    ld, lm = m.ld(lcrd)
    xi_web = (f_web[0] - f_web[1]) / f_web[0]
    fcrd = a2.fcrd_flexure(1.0, a2.k_phi_fe(f, ld), a2.k_phi_we_flexure_perpendicular(t, ho, ld), m.k_phi,
                           a2.k_phi_fg_flexure(f, ld), a2.k_phi_wg_flexure_perpendicular(t, ho, ld, xi_web))
    return {"value": m.p["Sx"] * fcrd / 1e6, "stress_MPa": fcrd, "Lcrd_mm": lcrd, "Lm_mm": lm, "Ld_mm": ld, "xi_web": xi_web,
            "beta": 1.0, "equation": "Eqs. 2.3.3.2-1 to 2.3.3.2-7, case (a); Table 2.3.3-1"}


def _flexure_y_distortional(m: _Member, compression_at_tips: bool) -> dict[str, Any]:
    if not m.is_c:
        raise RuleNotImplementedError("Mcrd of the Z about the y-axis is outside Appendix 2.3.3.2 (D8)", details={"decision": "D8"})
    if not compression_at_tips:
        raise RuleNotImplementedError("Mcrd with the web in compression is outside Appendix 2.3.3.2(b) (D8)",
                                      details={"decision": "D8"})
    f, t = m.flange, m.t
    he = a2.he_parallel(f)
    lcrd = a2.lcrd_flexure_parallel(f, t, he)
    ld, lm = m.ld(lcrd)
    f1 = m.B - m.xc                                             # extreme compression fiber of flange and stiffener
    xi_f = (f1 - (m.junction_x - m.xc)) / f1
    psi_f = (m.junction_x - f.xhf - m.xc) / f1                  # flange centroid = junction − xhf
    fcrd = a2.fcrd_flexure(1.0, a2.k_phi_fe(f, ld), a2.k_phi_we_flexure_parallel(t, he, ld), m.k_phi,
                           a2.k_phi_fg_flexure_parallel(f, ld, psi_f, xi_f), 0.0)
    return {"value": m.p["Sy_tip"] * fcrd / 1e6, "stress_MPa": fcrd, "Lcrd_mm": lcrd, "Lm_mm": lm, "Ld_mm": ld, "he_mm": he,
            "xi_f": xi_f, "psi_f": psi_f, "beta": 1.0, "equation": "Eqs. 2.3.3.2-1 to 2.3.3.2-3, 2.3.3.2-8 to 2.3.3.2-11, case (b)"}


# --- assembly --------------------------------------------------------------------------------------------------------

def elastic_buckling(member: MemberInput, section: SectionProperties) -> dict[str, Any]:
    """Pcre, Pcrl, Pcrd and Mcre, Mcrl, Mcrd for each bending case; blocked quantities carry their error."""
    m = _Member(member, section)
    out: dict[str, Any] = {
        "source": "analytical (S100-24 Appendix 2.3)",
        "constants": {"E_MPa": a2.E, "G_MPa": a2.G, "mu": a2.MU},
        "k_phi": {"value_N_mm_per_mm_rad": m.k_phi,
                  "source": "input" if member.buckling.k_phi is not None else "2.3.3: conservatively taken as zero"},
        "beta_distortional": {"value": 1.0, "source": "Eq. 2.3.3.2-3: conservatively taken as 1.0"},
    }
    half_h = m.H / 2
    out["compression"] = {
        "global": _blocked(lambda: _compression_global(m)),
        "local": _blocked(lambda: _local(m, lambda x, y: 1.0, 1.0, m.p["A"], 1e3, "Eqs. 2.3.2.1-1, 2.3.2.1-2")),
        "distortional": _blocked(lambda: _compression_distortional(m)),
    }
    web = m.elements[2][1]
    out["flexure_x"] = {
        "global": _blocked(lambda: _flexure_global(m, "x", True)),
        "local": _blocked(lambda: _local(m, lambda x, y: y, half_h, m.p["Sx"], 1e6, "Eqs. 2.3.2.2-1, 2.3.2.2-2")),
        "distortional": _blocked(lambda: _flexure_x_distortional(m, (web.p[1], web.q[1]))),
    }
    for name, tips in (("flexure_y_tips_compression", True), ("flexure_y_web_compression", False)):
        out[name] = _flexure_y(m, tips)
    return out


def _flexure_y_local(m: _Member, tips: bool) -> dict[str, Any]:
    if not m.is_c:
        raise RuleNotImplementedError("Mcrl of the Z about the y-axis is not implemented (D8)", details={"decision": "D8"})
    sign = 1.0 if tips else -1.0

    def stress(x: float, y: float) -> float:
        return sign * (x - m.xc)

    f_ext = (m.B - m.xc) if tips else m.xc
    sfc = m.p["Sy_tip"] if tips else m.p["Sy_web"]
    return _local(m, stress, f_ext, sfc, 1e6, "Eqs. 2.3.2.2-1, 2.3.2.2-2")


def _flexure_y(m: _Member, tips: bool) -> dict[str, Any]:
    """Bending about y: C with the tips (lips) or the web in compression; the Z is outside the scope (D8)."""
    return {"global": _blocked(lambda: _flexure_global(m, "y", tips)),
            "local": _blocked(lambda: _flexure_y_local(m, tips)),
            "distortional": _blocked(lambda: _flexure_y_distortional(m, tips))}
