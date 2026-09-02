"""Immutable common input consumed by future EWM and DSM capacity engines."""

from dataclasses import dataclass, field

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    AISIProjectScopeEvidence,
    DesignContext,
    DesignMethod,
    ResolvedMember,
    StandardMaterialQualification,
    StandardSectionDimensions,
)
from cfs_design.mechanics.sections import ResolvedSectionMechanics
from cfs_design.normative import (
    DesignAction,
    DesignEligibility,
    DesignExecutionPurpose,
)


@dataclass(frozen=True, slots=True)
class MemberDesignInput:
    """One coherent, traceable pre-resistance design-engine input."""

    resolved_member: ResolvedMember
    section_mechanics: ResolvedSectionMechanics
    standard_dimensions: StandardSectionDimensions | None
    material_qualification: StandardMaterialQualification | None
    design_context: DesignContext
    scope_evidence: AISIProjectScopeEvidence
    method: DesignMethod
    action: DesignAction
    purpose: DesignExecutionPurpose
    eligibility: DesignEligibility
    executable: bool = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.resolved_member, ResolvedMember):
            raise ValidationError("resolved_member must be ResolvedMember")
        if not isinstance(self.section_mechanics, ResolvedSectionMechanics):
            raise ValidationError(
                "section_mechanics must be ResolvedSectionMechanics"
            )
        section = self.resolved_member.section
        section_id = section.catalog_section.section_id
        if self.section_mechanics.section_id != section_id:
            raise ValidationError(
                "section_mechanics section_id must match resolved_member"
            )
        if not self.section_mechanics.design_use_permitted:
            raise ValidationError(
                "MemberDesignInput cannot contain mechanics blocked by the QA gate"
            )
        if self.standard_dimensions is not None:
            if not isinstance(self.standard_dimensions, StandardSectionDimensions):
                raise ValidationError(
                    "standard_dimensions must be StandardSectionDimensions or None"
                )
            if self.standard_dimensions.geometry_id != section.geometry.geometry_id:
                raise ValidationError(
                    "standard_dimensions geometry_id must match resolved_member"
                )
            if (
                self.standard_dimensions.standard_id
                != self.design_context.standard_id
                or self.standard_dimensions.standard_edition
                != self.design_context.standard_edition
            ):
                raise ValidationError(
                    "standard_dimensions must match DesignContext standard"
                )
        if self.material_qualification is not None:
            if not isinstance(
                self.material_qualification, StandardMaterialQualification
            ):
                raise ValidationError(
                    "material_qualification must be "
                    "StandardMaterialQualification or None"
                )
            expected_key = (
                self.resolved_member.material.material_id,
                self.design_context.standard_id,
                self.design_context.standard_edition,
            )
            if self.material_qualification.key != expected_key:
                raise ValidationError(
                    "material_qualification key must match resolved_member and "
                    "DesignContext"
                )
        if not isinstance(self.design_context, DesignContext):
            raise ValidationError("design_context must be DesignContext")
        if not isinstance(self.scope_evidence, AISIProjectScopeEvidence):
            raise ValidationError(
                "scope_evidence must be AISIProjectScopeEvidence"
            )
        if not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod")
        if not isinstance(self.action, DesignAction):
            raise ValidationError("action must be DesignAction")
        if not isinstance(self.purpose, DesignExecutionPurpose):
            raise ValidationError("purpose must be DesignExecutionPurpose")
        if not isinstance(self.eligibility, DesignEligibility):
            raise ValidationError("eligibility must be DesignEligibility")
        if self.eligibility.normative.method is not self.method:
            raise ValidationError("eligibility method must match method")
        if self.eligibility.normative.action is not self.action:
            raise ValidationError("eligibility action must match action")
        if self.eligibility.software.purpose is not self.purpose:
            raise ValidationError("eligibility purpose must match purpose")
        object.__setattr__(self, "executable", self.eligibility.executable)


__all__ = ["MemberDesignInput"]
