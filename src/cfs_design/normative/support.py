"""Independent StructureLab_CFS v0.1 software-support rules."""

from math import isclose

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    DesignContext,
    DesignFormat,
    DesignMethod,
    GeometryConvention,
    MemberType,
    ResolvedMember,
    SectionFamily,
)
from cfs_design.results import (
    DiagnosticSeverity,
    EngineeringDiagnostic,
    MetadataEntry,
)

from .enums import DesignAction, SoftwareSupportStatus
from .models import (
    SoftwareSupportCheck,
    SoftwareSupportResult,
    aggregate_software_status,
    make_software_check_id,
)
from .sources import S100_24_STANDARD_ID


SOFTWARE_SCOPE_VERSION = "0.1"
SUPPORTED_SECTION_FAMILIES = (
    SectionFamily.C_LIPPED,
    SectionFamily.C_UNLIPPED,
)
SUPPORTED_DESIGN_FORMATS = (DesignFormat.LRFD,)
SUPPORTED_DESIGN_METHODS = (DesignMethod.EWM, DesignMethod.DSM)
SUPPORTED_DESIGN_ACTIONS = (
    DesignAction.AXIAL_COMPRESSION,
    DesignAction.STRONG_AXIS_FLEXURE,
)
UNSUPPORTED_V01_FEATURES = (
    "SHEAR_DESIGN",
    "COMBINED_AXIAL_FLEXURE_INTERACTION",
    "HOLES_OR_OPENINGS",
    "BUILT_UP_MEMBERS",
    "CONNECTIONS",
    "WEB_CRIPPLING",
    "SEISMIC_SYSTEM_DESIGN",
    "ARBITRARY_USER_DEFINED_SECTIONS",
    "AUTOMATIC_LOAD_COMBINATION_GENERATION",
    "SAP2000_IMPORT",
    "ASD",
    "FLAT_WIDTHS_GEOMETRY",
    "OUT_TO_OUT_GEOMETRY",
    "NONZERO_BEND_RADII",
    "NON_ORTHOGONAL_GEOMETRY",
)

_NUMERIC_TOLERANCE = 1.0e-9


def _software_diagnostic(
    *,
    status: SoftwareSupportStatus,
    code: str,
    message: str,
    observed: tuple[MetadataEntry, ...],
) -> EngineeringDiagnostic:
    severity = (
        DiagnosticSeverity.ERROR
        if status is SoftwareSupportStatus.INVALID_INPUT
        else DiagnosticSeverity.WARNING
    )
    return EngineeringDiagnostic(
        severity=severity,
        code=code,
        message=message,
        context=observed,
    )


def _check(
    *,
    method: DesignMethod,
    action: DesignAction,
    capability_id: str,
    topic: str,
    status: SoftwareSupportStatus,
    observed: tuple[MetadataEntry, ...],
    requirement: str,
    diagnostic_code: str | None = None,
    diagnostic_message: str | None = None,
) -> SoftwareSupportCheck:
    diagnostic = None
    if diagnostic_code is not None and diagnostic_message is not None:
        diagnostic = _software_diagnostic(
            status=status,
            code=diagnostic_code,
            message=diagnostic_message,
            observed=observed,
        )
    return SoftwareSupportCheck(
        check_id=make_software_check_id(
            method=method,
            action=action,
            capability_id=capability_id,
        ),
        topic=topic,
        status=status,
        observed=observed,
        requirement=requirement,
        diagnostic=diagnostic,
    )


def _binary_support_check(
    *,
    method: DesignMethod,
    action: DesignAction,
    capability_id: str,
    topic: str,
    supported: bool,
    observed: tuple[MetadataEntry, ...],
    requirement: str,
    diagnostic_code: str,
    diagnostic_message: str,
) -> SoftwareSupportCheck:
    return _check(
        method=method,
        action=action,
        capability_id=capability_id,
        topic=topic,
        status=(
            SoftwareSupportStatus.SUPPORTED
            if supported
            else SoftwareSupportStatus.UNSUPPORTED
        ),
        observed=observed,
        requirement=requirement,
        diagnostic_code=None if supported else diagnostic_code,
        diagnostic_message=None if supported else diagnostic_message,
    )


def _input_checks(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[SoftwareSupportCheck, ...]:
    records_active = (
        member.member.active
        and member.section.catalog_section.active
        and member.material.active
    )
    active_observed = (
        MetadataEntry("member_active", member.member.active),
        MetadataEntry(
            "section_active", member.section.catalog_section.active
        ),
        MetadataEntry("material_active", member.material.active),
    )
    active_check = _check(
        method=method,
        action=action,
        capability_id="RESOLVED_ACTIVE_RECORDS",
        topic="resolved input validity",
        status=(
            SoftwareSupportStatus.SUPPORTED
            if records_active
            else SoftwareSupportStatus.INVALID_INPUT
        ),
        observed=active_observed,
        requirement="M7 requires active member, section, and material records.",
        diagnostic_code=(None if records_active else "INACTIVE_RESOLVED_INPUT"),
        diagnostic_message=(
            None
            if records_active
            else "Resolved execution input contains an inactive record"
        ),
    )

    method_selected = method in context.methods
    method_observed = (
        MetadataEntry("requested_method", method.value),
        MetadataEntry(
            "configured_methods",
            ",".join(item.value for item in context.methods),
        ),
    )
    configured_method_check = _check(
        method=method,
        action=action,
        capability_id="PROJECT_METHOD_SELECTION",
        topic="project method selection",
        status=(
            SoftwareSupportStatus.SUPPORTED
            if method_selected
            else SoftwareSupportStatus.INVALID_INPUT
        ),
        observed=method_observed,
        requirement="The requested method must be selected in DesignContext.",
        diagnostic_code=(None if method_selected else "METHOD_NOT_CONFIGURED"),
        diagnostic_message=(
            None
            if method_selected
            else "The requested design method is not enabled for this project"
        ),
    )

    m5_demands = member.section_demands is not None and member.source_demands is not None
    demand_observed = (
        MetadataEntry(
            "section_axis_demands", member.section_demands is not None
        ),
        MetadataEntry("source_demands_preserved", member.source_demands is not None),
    )
    demand_check = _check(
        method=method,
        action=action,
        capability_id="M4_M5_ETABS_DEMAND_PIPELINE",
        topic="demand-source boundary",
        status=(
            SoftwareSupportStatus.SUPPORTED
            if m5_demands
            else SoftwareSupportStatus.INVALID_INPUT
        ),
        observed=demand_observed,
        requirement=(
            "M7 execution input must preserve imported ETABS demands and their "
            "M5 section-axis transformation."
        ),
        diagnostic_code=(None if m5_demands else "M5_DEMAND_INPUT_REQUIRED"),
        diagnostic_message=(
            None
            if m5_demands
            else "The resolved member does not contain the approved M5 demand pair"
        ),
    )
    return active_check, configured_method_check, demand_check


def _context_checks(
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[SoftwareSupportCheck, ...]:
    standard_supported = (
        context.standard_id == S100_24_STANDARD_ID
        and context.standard_edition == 2024
    )
    standard_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="STANDARD_EDITION",
        topic="software standard support",
        supported=standard_supported,
        observed=(
            MetadataEntry("standard_id", context.standard_id),
            MetadataEntry("standard_edition", context.standard_edition),
        ),
        requirement="v0.1 supports ANSI/SDI AISI S100-2024 only.",
        diagnostic_code="UNSUPPORTED_STANDARD",
        diagnostic_message="The configured standard is outside v0.1 support",
    )
    format_supported = context.design_format in SUPPORTED_DESIGN_FORMATS
    format_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="DESIGN_FORMAT",
        topic="software design-format support",
        supported=format_supported,
        observed=(MetadataEntry("design_format", context.design_format.value),),
        requirement="v0.1 supports LRFD only.",
        diagnostic_code="UNSUPPORTED_DESIGN_FORMAT",
        diagnostic_message="The configured design format is outside v0.1 support",
    )
    method_supported = method in SUPPORTED_DESIGN_METHODS
    method_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="DESIGN_METHOD",
        topic="software design-method support",
        supported=method_supported,
        observed=(MetadataEntry("method", method.value),),
        requirement="v0.1 targets EWM and DSM methods.",
        diagnostic_code="UNSUPPORTED_DESIGN_METHOD",
        diagnostic_message="The requested method is outside v0.1 support",
    )
    return standard_check, format_check, method_check


def _section_checks(
    member: ResolvedMember,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[SoftwareSupportCheck, ...]:
    section = member.section
    geometry = section.geometry
    family = section.catalog_section.family
    family_supported = family in SUPPORTED_SECTION_FAMILIES
    family_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="SECTION_FAMILY",
        topic="software section-family support",
        supported=family_supported,
        observed=(MetadataEntry("section_family", family.value),),
        requirement="v0.1 supports catalog lipped and unlipped C-sections only.",
        diagnostic_code="UNSUPPORTED_SECTION_FAMILY",
        diagnostic_message="The section family is outside v0.1 support",
    )

    convention_supported = (
        geometry.geometry_convention is GeometryConvention.MIDLINE
    )
    convention_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="GEOMETRY_CONVENTION",
        topic="software geometry convention",
        supported=convention_supported,
        observed=(
            MetadataEntry(
                "geometry_convention", geometry.geometry_convention.value
            ),
        ),
        requirement="M3 supports MIDLINE geometry only.",
        diagnostic_code="UNSUPPORTED_GEOMETRY_CONVENTION",
        diagnostic_message=(
            "FLAT_WIDTHS and OUT_TO_OUT geometry remain unsupported software inputs"
        ),
    )

    sharp_corner_supported = isclose(
        geometry.ri_mm, 0.0, rel_tol=0.0, abs_tol=_NUMERIC_TOLERANCE
    )
    radius_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="SHARP_CORNERS",
        topic="software bend-radius support",
        supported=sharp_corner_supported,
        observed=(MetadataEntry("inside_radius_mm", geometry.ri_mm),),
        requirement="M3 supports sharp-corner geometry with zero bend radius.",
        diagnostic_code="UNSUPPORTED_BEND_RADIUS",
        diagnostic_message="Nonzero bend radii are outside M3 software support",
    )

    web_angle_supported = isclose(
        geometry.web_flange_angle_deg,
        90.0,
        rel_tol=0.0,
        abs_tol=_NUMERIC_TOLERANCE,
    )
    lip_angle_supported = geometry.flange_lip_angle_deg is None or isclose(
        geometry.flange_lip_angle_deg,
        90.0,
        rel_tol=0.0,
        abs_tol=_NUMERIC_TOLERANCE,
    )
    angles_supported = web_angle_supported and lip_angle_supported
    angle_check = _binary_support_check(
        method=method,
        action=action,
        capability_id="ORTHOGONAL_GEOMETRY",
        topic="software geometry angles",
        supported=angles_supported,
        observed=(
            MetadataEntry(
                "web_flange_angle_deg", geometry.web_flange_angle_deg
            ),
            MetadataEntry(
                "flange_lip_angle_deg", geometry.flange_lip_angle_deg
            ),
        ),
        requirement="M3 supports orthogonal web, flange, and lip geometry only.",
        diagnostic_code="UNSUPPORTED_NON_ORTHOGONAL_GEOMETRY",
        diagnostic_message="Non-orthogonal geometry is outside M3 software support",
    )
    return family_check, convention_check, radius_check, angle_check


def _action_checks(
    member: ResolvedMember,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[SoftwareSupportCheck, ...]:
    action_supported = action in SUPPORTED_DESIGN_ACTIONS
    checks: list[SoftwareSupportCheck] = [
        _binary_support_check(
            method=method,
            action=action,
            capability_id="DESIGN_ACTION",
            topic="software design-action support",
            supported=action_supported,
            observed=(MetadataEntry("action", action.value),),
            requirement=(
                "v0.1 supports axial compression and strong-axis flexure only."
            ),
            diagnostic_code="UNSUPPORTED_DESIGN_ACTION",
            diagnostic_message=(
                "The requested action is outside the v0.1 design scope"
            ),
        )
    ]
    if not action_supported:
        return tuple(checks)

    expected_member_type = (
        MemberType.COLUMN
        if action is DesignAction.AXIAL_COMPRESSION
        else MemberType.BEAM
    )
    member_type_supported = member.member.member_type is expected_member_type
    checks.append(
        _binary_support_check(
            method=method,
            action=action,
            capability_id="EXPLICIT_MEMBER_TYPE",
            topic="member action identity",
            supported=member_type_supported,
            observed=(
                MetadataEntry("member_type", member.member.member_type.value),
                MetadataEntry("expected_member_type", expected_member_type.value),
            ),
            requirement=(
                "The explicit member type must match the requested single-action "
                "v0.1 workflow."
            ),
            diagnostic_code="UNSUPPORTED_MEMBER_ACTION_TYPE",
            diagnostic_message=(
                "The explicit member type does not match this v0.1 action workflow"
            ),
        )
    )

    if action is DesignAction.STRONG_AXIS_FLEXURE:
        properties = member.section.properties
        axes_aligned = properties.ixy_mm4 is not None and isclose(
            properties.ixy_mm4,
            0.0,
            rel_tol=0.0,
            abs_tol=_NUMERIC_TOLERANCE,
        )
        distinct_axes = not isclose(
            properties.ix_mm4,
            properties.iy_mm4,
            rel_tol=1.0e-12,
            abs_tol=0.0,
        )
        strong_axis_supported = axes_aligned and distinct_axes
        strong_axis = (
            "X"
            if strong_axis_supported and properties.ix_mm4 > properties.iy_mm4
            else "Y"
            if strong_axis_supported
            else None
        )
        checks.append(
            _binary_support_check(
                method=method,
                action=action,
                capability_id="RESOLVED_STRONG_AXIS",
                topic="strong-axis convention",
                supported=strong_axis_supported,
                observed=(
                    MetadataEntry("ix_mm4", properties.ix_mm4),
                    MetadataEntry("iy_mm4", properties.iy_mm4),
                    MetadataEntry("ixy_mm4", properties.ixy_mm4),
                    MetadataEntry("strong_section_axis", strong_axis),
                ),
                requirement=(
                    "The resolved section x-y axes must be principal and have a "
                    "unique larger moment of inertia."
                ),
                diagnostic_code="STRONG_AXIS_NOT_RESOLVED",
                diagnostic_message=(
                    "Resolved section properties do not establish a unique strong "
                    "x or y section axis"
                ),
            )
        )
    return tuple(checks)


def evaluate_software_support(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> SoftwareSupportResult:
    """Evaluate only the approved software envelope, never AISI permission."""

    if not isinstance(member, ResolvedMember):
        raise ValidationError("member must be ResolvedMember")
    if not isinstance(context, DesignContext):
        raise ValidationError("context must be DesignContext")
    if not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod")
    if not isinstance(action, DesignAction):
        raise ValidationError("action must be DesignAction")

    checks = (
        _input_checks(member, context, method, action)
        + _context_checks(context, method, action)
        + _section_checks(member, method, action)
        + _action_checks(member, method, action)
    )
    return SoftwareSupportResult(
        method=method,
        action=action,
        status=aggregate_software_status(checks),
        checks=checks,
        software_scope_version=SOFTWARE_SCOPE_VERSION,
    )


__all__ = [
    "SOFTWARE_SCOPE_VERSION",
    "SUPPORTED_DESIGN_ACTIONS",
    "SUPPORTED_DESIGN_FORMATS",
    "SUPPORTED_DESIGN_METHODS",
    "SUPPORTED_SECTION_FAMILIES",
    "UNSUPPORTED_V01_FEATURES",
    "evaluate_software_support",
]
