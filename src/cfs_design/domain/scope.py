"""Typed project evidence used to evaluate the S100-24 general scope."""

from dataclasses import dataclass
from enum import Enum

from cfs_design.core.exceptions import ValidationError

from ._validation import require_enum, require_non_empty


class EvidenceState(str, Enum):
    """Three-state engineering assertion; UNKNOWN is not a failed condition."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class GoverningCountry(str, Enum):
    """Countries explicitly distinguished by S100-24 Section A1.2.3."""

    UNITED_STATES = "UNITED_STATES"
    MEXICO = "MEXICO"
    CANADA = "CANADA"
    UNKNOWN = "UNKNOWN"


class StructureApplication(str, Enum):
    """A1.1 application category needed for the dynamic-effects condition."""

    BUILDING = "BUILDING"
    OTHER_STRUCTURE = "OTHER_STRUCTURE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ScopeAssertion:
    """One auditable Boolean scope assertion and its stated basis."""

    state: EvidenceState
    basis: str

    def __post_init__(self) -> None:
        require_enum(self.state, EvidenceState, "state")
        require_non_empty(self.basis, "basis")


@dataclass(frozen=True, slots=True)
class GoverningCountryDeclaration:
    country: GoverningCountry
    basis: str

    def __post_init__(self) -> None:
        require_enum(self.country, GoverningCountry, "country")
        require_non_empty(self.basis, "basis")


@dataclass(frozen=True, slots=True)
class StructureApplicationDeclaration:
    application: StructureApplication
    basis: str

    def __post_init__(self) -> None:
        require_enum(self.application, StructureApplication, "application")
        require_non_empty(self.basis, "basis")


@dataclass(frozen=True, slots=True)
class AISIProjectScopeEvidence:
    """Project-wide A1.1/A1.2.3 facts that do not belong to a material row."""

    governing_country: GoverningCountryDeclaration
    structure_application: StructureApplicationDeclaration
    cold_formed_to_shape: ScopeAssertion
    structural_load_carrying_use: ScopeAssertion
    dynamic_effects_addressed: ScopeAssertion

    def __post_init__(self) -> None:
        expected = (
            ("governing_country", GoverningCountryDeclaration),
            ("structure_application", StructureApplicationDeclaration),
            ("cold_formed_to_shape", ScopeAssertion),
            ("structural_load_carrying_use", ScopeAssertion),
            ("dynamic_effects_addressed", ScopeAssertion),
        )
        for field_name, field_type in expected:
            if not isinstance(getattr(self, field_name), field_type):
                raise ValidationError(
                    f"{field_name} must be {field_type.__name__}"
                )

    @classmethod
    def unknown(cls, basis: str) -> "AISIProjectScopeEvidence":
        """Construct explicit unknown evidence for legacy/API compatibility."""

        require_non_empty(basis, "basis")
        return cls(
            governing_country=GoverningCountryDeclaration(
                country=GoverningCountry.UNKNOWN,
                basis=basis,
            ),
            structure_application=StructureApplicationDeclaration(
                application=StructureApplication.UNKNOWN,
                basis=basis,
            ),
            cold_formed_to_shape=ScopeAssertion(
                state=EvidenceState.UNKNOWN,
                basis=basis,
            ),
            structural_load_carrying_use=ScopeAssertion(
                state=EvidenceState.UNKNOWN,
                basis=basis,
            ),
            dynamic_effects_addressed=ScopeAssertion(
                state=EvidenceState.UNKNOWN,
                basis=basis,
            ),
        )


def unspecified_scope_evidence() -> AISIProjectScopeEvidence:
    """Default for callers that predate the versioned project evidence."""

    return AISIProjectScopeEvidence.unknown(
        "No project-level AISI scope evidence was supplied."
    )


__all__ = [
    "AISIProjectScopeEvidence",
    "EvidenceState",
    "GoverningCountry",
    "GoverningCountryDeclaration",
    "ScopeAssertion",
    "StructureApplication",
    "StructureApplicationDeclaration",
    "unspecified_scope_evidence",
]
