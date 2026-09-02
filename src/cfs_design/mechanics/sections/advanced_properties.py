"""Exact M3B sectorial mechanics on the canonical M3A centerline."""

from dataclasses import dataclass
from math import fsum

from cfs_design.core.exceptions import UnsupportedFeatureError, ValidationError
from cfs_design.domain import SectionFamily

from .centerline import CenterlineSection
from .models import (
    AdvancedPropertyMethod,
    AdvancedSectionProperties,
    ComputedSectionProperties,
    GeometryMethod,
    GrossPropertyMethod,
    SectorialNode,
    SectorialProperties,
)
from .numerics import RELATIVE_CLEANUP_TOLERANCE, clean_near_zero
from .primitives import Point2D


@dataclass(frozen=True, slots=True)
class _SectorialIntegral:
    area_first_mm4: float
    omega_x_mm5: float
    omega_y_mm5: float
    omega_squared_mm6: float


def _ordered_contour(section: CenterlineSection) -> tuple[Point2D, ...]:
    if section.family not in {SectionFamily.C_LIPPED, SectionFamily.C_UNLIPPED}:
        raise UnsupportedFeatureError(
            f"M3B does not support section family {section.family.value}"
        )
    if section.geometry_method is not GeometryMethod.MIDLINE_SHARP_CORNER:
        raise UnsupportedFeatureError(
            f"M3B does not support geometry method {section.geometry_method.value}"
        )
    for previous, current in zip(section.primitives, section.primitives[1:]):
        if previous.end != current.start:
            raise ValidationError(
                "CenterlineSection primitives must form one ordered connected "
                "free-edge-to-free-edge contour"
            )
    return (section.primitives[0].start,) + tuple(
        primitive.end for primitive in section.primitives
    )


def _validate_gross_result(
    section: CenterlineSection,
    gross: ComputedSectionProperties,
) -> None:
    if not isinstance(gross, ComputedSectionProperties):
        raise ValidationError("gross must be ComputedSectionProperties")
    if gross.geometry_id != section.geometry_id:
        raise ValidationError("gross geometry_id does not match CenterlineSection")
    if gross.section_id != section.section_id:
        raise ValidationError("gross section_id does not match CenterlineSection")
    if gross.method is not GrossPropertyMethod.THIN_WALL_CENTERLINE:
        raise ValidationError("gross result must use THIN_WALL_CENTERLINE")


def _centroidal_nodes(
    contour: tuple[Point2D, ...],
    gross: ComputedSectionProperties,
) -> tuple[Point2D, ...]:
    return tuple(
        Point2D(
            point.x_mm - gross.x_bar_mm,
            point.y_mm - gross.y_bar_mm,
        )
        for point in contour
    )


def _accumulate_sectorial(
    nodes: tuple[Point2D, ...],
    *,
    pole_x_mm: float,
    pole_y_mm: float,
) -> tuple[float, ...]:
    values = [0.0]
    for start, end in zip(nodes, nodes[1:]):
        xs0 = start.x_mm - pole_x_mm
        ys0 = start.y_mm - pole_y_mm
        xs1 = end.x_mm - pole_x_mm
        ys1 = end.y_mm - pole_y_mm
        increment = xs0 * ys1 - xs1 * ys0
        values.append(values[-1] + increment)
    return tuple(values)


def _linear_product_integral(
    first_start: float,
    first_end: float,
    second_start: float,
    second_end: float,
    length_mm: float,
) -> float:
    return length_mm * (
        2.0 * first_start * second_start
        + first_start * second_end
        + first_end * second_start
        + 2.0 * first_end * second_end
    ) / 6.0


def _integrate_sectorial(
    section: CenterlineSection,
    nodes: tuple[Point2D, ...],
    omega: tuple[float, ...],
) -> _SectorialIntegral:
    thickness = section.thickness_mm
    area_first_terms: list[float] = []
    omega_x_terms: list[float] = []
    omega_y_terms: list[float] = []
    omega_squared_terms: list[float] = []
    for index, primitive in enumerate(section.primitives):
        length = primitive.length_mm
        omega_start = omega[index]
        omega_end = omega[index + 1]
        area_first_terms.append(length * (omega_start + omega_end) / 2.0)
        omega_x_terms.append(
            _linear_product_integral(
                omega_start,
                omega_end,
                nodes[index].x_mm,
                nodes[index + 1].x_mm,
                length,
            )
        )
        omega_y_terms.append(
            _linear_product_integral(
                omega_start,
                omega_end,
                nodes[index].y_mm,
                nodes[index + 1].y_mm,
                length,
            )
        )
        omega_squared_terms.append(
            length
            * (
                omega_start * omega_start
                + omega_start * omega_end
                + omega_end * omega_end
            )
            / 3.0
        )
    return _SectorialIntegral(
        area_first_mm4=thickness * fsum(area_first_terms),
        omega_x_mm5=thickness * fsum(omega_x_terms),
        omega_y_mm5=thickness * fsum(omega_y_terms),
        omega_squared_mm6=thickness * fsum(omega_squared_terms),
    )


def _is_single_straight_strip(section: CenterlineSection) -> bool:
    return len(section.primitives) == 1


def compute_advanced_properties(
    section: CenterlineSection,
    gross: ComputedSectionProperties,
) -> AdvancedSectionProperties:
    """Calculate signed centroid-relative shear center and normalized ``Cw``.

    The ordered contour is consumed exactly as stored by ``CenterlineSection``.
    Gross area and inertia values are taken from the supplied M3A result.
    """

    if not isinstance(section, CenterlineSection):
        raise ValidationError("section must be a CenterlineSection")
    _validate_gross_result(section, gross)
    contour = _ordered_contour(section)
    nodes = _centroidal_nodes(contour, gross)
    omega_centroid = _accumulate_sectorial(
        nodes,
        pole_x_mm=0.0,
        pole_y_mm=0.0,
    )
    centroid_integrals = _integrate_sectorial(
        section,
        nodes,
        omega_centroid,
    )

    determinant = gross.ix_mm4 * gross.iy_mm4 - gross.ixy_mm4**2
    determinant_scale = max(
        abs(gross.ix_mm4 * gross.iy_mm4),
        gross.ixy_mm4**2,
    )
    if _is_single_straight_strip(section):
        x0 = 0.0
        y0 = 0.0
        determinant = 0.0
    elif abs(determinant) <= RELATIVE_CLEANUP_TOLERANCE * determinant_scale:
        raise ValidationError(
            "Gross inertia determinant is degenerate for shear-center calculation"
        )
    elif determinant < 0.0:
        raise ValidationError("Gross inertia determinant must be positive")
    else:
        x0 = (
            gross.iy_mm4 * centroid_integrals.omega_y_mm5
            - gross.ixy_mm4 * centroid_integrals.omega_x_mm5
        ) / determinant
        y0 = -(
            gross.ix_mm4 * centroid_integrals.omega_x_mm5
            - gross.ixy_mm4 * centroid_integrals.omega_y_mm5
        ) / determinant

    coordinate_scale = max(
        max(point.x_mm for point in nodes) - min(point.x_mm for point in nodes),
        max(point.y_mm for point in nodes) - min(point.y_mm for point in nodes),
        1.0,
    )
    x0 = clean_near_zero(x0, coordinate_scale)
    y0 = clean_near_zero(y0, coordinate_scale)
    omega_shear = _accumulate_sectorial(
        nodes,
        pole_x_mm=x0,
        pole_y_mm=y0,
    )
    shear_integrals = _integrate_sectorial(section, nodes, omega_shear)
    normalization_mean = shear_integrals.area_first_mm4 / gross.a_mm2
    omega_normalized = tuple(
        value - normalization_mean for value in omega_shear
    )
    normalized_integrals = _integrate_sectorial(
        section,
        nodes,
        omega_normalized,
    )
    sectorial_scale = max(
        coordinate_scale**2,
        max(abs(value) for value in omega_normalized),
        1.0,
    )
    normalized_first = clean_near_zero(
        normalized_integrals.area_first_mm4,
        gross.a_mm2 * sectorial_scale,
    )
    cw = normalized_integrals.omega_squared_mm6
    cw_scale = max(gross.a_mm2 * sectorial_scale**2, coordinate_scale**6, 1.0)
    if cw < -RELATIVE_CLEANUP_TOLERANCE * cw_scale:
        raise ValidationError("Calculated warping constant is materially negative")
    cw = max(clean_near_zero(cw, cw_scale), 0.0)

    sectorial_nodes = tuple(
        SectorialNode(
            node_index=index,
            x_centroid_mm=point.x_mm,
            y_centroid_mm=point.y_mm,
            omega_centroid_raw_mm2=omega_centroid[index],
            omega_shear_raw_mm2=omega_shear[index],
            omega_normalized_mm2=omega_normalized[index],
        )
        for index, point in enumerate(nodes)
    )
    return AdvancedSectionProperties(
        section_id=section.section_id,
        geometry_id=section.geometry_id,
        method=AdvancedPropertyMethod.SECTORIAL_THIN_WALL_CENTERLINE,
        sectorial=SectorialProperties(
            shear_center_offset_x_mm=x0,
            shear_center_offset_y_mm=y0,
            i_omega_x_mm5=clean_near_zero(
                centroid_integrals.omega_x_mm5,
                gross.a_mm2 * coordinate_scale**3,
            ),
            i_omega_y_mm5=clean_near_zero(
                centroid_integrals.omega_y_mm5,
                gross.a_mm2 * coordinate_scale**3,
            ),
            inertia_determinant_mm8=max(determinant, 0.0),
            normalization_mean_mm2=clean_near_zero(
                normalization_mean,
                sectorial_scale,
            ),
            normalized_first_moment_mm4=normalized_first,
            cw_mm6=cw,
            nodes=sectorial_nodes,
        ),
    )


__all__ = ["compute_advanced_properties"]
