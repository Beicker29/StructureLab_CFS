"""Independent analytical and invariance tests for M3A gross properties."""

from dataclasses import replace
from math import sqrt
from pathlib import Path

import pytest

from cfs_design.catalogs import load_section_catalog
from cfs_design.domain import SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import (
    CenterlineSection,
    GeometryMethod,
    Point2D,
    StraightSegment,
    build_centerline_section,
    compute_gross_properties,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SECTIONS_PATH = REPOSITORY_ROOT / "data" / "catalogs" / "sections_catalog.xlsx"


def _transform(
    section: CenterlineSection,
    *,
    scale: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
    mirror_x: bool = False,
) -> CenterlineSection:
    x_sign = -1.0 if mirror_x else 1.0

    def point(value: Point2D) -> Point2D:
        return Point2D(
            x_sign * scale * value.x_mm + dx,
            scale * value.y_mm + dy,
        )

    return replace(
        section,
        thickness_mm=scale * section.thickness_mm,
        primitives=tuple(
            StraightSegment(point(item.start), point(item.end))
            for item in section.primitives
        ),
    )


def test_straight_strip_matches_exact_line_integrals() -> None:
    section = CenterlineSection(
        geometry_id="STRIP",
        family=SectionFamily.C_UNLIPPED,
        thickness_mm=2.0,
        primitives=(StraightSegment(Point2D(0.0, 0.0), Point2D(10.0, 0.0)),),
        geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
    )

    result = compute_gross_properties(section)

    assert result.a_mm2 == pytest.approx(20.0)
    assert result.x_bar_mm == pytest.approx(5.0)
    assert result.y_bar_mm == pytest.approx(0.0)
    assert result.ix_mm4 == pytest.approx(0.0)
    assert result.iy_mm4 == pytest.approx(2.0 * 10.0**3 / 12.0)
    assert result.ixy_mm4 == pytest.approx(0.0)
    assert result.sx_pos_mm3 == pytest.approx(0.0)
    assert result.sx_neg_mm3 == pytest.approx(0.0)
    assert result.sy_pos_mm3 == pytest.approx(result.iy_mm4 / 5.0)
    assert result.sy_neg_mm3 == pytest.approx(result.iy_mm4 / 5.0)
    assert result.rx_mm == pytest.approx(0.0)
    assert result.ry_mm == pytest.approx(sqrt(result.iy_mm4 / 20.0))
    assert result.j_mm4 == pytest.approx(10.0 * 2.0**3 / 3.0)


def test_symmetric_lipped_c_reproduces_independent_closed_form_values(
    lipped_centerline: CenterlineSection,
) -> None:
    result = compute_gross_properties(lipped_centerline)

    assert result.a_mm2 == pytest.approx(760.0)
    assert result.x_bar_mm == pytest.approx(7700.0 / 380.0)
    assert result.y_bar_mm == pytest.approx(0.0, abs=1.0e-12)
    assert result.ix_mm4 == pytest.approx(4_784_000.0)
    assert result.iy_mm4 == pytest.approx(537_280.701754386)
    assert result.ixy_mm4 == pytest.approx(0.0, abs=1.0e-12)
    assert result.i1_mm4 == pytest.approx(result.ix_mm4)
    assert result.i2_mm4 == pytest.approx(result.iy_mm4)
    assert result.theta_p_deg == pytest.approx(0.0)
    assert result.sx_pos_mm3 == pytest.approx(47_840.0)
    assert result.sx_neg_mm3 == pytest.approx(47_840.0)
    assert result.sy_pos_mm3 == pytest.approx(10_802.4691358025)
    assert result.sy_neg_mm3 == pytest.approx(26_515.1515151515)
    assert result.rx_mm == pytest.approx(79.3393776262)
    assert result.ry_mm == pytest.approx(26.5884992390)
    assert result.j_mm4 == pytest.approx(1_013.3333333333)


def test_centroidal_properties_are_translation_invariant(
    asymmetric_geometry: SectionGeometry,
) -> None:
    original = build_centerline_section(asymmetric_geometry)
    translated = _transform(original, dx=1234.5, dy=-987.25)
    first = compute_gross_properties(original)
    second = compute_gross_properties(translated)

    assert second.x_bar_mm == pytest.approx(first.x_bar_mm + 1234.5)
    assert second.y_bar_mm == pytest.approx(first.y_bar_mm - 987.25)
    for name in ("ix_mm4", "iy_mm4", "ixy_mm4", "i1_mm4", "i2_mm4"):
        assert getattr(second, name) == pytest.approx(getattr(first, name), rel=1e-12)


def test_mirror_changes_signed_quantities_and_preserves_inertias(
    asymmetric_geometry: SectionGeometry,
) -> None:
    original = build_centerline_section(asymmetric_geometry)
    mirrored = _transform(original, mirror_x=True)
    first = compute_gross_properties(original)
    second = compute_gross_properties(mirrored)

    assert second.x_bar_mm == pytest.approx(-first.x_bar_mm)
    assert second.y_bar_mm == pytest.approx(first.y_bar_mm)
    assert second.ix_mm4 == pytest.approx(first.ix_mm4)
    assert second.iy_mm4 == pytest.approx(first.iy_mm4)
    assert second.ixy_mm4 == pytest.approx(-first.ixy_mm4)
    assert second.i1_mm4 == pytest.approx(first.i1_mm4)
    assert second.i2_mm4 == pytest.approx(first.i2_mm4)
    assert second.theta_p_deg == pytest.approx(-first.theta_p_deg)
    assert second.sy_pos_mm3 == pytest.approx(first.sy_neg_mm3)
    assert second.sy_neg_mm3 == pytest.approx(first.sy_pos_mm3)


def test_uniform_scaling_obeys_dimensional_exponents(
    asymmetric_geometry: SectionGeometry,
) -> None:
    factor = 3.0
    original = build_centerline_section(asymmetric_geometry)
    scaled = _transform(original, scale=factor)
    first = compute_gross_properties(original)
    second = compute_gross_properties(scaled)

    assert second.a_mm2 == pytest.approx(first.a_mm2 * factor**2)
    assert second.x_bar_mm == pytest.approx(first.x_bar_mm * factor)
    assert second.y_bar_mm == pytest.approx(first.y_bar_mm * factor)
    for name in ("ix_mm4", "iy_mm4", "ixy_mm4", "i1_mm4", "i2_mm4", "j_mm4"):
        assert getattr(second, name) == pytest.approx(
            getattr(first, name) * factor**4
        )
    for name in ("sx_pos_mm3", "sx_neg_mm3", "sy_pos_mm3", "sy_neg_mm3"):
        assert getattr(second, name) == pytest.approx(
            getattr(first, name) * factor**3
        )
    assert second.rx_mm == pytest.approx(first.rx_mm * factor)
    assert second.ry_mm == pytest.approx(first.ry_mm * factor)
    assert second.theta_p_deg == pytest.approx(first.theta_p_deg)


def test_principal_properties_preserve_inertia_invariants(
    asymmetric_geometry: SectionGeometry,
) -> None:
    result = compute_gross_properties(build_centerline_section(asymmetric_geometry))

    assert result.ixy_mm4 != pytest.approx(0.0)
    assert result.i1_mm4 >= result.i2_mm4
    assert result.i1_mm4 + result.i2_mm4 == pytest.approx(
        result.ix_mm4 + result.iy_mm4
    )
    assert result.i1_mm4 * result.i2_mm4 == pytest.approx(
        result.ix_mm4 * result.iy_mm4 - result.ixy_mm4**2
    )


@pytest.mark.parametrize(
    "section_id",
    ("EX_SEC_C200_70_20_2", "EX_SEC_C150_50_15_1P5"),
)
def test_approved_sharp_corner_catalog_examples_are_reproduced(
    section_id: str,
) -> None:
    resolved = load_section_catalog(SECTIONS_PATH).get_section(section_id)
    computed = compute_gross_properties(
        build_centerline_section(resolved.geometry, section_id=section_id)
    )
    catalog = resolved.properties

    for name in (
        "a_mm2",
        "x_bar_mm",
        "y_bar_mm",
        "ix_mm4",
        "iy_mm4",
        "ixy_mm4",
        "sx_pos_mm3",
        "sx_neg_mm3",
        "sy_pos_mm3",
        "sy_neg_mm3",
        "rx_mm",
        "ry_mm",
        "j_mm4",
    ):
        assert getattr(computed, name) == pytest.approx(
            getattr(catalog, name), rel=1.0e-5, abs=1.0e-8
        )
