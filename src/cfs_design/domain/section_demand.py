"""Demand states resolved from ETABS local axes into section x-y axes."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_finite,
    require_non_empty,
    require_optional_finite,
    require_optional_string,
)


@dataclass(frozen=True, slots=True)
class SectionDemandPoint:
    """One signed demand state expressed in the resolved section axes."""

    point_id: str
    source_point_id: str
    p_n: float
    vx_n: float
    vy_n: float
    t_nmm: float
    mx_nmm: float
    my_nmm: float
    station_mm: float | None = None
    step_type: str | None = None
    element_id: str | None = None
    element_station_mm: float | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.point_id, "point_id")
        require_non_empty(self.source_point_id, "source_point_id")
        for field_name in (
            "p_n",
            "vx_n",
            "vy_n",
            "t_nmm",
            "mx_nmm",
            "my_nmm",
        ):
            require_finite(getattr(self, field_name), field_name)
        require_optional_finite(self.station_mm, "station_mm")
        require_optional_finite(self.element_station_mm, "element_station_mm")
        for field_name in ("step_type", "element_id", "location"):
            require_optional_string(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class SectionDemandCombination:
    combination_id: str
    points: tuple[SectionDemandPoint, ...]
    case_type: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.combination_id, "combination_id")
        require_optional_string(self.case_type, "case_type")
        if not isinstance(self.points, tuple) or not self.points:
            raise ValidationError(
                "points must be a non-empty tuple of SectionDemandPoint"
            )
        if any(not isinstance(point, SectionDemandPoint) for point in self.points):
            raise ValidationError("points must contain only SectionDemandPoint")
        point_ids = tuple(point.point_id for point in self.points)
        if len(set(point_ids)) != len(point_ids):
            raise ValidationError(
                "SectionDemandPoint IDs must be unique within a combination"
            )
        source_ids = tuple(point.source_point_id for point in self.points)
        if len(set(source_ids)) != len(source_ids):
            raise ValidationError(
                "source DemandPoint IDs must be unique within a combination"
            )


@dataclass(frozen=True, slots=True)
class SectionDemandSet:
    combinations: tuple[SectionDemandCombination, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.combinations, tuple) or not self.combinations:
            raise ValidationError(
                "combinations must be a non-empty tuple of SectionDemandCombination"
            )
        if any(
            not isinstance(combination, SectionDemandCombination)
            for combination in self.combinations
        ):
            raise ValidationError(
                "combinations must contain only SectionDemandCombination"
            )
        identifiers = tuple(item.combination_id for item in self.combinations)
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError(
                "combination IDs must be unique within a SectionDemandSet"
            )


__all__ = [
    "SectionDemandCombination",
    "SectionDemandPoint",
    "SectionDemandSet",
]
