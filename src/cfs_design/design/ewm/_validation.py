"""Compatibility exports for M8B numerical validation guards."""

from cfs_design.design._validation import (
    EngineeringCalculationError,
    finite,
    finite_result,
    non_negative,
    positive,
    positive_result,
    square_root,
)

EWMCalculationError = EngineeringCalculationError


__all__ = [
    "EWMCalculationError",
    "finite",
    "finite_result",
    "non_negative",
    "positive",
    "positive_result",
    "square_root",
]
