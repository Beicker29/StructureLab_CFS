"""Combined M7 eligibility orchestration."""

from cfs_design.domain import (
    AISIProjectScopeEvidence,
    DesignContext,
    DesignMethod,
    ResolvedMember,
)

from .applicability import evaluate_normative_applicability
from .enums import DesignAction
from .models import DesignEligibility
from .support import evaluate_software_support


def evaluate_design_eligibility(
    member: ResolvedMember,
    context: DesignContext,
    method: DesignMethod,
    action: DesignAction,
    scope_evidence: AISIProjectScopeEvidence | None = None,
) -> DesignEligibility:
    """Retain independent AISI and software conclusions in one execution gate."""

    normative = evaluate_normative_applicability(
        member=member,
        context=context,
        method=method,
        action=action,
        scope_evidence=scope_evidence,
    )
    software = evaluate_software_support(
        member=member,
        context=context,
        method=method,
        action=action,
    )
    return DesignEligibility(normative=normative, software=software)


__all__ = ["evaluate_design_eligibility"]
