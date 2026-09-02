"""Analytical thin-wall gross properties from the canonical centerline."""

from math import atan2, degrees, fsum, hypot, sqrt

from cfs_design.core.exceptions import ValidationError

from .centerline import CenterlineSection
from .models import (
    ComputedSectionProperties,
    ExtremeFiberMethod,
    GrossPropertyMethod,
)
from .numerics import clean_near_zero


def _section_modulus(
    inertia: float,
    distance: float,
    coordinate_scale: float,
) -> float:
    coordinate_tolerance = 1.0e-12 * max(coordinate_scale, 1.0)
    if distance > coordinate_tolerance:
        return inertia / distance
    inertia_tolerance = 1.0e-12 * max(abs(inertia), 1.0)
    if abs(inertia) <= inertia_tolerance:
        return 0.0
    raise ValidationError("Extreme-fiber distance is zero for nonzero inertia")


def _principal_properties(
    ix_mm4: float,
    iy_mm4: float,
    ixy_mm4: float,
) -> tuple[float, float, float]:
    average = (ix_mm4 + iy_mm4) / 2.0
    half_difference = (ix_mm4 - iy_mm4) / 2.0
    radius = hypot(half_difference, ixy_mm4)
    i1 = average + radius
    i2 = max(average - radius, 0.0)
    if radius <= 1.0e-12 * max(i1, 1.0):
        return i1, i2, 0.0
    theta = 0.5 * degrees(atan2(-2.0 * ixy_mm4, ix_mm4 - iy_mm4))
    if theta >= 90.0:
        theta -= 180.0
    if theta < -90.0:
        theta += 180.0
    return i1, i2, clean_near_zero(theta, 90.0)


def compute_gross_properties(
    section: CenterlineSection,
) -> ComputedSectionProperties:
    """Calculate deterministic gross properties using line integrals.

    Area and first/second moments use ``dA = t ds``. Local plate ``t^3``
    inertia is omitted consistently with the approved sharp-corner catalog
    examples. The centerline endpoints define extreme fibers. For open uniform
    thin walls, ``J = sum(L * t^3 / 3)``.
    """

    if not isinstance(section, CenterlineSection):
        raise ValidationError("section must be a CenterlineSection")
    thickness = section.thickness_mm
    origin_integrals = tuple(
        primitive.line_integrals() for primitive in section.primitives
    )
    total_length = fsum(item.length_mm for item in origin_integrals)
    if total_length <= 0.0:
        raise ValidationError("CenterlineSection is degenerate")
    area = thickness * total_length
    x_bar = fsum(item.first_x_mm2 for item in origin_integrals) / total_length
    y_bar = fsum(item.first_y_mm2 for item in origin_integrals) / total_length

    centroidal = tuple(
        primitive.line_integrals(datum_x_mm=x_bar, datum_y_mm=y_bar)
        for primitive in section.primitives
    )
    ix = thickness * fsum(item.second_y_mm3 for item in centroidal)
    iy = thickness * fsum(item.second_x_mm3 for item in centroidal)
    ixy = thickness * fsum(item.product_xy_mm3 for item in centroidal)
    inertia_scale = max(ix, iy, 1.0)
    ix = clean_near_zero(ix, inertia_scale)
    iy = clean_near_zero(iy, inertia_scale)
    ixy = clean_near_zero(ixy, inertia_scale)
    if ix < 0.0 or iy < 0.0:
        raise ValidationError("Calculated second moment is negative")

    x_coordinates = tuple(
        point
        for primitive in section.primitives
        for point in (primitive.start.x_mm, primitive.end.x_mm)
    )
    y_coordinates = tuple(
        point
        for primitive in section.primitives
        for point in (primitive.start.y_mm, primitive.end.y_mm)
    )
    x_pos = max(x_coordinates) - x_bar
    x_neg = x_bar - min(x_coordinates)
    y_pos = max(y_coordinates) - y_bar
    y_neg = y_bar - min(y_coordinates)
    coordinate_scale = max(
        max(x_coordinates) - min(x_coordinates),
        max(y_coordinates) - min(y_coordinates),
        1.0,
    )

    i1, i2, theta = _principal_properties(ix, iy, ixy)
    return ComputedSectionProperties(
        section_id=section.section_id,
        geometry_id=section.geometry_id,
        method=GrossPropertyMethod.THIN_WALL_CENTERLINE,
        extreme_fiber_method=ExtremeFiberMethod.CENTERLINE_EXTENTS,
        a_mm2=area,
        x_bar_mm=x_bar,
        y_bar_mm=clean_near_zero(y_bar, coordinate_scale),
        ix_mm4=ix,
        iy_mm4=iy,
        ixy_mm4=ixy,
        i1_mm4=i1,
        i2_mm4=i2,
        theta_p_deg=theta,
        sx_pos_mm3=_section_modulus(ix, y_pos, coordinate_scale),
        sx_neg_mm3=_section_modulus(ix, y_neg, coordinate_scale),
        sy_pos_mm3=_section_modulus(iy, x_pos, coordinate_scale),
        sy_neg_mm3=_section_modulus(iy, x_neg, coordinate_scale),
        rx_mm=sqrt(ix / area),
        ry_mm=sqrt(iy / area),
        j_mm4=total_length * thickness**3 / 3.0,
    )


__all__ = ["compute_gross_properties"]
