"""Small validation primitives shared by immutable domain value objects."""

from enum import Enum
from math import isfinite
from numbers import Real
from typing import TypeVar

from cfs_design.core.exceptions import ValidationError


EnumType = TypeVar("EnumType", bound=Enum)


def require_non_empty(value: str, field_name: str) -> None:
    """Require a non-blank string without rewriting the supplied value."""

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def require_optional_string(value: str | None, field_name: str) -> None:
    """Require optional text values to be strings when supplied."""

    if value is not None and not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string or None")


def require_finite(value: float, field_name: str) -> None:
    """Reject booleans, non-numeric values, infinities, and NaN."""

    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValidationError(f"{field_name} must be a finite number")


def require_positive(value: float, field_name: str) -> None:
    require_finite(value, field_name)
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero")


def require_non_negative(value: float, field_name: str) -> None:
    require_finite(value, field_name)
    if value < 0:
        raise ValidationError(f"{field_name} must be greater than or equal to zero")


def require_optional_finite(value: float | None, field_name: str) -> None:
    if value is not None:
        require_finite(value, field_name)


def require_optional_positive(value: float | None, field_name: str) -> None:
    if value is not None:
        require_positive(value, field_name)


def require_optional_non_negative(value: float | None, field_name: str) -> None:
    if value is not None:
        require_non_negative(value, field_name)


def require_enum(value: EnumType, enum_type: type[EnumType], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise ValidationError(f"{field_name} must be a {enum_type.__name__}")


def require_bool(value: bool, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a bool")

