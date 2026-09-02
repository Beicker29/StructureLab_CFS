"""Normalized simultaneous demand value objects in canonical internal SI units."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_finite,
    require_non_empty,
    require_optional_finite,
    require_optional_string,
)


@dataclass(frozen=True, slots=True)
class DemandPoint:
    """One simultaneous force state after future importer normalization."""

    point_id: str
    p_n: float
    v2_n: float
    v3_n: float
    t_nmm: float
    m2_nmm: float
    m3_nmm: float
    station_mm: float | None = None
    step_type: str | None = None
    element_id: str | None = None
    element_station_mm: float | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.point_id, "point_id")
        for field_name in ("p_n", "v2_n", "v3_n", "t_nmm", "m2_nmm", "m3_nmm"):
            require_finite(getattr(self, field_name), field_name)
        require_optional_finite(self.station_mm, "station_mm")
        require_optional_finite(self.element_station_mm, "element_station_mm")
        for field_name in ("step_type", "element_id", "location"):
            require_optional_string(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class DemandCombination:
    combination_id: str
    points: tuple[DemandPoint, ...]
    case_type: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.combination_id, "combination_id")
        require_optional_string(self.case_type, "case_type")
        if not isinstance(self.points, tuple):
            raise ValidationError("points must be a tuple")
        if not self.points:
            raise ValidationError("points must contain at least one DemandPoint")
        if any(not isinstance(point, DemandPoint) for point in self.points):
            raise ValidationError("points must contain only DemandPoint objects")
        point_ids = tuple(point.point_id for point in self.points)
        if len(set(point_ids)) != len(point_ids):
            raise ValidationError("DemandPoint IDs must be unique within a combination")


@dataclass(frozen=True, slots=True)
class DemandSet:
    combinations: tuple[DemandCombination, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.combinations, tuple):
            raise ValidationError("combinations must be a tuple")
        if not self.combinations:
            raise ValidationError(
                "combinations must contain at least one DemandCombination"
            )
        if any(
            not isinstance(combination, DemandCombination)
            for combination in self.combinations
        ):
            raise ValidationError(
                "combinations must contain only DemandCombination objects"
            )
        combination_ids = tuple(
            combination.combination_id for combination in self.combinations
        )
        if len(set(combination_ids)) != len(combination_ids):
            raise ValidationError("combination IDs must be unique within a DemandSet")


__all__ = ["DemandCombination", "DemandPoint", "DemandSet"]

