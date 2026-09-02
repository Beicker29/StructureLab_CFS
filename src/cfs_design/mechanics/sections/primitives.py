"""Immutable analytical primitives for canonical section centerlines."""

from dataclasses import dataclass
from math import hypot, isfinite
from numbers import Real

from cfs_design.core.exceptions import ValidationError


def _require_finite(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValidationError(f"{field_name} must be a finite number")


@dataclass(frozen=True, slots=True)
class Point2D:
    """Point in the local section x-y plane, in millimetres."""

    x_mm: float
    y_mm: float

    def __post_init__(self) -> None:
        _require_finite(self.x_mm, "x_mm")
        _require_finite(self.y_mm, "y_mm")


@dataclass(frozen=True, slots=True)
class LineIntegralContribution:
    """Exact integrals along a centerline segment relative to a datum.

    The fields contain ``integral(ds)``, ``integral(x ds)``,
    ``integral(y ds)``, ``integral(x^2 ds)``, ``integral(y^2 ds)``, and
    ``integral(x y ds)`` respectively. Thickness is applied once by the gross
    property engine, not stored on each primitive.
    """

    length_mm: float
    first_x_mm2: float
    first_y_mm2: float
    second_x_mm3: float
    second_y_mm3: float
    product_xy_mm3: float


@dataclass(frozen=True, slots=True)
class StraightSegment:
    """A non-zero straight centerline segment between two local points."""

    start: Point2D
    end: Point2D

    def __post_init__(self) -> None:
        if not isinstance(self.start, Point2D) or not isinstance(self.end, Point2D):
            raise ValidationError("StraightSegment endpoints must be Point2D values")
        if self.length_mm <= 0.0:
            raise ValidationError("StraightSegment length must be greater than zero")

    @property
    def length_mm(self) -> float:
        return hypot(
            self.end.x_mm - self.start.x_mm,
            self.end.y_mm - self.start.y_mm,
        )

    def line_integrals(
        self,
        *,
        datum_x_mm: float = 0.0,
        datum_y_mm: float = 0.0,
    ) -> LineIntegralContribution:
        """Return exact polynomial line integrals relative to ``datum``."""

        _require_finite(datum_x_mm, "datum_x_mm")
        _require_finite(datum_y_mm, "datum_y_mm")
        x0 = self.start.x_mm - datum_x_mm
        y0 = self.start.y_mm - datum_y_mm
        x1 = self.end.x_mm - datum_x_mm
        y1 = self.end.y_mm - datum_y_mm
        length = self.length_mm
        return LineIntegralContribution(
            length_mm=length,
            first_x_mm2=length * (x0 + x1) / 2.0,
            first_y_mm2=length * (y0 + y1) / 2.0,
            second_x_mm3=length * (x0 * x0 + x0 * x1 + x1 * x1) / 3.0,
            second_y_mm3=length * (y0 * y0 + y0 * y1 + y1 * y1) / 3.0,
            product_xy_mm3=length
            * (2.0 * x0 * y0 + x0 * y1 + x1 * y0 + 2.0 * x1 * y1)
            / 6.0,
        )


__all__ = ["LineIntegralContribution", "Point2D", "StraightSegment"]
