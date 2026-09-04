"""Controlled synthetic M8B inputs independent of Excel and ETABS."""

from dataclasses import replace

import pytest

from cfs_design.design import MemberDesignInput
from cfs_design.domain import (
    A3ElongationGroup,
    AISIProjectScopeEvidence,
    CatalogSection,
    DesignContext,
    DesignFormat,
    DesignMethod,
    EvidenceState,
    GeometryConvention,
    GoverningCountry,
    GoverningCountryDeclaration,
    LengthDefinition,
    Material,
    MaterialProductForm,
    MaterialQualificationRoute,
    MaterialQualificationState,
    MemberCase,
    MemberGeometry,
    MemberType,
    QualificationRequirementState,
    ResolvedMember,
    ResolvedSection,
    Restraints,
    RunMode,
    ScopeAssertion,
    SectionFamily,
    SectionGeometry,
    SectionProperties,
    StandardMaterialQualification,
    StandardSectionDimensions,
    SteelClassification,
    StructureApplication,
    StructureApplicationDeclaration,
)
from cfs_design.mechanics.sections import (
    ResolvedSectionMechanics,
    VerificationPolicy,
    VerificationProperty,
    VerificationStatus,
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
    verify_catalog_properties,
)
from cfs_design.normative import (
    DesignAction,
    DesignExecutionPurpose,
    evaluate_design_eligibility,
)


def _scope(*, cold_formed: EvidenceState = EvidenceState.TRUE):
    return AISIProjectScopeEvidence(
        governing_country=GoverningCountryDeclaration(
            GoverningCountry.UNITED_STATES,
            "Controlled synthetic jurisdiction evidence.",
        ),
        structure_application=StructureApplicationDeclaration(
            StructureApplication.BUILDING,
            "Controlled synthetic building classification.",
        ),
        cold_formed_to_shape=ScopeAssertion(
            cold_formed,
            "Controlled synthetic forming evidence.",
        ),
        structural_load_carrying_use=ScopeAssertion(
            EvidenceState.TRUE,
            "Controlled synthetic structural-use evidence.",
        ),
        dynamic_effects_addressed=ScopeAssertion(
            EvidenceState.UNKNOWN,
            "Not required for the selected building branch.",
        ),
    )


def _qualification(material_id: str) -> StandardMaterialQualification:
    return StandardMaterialQualification(
        material_id=material_id,
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
        mandatory_mechanical_properties_state=(
            QualificationRequirementState.SATISFIED
        ),
        test_reports_required_state=QualificationRequirementState.SATISFIED,
        chemical_mechanical_conformance_state=(
            QualificationRequirementState.NOT_APPLICABLE
        ),
        properties_determined_per_reference_state=(
            QualificationRequirementState.NOT_APPLICABLE
        ),
        coating_requirements_state=QualificationRequirementState.NOT_APPLICABLE,
        welding_requirements_state=QualificationRequirementState.NOT_APPLICABLE,
        production_identification_state=(
            QualificationRequirementState.NOT_APPLICABLE
        ),
        master_coil_10_percent_overstrength_state=(
            QualificationRequirementState.NOT_APPLICABLE
        ),
        local_elongation_percent=None,
        uniform_elongation_percent=None,
        ductility_test_standard=None,
        source_id="SYNTHETIC_A3_SOURCE",
        basis="Controlled synthetic qualification for M8B validation.",
    )


def make_design_input(
    *,
    family: SectionFamily = SectionFamily.C_UNLIPPED,
    web_mm: float = 100.0,
    flange_1_mm: float = 40.0,
    flange_2_mm: float = 40.0,
    lip_1_mm: float = 10.0,
    lip_2_mm: float = 10.0,
    length_mm: float = 2500.0,
    kx: float = 1.0,
    ky: float = 1.0,
    kt: float = 1.0,
    distortional_length_mm: float | None = None,
    include_distortional_length: bool = True,
    include_dimensions: bool = True,
    include_qualification: bool = True,
    valid_scope: bool = True,
    design_use_permitted: bool = True,
    fy_mpa: float = 345.0,
    method: DesignMethod = DesignMethod.EWM,
) -> MemberDesignInput:
    """Build an executable or deliberately blocked immutable design boundary."""

    lipped = family is SectionFamily.C_LIPPED
    section_id = "SYN_C_LIPPED" if lipped else "SYN_C_UNLIPPED"
    geometry_id = f"GEO_{section_id}"
    geometry = SectionGeometry(
        geometry_id=geometry_id,
        section_type=family,
        h_mm=web_mm,
        b1_mm=flange_1_mm,
        b2_mm=flange_2_mm,
        d1_mm=lip_1_mm if lipped else None,
        d2_mm=lip_2_mm if lipped else None,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        flange_lip_angle_deg=90.0 if lipped else None,
        geometry_convention=GeometryConvention.MIDLINE,
        notes="SYNTHETIC_TEST_DATA",
    )
    centerline = build_centerline_section(geometry, section_id=section_id)
    gross = compute_gross_properties(centerline)
    advanced = compute_advanced_properties(centerline, gross)
    catalog_section = CatalogSection(
        section_id=section_id,
        designation=section_id,
        family=family,
        manufacturer="SYNTHETIC_TEST_ONLY",
        geometry_id=geometry_id,
        source_id="SYNTHETIC_SECTION_SOURCE",
        active=True,
    )
    properties = SectionProperties(
        section_id=section_id,
        a_mm2=gross.a_mm2,
        x_bar_mm=gross.x_bar_mm,
        y_bar_mm=gross.y_bar_mm,
        ix_mm4=gross.ix_mm4,
        iy_mm4=gross.iy_mm4,
        ixy_mm4=gross.ixy_mm4,
        i1_mm4=gross.i1_mm4,
        i2_mm4=gross.i2_mm4,
        theta_p_deg=gross.theta_p_deg,
        sx_pos_mm3=gross.sx_pos_mm3,
        sx_neg_mm3=gross.sx_neg_mm3,
        sy_pos_mm3=gross.sy_pos_mm3,
        sy_neg_mm3=gross.sy_neg_mm3,
        rx_mm=gross.rx_mm,
        ry_mm=gross.ry_mm,
        j_mm4=gross.j_mm4,
        cw_mm6=advanced.cw_mm6,
        x0_mm=advanced.x0_mm,
        y0_mm=advanced.y0_mm,
        property_basis="SYNTHETIC_M3_MATCH",
        source_id="SYNTHETIC_SECTION_SOURCE",
    )
    dimensions = StandardSectionDimensions(
        geometry_id=geometry_id,
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        web_flat_width_mm=web_mm,
        flange_1_flat_width_mm=flange_1_mm,
        flange_2_flat_width_mm=flange_2_mm,
        web_out_to_out_depth_mm=web_mm if lipped else None,
        flange_1_out_to_out_width_mm=flange_1_mm if lipped else None,
        flange_2_out_to_out_width_mm=flange_2_mm if lipped else None,
        lip_1_flat_width_mm=lip_1_mm if lipped else None,
        lip_2_flat_width_mm=lip_2_mm if lipped else None,
        lip_1_out_to_out_width_mm=lip_1_mm if lipped else None,
        lip_2_out_to_out_width_mm=lip_2_mm if lipped else None,
        lip_1_overall_depth_mm=lip_1_mm if lipped else None,
        lip_2_overall_depth_mm=lip_2_mm if lipped else None,
        source_id="INDEPENDENT_SYNTHETIC_DIMENSIONS",
        notes="Values are explicit fixtures, not conversions from MIDLINE.",
    )
    resolved_section = ResolvedSection(
        catalog_section=catalog_section,
        geometry=geometry,
        properties=properties,
        standard_dimensions=(dimensions,) if include_dimensions else (),
    )
    verification = verify_catalog_properties(
        resolved_section,
        gross,
        VerificationPolicy(
            relative_tolerance=1.0e-9,
            absolute_tolerance=1.0e-9,
            properties_to_check=(VerificationProperty.A,),
        ),
        advanced,
    )
    assert verification.overall_status is VerificationStatus.PASS
    mechanics = ResolvedSectionMechanics(
        section_id=section_id,
        gross=gross,
        advanced=advanced,
        verification=verification,
        design_use_permitted=True,
        gate_reason="Controlled synthetic verification passed.",
    )
    material = Material(
        material_id="SYN_MAT_G50",
        designation="Synthetic Grade 50",
        specification="SYNTHETIC_TEST_SPECIFICATION",
        grade="G50",
        fy_mpa=fy_mpa,
        fu_mpa=max(450.0, fy_mpa),
        e_mpa=200_000.0,
        nu=0.3,
        density_kg_m3=7850.0,
        source_id="SYNTHETIC_MATERIAL_SOURCE",
        active=True,
    )
    lm = distortional_length_mm
    if lipped and include_distortional_length and lm is None:
        lm = 500.0
    restraints = Restraints(
        x_translation_restrained=False,
        y_translation_restrained=False,
        torsion_restrained=False,
        warping_restrained=False,
        distortional_unbraced_length_mm=(
            lm if lipped and include_distortional_length else None
        ),
        distortional_restraint_source=(
            "Controlled synthetic restraint schedule."
            if lipped and include_distortional_length and lm is not None
            else None
        ),
    )
    member = ResolvedMember(
        member=MemberCase(
            case_id=f"CASE_{section_id}",
            label=f"Controlled {section_id}",
            member_type=MemberType.COLUMN,
            section_id=section_id,
            material_id=material.material_id,
            geometry=MemberGeometry(
                l_mm=length_mm,
                length_definition=LengthDefinition.K_FACTORS,
                kx=kx,
                ky=ky,
                kt=kt,
            ),
            restraints=restraints,
            active=True,
        ),
        section=resolved_section,
        material=material,
    )
    run_mode = RunMode.EWM if method is DesignMethod.EWM else RunMode.DSM
    context = DesignContext(
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        design_format=DesignFormat.LRFD,
        methods=(method,),
        run_mode=run_mode,
        canonical_units="SI",
    )
    scope = _scope(
        cold_formed=EvidenceState.TRUE if valid_scope else EvidenceState.FALSE
    )
    qualification = _qualification(material.material_id)
    selected_qualification = qualification if include_qualification else None
    eligibility = evaluate_design_eligibility(
        member,
        context,
        method,
        DesignAction.AXIAL_COMPRESSION,
        scope,
        selected_qualification,
        DesignExecutionPurpose.CAPACITY,
    )
    if not design_use_permitted:
        mechanics = replace(
            mechanics,
            design_use_permitted=False,
            gate_reason="Controlled synthetic QA failure.",
        )
    return MemberDesignInput(
        resolved_member=member,
        section_mechanics=mechanics,
        standard_dimensions=dimensions if include_dimensions else None,
        material_qualification=selected_qualification,
        design_context=context,
        scope_evidence=scope,
        method=method,
        action=DesignAction.AXIAL_COMPRESSION,
        purpose=DesignExecutionPurpose.CAPACITY,
        eligibility=eligibility,
    )


@pytest.fixture
def unlipped_design_input() -> MemberDesignInput:
    return make_design_input()


@pytest.fixture
def lipped_design_input() -> MemberDesignInput:
    return make_design_input(family=SectionFamily.C_LIPPED)


@pytest.fixture
def design_input_factory():
    return make_design_input
