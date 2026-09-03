"""Controlled normative interpretations authorized for M8B."""

from dataclasses import dataclass
from enum import Enum


class InterpretationStatus(str, Enum):
    CONTROLLED_ENGINEERING_INTERPRETATION = (
        "CONTROLLED_ENGINEERING_INTERPRETATION"
    )


@dataclass(frozen=True, slots=True)
class ControlledNormativeInterpretation:
    interpretation_id: str
    status: InterpretationStatus
    published_reference: str
    interpreted_reference: str
    technical_rationale: str
    corroborating_reference: str
    applicable_section_type: str
    restriction: str
    project: str
    decision_date: str
    supersession_rule: str


S10024_A1_1_3A_XREF_001 = ControlledNormativeInterpretation(
    interpretation_id="S10024-A1-1_3A-XREF-001",
    status=InterpretationStatus.CONTROLLED_ENGINEERING_INTERPRETATION,
    published_reference=(
        "S100-24 Appendix 1 Section 1.3(a) cites Section 1.1.1 for b in "
        "Eqs. 1.3-4 and 1.3-5."
    ),
    interpreted_reference=(
        "Appendix 1 Section 1.1(a), Eqs. 1.1-1 through 1.1-4, with k from "
        "Section 1.3 and Table 1.3-1."
    ),
    technical_rationale=(
        "Section 1.1.1 is the perforated-element route and requires hole data "
        "that is absent by design in the approved no-hole scope."
    ),
    corroborating_reference=(
        "Appendix 1 Section 1.1.4 reuses Eqs. 1.3-4 and 1.3-5 and directs "
        "the corresponding effective-width calculation to Section 1.1(a)."
    ),
    applicable_section_type="C_LIPPED_SIMPLE_LIP_NO_HOLES",
    restriction="Must not be applied to any section or element with holes.",
    project="StructureLab_CFS",
    decision_date="2026-09-02",
    supersession_rule=(
        "An official AISI correction supersedes this interpretation and "
        "requires review of the related regression tests."
    ),
)


__all__ = [
    "ControlledNormativeInterpretation",
    "InterpretationStatus",
    "S10024_A1_1_3A_XREF_001",
]
