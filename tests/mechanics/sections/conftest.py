"""Shared M3A section-mechanics fixtures."""

import pytest

from cfs_design.domain import GeometryConvention, SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import (
    CenterlineSection,
    build_centerline_section,
)


@pytest.fixture
def lipped_geometry() -> SectionGeometry:
    return SectionGeometry(
        geometry_id="GEO_C200",
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


@pytest.fixture
def lipped_centerline(lipped_geometry: SectionGeometry) -> CenterlineSection:
    return build_centerline_section(lipped_geometry, section_id="SEC_C200")


@pytest.fixture
def asymmetric_geometry() -> SectionGeometry:
    return SectionGeometry(
        geometry_id="GEO_ASYMMETRIC",
        section_type=SectionFamily.C_LIPPED,
        h_mm=100.0,
        b1_mm=40.0,
        b2_mm=30.0,
        d1_mm=10.0,
        d2_mm=20.0,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        flange_lip_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )
