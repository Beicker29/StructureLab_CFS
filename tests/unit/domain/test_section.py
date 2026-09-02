"""Section identity, geometry, sourced dimensions, and aggregation tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    CatalogSection,
    ResolvedSection,
    SectionFamily,
    SectionGeometry,
    SectionProperties,
    StandardSectionDimensions,
)


def _standard_dimensions(**updates: object) -> StandardSectionDimensions:
    values: dict[str, object] = {
        "geometry_id": "GEO_C200",
        "standard_id": "ANSI_SDI_AISI_S100",
        "standard_edition": 2024,
        "web_flat_width_mm": 196.0,
        "flange_1_flat_width_mm": 66.0,
        "flange_2_flat_width_mm": 66.0,
        "web_out_to_out_depth_mm": 204.0,
        "flange_1_out_to_out_width_mm": 72.0,
        "flange_2_out_to_out_width_mm": 72.0,
        "lip_1_flat_width_mm": 16.0,
        "lip_2_flat_width_mm": 16.0,
        "lip_1_out_to_out_width_mm": 20.0,
        "lip_2_out_to_out_width_mm": 20.0,
        "lip_1_overall_depth_mm": 20.0,
        "lip_2_overall_depth_mm": 20.0,
        "source_id": "SYNTHETIC_TEST_SOURCE",
        "notes": "SYNTHETIC_TEST_DATA",
    }
    values.update(updates)
    return StandardSectionDimensions(**values)  # type: ignore[arg-type]


def test_valid_section_geometry(section_geometry: SectionGeometry) -> None:
    assert section_geometry.ri_mm == 2.0


@pytest.mark.parametrize("field_name", ("h_mm", "b1_mm"))
@pytest.mark.parametrize("value", (0.0, -1.0))
def test_nonpositive_required_geometry_dimension_is_rejected(
    section_geometry: SectionGeometry,
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_geometry, **{field_name: value})


def test_nonpositive_optional_geometry_dimension_is_rejected(
    section_geometry: SectionGeometry,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_geometry, d1_mm=0.0)


def test_invalid_thickness_is_rejected(section_geometry: SectionGeometry) -> None:
    with pytest.raises(ValidationError):
        replace(section_geometry, t_mm=0.0)


def test_negative_inside_radius_is_rejected(section_geometry: SectionGeometry) -> None:
    with pytest.raises(ValidationError):
        replace(section_geometry, ri_mm=-0.1)


@pytest.mark.parametrize("angle", (0.0, 180.0, 200.0))
def test_nonphysical_angle_is_rejected(
    section_geometry: SectionGeometry,
    angle: float,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_geometry, web_flange_angle_deg=angle)


def test_valid_section_properties(section_properties: SectionProperties) -> None:
    assert section_properties.a_mm2 == 760.0


def test_standard_dimensions_are_immutable_and_keyed() -> None:
    dimensions = _standard_dimensions()

    assert dimensions.key == ("GEO_C200", "ANSI_SDI_AISI_S100", 2024)
    assert dimensions.has_lipped_dimensions
    with pytest.raises(FrozenInstanceError):
        dimensions.web_flat_width_mm = 100.0  # type: ignore[misc]


def test_partial_lipped_standard_dimensions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="complete set"):
        _standard_dimensions(lip_2_overall_depth_mm=None)


def test_nonpositive_standard_dimension_is_rejected() -> None:
    with pytest.raises(ValidationError, match="web_flat_width_mm"):
        _standard_dimensions(web_flat_width_mm=0.0)


def test_optional_section_properties_are_accepted(
    section_properties: SectionProperties,
) -> None:
    properties = replace(
        section_properties,
        ixy_mm4=None,
        i1_mm4=None,
        i2_mm4=None,
        theta_p_deg=None,
        cw_mm6=None,
        x0_mm=None,
        y0_mm=None,
    )
    assert properties.cw_mm6 is None


@pytest.mark.parametrize("field_name", ("a_mm2", "ix_mm4", "iy_mm4"))
def test_nonpositive_area_or_inertia_is_rejected(
    section_properties: SectionProperties,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_properties, **{field_name: 0.0})


@pytest.mark.parametrize("field_name", ("rx_mm", "ry_mm"))
def test_nonpositive_radius_of_gyration_is_rejected(
    section_properties: SectionProperties,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_properties, **{field_name: -1.0})


def test_negative_optional_warping_constant_is_rejected(
    section_properties: SectionProperties,
) -> None:
    with pytest.raises(ValidationError):
        replace(section_properties, cw_mm6=-1.0)


def test_valid_resolved_section(resolved_section: ResolvedSection) -> None:
    assert resolved_section.catalog_section.section_id == "SEC_C200"


def test_resolved_section_exposes_exact_standard_dimension_lookup(
    resolved_section: ResolvedSection,
) -> None:
    dimensions = _standard_dimensions()
    resolved = replace(resolved_section, standard_dimensions=(dimensions,))

    assert resolved.find_standard_dimensions(
        "ANSI_SDI_AISI_S100", 2024
    ) is dimensions
    assert resolved.find_standard_dimensions("ANSI_SDI_AISI_S100", 2016) is None


def test_resolved_section_rejects_dimension_geometry_mismatch(
    resolved_section: ResolvedSection,
) -> None:
    with pytest.raises(ValidationError, match="geometry_id"):
        replace(
            resolved_section,
            standard_dimensions=(_standard_dimensions(geometry_id="OTHER"),),
        )


def test_mismatched_geometry_id_is_rejected(
    catalog_section: CatalogSection,
    section_geometry: SectionGeometry,
    section_properties: SectionProperties,
) -> None:
    with pytest.raises(ValidationError):
        ResolvedSection(
            catalog_section,
            replace(section_geometry, geometry_id="OTHER"),
            section_properties,
        )


def test_mismatched_properties_section_id_is_rejected(
    catalog_section: CatalogSection,
    section_geometry: SectionGeometry,
    section_properties: SectionProperties,
) -> None:
    with pytest.raises(ValidationError):
        ResolvedSection(
            catalog_section,
            section_geometry,
            replace(section_properties, section_id="OTHER"),
        )


def test_mismatched_geometry_family_is_rejected(
    catalog_section: CatalogSection,
    section_geometry: SectionGeometry,
    section_properties: SectionProperties,
) -> None:
    with pytest.raises(ValidationError):
        ResolvedSection(
            catalog_section,
            replace(section_geometry, section_type=SectionFamily.C_UNLIPPED),
            section_properties,
        )
