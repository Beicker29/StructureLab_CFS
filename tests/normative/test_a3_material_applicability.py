"""M8A.2 material-specific A3 applicability behavior tests."""

from dataclasses import replace

from cfs_design.domain import (
    A3ElongationGroup,
    AISIProjectScopeEvidence,
    DesignMethod,
    EvidenceState,
    GoverningCountry,
    GoverningCountryDeclaration,
    MaterialProductForm,
    MaterialQualificationRoute,
    MaterialQualificationState,
    QualificationRequirementState,
    ScopeAssertion,
    StandardMaterialQualification,
    SteelClassification,
    StructureApplication,
    StructureApplicationDeclaration,
)
from cfs_design.normative import DesignAction, evaluate_normative_applicability
from cfs_design.results import ApplicabilityStatus


def _scope() -> AISIProjectScopeEvidence:
    return AISIProjectScopeEvidence(
        governing_country=GoverningCountryDeclaration(
            GoverningCountry.UNITED_STATES, "Synthetic jurisdiction evidence."
        ),
        structure_application=StructureApplicationDeclaration(
            StructureApplication.BUILDING, "Synthetic building classification."
        ),
        cold_formed_to_shape=ScopeAssertion(
            EvidenceState.TRUE, "Synthetic forming evidence."
        ),
        structural_load_carrying_use=ScopeAssertion(
            EvidenceState.TRUE, "Synthetic structural-use evidence."
        ),
        dynamic_effects_addressed=ScopeAssertion(
            EvidenceState.UNKNOWN, "Not required for the building branch."
        ),
    )


def _qualification(member, **updates: object) -> StandardMaterialQualification:
    qualification = StandardMaterialQualification(
        material_id=member.material.material_id,
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        qualification_route=MaterialQualificationRoute.A3_1,
        qualification_state=MaterialQualificationState.QUALIFIED,
        product_form=MaterialProductForm.SHEET,
        steel_classification=SteelClassification.CARBON,
        elongation_group=A3ElongationGroup.A3_1_1_GE_10,
        minimum_elongation_percent=10.0,
        elongation_gauge_length_mm=50.0,
        elongation_test_standard="ASTM_A370",
        mandatory_mechanical_properties_state=QualificationRequirementState.SATISFIED,
        test_reports_required_state=QualificationRequirementState.SATISFIED,
        chemical_mechanical_conformance_state=QualificationRequirementState.NOT_APPLICABLE,
        properties_determined_per_reference_state=QualificationRequirementState.NOT_APPLICABLE,
        coating_requirements_state=QualificationRequirementState.NOT_APPLICABLE,
        welding_requirements_state=QualificationRequirementState.NOT_APPLICABLE,
        production_identification_state=QualificationRequirementState.NOT_APPLICABLE,
        master_coil_10_percent_overstrength_state=QualificationRequirementState.NOT_APPLICABLE,
        local_elongation_percent=None,
        uniform_elongation_percent=None,
        ductility_test_standard=None,
        source_id="SYNTHETIC_A3_SOURCE",
        basis="Synthetic A3 evidence for applicability tests.",
    )
    return replace(qualification, **updates)


def _material_check(result):
    return next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=A1_1_QUALIFYING_STEEL_PRODUCT")
    )


def test_qualified_material_makes_a3_check_applicable(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_scope(),
        material_qualification=_qualification(compression_member),
    )

    assert _material_check(result).status is ApplicabilityStatus.APPLICABLE


def test_explicitly_unqualified_material_is_not_applicable(
    compression_member,
    design_context,
) -> None:
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_scope(),
        material_qualification=_qualification(
            compression_member,
            qualification_state=MaterialQualificationState.NOT_QUALIFIED,
        ),
    )

    assert _material_check(result).status is ApplicabilityStatus.NOT_APPLICABLE


def test_missing_qualification_remains_indeterminate_without_spec_inference(
    compression_member,
    design_context,
) -> None:
    familiar_text = replace(
        compression_member,
        material=replace(
            compression_member.material,
            specification="ASTM A653/A653M",
            grade="SS Grade 50",
        ),
    )
    result = evaluate_normative_applicability(
        familiar_text,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_scope(),
    )

    check = _material_check(result)
    assert check.status is ApplicabilityStatus.INDETERMINATE
    assert check.diagnostic is not None
    assert check.diagnostic.code == "AISI_MATERIAL_QUALIFICATION_MISSING"


def test_a3_1_3_is_not_applicable_to_single_web_c_member(
    compression_member,
    design_context,
) -> None:
    qualification = _qualification(
        compression_member,
        elongation_group=A3ElongationGroup.A3_1_3_LT_3,
        minimum_elongation_percent=2.0,
    )
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_scope(),
        material_qualification=qualification,
    )

    assert _material_check(result).status is ApplicabilityStatus.NOT_APPLICABLE


def test_a3_2_1_member_use_stays_indeterminate_without_new_member_field(
    compression_member,
    design_context,
) -> None:
    qualification = _qualification(
        compression_member,
        qualification_route=MaterialQualificationRoute.A3_2,
        elongation_group=A3ElongationGroup.A3_2_1_ALTERNATIVE_DUCTILITY,
        minimum_elongation_percent=None,
        elongation_gauge_length_mm=None,
        elongation_test_standard=None,
        mandatory_mechanical_properties_state=QualificationRequirementState.NOT_APPLICABLE,
        test_reports_required_state=QualificationRequirementState.NOT_APPLICABLE,
        chemical_mechanical_conformance_state=QualificationRequirementState.SATISFIED,
        properties_determined_per_reference_state=QualificationRequirementState.SATISFIED,
        production_identification_state=QualificationRequirementState.SATISFIED,
        local_elongation_percent=20.0,
        uniform_elongation_percent=3.0,
        ductility_test_standard="ANSI_SDI_AISI_S903",
    )
    result = evaluate_normative_applicability(
        compression_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
        scope_evidence=_scope(),
        material_qualification=qualification,
    )

    assert _material_check(result).status is ApplicabilityStatus.INDETERMINATE
