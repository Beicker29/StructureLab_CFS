"""Canonical unit policy and explicit IO-boundary conversions."""

from enum import Enum
from math import isfinite
from numbers import Real

from cfs_design.core.exceptions import ValidationError


class CanonicalUnitSystem(str, Enum):
    """Unit systems accepted for internal engineering-domain values."""

    SI = "SI"


class EngineeringUnit(str, Enum):
    """Controlled units for completed internal engineering values.

    These symbols describe already-normalized values.  They do not perform
    conversion or presentation formatting.  Dimensionless values use ``"1"``
    explicitly rather than an absent unit.
    """

    DIMENSIONLESS = "1"
    NEWTON = "N"
    NEWTON_MILLIMETRE = "N-mm"
    MEGAPASCAL = "MPa"
    MILLIMETRE = "mm"
    SQUARE_MILLIMETRE = "mm2"
    CUBIC_MILLIMETRE = "mm3"
    FOURTH_POWER_MILLIMETRE = "mm4"
    FIFTH_POWER_MILLIMETRE = "mm5"
    SIXTH_POWER_MILLIMETRE = "mm6"
    EIGHTH_POWER_MILLIMETRE = "mm8"
    DEGREE = "deg"
    SECOND = "s"
    KILOGRAM_PER_CUBIC_METRE = "kg/m3"


CANONICAL_UNIT_SYSTEM = CanonicalUnitSystem.SI

M_TO_MM = 1000.0
KGF_TO_N = 9.80665
KGF_M_TO_NMM = KGF_TO_N * M_TO_MM


def _finite_value(value: float, quantity: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValidationError(f"{quantity} value must be a finite number")
    return float(value)


def _normalized_unit(unit: str, quantity: str) -> str:
    if not isinstance(unit, str) or not unit.strip():
        raise ValidationError(f"{quantity} source unit must be explicit")
    return unit.strip()


def convert_length_to_mm(value: float, source_unit: str) -> float:
    """Convert an explicit supported length unit to canonical millimetres."""

    if _normalized_unit(source_unit, "length") != "m":
        raise ValidationError(f"unsupported length source unit: {source_unit!r}")
    return _finite_value(value, "length") * M_TO_MM


def convert_force_to_n(value: float, source_unit: str) -> float:
    """Convert an explicit supported force unit to canonical newtons."""

    if _normalized_unit(source_unit, "force") != "kgf":
        raise ValidationError(f"unsupported force source unit: {source_unit!r}")
    return _finite_value(value, "force") * KGF_TO_N


def convert_moment_to_nmm(value: float, source_unit: str) -> float:
    """Convert an explicit supported moment unit to canonical N-mm."""

    if _normalized_unit(source_unit, "moment") != "kgf-m":
        raise ValidationError(f"unsupported moment source unit: {source_unit!r}")
    return _finite_value(value, "moment") * KGF_M_TO_NMM


__all__ = [
    "CANONICAL_UNIT_SYSTEM",
    "KGF_M_TO_NMM",
    "KGF_TO_N",
    "M_TO_MM",
    "CanonicalUnitSystem",
    "EngineeringUnit",
    "convert_force_to_n",
    "convert_length_to_mm",
    "convert_moment_to_nmm",
]
