"""Complete M8B capacity, trace, and blocked-state tests."""

from dataclasses import replace
from pathlib import Path

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.ewm import calculate_ewm_compression_resistance
from cfs_design.design.ewm.compression import (
    LRFD_COMPRESSION_RESISTANCE_FACTOR,
    SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4,
    SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM,
)
from cfs_design.design.ewm.interpretations import (
    InterpretationStatus,
    S10024_A1_1_3A_XREF_001,
)
from cfs_design.design.ewm.models import (
    GlobalBucklingMode,
    NominalLimitState,
    PlateClassification,
    PlateElementId,
)
from cfs_design.domain import SectionFamily
from cfs_design.results import ApplicabilityStatus, CalculationStatus
from cfs_design.workflows.project import resolve_project

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _metadata(trace) -> dict[str, object]:
    return {item.key: item.value for item in trace.metadata}


def test_complete_unlipped_benchmark(unlipped_design_input) -> None:
    """Expected values come from the independent M8B benchmark worksheet."""

    result = calculate_ewm_compression_resistance(unlipped_design_input)
    elements = {item.element_id: item for item in result.effective_width_elements}

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert result.applicability_status is ApplicabilityStatus.APPLICABLE
    assert result.global_buckling is not None
    assert result.global_buckling.p_cre_n == pytest.approx(8_955.76335496274)
    assert result.global_buckling.f_cre_mpa == pytest.approx(49.75424086090412)
    assert result.global_buckling.governing_mode is GlobalBucklingMode.FLEXURAL_TORSIONAL
    assert result.global_column_strength is not None
    assert result.global_column_strength.fn_mpa == pytest.approx(43.634469235012915)
    assert result.global_column_strength.p_ne_n == pytest.approx(7_854.204462302325)
    assert elements[PlateElementId.WEB].effective_width_mm == pytest.approx(
        92.68649686086418
    )
    assert elements[PlateElementId.FLANGE_1].effective_width_mm == pytest.approx(
        32.57693441121566
    )
    assert result.effective_area is not None
    assert result.effective_area.ae_mm2 == pytest.approx(157.8403656832955)
    assert tuple(item.nominal_strength_n for item in result.candidate_strengths) == pytest.approx(
        (7_854.204462302325, 6_887.280580450945)
    )
    assert result.governing_limit_state is NominalLimitState.E3_1_LOCAL_GLOBAL
    assert result.nominal_strength_n == pytest.approx(6_887.280580450945)
    assert result.resistance_factor == 0.85
    assert result.design_strength_n == pytest.approx(5_854.1884933833035)
    assert result.e4_result is None


def test_complete_lipped_benchmark_with_non_governing_e4(lipped_design_input) -> None:
    result = calculate_ewm_compression_resistance(lipped_design_input)
    elements = {item.element_id: item for item in result.effective_width_elements}

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert len(result.candidate_strengths) == 3
    assert elements[PlateElementId.FLANGE_1].classification is (
        PlateClassification.SIMPLE_LIP_EDGE_STIFFENED_FLANGE
    )
    assert elements[PlateElementId.LIP_1].classification is (
        PlateClassification.SIMPLE_LIP_STIFFENER
    )
    assert elements[PlateElementId.FLANGE_1].effective_width_mm == pytest.approx(40.0)
    assert elements[PlateElementId.LIP_1].effective_width_mm == pytest.approx(10.0)
    assert result.effective_area is not None
    assert result.effective_area.ae_mm2 == pytest.approx(187.0681803887524)
    assert result.e4_result is not None
    assert result.e4_result.buckling.p_crd_n == pytest.approx(41_185.78403803327)
    assert result.e4_result.p_nd_n == pytest.approx(42_278.89687223019)
    assert result.governing_limit_state is NominalLimitState.E3_1_LOCAL_GLOBAL
    assert result.nominal_strength_n == pytest.approx(9_964.282697205643)
    assert result.design_strength_n == pytest.approx(8_469.640292624796)


def test_independent_lipped_case_has_e4_governing(design_input_factory) -> None:
    design_input = design_input_factory(
        family=SectionFamily.C_LIPPED,
        web_mm=100.0,
        flange_1_mm=20.0,
        flange_2_mm=20.0,
        lip_1_mm=5.0,
        lip_2_mm=5.0,
        length_mm=100.0,
        distortional_length_mm=5000.0,
    )
    result = calculate_ewm_compression_resistance(design_input)

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert result.effective_area is not None
    assert result.effective_area.ae_mm2 == pytest.approx(90.39685564389536)
    assert result.e4_result is not None
    assert result.e4_result.buckling.l_crd_mm == pytest.approx(155.81728474124952)
    assert result.e4_result.buckling.f_crd_mpa == pytest.approx(115.25107310107303)
    assert result.e4_result.lambda_d == pytest.approx(1.7301631528398242)
    assert tuple(item.nominal_strength_n for item in result.candidate_strengths) == pytest.approx(
        (50_949.33831113632, 30_704.399869758516, 23_753.727336681128)
    )
    assert result.governing_limit_state is NominalLimitState.E4_DISTORTIONAL
    assert result.nominal_strength_n == pytest.approx(23_753.727336681128)
    assert result.design_strength_n == pytest.approx(20_190.668236178957)


def test_capacity_boundary_does_not_require_etabs(unlipped_design_input) -> None:
    assert unlipped_design_input.resolved_member.demands is None
    assert unlipped_design_input.resolved_member.source_demands is None

    result = calculate_ewm_compression_resistance(unlipped_design_input)

    assert result.calculation_status is CalculationStatus.COMPLETED


def test_design_uses_only_m3_mechanics_not_catalog_property_claims(
    unlipped_design_input,
) -> None:
    baseline = calculate_ewm_compression_resistance(unlipped_design_input)
    catalog_properties = replace(
        unlipped_design_input.resolved_member.section.properties,
        a_mm2=9_999.0,
        ix_mm4=8_888_888.0,
        iy_mm4=777_777.0,
        j_mm4=66_666.0,
    )
    section = replace(
        unlipped_design_input.resolved_member.section,
        properties=catalog_properties,
    )
    member = replace(unlipped_design_input.resolved_member, section=section)
    modified = replace(unlipped_design_input, resolved_member=member)

    result = calculate_ewm_compression_resistance(modified)

    assert result.nominal_strength_n == baseline.nominal_strength_n
    assert result.global_buckling == baseline.global_buckling


def test_mirrored_shear_center_sign_is_axially_invariant(unlipped_design_input) -> None:
    baseline = calculate_ewm_compression_resistance(unlipped_design_input)
    mechanics = unlipped_design_input.section_mechanics
    mirrored_sectorial = replace(
        mechanics.advanced.sectorial,
        shear_center_offset_x_mm=-mechanics.advanced.x0_mm,
    )
    mirrored_advanced = replace(mechanics.advanced, sectorial=mirrored_sectorial)
    mirrored = replace(
        unlipped_design_input,
        section_mechanics=replace(mechanics, advanced=mirrored_advanced),
    )

    result = calculate_ewm_compression_resistance(mirrored)

    assert result.global_buckling == baseline.global_buckling
    assert result.nominal_strength_n == baseline.nominal_strength_n


def test_symmetry_tolerance_boundary_is_deterministic(unlipped_design_input) -> None:
    mechanics = unlipped_design_input.section_mechanics
    below_advanced = replace(
        mechanics.advanced,
        sectorial=replace(
            mechanics.advanced.sectorial,
            shear_center_offset_y_mm=SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM,
        ),
    )
    above_advanced = replace(
        mechanics.advanced,
        sectorial=replace(
            mechanics.advanced.sectorial,
            shear_center_offset_y_mm=(
                SECTION_SYMMETRY_Y0_ABSOLUTE_TOLERANCE_MM * (1.0 + 1.0e-6)
            ),
        ),
    )
    below = replace(
        unlipped_design_input,
        section_mechanics=replace(mechanics, advanced=below_advanced),
    )
    above = replace(
        unlipped_design_input,
        section_mechanics=replace(mechanics, advanced=above_advanced),
    )

    assert calculate_ewm_compression_resistance(below).calculation_status is (
        CalculationStatus.COMPLETED
    )
    failed = calculate_ewm_compression_resistance(above)
    assert failed.calculation_status is CalculationStatus.FAILED
    assert failed.design_strength_n is None
    assert any(
        item.code == "EWM_GLOBAL_NONSYMMETRIC_UNSUPPORTED"
        for item in failed.diagnostics
    )

    below_ixy = replace(
        unlipped_design_input,
        section_mechanics=replace(
            mechanics,
            gross=replace(
                mechanics.gross,
                ixy_mm4=SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4,
            ),
        ),
    )
    above_ixy = replace(
        unlipped_design_input,
        section_mechanics=replace(
            mechanics,
            gross=replace(
                mechanics.gross,
                ixy_mm4=(
                    SECTION_SYMMETRY_I_XY_ABSOLUTE_TOLERANCE_MM4
                    * (1.0 + 1.0e-6)
                ),
            ),
        ),
    )
    assert calculate_ewm_compression_resistance(below_ixy).calculation_status is (
        CalculationStatus.COMPLETED
    )
    assert calculate_ewm_compression_resistance(above_ixy).calculation_status is (
        CalculationStatus.FAILED
    )


def test_yield_stress_propagates_through_verified_branches(
    design_input_factory,
) -> None:
    lower = calculate_ewm_compression_resistance(
        design_input_factory(fy_mpa=300.0)
    )
    higher = calculate_ewm_compression_resistance(
        design_input_factory(fy_mpa=345.0)
    )
    lower_short = calculate_ewm_compression_resistance(
        design_input_factory(fy_mpa=300.0, length_mm=500.0)
    )
    higher_short = calculate_ewm_compression_resistance(
        design_input_factory(fy_mpa=345.0, length_mm=500.0)
    )

    assert lower.global_buckling == higher.global_buckling
    assert lower.global_column_strength is not None
    assert higher.global_column_strength is not None
    assert lower.global_column_strength.lambda_c < higher.global_column_strength.lambda_c
    # In the elastic E2 branch, Fy cancels exactly from Eq. E2-3 after E2-4.
    assert lower.global_column_strength.fn_mpa == pytest.approx(
        higher.global_column_strength.fn_mpa
    )
    assert lower.nominal_strength_n == pytest.approx(higher.nominal_strength_n)
    assert lower_short.global_column_strength is not None
    assert higher_short.global_column_strength is not None
    assert lower_short.global_column_strength.fn_mpa < (
        higher_short.global_column_strength.fn_mpa
    )
    assert lower_short.nominal_strength_n < higher_short.nominal_strength_n  # type: ignore[operator]


def test_trace_contains_all_required_stages_and_exact_references(
    lipped_design_input,
) -> None:
    result = calculate_ewm_compression_resistance(lipped_design_input)
    names = {step.name for step in result.trace.steps}
    equations = {
        step.reference.equation_id
        for step in result.trace.steps
        if step.reference is not None and step.reference.equation_id is not None
    }

    assert {
        "Resolved eligibility",
        "Member geometry and restraints",
        "Coherent M3 design mechanics",
        "S100-24 elastic constants",
        "Resolved material strengths",
        "Global effective lengths",
        "Global elastic buckling loads",
        "E2 global column strength",
        "Explicit AISI dimensions",
        "Controlled no-hole cross-reference interpretation",
        "E3.1 effective area",
        "E3.1 local-global nominal strength",
        "Appendix 2 distortional flange properties",
        "Appendix 2 analytical distortional buckling",
        "E4 distortional nominal strength",
        "Nominal strength candidates",
        "Governing nominal strength",
        "LRFD design strength",
    } <= names
    assert "E2-1 through E2-4" in equations
    assert "E3.1-1" in equations
    assert "E4-1 through E4-3" in equations
    assert "2.3.3.1-1 through 2.3.3.1-7" in equations
    lip_step = next(step for step in result.trace.steps if step.name == "Effective width LIP_1")
    assert "1.3-6" in lip_step.reference.equation_id  # type: ignore[union-attr,operator]
    assert all(value.unit.value in {"N", "1"} for value in result.trace.final_values)


def test_controlled_interpretation_record_and_trace_are_explicit(
    lipped_design_input,
) -> None:
    interpretation = S10024_A1_1_3A_XREF_001
    result = calculate_ewm_compression_resistance(lipped_design_input)
    step = next(
        item
        for item in result.trace.steps
        if item.name == "Controlled no-hole cross-reference interpretation"
    )
    notes = step.reference.notes  # type: ignore[union-attr]

    assert interpretation.status is (
        InterpretationStatus.CONTROLLED_ENGINEERING_INTERPRETATION
    )
    assert "Section 1.1.1" in interpretation.published_reference
    assert "Section 1.1(a)" in interpretation.interpreted_reference
    assert "Section 1.1.4" in interpretation.corroborating_reference
    assert "no_holes" in interpretation.applicable_section_type.lower()
    assert "holes" in interpretation.restriction
    assert "official AISI correction" in interpretation.supersession_rule
    assert interpretation.technical_rationale in notes
    assert interpretation.corroborating_reference in notes
    assert _metadata(result.trace)["controlled_interpretation_id"] == (
        "S10024-A1-1_3A-XREF-001"
    )
    assert _metadata(result.trace)["holes_supported"] is False


@pytest.mark.parametrize(
    "factory_kwargs",
    [
        pytest.param(
            {"include_dimensions": False},
            id="missing-dimensions",
        ),
        pytest.param(
            {"include_qualification": False},
            id="missing-qualification",
        ),
        pytest.param(
            {"valid_scope": False},
            id="failed-normative-eligibility",
        ),
        pytest.param(
            {"flange_2_mm": 35.0},
            id="failed-software-support",
        ),
        pytest.param(
            {
                "family": SectionFamily.C_LIPPED,
                "include_distortional_length": False,
            },
            id="missing-lm",
        ),
        pytest.param(
            {
                "family": SectionFamily.C_LIPPED,
                "flange_2_mm": 35.0,
                "lip_2_mm": 8.0,
            },
            id="unequal-lipped-numerical-route",
        ),
    ],
)
def test_blocked_input_never_emits_resistance(
    factory_kwargs,
    design_input_factory,
) -> None:
    result = calculate_ewm_compression_resistance(
        design_input_factory(**factory_kwargs)
    )

    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.nominal_strength_n is None
    assert result.resistance_factor is None
    assert result.design_strength_n is None
    assert result.candidate_strengths == ()
    assert result.trace.final_values == ()


def test_failed_m3_gate_cannot_cross_design_input_boundary(
    design_input_factory,
) -> None:
    with pytest.raises(ValidationError, match="blocked by the QA gate"):
        design_input_factory(design_use_permitted=False)


def test_resistance_factor_is_applied_exactly_once(lipped_design_input) -> None:
    result = calculate_ewm_compression_resistance(lipped_design_input)

    assert result.design_strength_n == pytest.approx(
        result.nominal_strength_n * LRFD_COMPRESSION_RESISTANCE_FACTOR  # type: ignore[operator]
    )
    assert all(
        item.design_strength_n
        == pytest.approx(item.nominal_strength_n * item.resistance_factor)
        for item in result.candidate_strengths
    )


def test_current_production_project_has_no_executable_capacity_member() -> None:
    resolved = resolve_project(
        REPOSITORY_ROOT / "projects" / "PRJ_001" / "project.yaml",
        repository_root=REPOSITORY_ROOT,
    )

    assert resolved.active_resolved_members == ()
