"""Equation and numerical-boundary tests independently checked for M8B."""

from dataclasses import replace
from math import pi, sqrt

import pytest

from cfs_design.domain import LengthDefinition, MemberGeometry
from cfs_design.design.ewm._validation import EWMCalculationError
from cfs_design.design.ewm.compression import (
    GLOBAL_SLENDERNESS_TRANSITION,
    calculate_global_column_strength,
    calculate_local_global_strength,
)
from cfs_design.design.ewm.e4 import (
    E4_MAX_DISTORTIONAL_SLENDERNESS,
    calculate_distortional_buckling,
    calculate_e4_strength,
    calculate_flange_lip_properties,
)
from cfs_design.design.ewm.effective_area import (
    EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2,
    calculate_effective_area,
)
from cfs_design.design.ewm.effective_width import (
    LOCAL_SLENDERNESS_TRANSITION,
    SIMPLE_LIP_MAX_D_OVER_W,
    SIMPLE_LIP_STOCKY_FACTOR,
    calculate_simple_lip_effective_width,
    calculate_uniform_effective_width,
)
from cfs_design.design.ewm.global_buckling import (
    calculate_global_buckling,
    resolve_effective_lengths,
)
from cfs_design.design.ewm.models import (
    ColumnCurveBranch,
    EffectiveWidthResult,
    GlobalBucklingMode,
    PlateClassification,
    PlateElementId,
)
from cfs_design.normative import S100_24_ELASTIC_CONSTANTS


def _uniform_width(*, width: float, thickness: float, stress: float, k: float):
    return calculate_uniform_effective_width(
        element_id=PlateElementId.WEB,
        classification=PlateClassification.UNIFORMLY_COMPRESSED_STIFFENED,
        width_mm=width,
        thickness_mm=thickness,
        stress_mpa=stress,
        plate_coefficient=k,
    )


def _plate_width_at_slenderness(
    slenderness: float, *, thickness: float = 1.0, stress: float = 100.0, k: float = 4.0
) -> float:
    e = 203_000.0
    mu = 0.3
    f_crl = stress / slenderness**2
    return thickness * sqrt(k * pi**2 * e / (12.0 * (1.0 - mu**2) * f_crl))


def test_uniform_plate_stocky_branch_retains_full_width() -> None:
    result = _uniform_width(width=10.0, thickness=1.0, stress=100.0, k=4.0)

    assert result.slenderness < LOCAL_SLENDERNESS_TRANSITION  # type: ignore[operator]
    assert result.reduction_factor == 1.0
    assert result.effective_width_mm == 10.0


def test_uniform_plate_slender_branch_matches_independent_arithmetic() -> None:
    result = _uniform_width(width=100.0, thickness=1.0, stress=345.0, k=4.0)

    assert result.f_crl_mpa == pytest.approx(73.3893660593824)
    assert result.slenderness == pytest.approx(2.1681682447662136)
    assert result.reduction_factor == pytest.approx(0.4144198042330786)
    assert result.effective_width_mm == pytest.approx(41.44198042330786)


def test_uniform_plate_transition_uses_stocky_branch_and_is_nearly_continuous() -> None:
    width = _plate_width_at_slenderness(LOCAL_SLENDERNESS_TRANSITION)
    at_transition = _uniform_width(
        width=width * (1.0 - 1.0e-12), thickness=1.0, stress=100.0, k=4.0
    )
    just_above = _uniform_width(
        width=width * (1.0 + 1.0e-3),
        thickness=1.0,
        stress=100.0,
        k=4.0,
    )

    assert at_transition.reduction_factor == 1.0
    assert just_above.reduction_factor == pytest.approx(1.0, rel=4.0e-4)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("width", 0.0),
        ("width", -1.0),
        ("width", float("nan")),
        ("thickness", 0.0),
        ("thickness", float("inf")),
        ("stress", -1.0),
        ("k", 0.0),
    ],
)
def test_uniform_plate_rejects_invalid_inputs(field: str, value: float) -> None:
    values = {"width": 40.0, "thickness": 1.0, "stress": 100.0, "k": 4.0}
    values[field] = value

    with pytest.raises(EWMCalculationError):
        _uniform_width(**values)


def test_uniform_plate_scale_sanity_preserves_reduction_factor() -> None:
    original = _uniform_width(width=100.0, thickness=1.0, stress=345.0, k=4.0)
    scaled = _uniform_width(width=250.0, thickness=2.5, stress=345.0, k=4.0)

    assert scaled.reduction_factor == pytest.approx(original.reduction_factor)
    assert scaled.effective_width_mm == pytest.approx(
        2.5 * original.effective_width_mm
    )


def test_simple_lip_stocky_branch_does_not_invoke_interpretation() -> None:
    flange, lip = calculate_simple_lip_effective_width(
        flange_element_id=PlateElementId.FLANGE_1,
        lip_element_id=PlateElementId.LIP_1,
        flange_flat_width_mm=10.0,
        lip_flat_width_mm=2.0,
        lip_overall_depth_mm=2.0,
        thickness_mm=1.0,
        stress_mpa=100.0,
        lip_angle_deg=90.0,
    )

    assert 10.0 <= SIMPLE_LIP_STOCKY_FACTOR * flange.s_parameter  # type: ignore[operator]
    assert flange.effective_width_mm == 10.0
    assert flange.interpretation_id is None
    assert lip.interpretation_id is None


def test_simple_lip_slender_branch_retains_controlled_interpretation() -> None:
    flange, lip = calculate_simple_lip_effective_width(
        flange_element_id=PlateElementId.FLANGE_1,
        lip_element_id=PlateElementId.LIP_1,
        flange_flat_width_mm=40.0,
        lip_flat_width_mm=10.0,
        lip_overall_depth_mm=10.0,
        thickness_mm=1.0,
        stress_mpa=53.26551354965097,
        lip_angle_deg=90.0,
    )

    assert flange.ia_mm4 == pytest.approx(2.2579841474084015)
    assert flange.is_mm4 == pytest.approx(83.33333333333333)
    assert flange.plate_coefficient == pytest.approx(4.0)
    assert flange.interpretation_id == "S10024-A1-1_3A-XREF-001"
    assert lip.interpretation_id is None


def test_simple_lip_plate_coefficient_is_continuous_at_d_over_w_quarter() -> None:
    common = {
        "flange_element_id": PlateElementId.FLANGE_1,
        "lip_element_id": PlateElementId.LIP_1,
        "flange_flat_width_mm": 40.0,
        "lip_flat_width_mm": 5.0,
        "thickness_mm": 1.0,
        "stress_mpa": 345.0,
        "lip_angle_deg": 90.0,
    }
    below, _ = calculate_simple_lip_effective_width(
        **common, lip_overall_depth_mm=40.0 * (0.25 - 1.0e-9)
    )
    above, _ = calculate_simple_lip_effective_width(
        **common, lip_overall_depth_mm=40.0 * (0.25 + 1.0e-9)
    )

    assert above.plate_coefficient == pytest.approx(
        below.plate_coefficient, rel=1.0e-8
    )


def test_simple_lip_dimensional_limit_accepts_point_eight_and_rejects_above() -> None:
    common = {
        "flange_element_id": PlateElementId.FLANGE_1,
        "lip_element_id": PlateElementId.LIP_1,
        "flange_flat_width_mm": 20.0,
        "lip_flat_width_mm": 5.0,
        "thickness_mm": 1.0,
        "stress_mpa": 345.0,
        "lip_angle_deg": 90.0,
    }
    accepted, _ = calculate_simple_lip_effective_width(
        **common,
        lip_overall_depth_mm=20.0 * SIMPLE_LIP_MAX_D_OVER_W,
    )

    assert accepted.d_over_w == pytest.approx(0.8)
    with pytest.raises(EWMCalculationError, match="greater than 0.8"):
        calculate_simple_lip_effective_width(
            **common,
            lip_overall_depth_mm=20.0 * (SIMPLE_LIP_MAX_D_OVER_W + 1.0e-9),
        )


def test_e2_inelastic_branch_matches_independent_value() -> None:
    result = calculate_global_column_strength(
        gross_area_mm2=180.0,
        yield_stress_mpa=345.0,
        f_cre_mpa=345.0,
    )

    assert result.branch is ColumnCurveBranch.INELASTIC
    assert result.lambda_c == pytest.approx(1.0)
    assert result.fn_mpa == pytest.approx(227.01)
    assert result.p_ne_n == pytest.approx(40_861.8)


def test_e2_elastic_branch_matches_independent_value() -> None:
    result = calculate_global_column_strength(
        gross_area_mm2=180.0,
        yield_stress_mpa=345.0,
        f_cre_mpa=100.0,
    )

    assert result.branch is ColumnCurveBranch.ELASTIC
    assert result.lambda_c == pytest.approx(sqrt(3.45))
    assert result.fn_mpa == pytest.approx(87.7)
    assert result.p_ne_n == pytest.approx(15_786.0)


def test_e2_transition_selects_verified_less_than_or_equal_branch() -> None:
    result = calculate_global_column_strength(
        gross_area_mm2=1.0,
        yield_stress_mpa=345.0,
        f_cre_mpa=345.0 / GLOBAL_SLENDERNESS_TRANSITION**2,
    )

    assert result.lambda_c == pytest.approx(1.5)
    assert result.branch is ColumnCurveBranch.INELASTIC


def test_e3_local_global_strength_respects_global_upper_limit() -> None:
    assert calculate_local_global_strength(
        effective_area_mm2=100.0, fn_mpa=50.0, p_ne_n=4_000.0
    ) == 4_000.0


def test_effective_area_is_element_by_element_and_has_unique_ids() -> None:
    web = _uniform_width(width=10.0, thickness=1.0, stress=10.0, k=4.0)
    flange = replace(web, element_id=PlateElementId.FLANGE_1)
    result = calculate_effective_area(
        elements=(web, flange), thickness_mm=2.0, gross_area_mm2=40.0
    )

    assert tuple(item.area_mm2 for item in result.contributions) == (20.0, 20.0)
    assert result.ae_mm2 == 40.0
    with pytest.raises(EWMCalculationError, match="identities must be unique"):
        calculate_effective_area(
            elements=(web, web), thickness_mm=1.0, gross_area_mm2=20.0
        )


def test_effective_area_tolerance_boundary_is_explicit() -> None:
    element = EffectiveWidthResult(
        element_id=PlateElementId.WEB,
        classification=PlateClassification.UNIFORMLY_COMPRESSED_STIFFENED,
        full_width_mm=10.0,
        effective_width_mm=10.0,
        plate_coefficient=4.0,
        f_crl_mpa=100.0,
        slenderness=0.5,
        reduction_factor=1.0,
    )
    allowed_area = 10.0 - 0.99 * EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2
    result = calculate_effective_area(
        elements=(element,), thickness_mm=1.0, gross_area_mm2=allowed_area
    )
    assert result.ae_mm2 == 10.0

    with pytest.raises(EWMCalculationError, match="exceeds M3 gross area"):
        calculate_effective_area(
            elements=(element,),
            thickness_mm=1.0,
            gross_area_mm2=10.0 - 1.01 * EFFECTIVE_AREA_ABSOLUTE_TOLERANCE_MM2,
        )


def test_effective_length_contract_keeps_global_lengths_independent() -> None:
    k_definition = MemberGeometry(
        l_mm=1000.0,
        length_definition=LengthDefinition.K_FACTORS,
        kx=1.0,
        ky=2.0,
        kt=3.0,
        lb_mm=77.0,
    )
    explicit_definition = MemberGeometry(
        l_mm=1000.0,
        length_definition=LengthDefinition.EFFECTIVE_LENGTHS,
        lx_mm=1100.0,
        ly_mm=1200.0,
        lt_mm=1300.0,
        lb_mm=88.0,
    )

    k_resolved = resolve_effective_lengths(k_definition)
    assert (k_resolved.lx_mm, k_resolved.ly_mm, k_resolved.lt_mm) == (
        1000.0,
        2000.0,
        3000.0,
    )
    resolved = resolve_effective_lengths(explicit_definition)
    assert (resolved.lx_mm, resolved.ly_mm, resolved.lt_mm) == (
        1100.0,
        1200.0,
        1300.0,
    )


def test_global_buckling_matches_independent_unlipped_benchmark(
    unlipped_design_input,
) -> None:
    result = calculate_global_buckling(
        unlipped_design_input.resolved_member.member.geometry,
        unlipped_design_input.section_mechanics,
    )

    assert result.ro_mm == pytest.approx(47.5541739676496)
    assert result.p_ex_n == pytest.approx(90_826.67943509166)
    assert result.p_ey_n == pytest.approx(9_118.286249169987)
    assert result.p_t_n == pytest.approx(9_185.06160997131)
    assert result.beta == pytest.approx(0.7659410885749315)
    assert result.p_flexural_torsional_n == pytest.approx(8_955.76335496274)
    assert result.governing_mode is GlobalBucklingMode.FLEXURAL_TORSIONAL


def test_global_y_mode_and_length_sensitivity(unlipped_design_input) -> None:
    original_geometry = unlipped_design_input.resolved_member.member.geometry
    y_long = replace(original_geometry, ky=4.0)
    base = calculate_global_buckling(
        original_geometry, unlipped_design_input.section_mechanics
    )
    changed = calculate_global_buckling(
        y_long, unlipped_design_input.section_mechanics
    )

    assert changed.governing_mode is GlobalBucklingMode.FLEXURAL_Y
    assert changed.p_ey_n == pytest.approx(base.p_ey_n / 16.0)
    assert changed.p_cre_n < base.p_cre_n


def test_global_x_and_torsional_length_sensitivity(unlipped_design_input) -> None:
    geometry = unlipped_design_input.resolved_member.member.geometry
    mechanics = unlipped_design_input.section_mechanics
    base = calculate_global_buckling(geometry, mechanics)
    x_long = calculate_global_buckling(replace(geometry, kx=2.0), mechanics)
    t_long = calculate_global_buckling(replace(geometry, kt=1.2), mechanics)

    assert x_long.p_ex_n == pytest.approx(base.p_ex_n / 4.0)
    assert x_long.p_cre_n < base.p_cre_n
    assert t_long.p_t_n < base.p_t_n
    assert t_long.p_cre_n < base.p_cre_n


def test_global_quadratic_repeated_root_remains_finite(
    unlipped_design_input,
) -> None:
    """Exercise the cancellation boundary protected by the named tolerance."""

    mechanics = unlipped_design_input.section_mechanics
    gross = mechanics.gross
    length = unlipped_design_input.resolved_member.member.geometry.l_mm
    e = 203_000.0
    g = 78_000.0
    ro_squared = (gross.ix_mm4 + gross.iy_mm4) / gross.a_mm2
    p_ex = pi**2 * e * gross.ix_mm4 / length**2
    matching_j = p_ex * ro_squared / g
    zero_offset_sectorial = replace(
        mechanics.advanced.sectorial,
        shear_center_offset_x_mm=0.0,
        shear_center_offset_y_mm=0.0,
        cw_mm6=0.0,
    )
    repeated_root_mechanics = replace(
        mechanics,
        gross=replace(gross, j_mm4=matching_j),
        advanced=replace(
            mechanics.advanced,
            sectorial=zero_offset_sectorial,
        ),
    )

    result = calculate_global_buckling(
        unlipped_design_input.resolved_member.member.geometry,
        repeated_root_mechanics,
    )

    assert result.beta == 1.0
    assert result.p_t_n == pytest.approx(result.p_ex_n)
    assert result.p_flexural_torsional_n == pytest.approx(result.p_ex_n)


def test_orthogonal_flange_lip_properties_match_table_benchmark() -> None:
    result = calculate_flange_lip_properties(
        flange_midline_width_mm=40.0,
        lip_midline_width_mm=10.0,
        thickness_mm=1.0,
    )

    assert result.af_mm2 == pytest.approx(50.0)
    assert result.jf_mm4 == pytest.approx(16.666666666666668)
    assert result.ixf_mm4 == pytest.approx(286.6666666666667)
    assert result.iyf_mm4 == pytest.approx(8_533.333333333334)
    assert result.ixyf_mm4 == pytest.approx(800.0)
    assert (result.xof_mm, result.xhf_mm, result.yof_mm, result.yhf_mm) == (
        16.0,
        -24.0,
        -1.0,
        -1.0,
    )


def test_appendix_2_distortional_equations_match_independent_benchmark() -> None:
    result = calculate_distortional_buckling(
        flange_midline_width_mm=40.0,
        lip_midline_width_mm=10.0,
        web_out_to_out_depth_mm=100.0,
        thickness_mm=1.0,
        gross_area_mm2=200.0,
        distortional_unbraced_length_mm=500.0,
    )

    assert result.l_crd_mm == pytest.approx(366.3457407637397)
    assert result.l_d_mm == pytest.approx(366.3457407637397)
    assert result.k_phi_fe_n == pytest.approx(467.39551282138063)
    assert result.k_phi_we_n == pytest.approx(371.7948717948718)
    assert result.k_phi_n == 0.0
    assert result.k_phi_fg_mm2 == pytest.approx(2.8494966065963805)
    assert result.k_phi_wg_mm2 == pytest.approx(1.2256492439296012)
    assert result.f_crd_mpa == pytest.approx(205.92892019016637)
    assert result.p_crd_n == pytest.approx(41_185.78403803327)


def test_e4_strength_and_slenderness_limit() -> None:
    buckling = calculate_distortional_buckling(
        flange_midline_width_mm=40.0,
        lip_midline_width_mm=10.0,
        web_out_to_out_depth_mm=100.0,
        thickness_mm=1.0,
        gross_area_mm2=200.0,
        distortional_unbraced_length_mm=500.0,
    )
    result = calculate_e4_strength(
        buckling=buckling,
        gross_area_mm2=200.0,
        yield_stress_mpa=345.0,
    )
    too_slender = replace(
        buckling,
        p_crd_n=result.p_y_n / (E4_MAX_DISTORTIONAL_SLENDERNESS + 0.01) ** 2,
    )

    assert result.lambda_d == pytest.approx(1.2943474618626338)
    assert result.p_nd_n == pytest.approx(42_278.89687223019)
    with pytest.raises(EWMCalculationError, match="not greater than 5"):
        calculate_e4_strength(
            buckling=too_slender,
            gross_area_mm2=200.0,
            yield_stress_mpa=345.0,
        )


def test_s100_elastic_constants_not_catalog_values() -> None:
    assert S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value == 203_000.0
    assert S100_24_ELASTIC_CONSTANTS.shear_modulus.value.value == 78_000.0
    assert S100_24_ELASTIC_CONSTANTS.poisson_ratio.value.value == 0.3
