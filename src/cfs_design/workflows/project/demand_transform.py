"""Single authoritative ETABS-local to section-axis demand transformation."""

from math import cos, radians, sin

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    DemandPoint,
    DemandSet,
    SectionDemandCombination,
    SectionDemandPoint,
    SectionDemandSet,
)
from cfs_design.domain._validation import require_finite


def _clean_direction_cosine(value: float) -> float:
    if abs(value) <= 1.0e-15:
        return 0.0
    if abs(value - 1.0) <= 1.0e-15:
        return 1.0
    if abs(value + 1.0) <= 1.0e-15:
        return -1.0
    return value


def transform_demand_point(
    point: DemandPoint,
    orientation_deg: float,
) -> SectionDemandPoint:
    """Rotate signed transverse forces and moments into section x-y axes.

    ``orientation_deg`` is the signed rotation from ETABS local +2 toward
    section +x, positive toward ETABS local +3. Axial force and torque are
    invariant under this transverse 2D basis transformation.
    """

    if not isinstance(point, DemandPoint):
        raise ValidationError("point must be a DemandPoint")
    require_finite(orientation_deg, "orientation_deg")
    angle = radians(orientation_deg)
    cosine = _clean_direction_cosine(cos(angle))
    sine = _clean_direction_cosine(sin(angle))
    return SectionDemandPoint(
        point_id=f"SECTION-{point.point_id}",
        source_point_id=point.point_id,
        p_n=point.p_n,
        vx_n=point.v2_n * cosine + point.v3_n * sine,
        vy_n=-point.v2_n * sine + point.v3_n * cosine,
        t_nmm=point.t_nmm,
        mx_nmm=point.m2_nmm * cosine + point.m3_nmm * sine,
        my_nmm=-point.m2_nmm * sine + point.m3_nmm * cosine,
        station_mm=point.station_mm,
        step_type=point.step_type,
        element_id=point.element_id,
        element_station_mm=point.element_station_mm,
        location=point.location,
    )


def transform_demand_set(
    demands: DemandSet,
    orientation_deg: float,
) -> SectionDemandSet:
    """Transform every point one-to-one without filtering or enveloping."""

    if not isinstance(demands, DemandSet):
        raise ValidationError("demands must be a DemandSet")
    require_finite(orientation_deg, "orientation_deg")
    return SectionDemandSet(
        combinations=tuple(
            SectionDemandCombination(
                combination_id=combination.combination_id,
                case_type=combination.case_type,
                points=tuple(
                    transform_demand_point(point, orientation_deg)
                    for point in combination.points
                ),
            )
            for combination in demands.combinations
        )
    )


__all__ = ["transform_demand_point", "transform_demand_set"]
