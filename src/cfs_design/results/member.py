"""Generic method- and member-level result aggregations."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import EngineeringUnit
from cfs_design.domain import DesignMethod
from cfs_design.domain._validation import require_non_empty

from .diagnostics import EngineeringDiagnostic, validate_diagnostics
from .enums import ApplicabilityStatus, CalculationStatus, DesignCheckStatus
from .limit_states import LimitStateResult
from .trace import CalculationTrace
from .values import (
    EngineeringValue,
    LimitStateId,
    MetadataEntry,
    validate_engineering_values,
    validate_metadata,
)


def _optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_empty(value, field_name)


@dataclass(frozen=True, slots=True)
class MethodDesignResult:
    """Results for one method and one simultaneous demand point."""

    method: DesignMethod
    case_id: str
    calculation_status: CalculationStatus
    limit_states: tuple[LimitStateResult, ...] = ()
    combination_id: str | None = None
    demand_point_id: str | None = None
    applicability_status: ApplicabilityStatus = ApplicabilityStatus.NOT_EVALUATED
    check_status: DesignCheckStatus = DesignCheckStatus.NOT_EVALUATED
    governing_limit_state: LimitStateId | None = None
    design_strengths: tuple[EngineeringValue, ...] = ()
    utilization: EngineeringValue | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod")
        require_non_empty(self.case_id, "case_id")
        _optional_non_empty(self.combination_id, "combination_id")
        _optional_non_empty(self.demand_point_id, "demand_point_id")
        if not isinstance(self.calculation_status, CalculationStatus):
            raise ValidationError("calculation_status must be CalculationStatus")
        if not isinstance(self.applicability_status, ApplicabilityStatus):
            raise ValidationError("applicability_status must be ApplicabilityStatus")
        if not isinstance(self.check_status, DesignCheckStatus):
            raise ValidationError("check_status must be DesignCheckStatus")
        if not isinstance(self.limit_states, tuple) or any(
            not isinstance(result, LimitStateResult) for result in self.limit_states
        ):
            raise ValidationError(
                "limit_states must be a tuple of LimitStateResult"
            )
        identifiers = tuple(result.limit_state.value for result in self.limit_states)
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError("limit-state IDs must be unique within a method result")
        if self.governing_limit_state is not None:
            if not isinstance(self.governing_limit_state, LimitStateId):
                raise ValidationError(
                    "governing_limit_state must be LimitStateId or None"
                )
            if self.governing_limit_state.value not in identifiers:
                raise ValidationError(
                    "governing_limit_state must identify a stored limit-state result"
                )
        validate_engineering_values(self.design_strengths, "design_strengths")
        if self.utilization is not None:
            if not isinstance(self.utilization, EngineeringValue):
                raise ValidationError("utilization must be EngineeringValue or None")
            if self.utilization.unit is not EngineeringUnit.DIMENSIONLESS:
                raise ValidationError("utilization must use the dimensionless unit '1'")
        for trace in self.traces:
            if trace.method is not None and trace.method is not self.method:
                raise ValidationError("trace method does not match method result")
            for field_name in (
                "case_id",
                "combination_id",
                "demand_point_id",
            ):
                trace_value = getattr(trace, field_name)
                result_value = getattr(self, field_name)
                if trace_value is not None and trace_value != result_value:
                    raise ValidationError(
                        f"trace {field_name} does not match method result"
                    )
        validate_diagnostics(self.diagnostics)
        validate_metadata(self.metadata)

    @property
    def traces(self) -> tuple[CalculationTrace, ...]:
        """Expose stored limit-state traces without duplicating trace records."""

        return tuple(
            result.trace for result in self.limit_states if result.trace is not None
        )


@dataclass(frozen=True, slots=True)
class MemberDesignResult:
    """All future method/demand-point results for one physical member."""

    case_id: str
    calculation_status: CalculationStatus
    method_results: tuple[MethodDesignResult, ...] = ()
    applicability_status: ApplicabilityStatus = ApplicabilityStatus.NOT_EVALUATED
    check_status: DesignCheckStatus = DesignCheckStatus.NOT_EVALUATED
    governing_result: MethodDesignResult | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        require_non_empty(self.case_id, "case_id")
        if not isinstance(self.calculation_status, CalculationStatus):
            raise ValidationError("calculation_status must be CalculationStatus")
        if not isinstance(self.applicability_status, ApplicabilityStatus):
            raise ValidationError("applicability_status must be ApplicabilityStatus")
        if not isinstance(self.check_status, DesignCheckStatus):
            raise ValidationError("check_status must be DesignCheckStatus")
        if not isinstance(self.method_results, tuple) or any(
            not isinstance(result, MethodDesignResult)
            for result in self.method_results
        ):
            raise ValidationError(
                "method_results must be a tuple of MethodDesignResult"
            )
        if any(result.case_id != self.case_id for result in self.method_results):
            raise ValidationError("method result case_id does not match member")
        identities = tuple(
            (
                result.method,
                result.combination_id,
                result.demand_point_id,
            )
            for result in self.method_results
        )
        if len(set(identities)) != len(identities):
            raise ValidationError(
                "method/demand-point identities must be unique within a member result"
            )
        if self.governing_result is not None:
            if not isinstance(self.governing_result, MethodDesignResult):
                raise ValidationError(
                    "governing_result must be MethodDesignResult or None"
                )
            if self.governing_result not in self.method_results:
                raise ValidationError(
                    "governing_result must be one of the stored method results"
                )
        validate_diagnostics(self.diagnostics)
        validate_metadata(self.metadata)


__all__ = ["MemberDesignResult", "MethodDesignResult"]
