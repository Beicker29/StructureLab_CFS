"""Numerical guards shared by normative design calculations."""

from math import isfinite, sqrt
from numbers import Real

from cfs_design.core.exceptions import ValidationError


class EngineeringCalculationError(ValidationError):
    """A deterministic engineering calculation failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise EngineeringCalculationError(
            "EWM_NONFINITE_VALUE", f"{name} must be a finite number"
        )
    return float(value)


def positive(value: float, name: str) -> float:
    checked = finite(value, name)
    if checked <= 0.0:
        raise EngineeringCalculationError(
            "EWM_INVALID_POSITIVE_INPUT", f"{name} must be greater than zero"
        )
    return checked


def non_negative(value: float, name: str) -> float:
    checked = finite(value, name)
    if checked < 0.0:
        raise EngineeringCalculationError(
            "EWM_INVALID_NON_NEGATIVE_INPUT",
            f"{name} must be greater than or equal to zero",
        )
    return checked


def finite_result(value: float, name: str) -> float:
    return finite(value, name)


def positive_result(value: float, name: str) -> float:
    checked = finite_result(value, name)
    if checked <= 0.0:
        raise EngineeringCalculationError(
            "EWM_EQUATION_DOMAIN_ERROR",
            f"{name} must be positive after calculation",
        )
    return checked


def square_root(value: float, name: str) -> float:
    checked = finite_result(value, name)
    if checked < 0.0:
        raise EngineeringCalculationError(
            "EWM_EQUATION_DOMAIN_ERROR",
            f"{name} is negative inside a square root",
        )
    return finite_result(sqrt(checked), f"sqrt({name})")


__all__ = [
    "EngineeringCalculationError",
    "finite",
    "finite_result",
    "non_negative",
    "positive",
    "positive_result",
    "square_root",
]
