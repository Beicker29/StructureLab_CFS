"""Immutable three-state S100 project scope-evidence tests."""

from dataclasses import FrozenInstanceError

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    AISIProjectScopeEvidence,
    EvidenceState,
    GoverningCountry,
    GoverningCountryDeclaration,
    ScopeAssertion,
    StructureApplication,
    StructureApplicationDeclaration,
)


def test_complete_scope_evidence_is_typed_and_preserves_provenance() -> None:
    evidence = AISIProjectScopeEvidence(
        governing_country=GoverningCountryDeclaration(
            GoverningCountry.UNITED_STATES,
            "Applicable building code and project design basis.",
        ),
        structure_application=StructureApplicationDeclaration(
            StructureApplication.BUILDING,
            "Project structural narrative.",
        ),
        cold_formed_to_shape=ScopeAssertion(
            EvidenceState.TRUE,
            "Approved member procurement specification.",
        ),
        structural_load_carrying_use=ScopeAssertion(
            EvidenceState.TRUE,
            "Structural framing drawings.",
        ),
        dynamic_effects_addressed=ScopeAssertion(
            EvidenceState.UNKNOWN,
            "Not required to resolve the declared building branch.",
        ),
    )

    assert evidence.governing_country.country is GoverningCountry.UNITED_STATES
    assert "procurement" in evidence.cold_formed_to_shape.basis
    with pytest.raises(FrozenInstanceError):
        evidence.cold_formed_to_shape.state = EvidenceState.FALSE  # type: ignore[misc]


def test_unknown_is_distinct_from_false() -> None:
    unknown = AISIProjectScopeEvidence.unknown("Legacy contract has no evidence.")

    assert unknown.cold_formed_to_shape.state is EvidenceState.UNKNOWN
    assert unknown.cold_formed_to_shape.state is not EvidenceState.FALSE
    assert unknown.governing_country.country is GoverningCountry.UNKNOWN


def test_scope_assertion_requires_nonblank_basis() -> None:
    with pytest.raises(ValidationError, match="basis"):
        ScopeAssertion(EvidenceState.TRUE, "  ")
