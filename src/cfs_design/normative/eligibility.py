"""Combined M7 eligibility orchestration."""

from cfs_design.domain import (
    AISIProjectScopeEvidence,
    DesignContext,
    DesignMethod,
    ResolvedMember,
    StandardMaterialQualification,
)

from .applicability import evaluate_normative_applicability
from .enums import DesignAction, DesignExecutionPurpose
from .models import DesignEligibility
from .support import evaluate_software_support


def evaluate_design_eligibility(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
    scope_evidence: AISIProjectScopeEvidence | None = None,
    material_qualification: StandardMaterialQualification | None = None,
    purpose: DesignExecutionPurpose = DesignExecutionPurpose.DEMAND_CHECK,
) -> DesignEligibility:
    """Retain independent AISI and software conclusions in one execution gate."""

    normative = evaluate_normative_applicability(
        member=member,
        context=context,
        method=method,
        action=action,
        scope_evidence=scope_evidence,
        material_qualification=material_qualification,
    )
    software = evaluate_software_support(
        member=member,
        context=context,
        method=method,
        action=action,
        purpose=purpose,
    )
    return DesignEligibility(normative=normative, software=software)


__all__ = ["evaluate_design_eligibility"]
