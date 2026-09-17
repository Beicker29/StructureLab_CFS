"""M9B integration tests across shared M8B and frozen M9A boundaries."""

from dataclasses import fields, replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.dsm import (
    DSMDesignReadiness,
    DSMDistortionalBranch,
    DSMElasticInputBasis,
    DSMGoverningLimitState,
    M9AUnavailable,
    calculate_dsm_compression_resistance,
)
from cfs_design.design.global_compression import (
    calculate_global_buckling,
    calculate_global_column_strength,
)
from cfs_design.domain import DesignMethod, SectionFamily
from cfs_design.normative import SoftwareSupportStatus
from cfs_design.results import CalculationStatus
from cfs_design.stability import (
    BucklingModeFamily,
    ClassificationStatus,
    EngineeringSelection,
)


def test_automatic_local_and_distortional_results_are_design_ready(
    dsm_design_input,
    m9a_factory,
) -> None:
    m9a = m9a_factory(dsm_design_input)

    result = calculate_dsm_compression_resistance(dsm_design_input, m9a)

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert result.design_readiness is DSMDesignReadiness.DESIGN_READY
    assert result.software_support_status is SoftwareSupportStatus.SUPPORTED
    assert result.elastic_input_basis is DSMElasticInputBasis.AUTOMATIC
    assert result.p_crl_n == 100_000.0
    assert result.p_crd_n == 100_000.0
    assert result.nominal_strength_n is not None
    assert result.design_strength_n == pytest.approx(
        0.85 * result.nominal_strength_n
    )
    assert result.phi == 0.85
    assert result.phi_pn_n == result.design_strength_n


def test_pne_is_the_authoritative_shared_m8b_e2_result(
    dsm_design_input,
    m9a_factory,
) -> None:
    buckling = calculate_global_buckling(
        dsm_design_input.resolved_member.member.geometry,
        dsm_design_input.section_mechanics,
    )
    expected = calculate_global_column_strength(
        gross_area_mm2=dsm_design_input.section_mechanics.gross.a_mm2,
        yield_stress_mpa=dsm_design_input.resolved_member.material.fy_mpa,
        f_cre_mpa=buckling.f_cre_mpa,
    )

    result = calculate_dsm_compression_resistance(
        dsm_design_input,
        m9a_factory(dsm_design_input),
    )

    assert result.global_buckling == buckling
    assert result.global_column_strength == expected
    assert result.global_column_strength.p_ne_n == expected.p_ne_n


def test_local_review_required_blocks_all_dsm_strength(
    dsm_design_input,
    m9a_factory,
) -> None:
    m9a = m9a_factory(
        dsm_design_input,
        local_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, m9a)

    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.design_readiness is DSMDesignReadiness.ENGINEERING_REVIEW_REQUIRED
    assert result.nominal_strength_n is None
    assert result.p_crl_n is None
    assert any(
        diagnostic.code == "DSM_ENGINEERING_REVIEW_REQUIRED"
        for diagnostic in result.diagnostics
    )


def test_distortional_review_required_blocks_all_dsm_strength(
    dsm_design_input,
    m9a_factory,
) -> None:
    m9a = m9a_factory(
        dsm_design_input,
        distortional_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, m9a)

    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.design_readiness is DSMDesignReadiness.ENGINEERING_REVIEW_REQUIRED
    assert result.p_nd_n is None


def test_valid_engineering_selection_is_consumed_with_distinct_provenance(
    dsm_design_input,
    m9a_factory,
) -> None:
    m9a = m9a_factory(
        dsm_design_input,
        local_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
        selection_family=BucklingModeFamily.LOCAL,
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, m9a)

    assert result.calculation_status is CalculationStatus.COMPLETED_WITH_WARNINGS
    assert result.design_readiness is DSMDesignReadiness.DESIGN_READY
    assert result.elastic_input_basis is DSMElasticInputBasis.MIXED
    provenance = result.local_buckling_provenance
    assert provenance is not None
    assert provenance.input_basis is DSMElasticInputBasis.ENGINEERING_SELECTED
    assert provenance.engineer_confirmed
    assert provenance.confirmed_by == "ENG-TEST-001"
    assert provenance.selection_reason == "Controlled engineering selection fixture."
    assert provenance.selection_provenance == ("M9B_TEST_ENGINEERING_REVIEW",)
    assert result.warnings
    metadata = {item.key: item.value for item in result.trace.metadata}
    assert metadata["elastic_input_basis"] == result.elastic_input_basis.value
    assert metadata["normative_applicability"] == "APPLICABLE"
    assert metadata["software_support"] == "SUPPORTED"


def test_unconfirmed_selection_is_invalid_and_absence_blocks(
    dsm_design_input,
    m9a_factory,
) -> None:
    with pytest.raises(ValidationError, match="explicitly engineer-confirmed"):
        EngineeringSelection(
            family=BucklingModeFamily.LOCAL,
            half_wavelength_mm=100.0,
            critical_stress_mpa=100.0,
            critical_load_n=20_000.0,
            confirmed_by="ENG-TEST-001",
            reason="Unconfirmed test selection.",
            candidate_eigenvector_ids=("local-candidate",),
            engineer_confirmed=False,
            provenance=("INVALID_TEST",),
        )

    result = calculate_dsm_compression_resistance(
        dsm_design_input,
        m9a_factory(
            dsm_design_input,
            local_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
        ),
    )
    assert result.design_readiness is DSMDesignReadiness.ENGINEERING_REVIEW_REQUIRED


def test_explicit_m9a_unsupported_state_is_propagated(dsm_design_input) -> None:
    unavailable = M9AUnavailable(
        case_id=dsm_design_input.resolved_member.member.case_id,
        reason="Rank-deficient production/reference mesh comparison.",
        provenance=("M9A_MESH_RANK_DEFICIENT",),
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, unavailable)

    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.design_readiness is DSMDesignReadiness.UNSUPPORTED
    assert result.software_support_status is SoftwareSupportStatus.SUPPORTED
    diagnostic = next(
        item for item in result.diagnostics if item.code == "DSM_M9A_UNSUPPORTED"
    )
    assert "Rank-deficient" in diagnostic.message
    assert diagnostic.context[0].value == "M9A_MESH_RANK_DEFICIENT"


def test_multiple_automatic_candidates_for_one_family_are_not_chosen_arbitrarily(
    dsm_design_input,
    m9a_factory,
) -> None:
    m9a = m9a_factory(dsm_design_input)
    local = m9a.local_result
    assert local is not None
    ambiguous = replace(
        m9a,
        automatic_candidates=m9a.automatic_candidates + (local,),
        accepted_results=m9a.accepted_results + (local,),
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, ambiguous)

    assert result.design_readiness is DSMDesignReadiness.UNSUPPORTED
    assert result.nominal_strength_n is None
    assert any(
        "multiple automatically accepted LOCAL" in item.message
        for item in result.diagnostics
    )


def test_unlipped_c_does_not_apply_e4_or_consume_distortional_candidate(
    dsm_input_factory,
    m9a_factory,
) -> None:
    design_input = dsm_input_factory(family=SectionFamily.C_UNLIPPED)
    m9a = m9a_factory(
        design_input,
        distortional_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
    )

    result = calculate_dsm_compression_resistance(design_input, m9a)

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert result.distortional_branch is DSMDistortionalBranch.NOT_APPLICABLE
    assert result.p_crd_n is None
    assert result.p_nd_n is None
    assert result.governing_limit_state is (
        DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION
    )
    assert all(reference.clause != "E4" for reference in result.equation_references)


def test_distortional_can_govern_for_a_short_lipped_member(
    dsm_input_factory,
    m9a_factory,
) -> None:
    design_input = dsm_input_factory(length_mm=100.0)
    m9a = m9a_factory(
        design_input,
        p_crl_n=1_000_000.0,
        p_crd_n=3_000.0,
    )

    result = calculate_dsm_compression_resistance(design_input, m9a)

    assert result.calculation_status is CalculationStatus.COMPLETED
    assert result.p_nd_n < result.p_nl_n  # type: ignore[operator]
    assert result.governing_limit_state is DSMGoverningLimitState.DISTORTIONAL
    assert result.nominal_strength_n == result.p_nd_n


def test_m9a_case_mismatch_is_invalid_input(dsm_design_input, m9a_factory) -> None:
    m9a = m9a_factory(dsm_design_input)
    mismatched = M9AUnavailable(
        case_id="DIFFERENT_CASE",
        reason="Controlled mismatch.",
        provenance=("M9A_TEST",),
    )

    result = calculate_dsm_compression_resistance(dsm_design_input, mismatched)

    assert result.design_readiness is DSMDesignReadiness.INVALID_INPUT
    assert result.nominal_strength_n is None
    assert m9a.case_id != mismatched.case_id


def test_lambda_over_five_returns_unsupported_without_strength(
    dsm_design_input,
    m9a_factory,
) -> None:
    buckling = calculate_global_buckling(
        dsm_design_input.resolved_member.member.geometry,
        dsm_design_input.section_mechanics,
    )
    global_strength = calculate_global_column_strength(
        gross_area_mm2=dsm_design_input.section_mechanics.gross.a_mm2,
        yield_stress_mpa=dsm_design_input.resolved_member.material.fy_mpa,
        f_cre_mpa=buckling.f_cre_mpa,
    )
    p_crl = global_strength.p_ne_n / 25.01

    result = calculate_dsm_compression_resistance(
        dsm_design_input,
        m9a_factory(dsm_design_input, p_crl_n=p_crl),
    )

    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.design_readiness is DSMDesignReadiness.UNSUPPORTED
    assert result.nominal_strength_n is None


def test_trace_preserves_equations_sources_and_no_utilization(
    dsm_design_input,
    m9a_factory,
) -> None:
    result = calculate_dsm_compression_resistance(
        dsm_design_input,
        m9a_factory(dsm_design_input),
    )
    equations = {
        reference.equation_id for reference in result.equation_references
    }
    step_names = {step.name for step in result.trace.steps}

    assert "E2-1 through E2-4" in equations
    assert "E3.2-1 and E3.2-2" in equations
    assert "E4-1 through E4-3" in equations
    assert "2.1-1" in equations
    assert {
        "M8B global elastic buckling",
        "M8B E2 global column strength",
        "M9A local elastic buckling input",
        "E3.2 DSM local nominal strength",
        "M9A distortional elastic buckling input",
        "E4 DSM distortional nominal strength",
        "E1 governing nominal strength",
        "LRFD design resistance",
    } <= step_names
    assert "utilization" not in {item.name for item in fields(type(result))}
    assert result.local_buckling_provenance.solver_version == "0.2.0"  # type: ignore[union-attr]


def test_dsm_and_ewm_share_input_type_without_parallel_physical_models(
    dsm_design_input,
) -> None:
    assert dsm_design_input.method is DesignMethod.DSM
    assert type(dsm_design_input).__name__ == "MemberDesignInput"
    assert not hasattr(dsm_design_input, "dsm_section")
    assert not hasattr(dsm_design_input, "dsm_material")
