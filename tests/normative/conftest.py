"""Valid M7 inputs independent of Excel IO."""

from dataclasses import replace

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
    ResolvedMember,
    ResolvedSection,
    Restraints,
    RunMode,
    SectionDemandCombination,
    SectionDemandPoint,
    SectionDemandSet,
    SectionFamily,
    SectionGeometry,
    SectionProperties,
)


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
def resolved_member() -> ResolvedMember:
    section_id = "SEC_C200"
    geometry_id = "GEO_C200"
    catalog_section = CatalogSection(
        section_id=section_id,
        designation="C200x70x20x2",
        family=SectionFamily.C_LIPPED,
        manufacturer="TEST_ONLY",
        geometry_id=geometry_id,
        source_id="CATALOG_SECTION_SOURCE",
        active=True,
    )
    geometry = SectionGeometry(
        geometry_id=geometry_id,
        section_type=SectionFamily.C_LIPPED,
        h_mm=200.0,
        b1_mm=70.0,
        b2_mm=70.0,
        d1_mm=20.0,
        d2_mm=20.0,
        t_mm=2.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        flange_lip_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )
    properties = SectionProperties(
        section_id=section_id,
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
        x0_mm=0.0,
        y0_mm=0.0,
        property_basis="CATALOG",
        source_id="CATALOG_SECTION_SOURCE",
    )
    section = ResolvedSection(catalog_section, geometry, properties)
    material = Material(
        material_id="MAT_G50",
        designation="Grade 50",
        specification="TEST_COLD_FORMED_STEEL_SPEC",
        grade="G50",
        fy_mpa=345.0,
        fu_mpa=450.0,
        e_mpa=200_000.0,
        nu=0.3,
        density_kg_m3=7_850.0,
        source_id="CATALOG_MATERIAL_SOURCE",
        active=True,
    )
    member = MemberCase(
        case_id="MEMBER_001",
        label="Test beam",
        member_type=MemberType.BEAM,
        section_id=section_id,
        material_id=material.material_id,
        geometry=MemberGeometry(
            l_mm=5_500.0,
            length_definition=LengthDefinition.K_FACTORS,
            kx=1.0,
            ky=1.0,
            kt=1.0,
            lb_mm=2_750.0,
        ),
        restraints=Restraints(
            x_translation_restrained=False,
            y_translation_restrained=True,
            torsion_restrained=True,
            warping_restrained=False,
            lateral_brace_spacing_mm=2_750.0,
        ),
        active=True,
    )
    source_point = DemandPoint(
        point_id="POINT_001",
        station_mm=250.0,
        p_n=0.0,
        v2_n=0.0,
        v3_n=0.0,
        t_nmm=0.0,
        m2_nmm=2_500_000.0,
        m3_nmm=0.0,
    )
    source_demands = DemandSet(
        combinations=(
            DemandCombination(
                combination_id="COMB_001",
                case_type="Linear Static",
                points=(source_point,),
            ),
        )
    )
    section_demands = SectionDemandSet(
        combinations=(
            SectionDemandCombination(
                combination_id="COMB_001",
                case_type="Linear Static",
                points=(
                    SectionDemandPoint(
                        point_id="SECTION_POINT_001",
                        source_point_id=source_point.point_id,
                        station_mm=250.0,
                        p_n=0.0,
                        vx_n=0.0,
                        vy_n=0.0,
                        t_nmm=0.0,
                        mx_nmm=2_500_000.0,
                        my_nmm=0.0,
                    ),
                ),
            ),
        )
    )
    return ResolvedMember(
        member=member,
        section=section,
        material=material,
        demands=section_demands,
        source_demands=source_demands,
    )


@pytest.fixture
def compression_member(resolved_member: ResolvedMember) -> ResolvedMember:
    return replace(
        resolved_member,
        member=replace(resolved_member.member, member_type=MemberType.COLUMN),
    )
