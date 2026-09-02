"""Future EWM/DSM comparison storage without comparison calculations."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import EngineeringUnit
from cfs_design.domain import DesignMethod
from cfs_design.domain._validation import require_non_empty

from .diagnostics import EngineeringDiagnostic, validate_diagnostics
from .enums import CalculationStatus
from .member import MethodDesignResult
from .values import EngineeringValue, MetadataEntry, validate_metadata


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Stored comparison values supplied by a future applicability-aware workflow."""

    case_id: str
    calculation_status: CalculationStatus
    ewm_result: MethodDesignResult | None = None
    dsm_result: MethodDesignResult | None = None
    strength_difference: EngineeringValue | None = None
    relative_difference: EngineeringValue | None = None
    lower_strength_method: DesignMethod | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        require_non_empty(self.case_id, "case_id")
        if not isinstance(self.calculation_status, CalculationStatus):
            raise ValidationError("calculation_status must be CalculationStatus")
        for field_name, result, expected_method in (
            ("ewm_result", self.ewm_result, DesignMethod.EWM),
            ("dsm_result", self.dsm_result, DesignMethod.DSM),
        ):
            if result is not None:
                if not isinstance(result, MethodDesignResult):
                    raise ValidationError(
                        f"{field_name} must be MethodDesignResult or None"
                    )
                if result.method is not expected_method:
                    raise ValidationError(
                        f"{field_name} must contain a {expected_method.value} result"
                    )
                if result.case_id != self.case_id:
                    raise ValidationError(
                        f"{field_name} case_id does not match comparison"
                    )
        if self.ewm_result is not None and self.dsm_result is not None:
            if (
                self.ewm_result.combination_id != self.dsm_result.combination_id
                or self.ewm_result.demand_point_id
                != self.dsm_result.demand_point_id
            ):
                raise ValidationError(
                    "EWM and DSM comparison results must identify the same "
                    "combination and demand point"
                )
        for field_name, value in (
            ("strength_difference", self.strength_difference),
            ("relative_difference", self.relative_difference),
        ):
            if value is not None and not isinstance(value, EngineeringValue):
                raise ValidationError(
                    f"{field_name} must be EngineeringValue or None"
                )
        if self.relative_difference is not None and (
            self.relative_difference.unit is not EngineeringUnit.DIMENSIONLESS
        ):
            raise ValidationError(
                "relative_difference must use the dimensionless unit '1'"
            )
        if self.lower_strength_method is not None:
            if not isinstance(self.lower_strength_method, DesignMethod):
                raise ValidationError(
                    "lower_strength_method must be DesignMethod or None"
                )
            selected = (
                self.ewm_result
                if self.lower_strength_method is DesignMethod.EWM
                else self.dsm_result
            )
            if selected is None:
                raise ValidationError(
                    "lower_strength_method requires its corresponding method result"
                )
        validate_diagnostics(self.diagnostics)
        validate_metadata(self.metadata)


__all__ = ["ComparisonResult"]
