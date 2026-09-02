"""M8A.1 S100-24 A1.1/A1.2.3 evidence semantics."""

from cfs_design.domain import (
    AISIProjectScopeEvidence,
    DesignMethod,
    EvidenceState,
    GoverningCountry,
    GoverningCountryDeclaration,
    ScopeAssertion,
    StructureApplication,
    StructureApplicationDeclaration,
)
from cfs_design.normative import DesignAction, evaluate_normative_applicability
from cfs_design.results import ApplicabilityStatus


def _evidence(
    *,
    country: GoverningCountry = GoverningCountry.UNITED_STATES,
    application: StructureApplication = StructureApplication.BUILDING,
    cold_formed: EvidenceState = EvidenceState.TRUE,
    load_carrying: EvidenceState = EvidenceState.TRUE,
    dynamic: EvidenceState = EvidenceState.UNKNOWN,
) -> AISIProjectScopeEvidence:
    return AISIProjectScopeEvidence(
        governing_country=GoverningCountryDeclaration(
            country,
            "Applicable building code and project design basis.",
        ),
        structure_application=StructureApplicationDeclaration(
            application,
            "Project structural narrative.",
        ),
        cold_formed_to_shape=ScopeAssertion(
            cold_formed,
            "Approved member procurement specification.",
        ),
        structural_load_carrying_use=ScopeAssertion(
            load_carrying,
            "Structural framing drawings.",
        ),
        dynamic_effects_addressed=ScopeAssertion(
            dynamic,
            "Project dynamic-effects design basis.",
        ),
    )


def _status(result, rule_id: str) -> ApplicabilityStatus:
    return next(
        item.status
        for item in result.checks
        if item.check_id.endswith(f"rule={rule_id}")
    )


def test_verified_project_evidence_makes_project_scope_checks_applicable(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_evidence(),
    )

    assert _status(result, "A1_1_COLD_FORMED_TO_SHAPE") is ApplicabilityStatus.APPLICABLE
    assert _status(result, "A1_1_STRUCTURAL_LOAD_CARRYING_USE") is ApplicabilityStatus.APPLICABLE
    assert _status(result, "A1_1_STRUCTURE_APPLICATION") is ApplicabilityStatus.APPLICABLE
    assert _status(result, "A1_2_3_DESIGN_FORMAT_JURISDICTION") is ApplicabilityStatus.APPLICABLE
    assert _status(result, "A1_1_QUALIFYING_STEEL_PRODUCT") is ApplicabilityStatus.INDETERMINATE
    assert result.status is ApplicabilityStatus.INDETERMINATE


def test_missing_project_evidence_remains_indeterminate_without_inference(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )

    assert _status(result, "A1_1_COLD_FORMED_TO_SHAPE") is ApplicabilityStatus.INDETERMINATE
    assert _status(result, "A1_1_STRUCTURAL_LOAD_CARRYING_USE") is ApplicabilityStatus.INDETERMINATE
    assert _status(result, "A1_2_3_DESIGN_FORMAT_JURISDICTION") is ApplicabilityStatus.INDETERMINATE


def test_explicit_failed_scope_requirement_is_not_applicable(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_evidence(cold_formed=EvidenceState.FALSE),
    )

    assert _status(result, "A1_1_COLD_FORMED_TO_SHAPE") is ApplicabilityStatus.NOT_APPLICABLE
    assert result.status is ApplicabilityStatus.NOT_APPLICABLE


def test_nonbuilding_without_dynamic_allowance_is_not_applicable(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_evidence(
            application=StructureApplication.OTHER_STRUCTURE,
            dynamic=EvidenceState.FALSE,
        ),
    )

    assert _status(result, "A1_1_STRUCTURE_APPLICATION") is ApplicabilityStatus.NOT_APPLICABLE


def test_lrfd_is_not_applicable_to_declared_canadian_route(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_evidence(country=GoverningCountry.CANADA),
    )

    assert _status(result, "A1_2_3_DESIGN_FORMAT_JURISDICTION") is ApplicabilityStatus.NOT_APPLICABLE


def test_project_evidence_basis_is_retained_in_check_observed_values(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_evidence(),
    )
    check = next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=A1_1_COLD_FORMED_TO_SHAPE")
    )

    assert {item.key: item.value for item in check.observed}["basis"] == (
        "Approved member procurement specification."
    )
