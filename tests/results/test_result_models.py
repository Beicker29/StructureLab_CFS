"""M6 limit-state, method, member, and comparison aggregation tests."""

from dataclasses import FrozenInstanceError

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignMethod
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    ComparisonResult,
    DesignCheckStatus,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EngineeringUnit,
    EngineeringValue,
    LimitStateId,
    LimitStateResult,
    MemberDesignResult,
    MetadataEntry,
    MethodDesignResult,
)


def _trace(
    *,
    method: DesignMethod = DesignMethod.EWM,
    case_id: str = "MEMBER_1",
    combination_id: str = "COMBO_1",
    point_id: str = "POINT_1",
    limit_state: LimitStateId | None = None,
) -> CalculationTrace:
    state = limit_state or LimitStateId("ILLUSTRATIVE_CHECK")
    stored = EngineeringValue("stored_result", 100.0, EngineeringUnit.NEWTON)
    return CalculationTrace(
        trace_id=f"TRACE-{method.value}-{point_id}",
        status=CalculationStatus.COMPLETED,
        case_id=case_id,
        combination_id=combination_id,
        demand_point_id=point_id,
        method=method,
        limit_state=state,
        steps=(CalculationStep("STEP-1", "Stored result", (stored,)),),
        final_values=(stored,),
    )


def _limit_result(
    *,
    method: DesignMethod = DesignMethod.EWM,
    case_id: str = "MEMBER_1",
    combination_id: str = "COMBO_1",
    point_id: str = "POINT_1",
    state_code: str = "ILLUSTRATIVE_CHECK",
) -> LimitStateResult:
    state = LimitStateId(state_code)
    return LimitStateResult(
        limit_state=state,
        calculation_status=CalculationStatus.COMPLETED,
        applicability_status=ApplicabilityStatus.APPLICABLE,
        check_status=DesignCheckStatus.PASS,
        nominal_strength=EngineeringValue(
            "nominal_strength", 125.0, EngineeringUnit.NEWTON
        ),
        design_strength=EngineeringValue(
            "design_strength", 100.0, EngineeringUnit.NEWTON
        ),
        demand=EngineeringValue("demand", 50.0, EngineeringUnit.NEWTON),
        utilization=EngineeringValue(
            "utilization", 0.5, EngineeringUnit.DIMENSIONLESS
        ),
        trace=_trace(
            method=method,
            case_id=case_id,
            combination_id=combination_id,
            point_id=point_id,
            limit_state=state,
        ),
    )


def _method_result(
    method: DesignMethod,
    *,
    point_id: str = "POINT_1",
) -> MethodDesignResult:
    limit_result = _limit_result(method=method, point_id=point_id)
    return MethodDesignResult(
        method=method,
        case_id="MEMBER_1",
        combination_id="COMBO_1",
        demand_point_id=point_id,
        calculation_status=CalculationStatus.COMPLETED,
        applicability_status=ApplicabilityStatus.APPLICABLE,
        check_status=DesignCheckStatus.PASS,
        limit_states=(limit_result,),
        design_strengths=(
            EngineeringValue("stored_strength", 100.0, EngineeringUnit.NEWTON),
        ),
        utilization=EngineeringValue(
            "method_utilization", 0.5, EngineeringUnit.DIMENSIONLESS
        ),
    )


def test_limit_state_result_allows_explicitly_absent_future_values() -> None:
    result = LimitStateResult(
        limit_state=LimitStateId("INFRASTRUCTURE_ONLY"),
        calculation_status=CalculationStatus.NOT_RUN,
        applicability_status=ApplicabilityStatus.NOT_EVALUATED,
    )
    assert result.nominal_strength is None
    assert result.design_strength is None
    assert result.demand is None
    assert result.utilization is None
    assert result.check_status is DesignCheckStatus.NOT_EVALUATED


def test_execution_applicability_and_design_check_statuses_are_separate() -> None:
    result = LimitStateResult(
        limit_state=LimitStateId("UNSUPPORTED_EXAMPLE"),
        calculation_status=CalculationStatus.NOT_RUN,
        applicability_status=ApplicabilityStatus.UNSUPPORTED,
        check_status=DesignCheckStatus.NOT_EVALUATED,
    )
    assert result.calculation_status is CalculationStatus.NOT_RUN
    assert result.applicability_status is ApplicabilityStatus.UNSUPPORTED
    assert result.check_status is DesignCheckStatus.NOT_EVALUATED


def test_limit_state_values_must_have_compatible_units() -> None:
    with pytest.raises(ValidationError, match="units must agree"):
        LimitStateResult(
            limit_state=LimitStateId("UNIT_MISMATCH"),
            calculation_status=CalculationStatus.COMPLETED,
            design_strength=EngineeringValue(
                "strength", 100.0, EngineeringUnit.NEWTON
            ),
            demand=EngineeringValue(
                "demand", 10.0, EngineeringUnit.NEWTON_MILLIMETRE
            ),
        )


def test_utilization_and_relative_difference_must_be_dimensionless() -> None:
    with pytest.raises(ValidationError, match="dimensionless"):
        LimitStateResult(
            limit_state=LimitStateId("BAD_UTILIZATION"),
            calculation_status=CalculationStatus.COMPLETED,
            utilization=EngineeringValue(
                "utilization", 0.5, EngineeringUnit.NEWTON
            ),
        )


def test_limit_state_trace_must_match_limit_state_identity() -> None:
    with pytest.raises(ValidationError, match="trace limit_state"):
        LimitStateResult(
            limit_state=LimitStateId("FIRST_STATE"),
            calculation_status=CalculationStatus.COMPLETED,
            trace=_trace(limit_state=LimitStateId("SECOND_STATE")),
        )


def test_method_result_aggregates_limit_states_and_exposes_their_traces() -> None:
    result = _method_result(DesignMethod.EWM)
    assert len(result.limit_states) == 1
    assert result.traces == (result.limit_states[0].trace,)
    assert result.governing_limit_state is None


def test_method_result_can_store_but_does_not_select_governing_limit_state() -> None:
    limit_result = _limit_result()
    result = MethodDesignResult(
        method=DesignMethod.EWM,
        case_id="MEMBER_1",
        combination_id="COMBO_1",
        demand_point_id="POINT_1",
        calculation_status=CalculationStatus.COMPLETED,
        limit_states=(limit_result,),
        governing_limit_state=limit_result.limit_state,
    )
    assert result.governing_limit_state is limit_result.limit_state

    with pytest.raises(ValidationError, match="stored limit-state"):
        MethodDesignResult(
            method=DesignMethod.EWM,
            case_id="MEMBER_1",
            calculation_status=CalculationStatus.COMPLETED,
            limit_states=(limit_result,),
            governing_limit_state=LimitStateId("NOT_STORED"),
        )


def test_method_result_rejects_trace_identity_mismatch() -> None:
    state = LimitStateId("ILLUSTRATIVE_CHECK")
    wrong_trace_result = LimitStateResult(
        limit_state=state,
        calculation_status=CalculationStatus.COMPLETED,
        trace=_trace(case_id="OTHER_MEMBER", limit_state=state),
    )
    with pytest.raises(ValidationError, match="trace case_id"):
        MethodDesignResult(
            method=DesignMethod.EWM,
            case_id="MEMBER_1",
            combination_id="COMBO_1",
            demand_point_id="POINT_1",
            calculation_status=CalculationStatus.COMPLETED,
            limit_states=(wrong_trace_result,),
        )


def test_member_result_holds_many_demand_points_without_ranking_them() -> None:
    first = _method_result(DesignMethod.EWM, point_id="POINT_1")
    second = _method_result(DesignMethod.EWM, point_id="POINT_2")
    member = MemberDesignResult(
        case_id="MEMBER_1",
        calculation_status=CalculationStatus.COMPLETED,
        method_results=(first, second),
    )
    assert tuple(result.demand_point_id for result in member.method_results) == (
        "POINT_1",
        "POINT_2",
    )
    assert member.governing_result is None


def test_member_governing_result_must_be_stored_but_is_never_calculated() -> None:
    stored = _method_result(DesignMethod.EWM)
    member = MemberDesignResult(
        case_id="MEMBER_1",
        calculation_status=CalculationStatus.COMPLETED,
        method_results=(stored,),
        governing_result=stored,
    )
    assert member.governing_result is stored

    with pytest.raises(ValidationError, match="one of the stored"):
        MemberDesignResult(
            case_id="MEMBER_1",
            calculation_status=CalculationStatus.COMPLETED,
            method_results=(stored,),
            governing_result=_method_result(DesignMethod.DSM),
        )


def test_member_result_rejects_duplicate_method_demand_identity() -> None:
    result = _method_result(DesignMethod.EWM)
    with pytest.raises(ValidationError, match="identities must be unique"):
        MemberDesignResult(
            case_id="MEMBER_1",
            calculation_status=CalculationStatus.COMPLETED,
            method_results=(result, result),
        )


def test_comparison_stores_precomputed_values_without_deriving_them() -> None:
    ewm = _method_result(DesignMethod.EWM)
    dsm = _method_result(DesignMethod.DSM)
    comparison = ComparisonResult(
        case_id="MEMBER_1",
        calculation_status=CalculationStatus.COMPLETED,
        ewm_result=ewm,
        dsm_result=dsm,
        strength_difference=EngineeringValue(
            "strength_difference", -7.25, EngineeringUnit.NEWTON
        ),
        relative_difference=EngineeringValue(
            "relative_difference", -0.0725, EngineeringUnit.DIMENSIONLESS
        ),
        lower_strength_method=DesignMethod.DSM,
        diagnostics=(
            EngineeringDiagnostic(
                DiagnosticSeverity.INFO,
                "PRECOMPUTED_COMPARISON",
                "Values were supplied; M6 performed no comparison calculation",
            ),
        ),
        metadata=(MetadataEntry("comparison_source", "future-workflow"),),
    )
    assert comparison.strength_difference is not None
    assert comparison.strength_difference.value == -7.25
    assert comparison.lower_strength_method is DesignMethod.DSM


def test_comparison_enforces_method_and_case_identity() -> None:
    with pytest.raises(ValidationError, match="must contain a EWM result"):
        ComparisonResult(
            case_id="MEMBER_1",
            calculation_status=CalculationStatus.COMPLETED,
            ewm_result=_method_result(DesignMethod.DSM),
        )


def test_comparison_requires_same_simultaneous_demand_identity() -> None:
    with pytest.raises(ValidationError, match="same combination and demand point"):
        ComparisonResult(
            case_id="MEMBER_1",
            calculation_status=CalculationStatus.COMPLETED,
            ewm_result=_method_result(DesignMethod.EWM, point_id="POINT_1"),
            dsm_result=_method_result(DesignMethod.DSM, point_id="POINT_2"),
        )


def test_comparison_does_not_infer_lower_method() -> None:
    comparison = ComparisonResult(
        case_id="MEMBER_1",
        calculation_status=CalculationStatus.NOT_RUN,
        ewm_result=_method_result(DesignMethod.EWM),
        dsm_result=_method_result(DesignMethod.DSM),
    )
    assert comparison.lower_strength_method is None
    assert comparison.strength_difference is None


def test_result_aggregates_are_frozen() -> None:
    method = _method_result(DesignMethod.EWM)
    member = MemberDesignResult(
        case_id="MEMBER_1",
        calculation_status=CalculationStatus.COMPLETED,
        method_results=(method,),
    )
    with pytest.raises(FrozenInstanceError):
        member.case_id = "changed"  # type: ignore[misc]
