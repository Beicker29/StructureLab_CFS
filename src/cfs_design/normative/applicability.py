"""Verified S100-24 applicability rules evaluable from the M5 domain."""

from math import isclose

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    DesignContext,
    DesignMethod,
    ResolvedMember,
    S100_24_STANDARD_EDITION,
    SectionFamily,
)
from cfs_design.results import (
    ApplicabilityStatus,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    MetadataEntry,
)

from .enums import DesignAction
from .models import (
    ApplicabilityCheck,
    NormativeApplicabilityResult,
    aggregate_normative_status,
    make_applicability_check_id,
)
from .sources import S100_24_STANDARD_ID, s100_24_reference


def _diagnostic(
    *, code: str, message: str, observed: tuple[MetadataEntry, ...]
) -> EngineeringDiagnostic:
    return EngineeringDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        code=code,
        message=message,
        context=observed,
    )


def _check(
    *,
    method: DesignMethod,
    action: DesignAction,
    rule_id: str,
    topic: str,
    status: ApplicabilityStatus,
    observed: tuple[MetadataEntry, ...],
    requirement: str,
    clause: str | None,
    reference_title: str,
    diagnostic_code: str | None = None,
    diagnostic_message: str | None = None,
) -> ApplicabilityCheck:
    diagnostic = None
    if diagnostic_code is not None and diagnostic_message is not None:
        diagnostic = _diagnostic(
            code=diagnostic_code,
            message=diagnostic_message,
            observed=observed,
        )
    return ApplicabilityCheck(
        check_id=make_applicability_check_id(
            method=method, action=action, rule_id=rule_id
        ),
        topic=topic,
        status=status,
        observed=observed,
        requirement=requirement,
        reference=s100_24_reference(clause=clause, title=reference_title),
        diagnostic=diagnostic,
    )


def _source_selection_check(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> ApplicabilityCheck:
    del member
    observed = (
        MetadataEntry("standard_id", context.standard_id),
        MetadataEntry("standard_edition", context.standard_edition),
    )
    matches = (
        context.standard_id == S100_24_STANDARD_ID
        and context.standard_edition == S100_24_STANDARD_EDITION
    )
    return _check(
        method=method,
        action=action,
        rule_id="M7_SOURCE_SELECTION",
        topic="normative source selection",
        status=(
            ApplicabilityStatus.APPLICABLE
            if matches
            else ApplicabilityStatus.INDETERMINATE
        ),
        observed=observed,
        requirement="M7 rules are verified only for ANSI/SDI AISI S100-2024.",
        clause=None,
        reference_title="S100-24 verified source identity",
        diagnostic_code=None if matches else "NORMATIVE_SOURCE_NOT_EVALUATED",
        diagnostic_message=(
            None
            if matches
            else "The selected standard is outside the verified M7 rule set"
        ),
    )


def _general_scope_checks(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[ApplicabilityCheck, ...]:
    thickness = member.section.geometry.t_mm
    thickness_observed = (MetadataEntry("thickness_mm", thickness),)
    within_thickness = thickness <= 25.4
    thickness_check = _check(
        method=method,
        action=action,
        rule_id="A1_1_THICKNESS",
        topic="specification thickness scope",
        status=(
            ApplicabilityStatus.APPLICABLE
            if within_thickness
            else ApplicabilityStatus.NOT_APPLICABLE
        ),
        observed=thickness_observed,
        requirement="Cold-formed member thickness must not exceed 25.4 mm.",
        clause="A1.1",
        reference_title="Specification scope",
        diagnostic_code=None if within_thickness else "AISI_SCOPE_THICKNESS",
        diagnostic_message=(
            None
            if within_thickness
            else "Member thickness exceeds the S100-24 scope limit"
        ),
    )

    provenance_observed = (
        MetadataEntry("material_specification", member.material.specification),
        MetadataEntry(
            "section_source_id", member.section.catalog_section.source_id
        ),
    )
    provenance_check = _check(
        method=method,
        action=action,
        rule_id="A1_1_MEMBER_PROVENANCE",
        topic="member and material scope",
        status=ApplicabilityStatus.INDETERMINATE,
        observed=provenance_observed,
        requirement=(
            "The member must have the qualifying cold-formed material and "
            "load-carrying use required by the specification scope."
        ),
        clause="A1.1",
        reference_title="Member and material scope",
        diagnostic_code="AISI_SCOPE_FACTS_UNMODELED",
        diagnostic_message=(
            "The domain does not explicitly record forming process, base-metal "
            "classification, structural use, or dynamic-effects context"
        ),
    )

    format_observed = (
        MetadataEntry("design_format", context.design_format.value),
        MetadataEntry("jurisdiction", None),
    )
    format_check = _check(
        method=method,
        action=action,
        rule_id="A1_2_3_DESIGN_FORMAT_JURISDICTION",
        topic="design-format jurisdiction",
        status=ApplicabilityStatus.INDETERMINATE,
        observed=format_observed,
        requirement=(
            "The selected design format must correspond to the governing country."
        ),
        clause="A1.2.3",
        reference_title="Geographic applicability of design methods",
        diagnostic_code="AISI_JURISDICTION_UNMODELED",
        diagnostic_message=(
            "The design format is known, but the governing country is not an "
            "explicit DesignContext field"
        ),
    )
    return thickness_check, provenance_check, format_check


def _b4_checks(
    member: ResolvedMember,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[ApplicabilityCheck, ...]:
    geometry = member.section.geometry
    family = member.section.catalog_section.family
    yield_limit_mpa = 552.0 if method is DesignMethod.EWM else 655.0
    yield_observed = (
        MetadataEntry("fy_mpa", member.material.fy_mpa),
        MetadataEntry("limit_mpa", yield_limit_mpa),
    )
    yield_within_limit = member.material.fy_mpa <= yield_limit_mpa
    checks: list[ApplicabilityCheck] = [
        _check(
            method=method,
            action=action,
            rule_id="B4_1_YIELD_STRESS",
            topic="B4 material limit",
            status=(
                ApplicabilityStatus.APPLICABLE
                if yield_within_limit
                else ApplicabilityStatus.NOT_APPLICABLE
            ),
            observed=yield_observed,
            requirement=(
                f"The B4.1 {method.value} route requires Fy not greater than "
                f"{yield_limit_mpa:g} MPa."
            ),
            clause="B4.1, Table B4.1-1",
            reference_title="Member-design applicability limits",
            diagnostic_code=(
                None if yield_within_limit else "AISI_B4_YIELD_STRESS_LIMIT"
            ),
            diagnostic_message=(
                None
                if yield_within_limit
                else "Yield stress is outside the B4.1 limit for this method"
            ),
        )
    ]

    radius_ratio = geometry.ri_mm / geometry.t_mm
    radius_limit = 10.0 if method is DesignMethod.EWM else 20.0
    radius_observed = (
        MetadataEntry("inside_radius_mm", geometry.ri_mm),
        MetadataEntry("thickness_mm", geometry.t_mm),
        MetadataEntry("inside_radius_to_thickness", radius_ratio),
        MetadataEntry("limit", radius_limit),
    )
    radius_within_limit = radius_ratio <= radius_limit
    checks.append(
        _check(
            method=method,
            action=action,
            rule_id="B4_1_INSIDE_RADIUS",
            topic="B4 geometry limit",
            status=(
                ApplicabilityStatus.APPLICABLE
                if radius_within_limit
                else ApplicabilityStatus.NOT_APPLICABLE
            ),
            observed=radius_observed,
            requirement=(
                f"The B4.1 {method.value} route limits inside-radius-to-"
                f"thickness ratio to {radius_limit:g}."
            ),
            clause="B4.1, Table B4.1-1",
            reference_title="Member-design applicability limits",
            diagnostic_code=(
                None if radius_within_limit else "AISI_B4_RADIUS_LIMIT"
            ),
            diagnostic_message=(
                None
                if radius_within_limit
                else "Inside bend radius is outside the B4.1 method limit"
            ),
        )
    )

    dimensions = member.section.find_standard_dimensions(
        S100_24_STANDARD_ID,
        S100_24_STANDARD_EDITION,
    )
    if dimensions is None:
        dimension_status = ApplicabilityStatus.INDETERMINATE
        dimension_observed = (
            MetadataEntry("dimension_source", None),
            MetadataEntry("geometry_convention", geometry.geometry_convention.value),
        )
        dimension_diagnostic_code = "AISI_B4_DIMENSION_BASIS_UNAVAILABLE"
        dimension_diagnostic_message = (
            "No explicit S100-24 dimensional record is resolved; MIDLINE "
            "geometry is not converted to flat or out-to-out dimensions"
        )
    else:
        thickness = geometry.t_mm
        web_limit = 500.0 if action is DesignAction.AXIAL_COMPRESSION else 300.0
        web_ratio = dimensions.web_flat_width_mm / thickness
        flange_ratios = (
            dimensions.flange_1_flat_width_mm / thickness,
            dimensions.flange_2_flat_width_mm / thickness,
        )
        failures = web_ratio > web_limit
        stiffness_unknown = False
        observed_values: list[MetadataEntry] = [
            MetadataEntry("dimension_source", dimensions.source_id),
            MetadataEntry("web_flat_width_to_thickness", web_ratio),
            MetadataEntry("web_ratio_limit", web_limit),
            MetadataEntry("flange_1_flat_width_to_thickness", flange_ratios[0]),
            MetadataEntry("flange_2_flat_width_to_thickness", flange_ratios[1]),
        ]
        if family is SectionFamily.C_UNLIPPED:
            flange_limit = 60.0
            failures = failures or any(
                ratio > flange_limit for ratio in flange_ratios
            )
            observed_values.append(MetadataEntry("flange_ratio_limit", flange_limit))
        elif family is SectionFamily.C_LIPPED and dimensions.has_lipped_dimensions:
            lipped_values = (
                dimensions.flange_1_out_to_out_width_mm,
                dimensions.flange_2_out_to_out_width_mm,
                dimensions.lip_1_flat_width_mm,
                dimensions.lip_2_flat_width_mm,
                dimensions.lip_1_out_to_out_width_mm,
                dimensions.lip_2_out_to_out_width_mm,
            )
            if any(value is None for value in lipped_values):
                raise ValidationError(
                    "resolved C_LIPPED standard dimensions are incomplete"
                )
            flange_1_out, flange_2_out, lip_1_flat, lip_2_flat, lip_1_out, lip_2_out = (
                float(value) for value in lipped_values
            )
            lip_ratios = (lip_1_flat / thickness, lip_2_flat / thickness)
            stiffener_ratios = (
                lip_1_out / flange_1_out,
                lip_2_out / flange_2_out,
            )
            flange_limit = 160.0 if method is DesignMethod.DSM else 90.0
            failures = (
                failures
                or any(ratio > flange_limit for ratio in flange_ratios)
                or any(ratio > 60.0 for ratio in lip_ratios)
                or any(ratio > 0.7 for ratio in stiffener_ratios)
            )
            if method is DesignMethod.EWM and any(
                60.0 < ratio <= 90.0 for ratio in flange_ratios
            ):
                stiffness_unknown = True
            observed_values.extend(
                (
                    MetadataEntry("flange_ratio_limit", flange_limit),
                    MetadataEntry("lip_1_flat_width_to_thickness", lip_ratios[0]),
                    MetadataEntry("lip_2_flat_width_to_thickness", lip_ratios[1]),
                    MetadataEntry("lip_ratio_limit", 60.0),
                    MetadataEntry("lip_1_do_to_bo", stiffener_ratios[0]),
                    MetadataEntry("lip_2_do_to_bo", stiffener_ratios[1]),
                    MetadataEntry("do_to_bo_limit", 0.7),
                )
            )
        else:
            stiffness_unknown = True
        dimension_observed = tuple(observed_values)
        if failures:
            dimension_status = ApplicabilityStatus.NOT_APPLICABLE
            dimension_diagnostic_code = "AISI_B4_ELEMENT_RATIO_LIMIT"
            dimension_diagnostic_message = (
                "At least one explicit element ratio is outside the ordinary "
                "B4.1 method limit"
            )
        elif stiffness_unknown:
            dimension_status = ApplicabilityStatus.INDETERMINATE
            dimension_diagnostic_code = "AISI_B4_STIFFENER_RIGIDITY_UNAVAILABLE"
            dimension_diagnostic_message = (
                "The EWM edge-stiffened flange ratio is between 60 and 90; "
                "Is/Ia is required to select its B4.1 limit"
            )
        else:
            dimension_status = ApplicabilityStatus.APPLICABLE
            dimension_diagnostic_code = None
            dimension_diagnostic_message = None
    checks.append(
        _check(
            method=method,
            action=action,
            rule_id="B4_1_ELEMENT_DIMENSIONS",
            topic="B4 element dimensional limits",
            status=dimension_status,
            observed=dimension_observed,
            requirement=(
                "B4.1 element ratios must use explicit flat and out-to-out "
                "dimensions for the applicable element types."
            ),
            clause="B4.1, Table B4.1-1",
            reference_title="Member-design applicability limits",
            diagnostic_code=dimension_diagnostic_code,
            diagnostic_message=dimension_diagnostic_message,
        )
    )

    c_family = family in (SectionFamily.C_LIPPED, SectionFamily.C_UNLIPPED)
    edge_observed = (
        MetadataEntry("section_family", family.value),
        MetadataEntry(
            "edge_stiffener_kind",
            "SIMPLE_LIP"
            if family is SectionFamily.C_LIPPED
            else "NONE"
            if family is SectionFamily.C_UNLIPPED
            else None,
        ),
    )
    checks.append(
        _check(
            method=method,
            action=action,
            rule_id="B4_1_EDGE_STIFFENER_TYPE",
            topic="B4 edge-stiffener type",
            status=(
                ApplicabilityStatus.APPLICABLE
                if c_family
                else ApplicabilityStatus.INDETERMINATE
            ),
            observed=edge_observed,
            requirement=(
                "The section edge-stiffener type must fall within the method's "
                "B4.1 category."
            ),
            clause="B4.1, Table B4.1-1",
            reference_title="Member-design applicability limits",
            diagnostic_code=(
                None if c_family else "AISI_B4_EDGE_TYPE_UNDETERMINED"
            ),
            diagnostic_message=(
                None
                if c_family
                else "The present M7 rule does not classify this section family"
            ),
        )
    )

    if any(
        item.status is ApplicabilityStatus.NOT_APPLICABLE for item in checks
    ):
        checks.append(
            _check(
                method=method,
                action=action,
                rule_id="B4_2_ALTERNATIVE_ROUTE",
                topic="member outside B4.1 limits",
                status=ApplicabilityStatus.INDETERMINATE,
                observed=(MetadataEntry("alternative_route_evaluated", False),),
                requirement=(
                    "A member outside B4.1 requires the separate factor-"
                    "determination route identified by B4.2."
                ),
                clause="B4.2",
                reference_title="Members outside B4.1 limits",
                diagnostic_code="AISI_B4_2_NOT_EVALUATED",
                diagnostic_message=(
                    "M7 does not evaluate testing or rational-analysis routes; "
                    "NOT_APPLICABLE refers to the ordinary Chapter E/F factor route"
                ),
            )
        )
    return tuple(checks)


def _compression_checks(
    method: DesignMethod, action: DesignAction
) -> tuple[ApplicabilityCheck, ...]:
    clause = "E3.1" if method is DesignMethod.EWM else "E3.2"
    title = (
        "Effective Width Method compression route"
        if method is DesignMethod.EWM
        else "Direct Strength Method compression route"
    )
    return (
        _check(
            method=method,
            action=action,
            rule_id="E3_METHOD_ROUTE",
            topic="compression method route",
            status=ApplicabilityStatus.APPLICABLE,
            observed=(
                MetadataEntry("requested_action", action.value),
                MetadataEntry("requested_method", method.value),
            ),
            requirement=(
                "Local interaction for concentric compression must use the "
                "selected E3 method route."
            ),
            clause=clause,
            reference_title=title,
        ),
    )


def _flexure_checks(
    member: ResolvedMember,
    method: DesignMethod,
    action: DesignAction,
) -> tuple[ApplicabilityCheck, ...]:
    properties = member.section.properties
    principal_axis_known = (
        properties.ixy_mm4 is not None
        and isclose(properties.ixy_mm4, 0.0, rel_tol=0.0, abs_tol=1.0e-9)
        and not isclose(
            properties.ix_mm4,
            properties.iy_mm4,
            rel_tol=1.0e-12,
            abs_tol=0.0,
        )
    )
    axis_observed = (
        MetadataEntry("ix_mm4", properties.ix_mm4),
        MetadataEntry("iy_mm4", properties.iy_mm4),
        MetadataEntry("ixy_mm4", properties.ixy_mm4),
    )
    axis_check = _check(
        method=method,
        action=action,
        rule_id="F_SCOPE_BENDING_AXIS",
        topic="flexure bending axis",
        status=(
            ApplicabilityStatus.APPLICABLE
            if principal_axis_known
            else ApplicabilityStatus.INDETERMINATE
        ),
        observed=axis_observed,
        requirement=(
            "The Chapter F member must satisfy one of its stated bending-axis cases."
        ),
        clause="F",
        reference_title="Members in flexure scope",
        diagnostic_code=(
            None if principal_axis_known else "AISI_F_AXIS_UNDETERMINED"
        ),
        diagnostic_message=(
            None
            if principal_axis_known
            else "Resolved properties do not establish an aligned principal axis"
        ),
    )

    torsion_restrained = member.member.restraints.torsion_restrained
    twist_observed = (
        MetadataEntry("torsion_restrained", torsion_restrained),
        MetadataEntry("load_plane_through_shear_center", None),
        MetadataEntry("combined_bending_torsion_route", False),
    )
    twist_check = _check(
        method=method,
        action=action,
        rule_id="F_SCOPE_TWIST_CONDITION",
        topic="flexure load plane and twisting",
        status=(
            ApplicabilityStatus.APPLICABLE
            if torsion_restrained
            else ApplicabilityStatus.INDETERMINATE
        ),
        observed=twist_observed,
        requirement=(
            "At least one Chapter F load-plane, twisting-restraint, or combined-"
            "torsion condition must be established."
        ),
        clause="F",
        reference_title="Members in flexure scope",
        diagnostic_code=(
            None if torsion_restrained else "AISI_F_TWIST_CONDITION_UNDETERMINED"
        ),
        diagnostic_message=(
            None
            if torsion_restrained
            else "Twisting is not restrained and load-plane coincidence with the "
            "shear center is not represented"
        ),
    )

    global_clause = "F2.1" if method is DesignMethod.EWM else "F2.2"
    local_clause = "F3.1" if method is DesignMethod.EWM else "F3.2"
    route_observed = (
        MetadataEntry("requested_action", action.value),
        MetadataEntry("requested_method", method.value),
    )
    global_check = _check(
        method=method,
        action=action,
        rule_id="F2_METHOD_ROUTE",
        topic="flexure global method route",
        status=ApplicabilityStatus.APPLICABLE,
        observed=route_observed,
        requirement="Yielding and global flexure must use the selected F2 route.",
        clause=global_clause,
        reference_title=f"{method.value} global flexure route",
    )
    local_check = _check(
        method=method,
        action=action,
        rule_id="F3_METHOD_ROUTE",
        topic="flexure local method route",
        status=ApplicabilityStatus.APPLICABLE,
        observed=route_observed,
        requirement="Local interaction in flexure must use the selected F3 route.",
        clause=local_clause,
        reference_title=f"{method.value} local flexure route",
    )
    return axis_check, twist_check, global_check, local_check


def _unimplemented_action_check(
    method: DesignMethod, action: DesignAction
) -> ApplicabilityCheck:
    observed = (
        MetadataEntry("requested_action", action.value),
        MetadataEntry("requested_method", method.value),
    )
    return _check(
        method=method,
        action=action,
        rule_id="B3_3_ACTION_ROUTE_NOT_EVALUATED",
        topic="structural-member action route",
        status=ApplicabilityStatus.INDETERMINATE,
        observed=observed,
        requirement=(
            "The applicable member-design chapter must be evaluated for the "
            "requested action."
        ),
        clause="B3.3",
        reference_title="Design of structural members",
        diagnostic_code="AISI_ACTION_RULE_NOT_IMPLEMENTED",
        diagnostic_message=(
            "M7 has no normative rule set for the requested future action"
        ),
    )


def evaluate_normative_applicability(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
) -> NormativeApplicabilityResult:
    """Evaluate verified clause-level criteria without calculating resistance."""

    if not isinstance(member, ResolvedMember):
        raise ValidationError("member must be ResolvedMember")
    if not isinstance(context, DesignContext):
        raise ValidationError("context must be DesignContext")
    if not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod")
    if not isinstance(action, DesignAction):
        raise ValidationError("action must be DesignAction")

    checks: list[ApplicabilityCheck] = [
        _source_selection_check(member, context, method, action)
    ]
    if (
        context.standard_id != S100_24_STANDARD_ID
        or context.standard_edition != S100_24_STANDARD_EDITION
    ):
        checked = tuple(checks)
        return NormativeApplicabilityResult(
            method=method,
            action=action,
            status=aggregate_normative_status(checked),
            checks=checked,
        )
    checks.extend(_general_scope_checks(member, context, method, action))
    checks.extend(_b4_checks(member, method, action))
    if action is DesignAction.AXIAL_COMPRESSION:
        checks.extend(_compression_checks(method, action))
    elif action is DesignAction.STRONG_AXIS_FLEXURE:
        checks.extend(_flexure_checks(member, method, action))
    else:
        checks.append(_unimplemented_action_check(method, action))
    checked = tuple(checks)
    return NormativeApplicabilityResult(
        method=method,
        action=action,
        status=aggregate_normative_status(checked),
        checks=checked,
    )


__all__ = ["evaluate_normative_applicability"]
