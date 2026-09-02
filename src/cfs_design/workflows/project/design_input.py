"""Resolve one coherent future design-engine input without calculating strength."""

from cfs_design.core.exceptions import ValidationError
from cfs_design.design import MemberDesignInput
from cfs_design.domain import DesignMethod
from cfs_design.normative import (
    DesignAction,
    DesignExecutionPurpose,
    evaluate_design_eligibility,
)

from .models import ResolvedProject


def resolve_member_design_input(
    resolved_project: ResolvedProject,
    case_id: str,
    method: DesignMethod,
    action: DesignAction,
    purpose: DesignExecutionPurpose,
) -> MemberDesignInput:
    """Resolve references and gates only; perform no resistance calculation."""

    if not isinstance(resolved_project, ResolvedProject):
        raise ValidationError("resolved_project must be ResolvedProject")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValidationError("case_id must be a non-empty string")
    if not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod")
    if not isinstance(action, DesignAction):
        raise ValidationError("action must be DesignAction")
    if not isinstance(purpose, DesignExecutionPurpose):
        raise ValidationError("purpose must be DesignExecutionPurpose")

    member = resolved_project.get_resolved_member(case_id)
    section_id = member.section.catalog_section.section_id
    mechanics = resolved_project.require_design_mechanics(section_id)
    context = resolved_project.design_context
    dimensions = member.section.find_standard_dimensions(
        context.standard_id,
        context.standard_edition,
    )
    qualification = resolved_project.catalog_registry.find_material_qualification(
        member.material.material_id,
        context.standard_id,
        context.standard_edition,
    )
    eligibility = evaluate_design_eligibility(
        member=member,
        context=context,
        method=method,
        action=action,
        scope_evidence=resolved_project.scope_evidence,
        material_qualification=qualification,
        purpose=purpose,
    )
    return MemberDesignInput(
        resolved_member=member,
        section_mechanics=mechanics,
        standard_dimensions=dimensions,
        material_qualification=qualification,
        design_context=context,
        scope_evidence=resolved_project.scope_evidence,
        method=method,
        action=action,
        purpose=purpose,
        eligibility=eligibility,
    )


__all__ = ["resolve_member_design_input"]
