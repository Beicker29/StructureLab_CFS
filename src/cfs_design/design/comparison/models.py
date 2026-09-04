"""Immutable M10 axial-compression comparison result models."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignFormat, DesignMethod, SectionDemandPoint
from cfs_design.normative import SoftwareSupportStatus
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationTrace,
    DesignCheckStatus,
    EngineeringDiagnostic,
    MetadataEntry,
)


class MethodAvailability(str, Enum):
    METHOD_AVAILABLE = "METHOD_AVAILABLE"
    METHOD_NOT_DESIGN_READY = "METHOD_NOT_DESIGN_READY"
    METHOD_NOT_APPLICABLE = "METHOD_NOT_APPLICABLE"
    METHOD_UNSUPPORTED = "METHOD_UNSUPPORTED"
    METHOD_INVALID_INPUT = "METHOD_INVALID_INPUT"


class MethodDesignReadiness(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class CompressionComparisonStatus(str, Enum):
    COMPLETE_COMPARISON = "COMPLETE_COMPARISON"
    PARTIAL_COMPARISON = "PARTIAL_COMPARISON"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class CompressionOverallStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class ComparisonGoverningMethod(str, Enum):
    EWM = "EWM"
    DSM = "DSM"
    EQUAL_CAPACITY = "EQUAL_CAPACITY"


def _non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def _optional_non_empty(value: str | None, name: str) -> None:
    if value is not None:
        _non_empty(value, name)


def _positive_finite(value: float | None, name: str) -> None:
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0.0
    ):
        raise ValidationError(f"{name} must be positive and finite")


@dataclass(frozen=True, slots=True)
class AxialDemandContext:
    """One resolved simultaneous force state; canonical ``p_n`` is compression-positive."""

    project_id: str
    case_id: str
    section_id: str
    material_id: str
    combination_id: str
    point: SectionDemandPoint
    case_type: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "project_id",
            "case_id",
            "section_id",
            "material_id",
            "combination_id",
        ):
            _non_empty(getattr(self, name), name)
        _optional_non_empty(self.case_type, "case_type")
        if not isinstance(self.point, SectionDemandPoint):
            raise ValidationError("point must be SectionDemandPoint")

    @property
    def signed_axial_demand_n(self) -> float:
        return self.point.p_n

    @property
    def is_compression(self) -> bool:
        return self.point.p_n > 0.0


@dataclass(frozen=True, slots=True)
class MethodCompressionSummary:
    method: DesignMethod
    demand_context: AxialDemandContext
    standard_id: str
    standard_edition: int
    design_format: DesignFormat
    availability: MethodAvailability
    design_readiness: MethodDesignReadiness
    normative_applicability: ApplicabilityStatus
    software_support: SoftwareSupportStatus
    source_calculation_status: CalculationStatus
    nominal_resistance_n: float | None
    resistance_factor: float | None
    design_resistance_n: float | None
    utilization: float | None
    check_status: DesignCheckStatus
    governing_limit_state: str | None
    source_trace: CalculationTrace | None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod")
        if not isinstance(self.demand_context, AxialDemandContext):
            raise ValidationError("demand_context must be AxialDemandContext")
        _non_empty(self.standard_id, "standard_id")
        if (
            isinstance(self.standard_edition, bool)
            or not isinstance(self.standard_edition, int)
            or self.standard_edition <= 0
        ):
            raise ValidationError("standard_edition must be a positive integer")
        for value, expected, name in (
            (self.design_format, DesignFormat, "design_format"),
            (self.availability, MethodAvailability, "availability"),
            (self.design_readiness, MethodDesignReadiness, "design_readiness"),
            (self.normative_applicability, ApplicabilityStatus, "normative_applicability"),
            (self.software_support, SoftwareSupportStatus, "software_support"),
            (self.source_calculation_status, CalculationStatus, "source_calculation_status"),
            (self.check_status, DesignCheckStatus, "check_status"),
        ):
            if not isinstance(value, expected):
                raise ValidationError(f"{name} must be {expected.__name__}")
        available = self.availability is MethodAvailability.METHOD_AVAILABLE
        numeric = (
            self.nominal_resistance_n,
            self.resistance_factor,
            self.design_resistance_n,
            self.utilization,
        )
        if available:
            for name, value in zip(
                ("nominal_resistance_n", "resistance_factor", "design_resistance_n", "utilization"),
                numeric,
            ):
                _positive_finite(value, name)
            if not self.demand_context.is_compression:
                raise ValidationError("available method requires positive compression demand")
            if self.check_status not in (DesignCheckStatus.PASS, DesignCheckStatus.FAIL):
                raise ValidationError("available method requires PASS or FAIL")
            if self.design_readiness is not MethodDesignReadiness.DESIGN_READY:
                raise ValidationError("available method must be DESIGN_READY")
            if self.normative_applicability is not ApplicabilityStatus.APPLICABLE:
                raise ValidationError("available method must be normatively applicable")
            if self.software_support is not SoftwareSupportStatus.SUPPORTED:
                raise ValidationError("available method must be software-supported")
            if self.source_trace is None or self.governing_limit_state is None:
                raise ValidationError("available method requires source trace and limit state")
        elif any(value is not None for value in numeric):
            raise ValidationError("unavailable method cannot claim resistance or utilization")
        elif self.check_status is not DesignCheckStatus.NOT_EVALUATED:
            raise ValidationError("unavailable method check must be NOT_EVALUATED")
        _optional_non_empty(self.governing_limit_state, "governing_limit_state")
        if self.source_trace is not None:
            if not isinstance(self.source_trace, CalculationTrace):
                raise ValidationError("source_trace must be CalculationTrace or None")
            if self.source_trace.method is not None and self.source_trace.method is not self.method:
                raise ValidationError("source trace method does not match summary method")
            if (
                self.source_trace.case_id is not None
                and self.source_trace.case_id != self.demand_context.case_id
            ):
                raise ValidationError("source trace member does not match summary demand")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, EngineeringDiagnostic) for item in self.diagnostics
        ):
            raise ValidationError("diagnostics must contain EngineeringDiagnostic")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.warnings
        ):
            raise ValidationError("warnings must contain non-empty strings")
        if not isinstance(self.provenance, tuple) or any(
            not isinstance(item, MetadataEntry) for item in self.provenance
        ):
            raise ValidationError("provenance must contain MetadataEntry")
        keys = tuple(item.key for item in self.provenance)
        if len(keys) != len(set(keys)):
            raise ValidationError("provenance keys must be unique")

    @property
    def demand_n(self) -> float:
        return self.demand_context.signed_axial_demand_n

    @property
    def source_trace_id(self) -> str | None:
        return self.source_trace.trace_id if self.source_trace is not None else None

    @property
    def phi(self) -> float | None:
        return self.resistance_factor

    @property
    def phi_pn_n(self) -> float | None:
        return self.design_resistance_n


@dataclass(frozen=True, slots=True)
class CompressionComparisonResult:
    demand_context: AxialDemandContext
    ewm: MethodCompressionSummary
    dsm: MethodCompressionSummary
    absolute_capacity_difference_n: float | None
    relative_capacity_difference_percent: float | None
    capacity_ratio_dsm_to_ewm: float | None
    utilization_difference: float | None
    comparison_governing_method: ComparisonGoverningMethod | None
    comparison_governing_capacity_n: float | None
    comparison_governing_utilization: float | None
    overall_status: CompressionOverallStatus
    comparison_status: CompressionComparisonStatus
    code_required_design_method: DesignMethod | None
    trace: CalculationTrace
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.demand_context, AxialDemandContext):
            raise ValidationError("demand_context must be AxialDemandContext")
        for summary, method in ((self.ewm, DesignMethod.EWM), (self.dsm, DesignMethod.DSM)):
            if not isinstance(summary, MethodCompressionSummary) or summary.method is not method:
                raise ValidationError(f"{method.value} summary is invalid")
            if summary.demand_context is not self.demand_context:
                raise ValidationError("method summaries must share one demand context object")
        if not isinstance(self.overall_status, CompressionOverallStatus):
            raise ValidationError("overall_status must be CompressionOverallStatus")
        if not isinstance(self.comparison_status, CompressionComparisonStatus):
            raise ValidationError("comparison_status must be CompressionComparisonStatus")
        if self.code_required_design_method is not None and not isinstance(
            self.code_required_design_method, DesignMethod
        ):
            raise ValidationError("code_required_design_method must be DesignMethod or None")
        if not isinstance(self.trace, CalculationTrace):
            raise ValidationError("trace must be CalculationTrace")
        metrics = (
            self.absolute_capacity_difference_n,
            self.relative_capacity_difference_percent,
            self.capacity_ratio_dsm_to_ewm,
            self.utilization_difference,
            self.comparison_governing_capacity_n,
            self.comparison_governing_utilization,
        )
        complete = self.comparison_status is CompressionComparisonStatus.COMPLETE_COMPARISON
        if complete:
            if any(value is None or not isfinite(value) for value in metrics):
                raise ValidationError("complete comparison requires finite metrics")
            if self.comparison_governing_method is None:
                raise ValidationError("complete comparison requires governing semantics")
            if any(
                summary.availability is not MethodAvailability.METHOD_AVAILABLE
                for summary in (self.ewm, self.dsm)
            ):
                raise ValidationError("complete comparison requires both methods")
            if self.comparison_governing_method is ComparisonGoverningMethod.EWM:
                if not self.ewm.design_resistance_n < self.dsm.design_resistance_n:  # type: ignore[operator]
                    raise ValidationError("EWM can govern only with lower capacity")
                expected_capacity = self.ewm.design_resistance_n
                expected_utilization = self.ewm.utilization
            elif self.comparison_governing_method is ComparisonGoverningMethod.DSM:
                if not self.dsm.design_resistance_n < self.ewm.design_resistance_n:  # type: ignore[operator]
                    raise ValidationError("DSM can govern only with lower capacity")
                expected_capacity = self.dsm.design_resistance_n
                expected_utilization = self.dsm.utilization
            else:
                if self.ewm.design_resistance_n != self.dsm.design_resistance_n:
                    raise ValidationError("EQUAL_CAPACITY requires exact equality")
                expected_capacity = self.ewm.design_resistance_n
                expected_utilization = self.ewm.utilization
            if (
                self.comparison_governing_capacity_n != expected_capacity
                or self.comparison_governing_utilization != expected_utilization
            ):
                raise ValidationError("governing values do not match governing method")
            expected_overall = (
                CompressionOverallStatus.PASS
                if self.ewm.check_status is DesignCheckStatus.PASS
                and self.dsm.check_status is DesignCheckStatus.PASS
                else CompressionOverallStatus.FAIL
            )
            if self.overall_status is not expected_overall:
                raise ValidationError("overall status does not match method checks")
        elif any(value is not None for value in metrics) or self.comparison_governing_method is not None:
            raise ValidationError("incomplete comparison cannot claim comparison metrics")
        if self.comparison_status is CompressionComparisonStatus.PARTIAL_COMPARISON:
            available_count = sum(
                item.availability is MethodAvailability.METHOD_AVAILABLE
                for item in (self.ewm, self.dsm)
            )
            if available_count != 1 or self.overall_status is not CompressionOverallStatus.PARTIAL:
                raise ValidationError("partial comparison requires exactly one available method")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, EngineeringDiagnostic) for item in self.diagnostics
        ):
            raise ValidationError("diagnostics must contain EngineeringDiagnostic")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.warnings
        ):
            raise ValidationError("warnings must contain non-empty strings")
        if not isinstance(self.provenance, tuple) or any(
            not isinstance(item, MetadataEntry) for item in self.provenance
        ):
            raise ValidationError("provenance must contain MetadataEntry")

    @property
    def member_id(self) -> str:
        return self.demand_context.case_id

    @property
    def demand_case(self) -> str:
        return self.demand_context.combination_id

    @property
    def station_mm(self) -> float | None:
        return self.demand_context.point.station_mm

    @property
    def demand_n(self) -> float:
        return self.demand_context.signed_axial_demand_n

    @property
    def phi_pn_ewm_n(self) -> float | None:
        return self.ewm.design_resistance_n

    @property
    def phi_pn_dsm_n(self) -> float | None:
        return self.dsm.design_resistance_n

    @property
    def comparison_is_informational(self) -> bool:
        return self.code_required_design_method is None

    @property
    def report_rows(self) -> tuple[MethodCompressionSummary, MethodCompressionSummary]:
        """Return presentation-ready stored summaries without recalculation."""

        return (self.ewm, self.dsm)


__all__ = [
    "AxialDemandContext",
    "ComparisonGoverningMethod",
    "CompressionComparisonResult",
    "CompressionComparisonStatus",
    "CompressionOverallStatus",
    "MethodAvailability",
    "MethodCompressionSummary",
    "MethodDesignReadiness",
]
