"""Conservative SectionGeometry-to-centerline conversion for M3A."""

from math import isclose

from cfs_design.core.exceptions import UnsupportedFeatureError, ValidationError
from cfs_design.domain import GeometryConvention, SectionFamily, SectionGeometry

from .centerline import CenterlineSection
from .models import GeometryMethod
from .primitives import Point2D, StraightSegment


_RIGHT_ANGLE_DEG = 90.0


def _require_explicit_second_flange(geometry: SectionGeometry) -> float:
    if geometry.b2_mm is None:
        raise UnsupportedFeatureError(
            "M3A requires explicit B2_mm; it does not infer a symmetric second "
            "flange from B1_mm"
        )
    return geometry.b2_mm


def _validate_supported_geometry(geometry: SectionGeometry) -> None:
    if not isinstance(geometry, SectionGeometry):
        raise ValidationError("geometry must be a SectionGeometry")
    if geometry.section_type not in {
        SectionFamily.C_LIPPED,
        SectionFamily.C_UNLIPPED,
    }:
        raise UnsupportedFeatureError(
            f"M3A does not support section family {geometry.section_type.value}"
        )
    if geometry.geometry_convention is not GeometryConvention.MIDLINE:
        raise UnsupportedFeatureError(
            "M3A supports only MIDLINE sharp-corner dimensions; "
            f"{geometry.geometry_convention.value} conversion is undefined"
        )
    if geometry.ri_mm != 0.0:
        raise UnsupportedFeatureError(
            "M3A MIDLINE supports only Ri_mm = 0 sharp corners; the repository "
            "does not yet define whether H/B/D with a nonzero radius terminate "
            "at vertices or bend tangent points"
        )
    if not isclose(
        geometry.web_flange_angle_deg,
        _RIGHT_ANGLE_DEG,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise UnsupportedFeatureError(
            "M3A supports only 90 degree web-flange angles because the signed "
            "orientation of other catalog angles is not yet defined"
        )
    _require_explicit_second_flange(geometry)

    if geometry.section_type is SectionFamily.C_LIPPED:
        if geometry.d1_mm is None or geometry.d2_mm is None:
            raise UnsupportedFeatureError(
                "M3A requires explicit D1_mm and D2_mm for C_LIPPED geometry; "
                "it does not infer a symmetric second lip"
            )
        if geometry.flange_lip_angle_deg is None:
            raise ValidationError(
                "C_LIPPED geometry requires flange_lip_angle_deg"
            )
        if not isclose(
            geometry.flange_lip_angle_deg,
            _RIGHT_ANGLE_DEG,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise UnsupportedFeatureError(
                "M3A supports only 90 degree flange-lip angles because the "
                "signed orientation of other catalog angles is not yet defined"
            )
    elif any(
        value is not None
        for value in (
            geometry.d1_mm,
            geometry.d2_mm,
            geometry.flange_lip_angle_deg,
        )
    ):
        raise ValidationError(
            "C_UNLIPPED geometry must not contain lip dimensions or a lip angle"
        )


def build_centerline_section(
    geometry: SectionGeometry,
    *,
    section_id: str | None = None,
) -> CenterlineSection:
    """Build the single M3A canonical geometry for an explicit sharp C section.

    MIDLINE means that H, B1, B2, D1, and D2 are the complete lengths of the
    straight centerline segments between ideal sharp intersection vertices.
    The initial datum is the midpoint of the web centerline; x points from the
    web to the flange tips and y points upward.
    """

    _validate_supported_geometry(geometry)
    if section_id is not None and (
        not isinstance(section_id, str) or not section_id.strip()
    ):
        raise ValidationError("section_id must be a non-empty string or None")

    half_height = geometry.h_mm / 2.0
    bottom_web = Point2D(0.0, -half_height)
    top_web = Point2D(0.0, half_height)
    top_flange_tip = Point2D(geometry.b1_mm, half_height)
    bottom_flange_tip = Point2D(geometry.b2_mm, -half_height)  # type: ignore[arg-type]

    primitives: list[StraightSegment] = []
    if geometry.section_type is SectionFamily.C_LIPPED:
        top_lip_tip = Point2D(
            geometry.b1_mm,
            half_height - geometry.d1_mm,  # type: ignore[operator]
        )
        bottom_lip_tip = Point2D(
            geometry.b2_mm,  # type: ignore[arg-type]
            -half_height + geometry.d2_mm,  # type: ignore[operator]
        )
        primitives.append(StraightSegment(top_lip_tip, top_flange_tip))

    primitives.extend(
        (
            StraightSegment(top_flange_tip, top_web),
            StraightSegment(top_web, bottom_web),
            StraightSegment(bottom_web, bottom_flange_tip),
        )
    )
    if geometry.section_type is SectionFamily.C_LIPPED:
        primitives.append(StraightSegment(bottom_flange_tip, bottom_lip_tip))

    return CenterlineSection(
        section_id=section_id,
        geometry_id=geometry.geometry_id,
        family=geometry.section_type,
        thickness_mm=geometry.t_mm,
        primitives=tuple(primitives),
        geometry_method=GeometryMethod.MIDLINE_SHARP_CORNER,
        metadata=(
            ("coordinate_origin", "web centerline at mid-depth"),
            ("x_direction", "web toward flange and lip tips"),
            ("y_direction", "upward"),
            ("bend_model", "ideal sharp corners; Ri_mm = 0"),
        ),
    )


__all__ = ["build_centerline_section"]
