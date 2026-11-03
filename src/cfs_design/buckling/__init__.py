"""Elastic critical loads (DC-2): analytical Appendix 2.3 in the core; finite strip (`fsm`) arrives in M8."""
from typing import Any

from ..errors import RuleNotImplementedError
from ..models import MemberInput
from ..sections import SectionProperties
from .analytical import elastic_buckling


def member_buckling(member: MemberInput, section: SectionProperties) -> dict[str, Any]:
    if member.buckling.source == "fsm":
        error = RuleNotImplementedError("finite strip buckling (fsm) is not implemented yet (milestone M8)",
                                        details={"milestone": "M8"})
        return {"source": "fsm", "error": error.to_dict()}
    return elastic_buckling(member, section)


__all__ = ["member_buckling"]
