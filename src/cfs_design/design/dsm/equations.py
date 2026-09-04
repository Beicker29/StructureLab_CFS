"""ANSI/SDI AISI S100-24 DSM axial-compression equations."""

from math import isfinite, sqrt
from numbers import Real

from cfs_design.core.exceptions import ValidationError

from .models import (
    DSMDistortionalBranch,
    DSMDistortionalStrengthResult,
    DSMGoverningLimitState,
    DSMLocalBranch,
    DSMLocalStrengthResult,
)


DSM_MAX_SLENDERNESS = 5.0
LOCAL_UPPER_BOUND_TRANSITION = sqrt(20.0 / 43.0)
DISTORTIONAL_UPPER_BOUND_TRANSITION = sqrt(20.0 / 61.0)


class DSMCalculationError(ValidationError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _positive(value: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(value)
        or value <= 0.0
    ):
        raise DSMCalculationError(
            "DSM_INVALID_POSITIVE_INPUT",
            f"{name} must be a finite number greater than zero",
        )
    return float(value)


def calculate_dsm_local_strength(
    *, p_ne_n: float, p_crl_n: float
) -> DSMLocalStrengthResult:
    """Apply S100-24 Eqs. E3.2-1 and E3.2-2 for the no-hole scope."""

    p_ne = _positive(p_ne_n, "Pne")
    p_crl = _positive(p_crl_n, "Pcrl")
    lambda_l = sqrt(p_ne / p_crl)
    if lambda_l > DSM_MAX_SLENDERNESS:
        raise DSMCalculationError(
            "DSM_E3_2_SLENDERNESS_UNSUPPORTED",
            "S100-24 E3.2-1 is specified for local slenderness not greater than 5",
        )
    if lambda_l <= LOCAL_UPPER_BOUND_TRANSITION:
        p_nl = p_ne
        branch = DSMLocalBranch.PNE_UPPER_BOUND
    else:
        squared = lambda_l * lambda_l
        p_nl = 1.2 * (1.0 + 0.10 * squared) / (1.0 + 0.55 * squared) * p_ne
        branch = DSMLocalBranch.LOCAL_REDUCTION
    if not isfinite(p_nl) or p_nl <= 0.0 or p_nl > p_ne:
        raise DSMCalculationError(
            "DSM_E3_2_EQUATION_DOMAIN_ERROR",
            "E3.2 nominal local strength must be positive and not exceed Pne",
        )
    return DSMLocalStrengthResult(
        lambda_l=lambda_l,
        p_nl_n=p_nl,
        branch=branch,
    )


def calculate_dsm_distortional_strength(
    *, p_y_n: float, p_crd_n: float
) -> DSMDistortionalStrengthResult:
    """Apply S100-24 Eqs. E4-1 through E4-3 for the no-hole scope."""

    p_y = _positive(p_y_n, "Py")
    p_crd = _positive(p_crd_n, "Pcrd")
    lambda_d = sqrt(p_y / p_crd)
    if lambda_d > DSM_MAX_SLENDERNESS:
        raise DSMCalculationError(
            "DSM_E4_SLENDERNESS_UNSUPPORTED",
            "S100-24 E4-1 is specified for distortional slenderness not greater than 5",
        )
    if lambda_d <= DISTORTIONAL_UPPER_BOUND_TRANSITION:
        p_nd = p_y
        branch = DSMDistortionalBranch.PY_UPPER_BOUND
    else:
        squared = lambda_d * lambda_d
        p_nd = 1.2 * (1.0 + 0.05 * squared) / (1.0 + 0.67 * squared) * p_y
        branch = DSMDistortionalBranch.DISTORTIONAL_REDUCTION
    if not isfinite(p_nd) or p_nd <= 0.0 or p_nd > p_y:
        raise DSMCalculationError(
            "DSM_E4_EQUATION_DOMAIN_ERROR",
            "E4 nominal distortional strength must be positive and not exceed Py",
        )
    return DSMDistortionalStrengthResult(
        lambda_d=lambda_d,
        p_nd_n=p_nd,
        branch=branch,
    )


def select_dsm_nominal_strength(
    *, p_nl_n: float, p_nd_n: float | None
) -> tuple[float, DSMGoverningLimitState]:
    """Apply S100-24 E1: select the smallest applicable nominal strength."""

    p_nl = _positive(p_nl_n, "Pnl")
    if p_nd_n is None:
        return p_nl, DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION
    p_nd = _positive(p_nd_n, "Pnd")
    if p_nl <= p_nd:
        return p_nl, DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION
    return p_nd, DSMGoverningLimitState.DISTORTIONAL


__all__ = [
    "DISTORTIONAL_UPPER_BOUND_TRANSITION",
    "DSMCalculationError",
    "DSM_MAX_SLENDERNESS",
    "LOCAL_UPPER_BOUND_TRANSITION",
    "calculate_dsm_distortional_strength",
    "calculate_dsm_local_strength",
    "select_dsm_nominal_strength",
]
