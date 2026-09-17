"""Thin M10 routing for EWM, DSM, and comparison axial-compression checks."""

from dataclasses import dataclass
from typing import TypeAlias

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.comparison import (
    AxialDemandContext,
    CompressionComparisonResult,
    MethodCompressionSummary,
    compare_compression_summaries,
    noncompression_summary,
    summarize_dsm_compression,
    summarize_ewm_compression,
)
from cfs_design.design.dsm import (
    M9AUnavailable,
    calculate_dsm_compression_resistance,
)
from cfs_design.design.ewm import calculate_ewm_compression_resistance
from cfs_design.design.inputs import MemberDesignInput
from cfs_design.domain import DesignMethod, RunMode, SectionDemandSet
from cfs_design.normative import DesignAction, DesignExecutionPurpose
from cfs_design.stability import ElasticBucklingResult

from .project.design_input import resolve_member_design_input
from .project.models import ResolvedProject


AxialCompressionDesignResult: TypeAlias = (
    MethodCompressionSummary | CompressionComparisonResult
)


def _validate_method_input(
    design_input: MemberDesignInput,
    *,
    expected_method: DesignMethod,
    run_mode: RunMode,
    demand: AxialDemandContext,
) -> None:
    if not isinstance(design_input, MemberDesignInput):
        raise ValidationError(
            f"{expected_method.value.lower()}_input must be MemberDesignInput"
        )
    if design_input.method is not expected_method:
        raise ValidationError(
            f"{expected_method.value} route requires method-specific eligibility"
        )
    if design_input.action is not DesignAction.AXIAL_COMPRESSION:
        raise ValidationError("M10 supports axial compression only")
    if design_input.purpose is not DesignExecutionPurpose.DEMAND_CHECK:
        raise ValidationError("M10 requires DEMAND_CHECK MemberDesignInput")
    if design_input.design_context.run_mode is not run_mode:
        raise ValidationError("request run_mode must match the shared DesignContext")
    if expected_method not in design_input.design_context.methods:
        raise ValidationError("requested method is absent from DesignContext.methods")
    member = design_input.resolved_member
    if (
        member.member.case_id != demand.case_id
        or member.section.catalog_section.section_id != demand.section_id
        or member.material.material_id != demand.material_id
    ):
        raise ValidationError("demand identity does not match resolved physical input")
    demands = member.section_demands
    if not isinstance(demands, SectionDemandSet):
        raise ValidationError("M10 requires resolved section-axis demands")
    combination = next(
        (
            item
            for item in demands.combinations
            if item.combination_id == demand.combination_id
        ),
        None,
    )
    if combination is None or combination.case_type != demand.case_type:
        raise ValidationError("demand combination does not match resolved member")
    point = next(
        (item for item in combination.points if item.point_id == demand.point.point_id),
        None,
    )
    if point is not demand.point:
        raise ValidationError(
            "demand point must be the exact resolved simultaneous force state"
        )


@dataclass(frozen=True, slots=True)
class AxialCompressionDesignRequest:
    project_id: str
    run_mode: RunMode
    demand: AxialDemandContext
    ewm_input: MemberDesignInput | None = None
    dsm_input: MemberDesignInput | None = None
    elastic_buckling: ElasticBucklingResult | M9AUnavailable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ValidationError("project_id must be a non-empty string")
        if not isinstance(self.run_mode, RunMode):
            raise ValidationError("run_mode must be RunMode")
        if not isinstance(self.demand, AxialDemandContext):
            raise ValidationError("demand must be AxialDemandContext")
        if self.project_id != self.demand.project_id:
            raise ValidationError("project_id must match demand context")
        required_ewm = self.run_mode in (RunMode.EWM, RunMode.COMPARE)
        required_dsm = self.run_mode in (RunMode.DSM, RunMode.COMPARE)
        if required_ewm and self.ewm_input is None:
            raise ValidationError("EWM or COMPARE mode requires ewm_input")
        if required_dsm and self.dsm_input is None:
            raise ValidationError("DSM or COMPARE mode requires dsm_input")
        if required_dsm and self.elastic_buckling is None:
            raise ValidationError(
                "DSM or COMPARE mode requires an M9A result or M9AUnavailable"
            )
        if self.elastic_buckling is not None and not isinstance(
            self.elastic_buckling, (ElasticBucklingResult, M9AUnavailable)
        ):
            raise ValidationError(
                "elastic_buckling must be ElasticBucklingResult, M9AUnavailable, or None"
            )
        if self.ewm_input is not None:
            _validate_method_input(
                self.ewm_input,
                expected_method=DesignMethod.EWM,
                run_mode=self.run_mode,
                demand=self.demand,
            )
        if self.dsm_input is not None:
            _validate_method_input(
                self.dsm_input,
                expected_method=DesignMethod.DSM,
                run_mode=self.run_mode,
                demand=self.demand,
            )
        if self.run_mode is RunMode.COMPARE:
            assert self.ewm_input is not None and self.dsm_input is not None
            for name in (
                "resolved_member",
                "section_mechanics",
                "design_context",
                "scope_evidence",
                "standard_dimensions",
                "material_qualification",
            ):
                if getattr(self.ewm_input, name) is not getattr(self.dsm_input, name):
                    raise ValidationError(
                        "COMPARE inputs must share the exact same "
                        f"{name} object"
                    )


def prepare_axial_compression_request(
    resolved_project: ResolvedProject,
    case_id: str,
    combination_id: str,
    demand_point_id: str,
    *,
    elastic_buckling: ElasticBucklingResult | M9AUnavailable | None = None,
) -> AxialCompressionDesignRequest:
    """Select one resolved simultaneous demand point and build the M10 request."""

    if not isinstance(resolved_project, ResolvedProject):
        raise ValidationError("resolved_project must be ResolvedProject")
    for name, value in (
        ("case_id", case_id),
        ("combination_id", combination_id),
        ("demand_point_id", demand_point_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{name} must be a non-empty string")
    member = resolved_project.get_resolved_member(case_id)
    demands = member.section_demands
    if demands is None:
        raise ValidationError("member has no resolved section-axis demands")
    combination = next(
        (
            item
            for item in demands.combinations
            if item.combination_id == combination_id
        ),
        None,
    )
    if combination is None:
        raise ValidationError(f"unknown demand combination {combination_id!r}")
    point = next(
        (item for item in combination.points if item.point_id == demand_point_id),
        None,
    )
    if point is None:
        raise ValidationError(f"unknown demand point {demand_point_id!r}")
    context = resolved_project.design_context
    demand = AxialDemandContext(
        project_id=resolved_project.metadata.project_id,
        case_id=case_id,
        section_id=member.section.catalog_section.section_id,
        material_id=member.material.material_id,
        combination_id=combination_id,
        case_type=combination.case_type,
        point=point,
    )
    ewm_input = (
        resolve_member_design_input(
            resolved_project,
            case_id,
            DesignMethod.EWM,
            DesignAction.AXIAL_COMPRESSION,
            DesignExecutionPurpose.DEMAND_CHECK,
        )
        if context.run_mode in (RunMode.EWM, RunMode.COMPARE)
        else None
    )
    dsm_input = (
        resolve_member_design_input(
            resolved_project,
            case_id,
            DesignMethod.DSM,
            DesignAction.AXIAL_COMPRESSION,
            DesignExecutionPurpose.DEMAND_CHECK,
        )
        if context.run_mode in (RunMode.DSM, RunMode.COMPARE)
        else None
    )
    return AxialCompressionDesignRequest(
        project_id=resolved_project.metadata.project_id,
        run_mode=context.run_mode,
        demand=demand,
        ewm_input=ewm_input,
        dsm_input=dsm_input,
        elastic_buckling=elastic_buckling,
    )


def design_axial_compression(
    request: AxialCompressionDesignRequest,
) -> AxialCompressionDesignResult:
    """Execute exactly the route selected by the shared project run mode."""

    if not isinstance(request, AxialCompressionDesignRequest):
        raise ValidationError("request must be AxialCompressionDesignRequest")
    if not request.demand.is_compression:
        if request.run_mode is RunMode.EWM:
            return noncompression_summary(
                method=DesignMethod.EWM,
                design_input=request.ewm_input,  # type: ignore[arg-type]
                demand=request.demand,
            )
        if request.run_mode is RunMode.DSM:
            return noncompression_summary(
                method=DesignMethod.DSM,
                design_input=request.dsm_input,  # type: ignore[arg-type]
                demand=request.demand,
            )
        ewm = noncompression_summary(
            method=DesignMethod.EWM,
            design_input=request.ewm_input,  # type: ignore[arg-type]
            demand=request.demand,
        )
        dsm = noncompression_summary(
            method=DesignMethod.DSM,
            design_input=request.dsm_input,  # type: ignore[arg-type]
            demand=request.demand,
        )
        return compare_compression_summaries(ewm=ewm, dsm=dsm)

    if request.run_mode is RunMode.EWM:
        design_input = request.ewm_input
        assert design_input is not None
        resistance = calculate_ewm_compression_resistance(design_input)
        return summarize_ewm_compression(
            design_input=design_input,
            demand=request.demand,
            resistance=resistance,
        )
    if request.run_mode is RunMode.DSM:
        design_input = request.dsm_input
        assert design_input is not None and request.elastic_buckling is not None
        resistance = calculate_dsm_compression_resistance(
            design_input,
            request.elastic_buckling,
        )
        return summarize_dsm_compression(
            design_input=design_input,
            demand=request.demand,
            resistance=resistance,
        )

    ewm_input = request.ewm_input
    dsm_input = request.dsm_input
    assert (
        ewm_input is not None
        and dsm_input is not None
        and request.elastic_buckling is not None
    )
    ewm_resistance = calculate_ewm_compression_resistance(ewm_input)
    dsm_resistance = calculate_dsm_compression_resistance(
        dsm_input,
        request.elastic_buckling,
    )
    ewm = summarize_ewm_compression(
        design_input=ewm_input,
        demand=request.demand,
        resistance=ewm_resistance,
    )
    dsm = summarize_dsm_compression(
        design_input=dsm_input,
        demand=request.demand,
        resistance=dsm_resistance,
    )
    return compare_compression_summaries(ewm=ewm, dsm=dsm)


__all__ = [
    "AxialCompressionDesignRequest",
    "AxialCompressionDesignResult",
    "design_axial_compression",
    "prepare_axial_compression_request",
]
