"""S100-24 Appendix 1 effective widths needed by axial EWM."""

from math import pi, radians, sin

from cfs_design.normative import S100_24_ELASTIC_CONSTANTS

from ._validation import EWMCalculationError, finite_result, positive, positive_result, square_root
from .interpretations import S10024_A1_1_3A_XREF_001
from .models import EffectiveWidthResult, PlateClassification, PlateElementId


LOCAL_SLENDERNESS_TRANSITION = 0.673
SIMPLE_LIP_STOCKY_FACTOR = 0.328
STIFFENED_PLATE_COEFFICIENT = 4.0
UNSTIFFENED_PLATE_COEFFICIENT = 0.43
SIMPLE_LIP_MAX_D_OVER_W = 0.8


def calculate_uniform_effective_width(
    *,
    element_id: PlateElementId,
    classification: PlateClassification,
    width_mm: float,
    thickness_mm: float,
    stress_mpa: float,
    plate_coefficient: float,
) -> EffectiveWidthResult:
    """Apply Appendix 1 Eqs. 1.1-1 through 1.1-4."""

    width = positive(width_mm, "w")
    thickness = positive(thickness_mm, "t")
    stress = positive(stress_mpa, "f")
    coefficient = positive(plate_coefficient, "k")
    e = S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value
    mu = S100_24_ELASTIC_CONSTANTS.poisson_ratio.value.value

    f_crl = positive_result(
        coefficient
        * pi
        * pi
        * e
        / (12.0 * (1.0 - mu * mu))
        * (thickness / width) ** 2,
        "Fcrl",
    )
    slenderness = positive_result(square_root(stress / f_crl, "f/Fcrl"), "lambda")
    if slenderness <= LOCAL_SLENDERNESS_TRANSITION:
        rho = 1.0
    else:
        rho = finite_result(
            (1.0 - 0.22 / slenderness) / slenderness,
            "rho",
        )
    if not 0.0 < rho <= 1.0:
        raise EWMCalculationError(
            "EWM_EFFECTIVE_WIDTH_DOMAIN_ERROR",
            "Appendix 1 local reduction factor must be in (0, 1]",
        )
    effective_width = positive_result(rho * width, "effective width")
    if effective_width > width:
        raise EWMCalculationError(
            "EWM_EFFECTIVE_WIDTH_DOMAIN_ERROR",
            "effective width exceeds full plate width",
        )
    return EffectiveWidthResult(
        element_id=element_id,
        classification=classification,
        full_width_mm=width,
        effective_width_mm=effective_width,
        plate_coefficient=coefficient,
        f_crl_mpa=f_crl,
        slenderness=slenderness,
        reduction_factor=rho,
    )


def calculate_stiffened_effective_width(
    *,
    element_id: PlateElementId,
    width_mm: float,
    thickness_mm: float,
    stress_mpa: float,
) -> EffectiveWidthResult:
    return calculate_uniform_effective_width(
        element_id=element_id,
        classification=PlateClassification.UNIFORMLY_COMPRESSED_STIFFENED,
        width_mm=width_mm,
        thickness_mm=thickness_mm,
        stress_mpa=stress_mpa,
        plate_coefficient=STIFFENED_PLATE_COEFFICIENT,
    )


def calculate_unstiffened_effective_width(
    *,
    element_id: PlateElementId,
    classification: PlateClassification = (
        PlateClassification.UNIFORMLY_COMPRESSED_UNSTIFFENED
    ),
    width_mm: float,
    thickness_mm: float,
    stress_mpa: float,
) -> EffectiveWidthResult:
    return calculate_uniform_effective_width(
        element_id=element_id,
        classification=classification,
        width_mm=width_mm,
        thickness_mm=thickness_mm,
        stress_mpa=stress_mpa,
        plate_coefficient=UNSTIFFENED_PLATE_COEFFICIENT,
    )


def calculate_simple_lip_effective_width(
    *,
    flange_element_id: PlateElementId,
    lip_element_id: PlateElementId,
    flange_flat_width_mm: float,
    lip_flat_width_mm: float,
    lip_overall_depth_mm: float,
    thickness_mm: float,
    stress_mpa: float,
    lip_angle_deg: float,
) -> tuple[EffectiveWidthResult, EffectiveWidthResult]:
    """Apply Appendix 1 Section 1.3(a) for a no-hole simple lip."""

    w = positive(flange_flat_width_mm, "flange w")
    d = positive(lip_flat_width_mm, "lip d")
    overall_d = positive(lip_overall_depth_mm, "lip D")
    thickness = positive(thickness_mm, "t")
    stress = positive(stress_mpa, "f")
    angle = positive(lip_angle_deg, "theta")
    if not 40.0 <= angle <= 140.0:
        raise EWMCalculationError(
            "EWM_SIMPLE_LIP_ANGLE_UNSUPPORTED",
            "Table 1.3-1 requires a simple-lip angle between 40 and 140 degrees",
        )
    d_over_w = finite_result(overall_d / w, "D/w")
    if d_over_w > SIMPLE_LIP_MAX_D_OVER_W:
        raise EWMCalculationError(
            "EWM_SIMPLE_LIP_DIMENSION_UNSUPPORTED",
            "Table 1.3-1 provides no plate coefficient for D/w greater than 0.8",
        )

    e = S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value
    s_parameter = positive_result(1.28 * square_root(e / stress, "E/f"), "S")
    lip_base = calculate_unstiffened_effective_width(
        element_id=lip_element_id,
        classification=PlateClassification.SIMPLE_LIP_STIFFENER,
        width_mm=d,
        thickness_mm=thickness,
        stress_mpa=stress,
    )
    slender_flange = w / thickness > SIMPLE_LIP_STOCKY_FACTOR * s_parameter
    if not slender_flange:
        flange = EffectiveWidthResult(
            element_id=flange_element_id,
            classification=PlateClassification.SIMPLE_LIP_EDGE_STIFFENED_FLANGE,
            full_width_mm=w,
            effective_width_mm=w,
            plate_coefficient=None,
            f_crl_mpa=None,
            slenderness=None,
            reduction_factor=1.0,
            flange_b1_mm=w / 2.0,
            flange_b2_mm=w / 2.0,
            s_parameter=s_parameter,
            ia_mm4=0.0,
            is_mm4=None,
            stiffener_ratio=1.0,
            exponent_n=None,
            d_over_w=d_over_w,
        )
        lip = EffectiveWidthResult(
            element_id=lip_element_id,
            classification=PlateClassification.SIMPLE_LIP_STIFFENER,
            full_width_mm=d,
            effective_width_mm=lip_base.effective_width_mm,
            plate_coefficient=lip_base.plate_coefficient,
            f_crl_mpa=lip_base.f_crl_mpa,
            slenderness=lip_base.slenderness,
            reduction_factor=lip_base.reduction_factor,
            s_parameter=s_parameter,
            ia_mm4=0.0,
            is_mm4=None,
            stiffener_ratio=1.0,
            d_over_w=d_over_w,
        )
        return flange, lip

    normalized_width = w / thickness / s_parameter
    ia_first = 399.0 * thickness**4 * (normalized_width - 0.328) ** 3
    ia_upper = thickness**4 * (115.0 * normalized_width + 5.0)
    ia = positive_result(min(ia_first, ia_upper), "Ia")
    is_value = positive_result(
        d**3 * thickness * sin(radians(angle)) ** 2 / 12.0,
        "Is",
    )
    stiffener_ratio = min(is_value / ia, 1.0)
    stiffener_ratio = positive_result(stiffener_ratio, "RI")
    exponent_n = max(0.582 - (w / thickness) / (4.0 * s_parameter), 1.0 / 3.0)
    exponent_n = positive_result(exponent_n, "n")
    if d_over_w <= 0.25:
        coefficient = 3.57 * stiffener_ratio**exponent_n + 0.43
    else:
        coefficient = (
            (4.82 - 5.0 * d_over_w) * stiffener_ratio**exponent_n + 0.43
        )
    coefficient = positive_result(min(coefficient, 4.0), "k")

    interpreted = calculate_uniform_effective_width(
        element_id=flange_element_id,
        classification=PlateClassification.SIMPLE_LIP_EDGE_STIFFENED_FLANGE,
        width_mm=w,
        thickness_mm=thickness,
        stress_mpa=stress,
        plate_coefficient=coefficient,
    )
    b = interpreted.effective_width_mm
    b1 = positive_result((b / 2.0) * stiffener_ratio, "b1")
    b2 = positive_result(b - b1, "b2")
    ds = positive_result(lip_base.effective_width_mm * stiffener_ratio, "ds")
    flange = EffectiveWidthResult(
        element_id=flange_element_id,
        classification=PlateClassification.SIMPLE_LIP_EDGE_STIFFENED_FLANGE,
        full_width_mm=w,
        effective_width_mm=b,
        plate_coefficient=coefficient,
        f_crl_mpa=interpreted.f_crl_mpa,
        slenderness=interpreted.slenderness,
        reduction_factor=interpreted.reduction_factor,
        flange_b1_mm=b1,
        flange_b2_mm=b2,
        s_parameter=s_parameter,
        ia_mm4=ia,
        is_mm4=is_value,
        stiffener_ratio=stiffener_ratio,
        exponent_n=exponent_n,
        d_over_w=d_over_w,
        interpretation_id=S10024_A1_1_3A_XREF_001.interpretation_id,
    )
    lip = EffectiveWidthResult(
        element_id=lip_element_id,
        classification=PlateClassification.SIMPLE_LIP_STIFFENER,
        full_width_mm=d,
        effective_width_mm=ds,
        plate_coefficient=lip_base.plate_coefficient,
        f_crl_mpa=lip_base.f_crl_mpa,
        slenderness=lip_base.slenderness,
        reduction_factor=lip_base.reduction_factor * stiffener_ratio,  # type: ignore[operator]
        s_parameter=s_parameter,
        ia_mm4=ia,
        is_mm4=is_value,
        stiffener_ratio=stiffener_ratio,
        exponent_n=exponent_n,
        d_over_w=d_over_w,
        interpretation_id=None,
    )
    return flange, lip


__all__ = [
    "LOCAL_SLENDERNESS_TRANSITION",
    "SIMPLE_LIP_MAX_D_OVER_W",
    "SIMPLE_LIP_STOCKY_FACTOR",
    "STIFFENED_PLATE_COEFFICIENT",
    "UNSTIFFENED_PLATE_COEFFICIENT",
    "calculate_simple_lip_effective_width",
    "calculate_stiffened_effective_width",
    "calculate_uniform_effective_width",
    "calculate_unstiffened_effective_width",
]
