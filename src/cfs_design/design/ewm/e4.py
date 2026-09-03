"""S100-24 E4 and Appendix 2 analytical distortional compression route."""

from math import pi

from cfs_design.normative import S100_24_ELASTIC_CONSTANTS

from ._validation import EWMCalculationError, finite_result, positive, positive_result, square_root
from .models import DistortionalBucklingResult, E4StrengthResult, FlangeLipProperties


E4_MAX_DISTORTIONAL_SLENDERNESS = 5.0


def calculate_flange_lip_properties(
    *,
    flange_midline_width_mm: float,
    lip_midline_width_mm: float,
    thickness_mm: float,
) -> FlangeLipProperties:
    """Calculate the orthogonal simple-lip terms in Appendix 2 Table 2.3.3-1."""

    b = positive(flange_midline_width_mm, "midline b")
    d = positive(lip_midline_width_mm, "midline d")
    thickness = positive(thickness_mm, "t")
    denominator = positive_result(12.0 * (b + d), "flange property denominator")
    af = positive_result((b + d) * thickness, "Af")
    jf = positive_result((b + d) * thickness**3 / 3.0, "Jf")
    ixf = positive_result(
        thickness
        * (
            thickness**2 * b**2
            + 4.0 * b * d**3
            + thickness**2 * b * d
            + d**4
        )
        / denominator,
        "Ixf",
    )
    iyf = positive_result(
        thickness * (b**4 + 4.0 * d * b**3) / denominator,
        "Iyf",
    )
    ixyf = positive_result(
        thickness * b**2 * d**2 / (4.0 * (b + d)),
        "Ixyf",
    )
    xof = finite_result(b**2 / (2.0 * (b + d)), "xof")
    xhf = finite_result(-(b**2 + 2.0 * d * b) / (2.0 * (b + d)), "xhf")
    yof = finite_result(-(d**2) / (2.0 * (b + d)), "yof")
    return FlangeLipProperties(
        af_mm2=af,
        jf_mm4=jf,
        ixf_mm4=ixf,
        iyf_mm4=iyf,
        ixyf_mm4=ixyf,
        cwf_mm6=0.0,
        xof_mm=xof,
        xhf_mm=xhf,
        yof_mm=yof,
        yhf_mm=yof,
    )


def calculate_distortional_buckling(
    *,
    flange_midline_width_mm: float,
    lip_midline_width_mm: float,
    web_out_to_out_depth_mm: float,
    thickness_mm: float,
    gross_area_mm2: float,
    distortional_unbraced_length_mm: float,
) -> DistortionalBucklingResult:
    """Apply Appendix 2 Eqs. 2.3.3.1-1 through 2.3.3.1-7."""

    flange = calculate_flange_lip_properties(
        flange_midline_width_mm=flange_midline_width_mm,
        lip_midline_width_mm=lip_midline_width_mm,
        thickness_mm=thickness_mm,
    )
    ho = positive(web_out_to_out_depth_mm, "ho")
    thickness = positive(thickness_mm, "t")
    area = positive(gross_area_mm2, "Ag")
    lm = positive(distortional_unbraced_length_mm, "Lm")
    e = S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value
    g = S100_24_ELASTIC_CONSTANTS.shear_modulus.value.value
    mu = S100_24_ELASTIC_CONSTANTS.poisson_ratio.value.value

    inertia_coupling_ratio = finite_result(
        flange.ixyf_mm4**2 / (flange.ixf_mm4 * flange.iyf_mm4),
        "Ixyf squared over Ixf Iyf",
    )
    if not 0.0 <= inertia_coupling_ratio < 1.0:
        raise EWMCalculationError(
            "EWM_E4_FLANGE_PROPERTY_DOMAIN_ERROR",
            "Table 2.3.3-1 flange inertia coupling ratio must be in [0, 1)",
        )
    delta_x = flange.xof_mm - flange.xhf_mm
    flange_warping_term = positive_result(
        flange.cwf_mm6
        + flange.ixf_mm4
        * delta_x**2
        * (1.0 - inertia_coupling_ratio),
        "distortional flange warping term",
    )
    lcrd_root = positive_result(
        6.0
        * (1.0 - mu**2)
        / (thickness**3 * ho**3)
        * flange_warping_term,
        "Lcrd fourth-power term",
    )
    l_crd = positive_result(pi * ho * lcrd_root ** 0.25, "Lcrd")
    l_d = positive_result(min(l_crd, lm), "Ld")
    wave = pi / l_d

    k_phi_fe = positive_result(
        wave**4 * e * flange_warping_term
        + wave**2 * g * flange.jf_mm4,
        "k_phi_fe",
    )
    k_phi_we = positive_result(
        e * thickness**3 / (12.0 * (1.0 - mu**2)) * (2.0 / ho),
        "k_phi_we",
    )
    # Appendix 2 Section 2.3.3.1 explicitly permits this conservative value.
    k_phi = 0.0
    ratio = flange.ixyf_mm4 / flange.iyf_mm4
    k_phi_fg = positive_result(
        wave**2
        * (
            flange.ixf_mm4
            + flange.iyf_mm4
            + flange.af_mm2
            * (
                flange.xhf_mm**2
                + flange.yof_mm**2
                - 2.0 * flange.yof_mm * delta_x * ratio
                + delta_x**2 * ratio**2
            )
        ),
        "k_phi_fg",
    )
    k_phi_wg = positive_result(
        wave**2 * thickness * ho**3 / 60.0,
        "k_phi_wg",
    )
    f_crd = positive_result(
        (k_phi_fe + k_phi_we + k_phi) / (k_phi_fg + k_phi_wg),
        "Fcrd",
    )
    p_crd = positive_result(area * f_crd, "Pcrd")
    return DistortionalBucklingResult(
        flange=flange,
        l_crd_mm=l_crd,
        l_m_mm=lm,
        l_d_mm=l_d,
        k_phi_fe_n=k_phi_fe,
        k_phi_we_n=k_phi_we,
        k_phi_n=k_phi,
        k_phi_fg_mm2=k_phi_fg,
        k_phi_wg_mm2=k_phi_wg,
        f_crd_mpa=f_crd,
        p_crd_n=p_crd,
    )


def calculate_e4_strength(
    *,
    buckling: DistortionalBucklingResult,
    gross_area_mm2: float,
    yield_stress_mpa: float,
) -> E4StrengthResult:
    """Apply S100-24 Eqs. E4-1 through E4-3."""

    area = positive(gross_area_mm2, "Ag")
    fy = positive(yield_stress_mpa, "Fy")
    p_y = positive_result(area * fy, "Py")
    lambda_d = positive_result(
        square_root(p_y / positive(buckling.p_crd_n, "Pcrd"), "Py/Pcrd"),
        "lambda_d",
    )
    if lambda_d > E4_MAX_DISTORTIONAL_SLENDERNESS:
        raise EWMCalculationError(
            "EWM_E4_SLENDERNESS_UNSUPPORTED",
            "S100-24 E4-1 is limited to lambda_d not greater than 5",
        )
    p_nd = positive_result(
        1.2
        * p_y
        * (1.0 + 0.05 * lambda_d**2)
        / (1.0 + 0.67 * lambda_d**2),
        "Pnd",
    )
    if p_nd > p_y:
        p_nd = p_y
    return E4StrengthResult(
        buckling=buckling,
        p_y_n=p_y,
        lambda_d=lambda_d,
        p_nd_n=p_nd,
    )


__all__ = [
    "E4_MAX_DISTORTIONAL_SLENDERNESS",
    "calculate_distortional_buckling",
    "calculate_e4_strength",
    "calculate_flange_lip_properties",
]
