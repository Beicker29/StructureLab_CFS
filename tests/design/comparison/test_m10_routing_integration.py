"""M10 routing and frozen M8B/M9A/M9B integration tests."""

from dataclasses import replace

import pytest

import cfs_design.workflows.axial_compression as workflow
from cfs_design.core.exceptions import ValidationError
from cfs_design.design.comparison import (
    ComparisonGoverningMethod,
    CompressionComparisonResult,
    CompressionComparisonStatus,
    MethodAvailability,
    MethodCompressionSummary,
    MethodDesignReadiness,
)
from cfs_design.design.dsm import M9AUnavailable
from cfs_design.domain import DesignMethod, RunMode, SectionFamily
from cfs_design.results import CalculationStatus
from cfs_design.stability import BucklingModeFamily, ClassificationStatus
from cfs_design.workflows import design_axial_compression


def test_ewm_mode_executes_only_ewm(monkeypatch, m10_request_factory) -> None:
    request = m10_request_factory(run_mode=RunMode.EWM)
    calls: list[str] = []
    original = workflow.calculate_ewm_compression_resistance

    def ewm(design_input):
        calls.append("EWM")
        return original(design_input)

    def forbidden_dsm(*args, **kwargs):
        raise AssertionError("DSM must not execute in EWM mode")

    monkeypatch.setattr(workflow, "calculate_ewm_compression_resistance", ewm)
    monkeypatch.setattr(workflow, "calculate_dsm_compression_resistance", forbidden_dsm)

    result = design_axial_compression(request)

    assert isinstance(result, MethodCompressionSummary)
    assert result.method is DesignMethod.EWM
    assert result.availability is MethodAvailability.METHOD_AVAILABLE
    assert calls == ["EWM"]


def test_dsm_mode_executes_only_dsm(monkeypatch, m10_request_factory) -> None:
    request = m10_request_factory(run_mode=RunMode.DSM)
    calls: list[str] = []
    original = workflow.calculate_dsm_compression_resistance

    def dsm(design_input, elastic):
        calls.append("DSM")
        return original(design_input, elastic)

    def forbidden_ewm(*args, **kwargs):
        raise AssertionError("EWM must not execute in DSM mode")

    monkeypatch.setattr(workflow, "calculate_dsm_compression_resistance", dsm)
    monkeypatch.setattr(workflow, "calculate_ewm_compression_resistance", forbidden_ewm)

    result = design_axial_compression(request)

    assert isinstance(result, MethodCompressionSummary)
    assert result.method is DesignMethod.DSM
    assert result.availability is MethodAvailability.METHOD_AVAILABLE
    assert calls == ["DSM"]


def test_compare_executes_both_once_with_same_physical_objects(
    monkeypatch,
    m10_request_factory,
) -> None:
    request = m10_request_factory(run_mode=RunMode.COMPARE)
    calls: list[tuple[str, object]] = []
    source_results: dict[str, object] = {}
    original_ewm = workflow.calculate_ewm_compression_resistance
    original_dsm = workflow.calculate_dsm_compression_resistance

    def ewm(design_input):
        calls.append(("EWM", design_input.resolved_member))
        source_results["EWM"] = original_ewm(design_input)
        return source_results["EWM"]

    def dsm(design_input, elastic):
        calls.append(("DSM", design_input.resolved_member))
        source_results["DSM"] = original_dsm(design_input, elastic)
        return source_results["DSM"]

    monkeypatch.setattr(workflow, "calculate_ewm_compression_resistance", ewm)
    monkeypatch.setattr(workflow, "calculate_dsm_compression_resistance", dsm)

    result = design_axial_compression(request)

    assert isinstance(result, CompressionComparisonResult)
    assert [item[0] for item in calls] == ["EWM", "DSM"]
    assert calls[0][1] is calls[1][1]
    assert request.ewm_input.resolved_member is request.dsm_input.resolved_member  # type: ignore[union-attr]
    assert request.ewm_input.section_mechanics is request.dsm_input.section_mechanics  # type: ignore[union-attr]
    assert result.ewm.demand_context is result.dsm.demand_context is request.demand
    assert result.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert result.ewm.nominal_resistance_n == source_results["EWM"].nominal_strength_n
    assert result.ewm.resistance_factor == source_results["EWM"].resistance_factor
    assert result.ewm.design_resistance_n == source_results["EWM"].design_strength_n
    assert result.dsm.nominal_resistance_n == source_results["DSM"].nominal_strength_n
    assert result.dsm.resistance_factor == source_results["DSM"].resistance_factor
    assert result.dsm.design_resistance_n == source_results["DSM"].design_strength_n


def test_compare_rejects_value_equal_but_duplicated_physical_member(
    m10_request_factory,
) -> None:
    request = m10_request_factory()
    cloned_member = replace(request.dsm_input.resolved_member)  # type: ignore[union-attr]
    cloned_input = replace(request.dsm_input, resolved_member=cloned_member)

    with pytest.raises(ValidationError, match="exact same resolved_member"):
        replace(request, dsm_input=cloned_input)


def test_dsm_engineering_review_creates_partial_comparison_without_fabrication(
    m10_request_factory,
) -> None:
    request = m10_request_factory(
        local_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
    )

    result = design_axial_compression(request)

    assert result.comparison_status is CompressionComparisonStatus.PARTIAL_COMPARISON
    assert result.ewm.availability is MethodAvailability.METHOD_AVAILABLE
    assert result.dsm.availability is MethodAvailability.METHOD_NOT_DESIGN_READY
    assert result.dsm.design_readiness is MethodDesignReadiness.ENGINEERING_REVIEW_REQUIRED
    assert result.dsm.design_resistance_n is None
    assert result.comparison_governing_method is None
    assert result.comparison_governing_capacity_n is None
    assert result.absolute_capacity_difference_n is None
    assert result.trace.status is CalculationStatus.COMPLETED_WITH_WARNINGS


def test_valid_engineering_selection_restores_complete_comparison_and_provenance(
    m10_request_factory,
) -> None:
    request = m10_request_factory(
        local_status=ClassificationStatus.ENGINEERING_REVIEW_REQUIRED,
        selection_family=BucklingModeFamily.LOCAL,
    )

    result = design_axial_compression(request)

    assert result.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert result.dsm.availability is MethodAvailability.METHOD_AVAILABLE
    assert result.dsm.warnings
    assert result.warnings
    assert result.dsm.source_trace_id is not None


def test_m9a_unsupported_state_is_partial_and_does_not_make_ewm_governing(
    m10_request_factory,
) -> None:
    request = m10_request_factory()
    unavailable = M9AUnavailable(
        case_id=request.demand.case_id,
        reason="Controlled unsupported topology.",
        provenance=("M9A_UNSUPPORTED_TOPOLOGY",),
    )

    result = design_axial_compression(
        replace(request, elastic_buckling=unavailable)
    )

    assert result.comparison_status is CompressionComparisonStatus.PARTIAL_COMPARISON
    assert result.dsm.availability is MethodAvailability.METHOD_UNSUPPORTED
    assert result.ewm.availability is MethodAvailability.METHOD_AVAILABLE
    assert result.comparison_governing_method is None


@pytest.mark.parametrize(
    ("family", "length_mm"),
    (
        (SectionFamily.C_LIPPED, 500.0),
        (SectionFamily.C_UNLIPPED, 500.0),
        (SectionFamily.C_LIPPED, 100.0),
        (SectionFamily.C_LIPPED, 2500.0),
    ),
)
def test_lipped_unlipped_short_and_global_sensitive_cases_integrate(
    m10_request_factory,
    family,
    length_mm,
) -> None:
    result = design_axial_compression(
        m10_request_factory(family=family, length_mm=length_mm)
    )

    assert result.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert result.ewm.availability is MethodAvailability.METHOD_AVAILABLE
    assert result.dsm.availability is MethodAvailability.METHOD_AVAILABLE
    assert result.ewm.source_trace_id
    assert result.dsm.source_trace_id
    assert result.trace.combination_id == "LC1"
    assert result.trace.demand_point_id == result.demand_context.point.point_id
    if family is SectionFamily.C_UNLIPPED:
        assert result.dsm.governing_limit_state == "LOCAL_GLOBAL_INTERACTION"


def test_local_and_distortional_controlled_dsm_inputs_remain_comparison_ready(
    m10_request_factory,
) -> None:
    local_sensitive = design_axial_compression(
        m10_request_factory(length_mm=100.0, p_crl_n=3_000.0, p_crd_n=1_000_000.0)
    )
    distortional_sensitive = design_axial_compression(
        m10_request_factory(length_mm=100.0, p_crl_n=1_000_000.0, p_crd_n=3_000.0)
    )

    assert local_sensitive.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert distortional_sensitive.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert local_sensitive.dsm.governing_limit_state == "LOCAL_GLOBAL_INTERACTION"
    assert distortional_sensitive.dsm.governing_limit_state == "DISTORTIONAL"


def test_reporting_rows_are_stored_summaries_not_recalculations(
    m10_request_factory,
) -> None:
    result = design_axial_compression(m10_request_factory())

    assert result.report_rows == (result.ewm, result.dsm)
    assert result.report_rows[0].design_resistance_n == result.ewm.design_resistance_n
    assert result.report_rows[1].design_resistance_n == result.dsm.design_resistance_n
    assert result.phi_pn_ewm_n == result.ewm.phi_pn_n
    assert result.phi_pn_dsm_n == result.dsm.phi_pn_n
    assert result.demand_case == "LC1"
    assert result.station_mm == 250.0
    assert result.comparison_is_informational
