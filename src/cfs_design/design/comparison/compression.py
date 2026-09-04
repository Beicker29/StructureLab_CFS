"""M10 utilization and comparison of approved compression resistance results."""

from math import isfinite

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.dsm import DSMCompressionResistance, DSMDesignReadiness
from cfs_design.design.ewm import EWMCompressionResistance
from cfs_design.design.inputs import MemberDesignInput
from cfs_design.domain import DesignFormat, DesignMethod
from cfs_design.normative import SoftwareSupportStatus
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DesignCheckStatus,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EngineeringUnit,
    EngineeringValue,
    LimitStateId,
    MetadataEntry,
    ReferenceSourceType,
    EquationReference,
    make_step_id,
    make_trace_id,
)

from .models import (
    AxialDemandContext,
    ComparisonGoverningMethod,
    CompressionComparisonResult,
    CompressionComparisonStatus,
    CompressionOverallStatus,
    MethodAvailability,
    MethodCompressionSummary,
    MethodDesignReadiness,
)


_COMPARISON_LIMIT_STATE = LimitStateId(
    "AXIAL_COMPRESSION_COMPARISON",
    "Informational EWM and DSM axial-compression comparison",
)
_COMPARISON_REFERENCE = EquationReference(
    source_type=ReferenceSourceType.OTHER,
    title="StructureLab M10 informational comparison definitions",
    notes="This comparison does not select a code-required design method.",
)


def _diagnostic(
    code: str,
    message: str,
    *,
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
) -> EngineeringDiagnostic:
    return EngineeringDiagnostic(severity=severity, code=code, message=message)


def calculate_axial_utilization(
    *, compression_demand_n: float, design_resistance_n: float
) -> tuple[float, DesignCheckStatus]:
    """Evaluate positive compression demand with the exact ``UR <= 1`` limit."""

    for name, value in (
        ("compression_demand_n", compression_demand_n),
        ("design_resistance_n", design_resistance_n),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0.0
        ):
            raise ValidationError(f"{name} must be positive and finite")
    utilization = compression_demand_n / design_resistance_n
    if not isfinite(utilization) or utilization <= 0.0:
        raise ValidationError("axial utilization must be positive and finite")
    status = (
        DesignCheckStatus.PASS
        if utilization <= 1.0
        else DesignCheckStatus.FAIL
    )
    return utilization, status


def _provenance(
    design_input: MemberDesignInput,
    source_trace: CalculationTrace | None,
) -> tuple[MetadataEntry, ...]:
    member = design_input.resolved_member
    return (
        MetadataEntry("case_id", member.member.case_id),
        MetadataEntry("section_id", member.section.catalog_section.section_id),
        MetadataEntry("material_id", member.material.material_id),
        MetadataEntry(
            "source_resistance_trace_id",
            source_trace.trace_id if source_trace is not None else None,
        ),
    )


def _unavailable_summary(
    *,
    method: DesignMethod,
    design_input: MemberDesignInput,
    demand: AxialDemandContext,
    availability: MethodAvailability,
    readiness: MethodDesignReadiness,
    normative: ApplicabilityStatus,
    software: SoftwareSupportStatus,
    calculation_status: CalculationStatus,
    diagnostics: tuple[EngineeringDiagnostic, ...],
    source_trace: CalculationTrace | None = None,
    warnings: tuple[str, ...] = (),
) -> MethodCompressionSummary:
    context = design_input.design_context
    if design_input.method is not method:
        raise ValidationError("method summary input does not match requested method")
    return MethodCompressionSummary(
        method=method,
        demand_context=demand,
        standard_id=context.standard_id,
        standard_edition=context.standard_edition,
        design_format=context.design_format,
        availability=availability,
        design_readiness=readiness,
        normative_applicability=normative,
        software_support=software,
        source_calculation_status=calculation_status,
        nominal_resistance_n=None,
        resistance_factor=None,
        design_resistance_n=None,
        utilization=None,
        check_status=DesignCheckStatus.NOT_EVALUATED,
        governing_limit_state=None,
        source_trace=source_trace,
        diagnostics=diagnostics,
        warnings=warnings,
        provenance=_provenance(design_input, source_trace),
    )


def noncompression_summary(
    *,
    method: DesignMethod,
    design_input: MemberDesignInput,
    demand: AxialDemandContext,
) -> MethodCompressionSummary:
    """Return an explicit non-applicable method state without running an engine."""

    return _unavailable_summary(
        method=method,
        design_input=design_input,
        demand=demand,
        availability=MethodAvailability.METHOD_NOT_APPLICABLE,
        readiness=MethodDesignReadiness.NOT_APPLICABLE,
        normative=design_input.eligibility.normative.status,
        software=design_input.eligibility.software.status,
        calculation_status=CalculationStatus.NOT_RUN,
        diagnostics=(
            _diagnostic(
                "M10_DEMAND_NOT_COMPRESSION",
                "Canonical axial demand is not positive compression; capacity and utilization were not evaluated.",
                severity=DiagnosticSeverity.INFO,
            ),
        ),
    )


def summarize_ewm_compression(
    *,
    design_input: MemberDesignInput,
    demand: AxialDemandContext,
    resistance: EWMCompressionResistance,
) -> MethodCompressionSummary:
    """Copy approved M8B resistance outputs and add only M10 utilization."""

    if design_input.method is not DesignMethod.EWM:
        raise ValidationError("EWM summary requires an EWM MemberDesignInput")
    if resistance.case_id != demand.case_id:
        raise ValidationError("EWM result does not match demand member")
    completed = resistance.calculation_status in (
        CalculationStatus.COMPLETED,
        CalculationStatus.COMPLETED_WITH_WARNINGS,
    )
    if completed:
        utilization, check = calculate_axial_utilization(
            compression_demand_n=demand.signed_axial_demand_n,
            design_resistance_n=resistance.design_strength_n,  # type: ignore[arg-type]
        )
        return MethodCompressionSummary(
            method=DesignMethod.EWM,
            demand_context=demand,
            standard_id=design_input.design_context.standard_id,
            standard_edition=design_input.design_context.standard_edition,
            design_format=design_input.design_context.design_format,
            availability=MethodAvailability.METHOD_AVAILABLE,
            design_readiness=MethodDesignReadiness.DESIGN_READY,
            normative_applicability=resistance.applicability_status,
            software_support=design_input.eligibility.software.status,
            source_calculation_status=resistance.calculation_status,
            nominal_resistance_n=resistance.nominal_strength_n,
            resistance_factor=resistance.resistance_factor,
            design_resistance_n=resistance.design_strength_n,
            utilization=utilization,
            check_status=check,
            governing_limit_state=resistance.governing_limit_state.value,  # type: ignore[union-attr]
            source_trace=resistance.trace,
            diagnostics=resistance.diagnostics,
            provenance=_provenance(design_input, resistance.trace),
        )
    normative = resistance.applicability_status
    software = design_input.eligibility.software.status
    if normative is ApplicabilityStatus.NOT_APPLICABLE:
        availability = MethodAvailability.METHOD_NOT_APPLICABLE
        readiness = MethodDesignReadiness.NOT_APPLICABLE
    elif normative is ApplicabilityStatus.INVALID_INPUT or software is SoftwareSupportStatus.INVALID_INPUT or resistance.calculation_status is CalculationStatus.FAILED:
        availability = MethodAvailability.METHOD_INVALID_INPUT
        readiness = MethodDesignReadiness.INVALID_INPUT
    else:
        availability = MethodAvailability.METHOD_UNSUPPORTED
        readiness = MethodDesignReadiness.UNSUPPORTED
    return _unavailable_summary(
        method=DesignMethod.EWM,
        design_input=design_input,
        demand=demand,
        availability=availability,
        readiness=readiness,
        normative=normative,
        software=software,
        calculation_status=resistance.calculation_status,
        diagnostics=resistance.diagnostics,
        source_trace=resistance.trace,
    )


def summarize_dsm_compression(
    *,
    design_input: MemberDesignInput,
    demand: AxialDemandContext,
    resistance: DSMCompressionResistance,
) -> MethodCompressionSummary:
    """Copy approved M9B resistance outputs and preserve design-readiness states."""

    if design_input.method is not DesignMethod.DSM:
        raise ValidationError("DSM summary requires a DSM MemberDesignInput")
    if resistance.case_id != demand.case_id:
        raise ValidationError("DSM result does not match demand member")
    if resistance.design_readiness is DSMDesignReadiness.DESIGN_READY:
        utilization, check = calculate_axial_utilization(
            compression_demand_n=demand.signed_axial_demand_n,
            design_resistance_n=resistance.design_strength_n,  # type: ignore[arg-type]
        )
        return MethodCompressionSummary(
            method=DesignMethod.DSM,
            demand_context=demand,
            standard_id=resistance.standard_id,
            standard_edition=resistance.standard_edition,
            design_format=resistance.design_format,
            availability=MethodAvailability.METHOD_AVAILABLE,
            design_readiness=MethodDesignReadiness.DESIGN_READY,
            normative_applicability=resistance.applicability_status,
            software_support=resistance.software_support_status,
            source_calculation_status=resistance.calculation_status,
            nominal_resistance_n=resistance.nominal_strength_n,
            resistance_factor=resistance.resistance_factor,
            design_resistance_n=resistance.design_strength_n,
            utilization=utilization,
            check_status=check,
            governing_limit_state=resistance.governing_limit_state.value,  # type: ignore[union-attr]
            source_trace=resistance.trace,
            diagnostics=resistance.diagnostics,
            warnings=resistance.warnings,
            provenance=_provenance(design_input, resistance.trace),
        )
    mapping = {
        DSMDesignReadiness.ENGINEERING_REVIEW_REQUIRED: (
            MethodAvailability.METHOD_NOT_DESIGN_READY,
            MethodDesignReadiness.ENGINEERING_REVIEW_REQUIRED,
        ),
        DSMDesignReadiness.UNSUPPORTED: (
            MethodAvailability.METHOD_UNSUPPORTED,
            MethodDesignReadiness.UNSUPPORTED,
        ),
        DSMDesignReadiness.INVALID_INPUT: (
            MethodAvailability.METHOD_INVALID_INPUT,
            MethodDesignReadiness.INVALID_INPUT,
        ),
    }
    availability, readiness = mapping[resistance.design_readiness]
    return _unavailable_summary(
        method=DesignMethod.DSM,
        design_input=design_input,
        demand=demand,
        availability=availability,
        readiness=readiness,
        normative=resistance.applicability_status,
        software=resistance.software_support_status,
        calculation_status=resistance.calculation_status,
        diagnostics=resistance.diagnostics,
        source_trace=resistance.trace,
        warnings=resistance.warnings,
    )


def _comparison_trace(
    *,
    demand: AxialDemandContext,
    ewm: MethodCompressionSummary,
    dsm: MethodCompressionSummary,
    status: CompressionComparisonStatus,
    metrics: tuple[float, float, float, float, float, float] | None,
    diagnostics: tuple[EngineeringDiagnostic, ...],
    warnings: tuple[str, ...],
) -> CalculationTrace:
    trace_id = make_trace_id(
        project_id=demand.project_id,
        case_id=demand.case_id,
        combination_id=demand.combination_id,
        demand_point_id=demand.point.point_id,
        limit_state=_COMPARISON_LIMIT_STATE,
    )
    metadata = (
        MetadataEntry("section_id", demand.section_id),
        MetadataEntry("material_id", demand.material_id),
        MetadataEntry("source_point_id", demand.point.source_point_id),
        MetadataEntry("ewm_trace_id", ewm.source_trace_id),
        MetadataEntry("dsm_trace_id", dsm.source_trace_id),
        MetadataEntry("comparison_status", status.value),
        MetadataEntry("code_required_design_method", None),
    )
    if metrics is None:
        available = tuple(
            item
            for item in (ewm, dsm)
            if item.availability is MethodAvailability.METHOD_AVAILABLE
        )
        if not available:
            return CalculationTrace(
                trace_id=trace_id,
                status=CalculationStatus.NOT_RUN,
                project_id=demand.project_id,
                case_id=demand.case_id,
                combination_id=demand.combination_id,
                demand_point_id=demand.point.point_id,
                limit_state=_COMPARISON_LIMIT_STATE,
                diagnostics=diagnostics,
                metadata=metadata,
            )
        item = available[0]
        step = CalculationStep(
            step_id=make_step_id(trace_id, 1),
            name="Preserved available method in partial comparison",
            results=(
                EngineeringValue("available_design_resistance", item.design_resistance_n, EngineeringUnit.NEWTON),  # type: ignore[arg-type]
                EngineeringValue("available_utilization", item.utilization, EngineeringUnit.DIMENSIONLESS),  # type: ignore[arg-type]
            ),
            reference=_COMPARISON_REFERENCE,
            description=f"{item.method.value} remains available; no governing comparison is asserted.",
        )
        return CalculationTrace(
            trace_id=trace_id,
            status=CalculationStatus.COMPLETED_WITH_WARNINGS,
            steps=(step,),
            final_values=step.results,
            project_id=demand.project_id,
            case_id=demand.case_id,
            combination_id=demand.combination_id,
            demand_point_id=demand.point.point_id,
            limit_state=_COMPARISON_LIMIT_STATE,
            diagnostics=diagnostics,
            metadata=metadata,
        )
    absolute, relative, ratio, utilization_difference, governing_capacity, governing_utilization = metrics
    first = CalculationStep(
        step_id=make_step_id(trace_id, 1),
        name="Approved method design resistances and common demand",
        results=(
            EngineeringValue("ewm_design_resistance", ewm.design_resistance_n, EngineeringUnit.NEWTON),  # type: ignore[arg-type]
            EngineeringValue("dsm_design_resistance", dsm.design_resistance_n, EngineeringUnit.NEWTON),  # type: ignore[arg-type]
            EngineeringValue("compression_demand", demand.signed_axial_demand_n, EngineeringUnit.NEWTON),
            EngineeringValue("ewm_utilization", ewm.utilization, EngineeringUnit.DIMENSIONLESS),  # type: ignore[arg-type]
            EngineeringValue("dsm_utilization", dsm.utilization, EngineeringUnit.DIMENSIONLESS),  # type: ignore[arg-type]
        ),
        reference=_COMPARISON_REFERENCE,
        description="Resistance values are copied from M8B and M9B; phi is not reapplied.",
    )
    second = CalculationStep(
        step_id=make_step_id(trace_id, 2),
        name="Informational EWM versus DSM metrics",
        inputs=first.results,
        results=(
            EngineeringValue("absolute_capacity_difference", absolute, EngineeringUnit.NEWTON),
            EngineeringValue(
                "relative_capacity_difference_percent",
                relative,
                EngineeringUnit.DIMENSIONLESS,
                description="Numerical percentage value; 100 means one hundred percent.",
            ),
            EngineeringValue("capacity_ratio_dsm_to_ewm", ratio, EngineeringUnit.DIMENSIONLESS),
            EngineeringValue("utilization_difference", utilization_difference, EngineeringUnit.DIMENSIONLESS),
            EngineeringValue("comparison_governing_capacity", governing_capacity, EngineeringUnit.NEWTON),
            EngineeringValue("comparison_governing_utilization", governing_utilization, EngineeringUnit.DIMENSIONLESS),
        ),
        reference=_COMPARISON_REFERENCE,
        description="Positive capacity difference means DSM capacity is larger than EWM capacity.",
    )
    return CalculationTrace(
        trace_id=trace_id,
        status=(
            CalculationStatus.COMPLETED_WITH_WARNINGS
            if warnings
            else CalculationStatus.COMPLETED
        ),
        steps=(first, second),
        final_values=second.results,
        project_id=demand.project_id,
        case_id=demand.case_id,
        combination_id=demand.combination_id,
        demand_point_id=demand.point.point_id,
        limit_state=_COMPARISON_LIMIT_STATE,
        diagnostics=diagnostics,
        metadata=metadata,
    )


def compare_compression_summaries(
    *,
    ewm: MethodCompressionSummary,
    dsm: MethodCompressionSummary,
) -> CompressionComparisonResult:
    """Compare stored EWM/DSM capacities without modifying either method result."""

    if ewm.method is not DesignMethod.EWM or dsm.method is not DesignMethod.DSM:
        raise ValidationError("comparison requires EWM and DSM summaries")
    if ewm.demand_context is not dsm.demand_context:
        raise ValidationError("comparison methods must use the same demand context object")
    if (
        ewm.standard_id != dsm.standard_id
        or ewm.standard_edition != dsm.standard_edition
        or ewm.design_format is not dsm.design_format
    ):
        raise ValidationError("comparison methods must share standard and design format")
    demand = ewm.demand_context
    ewm_available = ewm.availability is MethodAvailability.METHOD_AVAILABLE
    dsm_available = dsm.availability is MethodAvailability.METHOD_AVAILABLE
    warnings = ewm.warnings + dsm.warnings
    diagnostics = ewm.diagnostics + dsm.diagnostics
    if ewm_available and dsm_available:
        absolute = dsm.design_resistance_n - ewm.design_resistance_n  # type: ignore[operator]
        relative = absolute / ewm.design_resistance_n * 100.0  # type: ignore[operator]
        ratio = dsm.design_resistance_n / ewm.design_resistance_n  # type: ignore[operator]
        utilization_difference = dsm.utilization - ewm.utilization  # type: ignore[operator]
        if ewm.design_resistance_n < dsm.design_resistance_n:  # type: ignore[operator]
            governing = ComparisonGoverningMethod.EWM
            governing_capacity = ewm.design_resistance_n
            governing_utilization = ewm.utilization
        elif dsm.design_resistance_n < ewm.design_resistance_n:  # type: ignore[operator]
            governing = ComparisonGoverningMethod.DSM
            governing_capacity = dsm.design_resistance_n
            governing_utilization = dsm.utilization
        else:
            governing = ComparisonGoverningMethod.EQUAL_CAPACITY
            governing_capacity = ewm.design_resistance_n
            governing_utilization = ewm.utilization
        overall = (
            CompressionOverallStatus.PASS
            if ewm.check_status is DesignCheckStatus.PASS
            and dsm.check_status is DesignCheckStatus.PASS
            else CompressionOverallStatus.FAIL
        )
        metrics = (
            absolute,
            relative,
            ratio,
            utilization_difference,
            governing_capacity,
            governing_utilization,
        )
        comparison_status = CompressionComparisonStatus.COMPLETE_COMPARISON
    else:
        metrics = None
        governing = None
        if ewm_available or dsm_available:
            comparison_status = CompressionComparisonStatus.PARTIAL_COMPARISON
            overall = CompressionOverallStatus.PARTIAL
            message = (
                "Only one method is design-ready; no comparison-governing method is reported."
            )
            warnings += (message,)
            diagnostics += (
                _diagnostic(
                    "M10_PARTIAL_COMPARISON",
                    message,
                    severity=DiagnosticSeverity.WARNING,
                ),
            )
        elif all(
            item.availability is MethodAvailability.METHOD_NOT_APPLICABLE
            for item in (ewm, dsm)
        ):
            comparison_status = CompressionComparisonStatus.NOT_APPLICABLE
            overall = CompressionOverallStatus.NOT_APPLICABLE
        elif any(
            item.availability is MethodAvailability.METHOD_INVALID_INPUT
            for item in (ewm, dsm)
        ):
            comparison_status = CompressionComparisonStatus.INVALID_INPUT
            overall = CompressionOverallStatus.INVALID_INPUT
        else:
            comparison_status = CompressionComparisonStatus.UNSUPPORTED
            overall = CompressionOverallStatus.UNSUPPORTED
    trace = _comparison_trace(
        demand=demand,
        ewm=ewm,
        dsm=dsm,
        status=comparison_status,
        metrics=metrics,
        diagnostics=diagnostics,
        warnings=warnings,
    )
    return CompressionComparisonResult(
        demand_context=demand,
        ewm=ewm,
        dsm=dsm,
        absolute_capacity_difference_n=(metrics[0] if metrics is not None else None),
        relative_capacity_difference_percent=(metrics[1] if metrics is not None else None),
        capacity_ratio_dsm_to_ewm=(metrics[2] if metrics is not None else None),
        utilization_difference=(metrics[3] if metrics is not None else None),
        comparison_governing_method=governing,
        comparison_governing_capacity_n=(metrics[4] if metrics is not None else None),
        comparison_governing_utilization=(metrics[5] if metrics is not None else None),
        overall_status=overall,
        comparison_status=comparison_status,
        code_required_design_method=None,
        trace=trace,
        diagnostics=diagnostics,
        warnings=warnings,
        provenance=(
            MetadataEntry("ewm_trace_id", ewm.source_trace_id),
            MetadataEntry("dsm_trace_id", dsm.source_trace_id),
            MetadataEntry("comparison_semantics", "INFORMATIONAL_LOWER_CAPACITY"),
        ),
    )


__all__ = [
    "calculate_axial_utilization",
    "compare_compression_summaries",
    "noncompression_summary",
    "summarize_dsm_compression",
    "summarize_ewm_compression",
]
