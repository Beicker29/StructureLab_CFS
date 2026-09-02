"""Shared valid M1 domain fixtures."""

import pytest

from cfs_design.domain import (
    CatalogSection,
    DemandCombination,
    DemandPoint,
    DemandSet,
    DesignContext,
    DesignFormat,
    DesignMethod,
    GeometryConvention,
    LengthDefinition,
    Material,
    MemberCase,
    MemberGeometry,
    MemberType,
    ProjectMetadata,
    ResolvedSection,
    Restraints,
    RunMode,
    SectionFamily,
    SectionGeometry,
    SectionProperties,
)


@pytest.fixture
def material() -> Material:
    return Material(
        material_id="MAT_G50",
        designation="Grade 50",
        specification="TEST_SPEC",
        grade="G50",
        fy_mpa=345.0,
        fu_mpa=450.0,
        e_mpa=200_000.0,
        nu=0.3,
        density_kg_m3=7_850.0,
        source_id="SRC_MAT",
        active=True,
    )


@pytest.fixture
def catalog_section() -> CatalogSection:
    return CatalogSection(
        section_id="SEC_C200",
        designation="C200x70x20x2",
        family=SectionFamily.C_LIPPED,
        manufacturer="TEST_ONLY",
        geometry_id="GEO_C200",
        source_id="SRC_SEC",
        active=True,
    )


@pytest.fixture
def section_geometry() -> SectionGeometry:
    return SectionGeometry(
        geometry_id="GEO_C200",
        section_type=SectionFamily.C_LIPPED,
        h_mm=200.0,
        b1_mm=70.0,
        b2_mm=70.0,
        d1_mm=20.0,
        d2_mm=20.0,
        t_mm=2.0,
        ri_mm=2.0,
        web_flange_angle_deg=90.0,
        flange_lip_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )


@pytest.fixture
def section_properties() -> SectionProperties:
    return SectionProperties(
        section_id="SEC_C200",
        a_mm2=760.0,
        x_bar_mm=20.0,
        y_bar_mm=0.0,
        ix_mm4=4_784_000.0,
        iy_mm4=537_000.0,
        ixy_mm4=0.0,
        i1_mm4=4_784_000.0,
        i2_mm4=537_000.0,
        theta_p_deg=0.0,
        sx_pos_mm3=47_840.0,
        sx_neg_mm3=47_840.0,
        sy_pos_mm3=10_800.0,
        sy_neg_mm3=26_500.0,
        rx_mm=79.0,
        ry_mm=26.0,
        j_mm4=1_013.0,
        cw_mm6=0.0,
        x0_mm=None,
        y0_mm=None,
        property_basis="CATALOG",
        source_id="SRC_SEC",
    )


@pytest.fixture
def resolved_section(
    catalog_section: CatalogSection,
    section_geometry: SectionGeometry,
    section_properties: SectionProperties,
) -> ResolvedSection:
    return ResolvedSection(catalog_section, section_geometry, section_properties)


@pytest.fixture
def member_geometry() -> MemberGeometry:
    return MemberGeometry(
        l_mm=5_500.0,
        length_definition=LengthDefinition.K_FACTORS,
        kx=1.0,
        ky=1.0,
        kt=1.0,
        lb_mm=2_750.0,
    )


@pytest.fixture
def restraints() -> Restraints:
    return Restraints(
        x_translation_restrained=False,
        y_translation_restrained=True,
        torsion_restrained=False,
        warping_restrained=False,
        lateral_brace_spacing_mm=2_750.0,
    )


@pytest.fixture
def member(member_geometry: MemberGeometry, restraints: Restraints) -> MemberCase:
    return MemberCase(
        case_id="MEMBER_001",
        label="Test member",
        member_type=MemberType.BEAM,
        section_id="SEC_C200",
        material_id="MAT_G50",
        geometry=member_geometry,
        restraints=restraints,
        active=True,
    )


@pytest.fixture
def demand_point() -> DemandPoint:
    return DemandPoint(
        point_id="POINT_001",
        station_mm=250.0,
        p_n=-10_000.0,
        v2_n=5_000.0,
        v3_n=0.0,
        t_nmm=100_000.0,
        m2_nmm=0.0,
        m3_nmm=2_500_000.0,
        step_type="Max",
        element_id="1263",
        element_station_mm=250.0,
    )


@pytest.fixture
def demand_combination(demand_point: DemandPoint) -> DemandCombination:
    return DemandCombination(
        combination_id="COMB_001",
        case_type="Linear Static",
        points=(demand_point,),
    )


@pytest.fixture
def demand_set(demand_combination: DemandCombination) -> DemandSet:
    return DemandSet(combinations=(demand_combination,))


@pytest.fixture
def design_context() -> DesignContext:
    return DesignContext(
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        design_format=DesignFormat.LRFD,
        methods=(DesignMethod.EWM, DesignMethod.DSM),
        run_mode=RunMode.COMPARE,
        canonical_units="SI",
    )


@pytest.fixture
def project_metadata() -> ProjectMetadata:
    return ProjectMetadata(project_id="PRJ_001", name="Test project")

