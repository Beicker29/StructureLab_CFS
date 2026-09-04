"""M10 utilization, comparison metrics, and status tests."""

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.comparison import (
    ComparisonGoverningMethod,
    CompressionComparisonStatus,
    CompressionOverallStatus,
    MethodAvailability,
    MethodCompressionSummary,
    MethodDesignReadiness,
    calculate_axial_utilization,
    compare_compression_summaries,
)
from cfs_design.domain import DesignFormat, DesignMethod, RunMode
from cfs_design.normative import SoftwareSupportStatus
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DesignCheckStatus,
    EngineeringUnit,
    EngineeringValue,
    LimitStateId,
)
from cfs_design.workflows import design_axial_compression


@pytest.mark.parametrize(
    ("demand", "resistance", "expected", "status"),
    (
        (90.0, 100.0, 0.9, DesignCheckStatus.PASS),
        (100.0, 100.0, 1.0, DesignCheckStatus.PASS),
        (110.0, 100.0, 1.1, DesignCheckStatus.FAIL),
    ),
)
def test_utilization_uses_exact_one_limit(demand, resistance, expected, status) -> None:
    utilization, check = calculate_axial_utilization(
        compression_demand_n=demand,
        design_resistance_n=resistance,
    )

    assert utilization == pytest.approx(expected)
    assert check is status


@pytest.mark.parametrize("resistance", (0.0, -1.0, float("nan"), float("inf")))
def test_zero_or_invalid_resistance_is_blocked(resistance: float) -> None:
    with pytest.raises(ValidationError, match="design_resistance_n"):
        calculate_axial_utilization(
            compression_demand_n=10.0,
            design_resistance_n=resistance,
        )


@pytest.mark.parametrize("demand", (0.0, -1.0, float("nan"), float("inf")))
def test_nonpositive_or_invalid_compression_demand_is_blocked(demand: float) -> None:
    with pytest.raises(ValidationError, match="compression_demand_n"):
        calculate_axial_utilization(
            compression_demand_n=demand,
            design_resistance_n=10.0,
        )


def _available_summary(method, capacity, demand_context) -> MethodCompressionSummary:
    utilization, check = calculate_axial_utilization(
        compression_demand_n=demand_context.signed_axial_demand_n,
        design_resistance_n=capacity,
    )
    limit_state = LimitStateId(
        f"{method.value}_AXIAL", f"Controlled {method.value} test resistance"
    )
    trace_id = f"trace:case={demand_context.case_id}:method={method.value}:name=M10_TEST"
    value = EngineeringValue("design_resistance", capacity, EngineeringUnit.NEWTON)
    trace = CalculationTrace(
        trace_id=trace_id,
        status=CalculationStatus.COMPLETED,
        steps=(
            CalculationStep(
                step_id=f"{trace_id}:step=001",
                name="Controlled approved resistance",
                results=(value,),
            ),
        ),
        final_values=(value,),
        case_id=demand_context.case_id,
        method=method,
        limit_state=limit_state,
    )
    return MethodCompressionSummary(
        method=method,
        demand_context=demand_context,
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        design_format=DesignFormat.LRFD,
        availability=MethodAvailability.METHOD_AVAILABLE,
        design_readiness=MethodDesignReadiness.DESIGN_READY,
        normative_applicability=ApplicabilityStatus.APPLICABLE,
        software_support=SoftwareSupportStatus.SUPPORTED,
        source_calculation_status=CalculationStatus.COMPLETED,
        nominal_resistance_n=capacity / 0.85,
        resistance_factor=0.85,
        design_resistance_n=capacity,
        utilization=utilization,
        check_status=check,
        governing_limit_state=limit_state.value,
        source_trace=trace,
    )


@pytest.mark.parametrize(
    ("ewm_capacity", "dsm_capacity", "governing", "difference", "ratio"),
    (
        (80_000.0, 100_000.0, ComparisonGoverningMethod.EWM, 20_000.0, 1.25),
        (100_000.0, 80_000.0, ComparisonGoverningMethod.DSM, -20_000.0, 0.8),
        (90_000.0, 90_000.0, ComparisonGoverningMethod.EQUAL_CAPACITY, 0.0, 1.0),
    ),
)
def test_capacity_comparison_signs_and_equality_are_deterministic(
    m10_request_factory,
    ewm_capacity,
    dsm_capacity,
    governing,
    difference,
    ratio,
) -> None:
    demand = m10_request_factory(p_n=50_000.0).demand
    ewm = _available_summary(DesignMethod.EWM, ewm_capacity, demand)
    dsm = _available_summary(DesignMethod.DSM, dsm_capacity, demand)

    result = compare_compression_summaries(ewm=ewm, dsm=dsm)

    assert result.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
    assert result.comparison_governing_method is governing
    assert result.absolute_capacity_difference_n == difference
    assert result.capacity_ratio_dsm_to_ewm == ratio
    assert result.relative_capacity_difference_percent == pytest.approx(
        difference / ewm_capacity * 100.0
    )
    assert result.comparison_governing_capacity_n == min(ewm_capacity, dsm_capacity)
    assert result.comparison_is_informational
    assert result.code_required_design_method is None


def test_both_methods_pass_uses_the_same_compression_demand(m10_request_factory) -> None:
    demand = m10_request_factory(p_n=50_000.0).demand
    ewm = _available_summary(DesignMethod.EWM, 80_000.0, demand)
    dsm = _available_summary(DesignMethod.DSM, 100_000.0, demand)

    result = compare_compression_summaries(ewm=ewm, dsm=dsm)

    assert result.overall_status is CompressionOverallStatus.PASS
    assert result.ewm.demand_n == result.dsm.demand_n == 50_000.0
    assert result.ewm.utilization == pytest.approx(0.625)
    assert result.dsm.utilization == pytest.approx(0.5)


def test_one_method_pass_and_other_fail_sets_overall_fail(m10_request_factory) -> None:
    demand = m10_request_factory(p_n=90_000.0).demand
    ewm = _available_summary(DesignMethod.EWM, 100_000.0, demand)
    dsm = _available_summary(DesignMethod.DSM, 80_000.0, demand)

    result = compare_compression_summaries(ewm=ewm, dsm=dsm)

    assert result.ewm.check_status is DesignCheckStatus.PASS
    assert result.dsm.check_status is DesignCheckStatus.FAIL
    assert result.overall_status is CompressionOverallStatus.FAIL
    assert result.comparison_governing_method is ComparisonGoverningMethod.DSM


@pytest.mark.parametrize("p_n", (0.0, -10_000.0))
def test_noncompression_force_state_is_explicitly_not_applicable(
    m10_request_factory,
    p_n,
) -> None:
    request = m10_request_factory(run_mode=RunMode.COMPARE, p_n=p_n)

    result = design_axial_compression(request)

    assert result.comparison_status is CompressionComparisonStatus.NOT_APPLICABLE
    assert result.overall_status is CompressionOverallStatus.NOT_APPLICABLE
    assert result.ewm.availability is MethodAvailability.METHOD_NOT_APPLICABLE
    assert result.dsm.availability is MethodAvailability.METHOD_NOT_APPLICABLE
    assert result.ewm.utilization is result.dsm.utilization is None
    assert result.trace.status is CalculationStatus.NOT_RUN

