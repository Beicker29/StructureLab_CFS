"""Shared S100-24 E2 and Appendix 2 global-compression mechanics."""

from math import pi

from cfs_design.domain import LengthDefinition, MemberGeometry, SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import ResolvedSectionMechanics
from cfs_design.normative import S100_24_ELASTIC_CONSTANTS

from ._validation import (
    EngineeringCalculationError,
    finite_result,
    non_negative,
    positive,
    positive_result,
    square_root,
)
from .models import (
    ColumnCurveBranch,
    EffectiveLengths,
    GlobalBucklingMode,
    GlobalBucklingResult,
    GlobalColumnStrength,
)


GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE = 1.0e-12
GLOBAL_SLENDERNESS_TRANSITION = 1.5
SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4 = 1.0e-9
SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM = 1.0e-9


def require_singly_symmetric_c(
    geometry: SectionGeometry,
    mechanics: ResolvedSectionMechanics,
    *,
    error_code: str,
    owner: str,
) -> None:
    """Enforce the validated M8B singly-symmetric C global-buckling route."""

    symmetric_dimensions = (
        geometry.b2_mm is not None and geometry.b1_mm == geometry.b2_mm
    )
    if geometry.section_type is SectionFamily.C_LIPPED:
        symmetric_dimensions = (
            symmetric_dimensions
            and geometry.d1_mm is not None
            and geometry.d1_mm == geometry.d2_mm
        )
    if (
        not symmetric_dimensions
        or abs(mechanics.gross.ixy_mm4)
        > SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4
        or abs(mechanics.advanced.y0_mm)
        > SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM
    ):
        raise EngineeringCalculationError(
            error_code,
            f"{owner} global buckling implements the singly symmetric C-section route only",
        )


def resolve_effective_lengths(member_geometry: MemberGeometry) -> EffectiveLengths:
    """Resolve the existing member length contract without substituting Lb or Lm."""

    if member_geometry.length_definition is LengthDefinition.K_FACTORS:
        if any(
            value is None
            for value in (member_geometry.kx, member_geometry.ky, member_geometry.kt)
        ):
            raise EngineeringCalculationError(
                "EWM_GLOBAL_LENGTHS_REQUIRED",
                "K-factor length definition is incomplete",
            )
        length = positive(member_geometry.l_mm, "L")
        lx = length * positive(member_geometry.kx, "Kx")  # type: ignore[arg-type]
        ly = length * positive(member_geometry.ky, "Ky")  # type: ignore[arg-type]
        lt = length * positive(member_geometry.kt, "Kt")  # type: ignore[arg-type]
        source = "K_FACTORS_TIMES_MEMBER_LENGTH"
    else:
        if any(
            value is None
            for value in (
                member_geometry.lx_mm,
                member_geometry.ly_mm,
                member_geometry.lt_mm,
            )
        ):
            raise EngineeringCalculationError(
                "EWM_GLOBAL_LENGTHS_REQUIRED",
                "explicit effective-length definition is incomplete",
            )
        lx = positive(member_geometry.lx_mm, "Lx")  # type: ignore[arg-type]
        ly = positive(member_geometry.ly_mm, "Ly")  # type: ignore[arg-type]
        lt = positive(member_geometry.lt_mm, "Lt")  # type: ignore[arg-type]
        source = "EXPLICIT_EFFECTIVE_LENGTHS"
    return EffectiveLengths(
        lx_mm=positive_result(lx, "KxLx"),
        ly_mm=positive_result(ly, "KyLy"),
        lt_mm=positive_result(lt, "KtLt"),
        source=source,
    )


def calculate_global_buckling(
    member_geometry: MemberGeometry,
    mechanics: ResolvedSectionMechanics,
) -> GlobalBucklingResult:
    """Calculate Appendix 2 Sections 2.3.1 and 2.3.1.1.2 quantities."""

    lengths = resolve_effective_lengths(member_geometry)
    gross = mechanics.gross
    advanced = mechanics.advanced
    area = positive(gross.a_mm2, "Ag")
    ix = positive(gross.ix_mm4, "Ix")
    iy = positive(gross.iy_mm4, "Iy")
    j = positive(gross.j_mm4, "J")
    cw = non_negative(advanced.cw_mm6, "Cw")
    x0 = finite_result(advanced.x0_mm, "x0")
    y0 = finite_result(advanced.y0_mm, "y0")
    e = S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value
    g = S100_24_ELASTIC_CONSTANTS.shear_modulus.value.value

    ro_squared = ix / area + iy / area + x0 * x0 + y0 * y0
    ro = positive_result(square_root(ro_squared, "ro squared"), "ro")
    p_ex = positive_result(pi * pi * e * ix / (lengths.lx_mm**2), "Pex")
    p_ey = positive_result(pi * pi * e * iy / (lengths.ly_mm**2), "Pey")
    p_t = positive_result(
        (g * j + pi * pi * e * cw / (lengths.lt_mm**2)) / ro_squared,
        "Pt",
    )
    beta = finite_result(
        1.0 - (x0 / ro) ** 2 * (lengths.lt_mm / lengths.lx_mm) ** 2,
        "beta",
    )
    if beta <= 0.0:
        raise EngineeringCalculationError(
            "EWM_GLOBAL_BETA_DOMAIN_ERROR",
            "Appendix 2 flexural-torsional coefficient beta must be positive",
        )

    p_flexural = min(p_ex, p_ey)
    flexural_mode = (
        GlobalBucklingMode.FLEXURAL_X
        if p_ex <= p_ey
        else GlobalBucklingMode.FLEXURAL_Y
    )
    total = positive_result(p_ex + p_t, "Pex plus Pt")
    discriminant = finite_result(
        total * total - 4.0 * beta * p_ex * p_t,
        "discriminant",
    )
    if discriminant < 0.0:
        if (
            abs(discriminant)
            <= GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE * total * total
        ):
            discriminant = 0.0
        else:
            raise EngineeringCalculationError(
                "EWM_GLOBAL_DISCRIMINANT_DOMAIN_ERROR",
                "Appendix 2 flexural-torsional discriminant is negative",
            )
    root = square_root(discriminant, "flexural-torsional discriminant")
    p_ft = positive_result(
        2.0 * p_ex * p_t / (total + root),
        "Pcre flexural-torsional",
    )

    if p_flexural <= p_ft:
        p_cre = p_flexural
        governing = flexural_mode
    else:
        p_cre = p_ft
        governing = GlobalBucklingMode.FLEXURAL_TORSIONAL
    f_cre = positive_result(p_cre / area, "Fcre")
    return GlobalBucklingResult(
        effective_lengths=lengths,
        ro_mm=ro,
        p_ex_n=p_ex,
        p_ey_n=p_ey,
        p_t_n=p_t,
        beta=beta,
        p_flexural_n=p_flexural,
        flexural_mode=flexural_mode,
        p_flexural_torsional_n=p_ft,
        p_cre_n=p_cre,
        f_cre_mpa=f_cre,
        governing_mode=governing,
    )


def calculate_global_column_strength(
    *, gross_area_mm2: float, yield_stress_mpa: float, f_cre_mpa: float
) -> GlobalColumnStrength:
    """Apply S100-24 Eqs. E2-1 through E2-4."""

    area = positive(gross_area_mm2, "Ag")
    fy = positive(yield_stress_mpa, "Fy")
    f_cre = positive(f_cre_mpa, "Fcre")
    lambda_c = positive_result(square_root(fy / f_cre, "Fy/Fcre"), "lambda_c")
    if lambda_c <= GLOBAL_SLENDERNESS_TRANSITION:
        fn = positive_result(0.658 ** (lambda_c**2) * fy, "Fn")
        branch = ColumnCurveBranch.INELASTIC
    else:
        fn = positive_result(0.877 / (lambda_c**2) * fy, "Fn")
        branch = ColumnCurveBranch.ELASTIC
    p_ne = positive_result(area * fn, "Pne")
    return GlobalColumnStrength(
        lambda_c=lambda_c,
        fn_mpa=fn,
        p_ne_n=p_ne,
        branch=branch,
    )


__all__ = [
    "GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE",
    "GLOBAL_SLENDERNESS_TRANSITION",
    "SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4",
    "SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM",
    "calculate_global_buckling",
    "calculate_global_column_strength",
    "resolve_effective_lengths",
    "require_singly_symmetric_c",
]
