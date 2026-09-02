"""Generic limit-state result records without design calculations."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import EngineeringUnit

from .diagnostics import EngineeringDiagnostic, validate_diagnostics
from .enums import ApplicabilityStatus, CalculationStatus, DesignCheckStatus
from .trace import CalculationTrace
from .values import (
    EngineeringValue,
    LimitStateId,
    MetadataEntry,
    validate_metadata,
)


@dataclass(frozen=True, slots=True)
class LimitStateResult:
    """Storage for values that a future design engine computes exactly once."""

    limit_state: LimitStateId
    calculation_status: CalculationStatus
    applicability_status: ApplicabilityStatus = ApplicabilityStatus.NOT_EVALUATED
    check_status: DesignCheckStatus = DesignCheckStatus.NOT_EVALUATED
    nominal_strength: EngineeringValue | None = None
    design_strength: EngineeringValue | None = None
    demand: EngineeringValue | None = None
    utilization: EngineeringValue | None = None
    trace: CalculationTrace | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.limit_state, LimitStateId):
            raise ValidationError("limit_state must be LimitStateId")
        if not isinstance(self.calculation_status, CalculationStatus):
            raise ValidationError("calculation_status must be CalculationStatus")
        if not isinstance(self.applicability_status, ApplicabilityStatus):
            raise ValidationError("applicability_status must be ApplicabilityStatus")
        if not isinstance(self.check_status, DesignCheckStatus):
            raise ValidationError("check_status must be DesignCheckStatus")
        named_values = (
            ("nominal_strength", self.nominal_strength),
            ("design_strength", self.design_strength),
            ("demand", self.demand),
            ("utilization", self.utilization),
        )
        for field_name, value in named_values:
            if value is not None and not isinstance(value, EngineeringValue):
                raise ValidationError(
                    f"{field_name} must be EngineeringValue or None"
                )
        strengths_and_demand = tuple(
            value
            for value in (
                self.nominal_strength,
                self.design_strength,
                self.demand,
            )
            if value is not None
        )
        if strengths_and_demand and len(
            {value.unit for value in strengths_and_demand}
        ) != 1:
            raise ValidationError(
                "nominal strength, design strength, and demand units must agree"
            )
        if self.utilization is not None and (
            self.utilization.unit is not EngineeringUnit.DIMENSIONLESS
        ):
            raise ValidationError("utilization must use the dimensionless unit '1'")
        if self.trace is not None:
            if not isinstance(self.trace, CalculationTrace):
                raise ValidationError("trace must be CalculationTrace or None")
            if (
                self.trace.limit_state is not None
                and self.trace.limit_state != self.limit_state
            ):
                raise ValidationError("trace limit_state does not match result")
        validate_diagnostics(self.diagnostics)
        validate_metadata(self.metadata)


__all__ = ["LimitStateResult"]
