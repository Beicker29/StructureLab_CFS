"""Independent M3B sectorial, shear-center, and warping benchmarks."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cfs_design.core.exceptions import UnsupportedFeatureError, ValidationError
from cfs_design.domain import GeometryConvention, SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import (
    AdvancedPropertyMethod,
    AdvancedSectionProperties,
    CenterlineSection,
    GeometryMethod,
    Point2D,
    StraightSegment,
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
)


def _unlipped_channel() -> CenterlineSection:
    geometry = SectionGeometry(
        geometry_id="BENCHMARK_CU",
        section_type=SectionFamily.C_UNLIPPED,
        h_mm=100.0,
        b1_mm=40.0,
        b2_mm=40.0,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )
    return build_centerline_section(geometry, section_id="BENCHMARK_CU")


def _transform(
    section: CenterlineSection,
    *,
    scale: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
    mirror_x: bool = False,
) -> CenterlineSection:
    x_sign = -1.0 if mirror_x else 1.0

    def transform_point(point: Point2D) -> Point2D:
        return Point2D(
            x_sign * scale * point.x_mm + dx,
            scale * point.y_mm + dy,
        )

    return replace(
        section,
        thickness_mm=section.thickness_mm * scale,
        primitives=tuple(
            StraightSegment(
                transform_point(primitive.start),
                transform_point(primitive.end),
            )
            for primitive in section.primitives
        ),
    )


def _advanced(section: CenterlineSection) -> AdvancedSectionProperties:
    gross = compute_gross_properties(section)
    return compute_advanced_properties(section, gross)


def test_sectorial_accumulation_matches_unlipped_channel_derivation() -> None:
    result = _advanced(_unlipped_channel())
    sectorial = result.sectorial

    assert result.method is AdvancedPropertyMethod.SECTORIAL_THIN_WALL_CENTERLINE
    assert tuple(
        node.omega_centroid_raw_mm2 for node in sectorial.nodes
    ) == pytest.approx((0.0, 2000.0, 26_000.0 / 9.0, 44_000.0 / 9.0))
    assert sectorial.i_omega_x_mm5 == pytest.approx(0.0, abs=1.0e-10)
    assert sectorial.i_omega_y_mm5 == pytest.approx(-176_000_000.0 / 27.0)


def test_unlipped_channel_matches_independent_shear_center_and_cw_solution() -> None:
    result = _advanced(_unlipped_channel())

    # Hand derivation for h=100, b=40, t=1:
    # x_bar=b^2/(h+2b)=80/9; x_sc=-3b^2/(h+6b)=-240/17.
    # Thus x0=x_sc-x_bar=-3520/153. Exact segment integration gives
    # Cw=2_560_000_000/51 mm^6.
    assert result.x0_mm == pytest.approx(-3520.0 / 153.0)
    assert result.y0_mm == pytest.approx(0.0, abs=1.0e-12)
    assert result.x0_mm + 80.0 / 9.0 == pytest.approx(-240.0 / 17.0)
    assert result.cw_mm6 == pytest.approx(2_560_000_000.0 / 51.0)


def test_shear_pole_sectorial_field_is_area_mean_normalized() -> None:
    result = _advanced(_unlipped_channel())
    sectorial = result.sectorial

    assert sectorial.normalization_mean_mm2 == pytest.approx(22_000.0 / 17.0)
    assert tuple(
        node.omega_normalized_mm2 for node in sectorial.nodes
    ) == pytest.approx(
        (-22_000.0 / 17.0, 12_000.0 / 17.0, -12_000.0 / 17.0, 22_000.0 / 17.0)
    )
    assert sectorial.normalized_first_moment_mm4 == pytest.approx(
        0.0, abs=1.0e-9
    )


def test_lipped_channel_matches_independent_exact_segment_benchmark(
    lipped_centerline: CenterlineSection,
) -> None:
    result = _advanced(lipped_centerline)

    # Independent rational integration of the six contour nodes documented
    # in docs/11_SECTION_MECHANICS_M3B.md.
    assert result.x0_mm == pytest.approx(-891_310.0 / 17_043.0)
    assert result.y0_mm == pytest.approx(0.0, abs=1.0e-12)
    assert result.sectorial.i_omega_x_mm5 == pytest.approx(0.0, abs=1.0e-8)
    assert result.sectorial.i_omega_y_mm5 == pytest.approx(
        -14_260_960_000.0 / 57.0
    )
    assert result.sectorial.normalization_mean_mm2 == pytest.approx(
        5_236_000.0 / 897.0
    )
    assert result.cw_mm6 == pytest.approx(11_894_750_000_000.0 / 2691.0)


def test_single_straight_strip_uses_explicit_centroidal_degenerate_convention() -> None:
    section = CenterlineSection(
        geometry_id="STRIP",
        family=SectionFamily.C_UNLIPPED,
        thickness_mm=2.0,
        primitives=(
            StraightSegment(Point2D(-5.0, 0.0), Point2D(5.0, 0.0)),
        ),
        geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
    )

    result = _advanced(section)

    assert result.x0_mm == 0.0
    assert result.y0_mm == 0.0
    assert result.cw_mm6 == 0.0
    assert result.sectorial.inertia_determinant_mm8 == 0.0
    assert all(node.omega_normalized_mm2 == 0.0 for node in result.sectorial.nodes)


def test_other_degenerate_contours_are_rejected() -> None:
    section = CenterlineSection(
        geometry_id="DEGENERATE",
        family=SectionFamily.C_UNLIPPED,
        thickness_mm=1.0,
        primitives=(
            StraightSegment(Point2D(-10.0, 0.0), Point2D(0.0, 0.0)),
            StraightSegment(Point2D(0.0, 0.0), Point2D(10.0, 0.0)),
        ),
        geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
    )
    gross = compute_gross_properties(section)

    with pytest.raises(ValidationError, match="determinant is degenerate"):
        compute_advanced_properties(section, gross)


def test_translation_preserves_centroid_relative_advanced_properties(
    asymmetric_geometry: SectionGeometry,
) -> None:
    original = build_centerline_section(asymmetric_geometry)
    translated = _transform(original, dx=1234.5, dy=-987.25)
    first = _advanced(original)
    second = _advanced(translated)

    assert second.x0_mm == pytest.approx(first.x0_mm, rel=1.0e-12)
    assert second.y0_mm == pytest.approx(first.y0_mm, rel=1.0e-12)
    assert second.cw_mm6 == pytest.approx(first.cw_mm6, rel=1.0e-12)


def test_uniform_scaling_obeys_m3b_dimensional_exponents(
    asymmetric_geometry: SectionGeometry,
) -> None:
    factor = 3.0
    original = build_centerline_section(asymmetric_geometry)
    scaled = _transform(original, scale=factor)
    first = _advanced(original)
    second = _advanced(scaled)

    assert second.x0_mm == pytest.approx(first.x0_mm * factor)
    assert second.y0_mm == pytest.approx(first.y0_mm * factor)
    assert second.cw_mm6 == pytest.approx(first.cw_mm6 * factor**6)
    assert second.sectorial.i_omega_x_mm5 == pytest.approx(
        first.sectorial.i_omega_x_mm5 * factor**5
    )
    assert second.sectorial.i_omega_y_mm5 == pytest.approx(
        first.sectorial.i_omega_y_mm5 * factor**5
    )


def test_x_mirror_changes_x_offset_sign_and_preserves_cw(
    asymmetric_geometry: SectionGeometry,
) -> None:
    original = build_centerline_section(asymmetric_geometry)
    mirrored = _transform(original, mirror_x=True)
    first = _advanced(original)
    second = _advanced(mirrored)

    assert second.x0_mm == pytest.approx(-first.x0_mm)
    assert second.y0_mm == pytest.approx(first.y0_mm)
    assert second.cw_mm6 == pytest.approx(first.cw_mm6)


def test_equivalent_ordered_point_objects_produce_identical_result() -> None:
    original = _unlipped_channel()
    rebuilt = replace(
        original,
        primitives=tuple(
            StraightSegment(
                Point2D(item.start.x_mm, item.start.y_mm),
                Point2D(item.end.x_mm, item.end.y_mm),
            )
            for item in original.primitives
        ),
    )

    assert _advanced(rebuilt) == _advanced(original)


def test_disconnected_or_shuffled_contour_is_rejected() -> None:
    original = _unlipped_channel()
    disconnected = replace(
        original,
        primitives=(
            original.primitives[1],
            original.primitives[0],
            original.primitives[2],
        ),
    )
    gross = compute_gross_properties(disconnected)

    with pytest.raises(ValidationError, match="ordered connected"):
        compute_advanced_properties(disconnected, gross)


def test_advanced_mechanics_rejects_manually_constructed_unsupported_family() -> None:
    section = CenterlineSection(
        geometry_id="Z",
        family=SectionFamily.Z_UNLIPPED,
        thickness_mm=1.0,
        primitives=(
            StraightSegment(Point2D(-5.0, 0.0), Point2D(5.0, 0.0)),
        ),
        geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
    )
    gross = compute_gross_properties(section)

    with pytest.raises(UnsupportedFeatureError, match="section family"):
        compute_advanced_properties(section, gross)


@pytest.mark.parametrize(
    "changed",
    ({"geometry_id": "OTHER"}, {"section_id": "OTHER"}),
)
def test_advanced_mechanics_rejects_mismatched_m3a_traceability(
    lipped_centerline: CenterlineSection,
    changed: dict[str, str],
) -> None:
    gross = replace(compute_gross_properties(lipped_centerline), **changed)
    with pytest.raises(ValidationError, match="does not match"):
        compute_advanced_properties(lipped_centerline, gross)


def test_advanced_results_and_sectorial_nodes_are_immutable() -> None:
    result = _advanced(_unlipped_channel())
    with pytest.raises(FrozenInstanceError):
        result.sectorial.cw_mm6 = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.sectorial.nodes[0].omega_normalized_mm2 = 1.0  # type: ignore[misc]
