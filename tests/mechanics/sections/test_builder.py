"""Canonical M3A centerline construction and support-boundary tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cfs_design.core.exceptions import UnsupportedFeatureError, ValidationError
from cfs_design.domain import GeometryConvention, SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import (
    CenterlineSection,
    GeometryMethod,
    Point2D,
    StraightSegment,
    build_centerline_section,
)


def test_lipped_midline_builds_one_connected_sharp_centerline(
    lipped_geometry: SectionGeometry,
) -> None:
    section = build_centerline_section(lipped_geometry, section_id="SEC_C200")

    assert section.geometry_method is GeometryMethod.MIDLINE_SHARP_CORNER
    assert section.section_id == "SEC_C200"
    assert section.thickness_mm == 2.0
    assert len(section.primitives) == 5
    assert sum(item.length_mm for item in section.primitives) == pytest.approx(380.0)
    assert section.primitives[0] == StraightSegment(
        Point2D(70.0, 80.0), Point2D(70.0, 100.0)
    )
    assert section.primitives[1] == StraightSegment(
        Point2D(70.0, 100.0), Point2D(0.0, 100.0)
    )
    assert section.primitives[2] == StraightSegment(
        Point2D(0.0, 100.0), Point2D(0.0, -100.0)
    )
    assert section.primitives[-1] == StraightSegment(
        Point2D(70.0, -100.0), Point2D(70.0, -80.0)
    )
    for first, second in zip(section.primitives, section.primitives[1:]):
        assert first.end == second.start


def test_unlipped_c_with_explicit_dimensions_is_supported() -> None:
    geometry = SectionGeometry(
        geometry_id="GEO_CU",
        section_type=SectionFamily.C_UNLIPPED,
        h_mm=100.0,
        b1_mm=40.0,
        b2_mm=30.0,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )

    section = build_centerline_section(geometry)

    assert section.family is SectionFamily.C_UNLIPPED
    assert len(section.primitives) == 3
    assert sum(item.length_mm for item in section.primitives) == pytest.approx(170.0)
    assert section.primitives[0].start == Point2D(40.0, 50.0)
    assert section.primitives[-1].end == Point2D(30.0, -50.0)


@pytest.mark.parametrize(
    "family",
    (
        SectionFamily.Z_LIPPED,
        SectionFamily.Z_UNLIPPED,
        SectionFamily.HAT,
        SectionFamily.TRACK,
        SectionFamily.OTHER,
    ),
)
def test_other_section_families_are_explicitly_unsupported(
    lipped_geometry: SectionGeometry,
    family: SectionFamily,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match="section family"):
        build_centerline_section(replace(lipped_geometry, section_type=family))


@pytest.mark.parametrize(
    "convention",
    (GeometryConvention.OUT_TO_OUT, GeometryConvention.FLAT_WIDTHS),
)
def test_ambiguous_dimension_conventions_are_not_reinterpreted(
    lipped_geometry: SectionGeometry,
    convention: GeometryConvention,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match=convention.value):
        build_centerline_section(
            replace(lipped_geometry, geometry_convention=convention)
        )


def test_nonzero_radius_midline_is_unsupported_until_datum_is_defined(
    lipped_geometry: SectionGeometry,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match="nonzero radius"):
        build_centerline_section(replace(lipped_geometry, ri_mm=2.0))


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("web_flange_angle_deg", 85.0, "web-flange"),
        ("flange_lip_angle_deg", 95.0, "flange-lip"),
    ),
)
def test_nonorthogonal_angles_are_not_given_an_invented_orientation(
    lipped_geometry: SectionGeometry,
    field_name: str,
    value: float,
    message: str,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match=message):
        build_centerline_section(replace(lipped_geometry, **{field_name: value}))


def test_implicit_second_flange_is_not_assumed(
    lipped_geometry: SectionGeometry,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match="explicit B2_mm"):
        build_centerline_section(replace(lipped_geometry, b2_mm=None))


def test_implicit_second_lip_is_not_assumed(
    lipped_geometry: SectionGeometry,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match="explicit D1_mm and D2_mm"):
        build_centerline_section(replace(lipped_geometry, d2_mm=None))


def test_unlipped_geometry_rejects_contradictory_lip_data() -> None:
    geometry = SectionGeometry(
        geometry_id="BAD_CU",
        section_type=SectionFamily.C_UNLIPPED,
        h_mm=100.0,
        b1_mm=40.0,
        b2_mm=40.0,
        d1_mm=10.0,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )
    with pytest.raises(ValidationError, match="must not contain lip"):
        build_centerline_section(geometry)


def test_centerline_requires_an_immutable_nonempty_primitive_tuple() -> None:
    with pytest.raises(ValidationError, match="non-empty tuple"):
        CenterlineSection(
            geometry_id="EMPTY",
            family=SectionFamily.C_UNLIPPED,
            thickness_mm=1.0,
            primitives=(),
            geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
        )


def test_primitives_and_centerline_are_immutable(
    lipped_centerline: CenterlineSection,
) -> None:
    with pytest.raises(FrozenInstanceError):
        lipped_centerline.thickness_mm = 3.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        lipped_centerline.primitives[0].start = Point2D(0.0, 0.0)  # type: ignore[misc]
