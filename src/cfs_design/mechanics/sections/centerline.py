"""Canonical immutable centerline representation shared by future mechanics."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import SectionFamily

from .models import GeometryMethod
from .primitives import StraightSegment


@dataclass(frozen=True, slots=True)
class CenterlineSection:
    """One authoritative mechanical geometry derived from SectionGeometry."""

    geometry_id: str
    family: SectionFamily
    thickness_mm: float
    primitives: tuple[StraightSegment, ...]
    geometry_method: GeometryMethod
    section_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.geometry_id, str) or not self.geometry_id.strip():
            raise ValidationError("geometry_id must be a non-empty string")
        if self.section_id is not None and (
            not isinstance(self.section_id, str) or not self.section_id.strip()
        ):
            raise ValidationError("section_id must be a non-empty string or None")
        if not isinstance(self.family, SectionFamily):
            raise ValidationError("family must be a SectionFamily")
        if (
            isinstance(self.thickness_mm, bool)
            or not isinstance(self.thickness_mm, Real)
            or not isfinite(self.thickness_mm)
        ):
            raise ValidationError("thickness_mm must be a finite positive number")
        if self.thickness_mm <= 0.0:
            raise ValidationError("thickness_mm must be greater than zero")
        if not isinstance(self.primitives, tuple) or not self.primitives:
            raise ValidationError("primitives must be a non-empty tuple")
        if any(not isinstance(item, StraightSegment) for item in self.primitives):
            raise ValidationError("M3A primitives must be StraightSegment values")
        if not isinstance(self.geometry_method, GeometryMethod):
            raise ValidationError("geometry_method must be a GeometryMethod")
        if not isinstance(self.metadata, tuple):
            raise ValidationError("metadata must be a tuple")
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
            for item in self.metadata
        ):
            raise ValidationError("metadata entries must be (str, str) tuples")


__all__ = ["CenterlineSection"]
