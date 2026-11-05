"""AISI S100-24 Chapter E, Members in Compression (pp. 43-47), LRFD. Units: N, mm, MPa (any consistent force unit).

Transcribed from the 2024 edition; Eqs. E3.2-1 and E4-1 differ from earlier editions.
Not here: E2.1 (closed-box), E3.1 (EWM, milestone M7), E3.3 (cylindrical tubes), members with holes.
"""
import math

PHI_C = 0.85
"""E2, E3, E4 (pp. 43, 44, 46): resistance factor φc, LRFD."""

LAMBDA_DSM_MAX = 5.0
"""E3.2 (p. 45) and E4 (p. 46): DSM equations apply for λℓ ≤ 5 and λd ≤ 5."""


def lambda_c(fy: float, fcre: float) -> float:
    """Eq. E2-4, p. 43: λc = √(Fy/Fcre)."""
    return math.sqrt(fy / fcre)


def fn_global(fy: float, lam_c: float) -> float:
    """Eqs. E2-2 and E2-3, p. 43: Fn = 0.658^(λc²) Fy for λc ≤ 1.5; Fn = (0.877/λc²) Fy for λc > 1.5."""
    if lam_c <= 1.5:
        return 0.658 ** (lam_c**2) * fy
    return 0.877 / lam_c**2 * fy


def pne(ag: float, fn: float) -> float:
    """Eq. E2-1, p. 43: Pne = Ag Fn."""
    return ag * fn


def lambda_local(p_ne: float, p_crl: float) -> float:
    """Eq. E3.2-2, p. 45: λℓ = √(Pne/Pcrℓ)."""
    return math.sqrt(p_ne / p_crl)


def pnl_dsm(p_ne: float, lam_l: float) -> float:
    """Eq. E3.2-1, p. 45: Pnℓ = 1.2 Pne (1 + 0.10 λℓ²)/(1 + 0.55 λℓ²) ≤ Pne, for λℓ ≤ 5."""
    return min(1.2 * p_ne * (1 + 0.10 * lam_l**2) / (1 + 0.55 * lam_l**2), p_ne)


def py(ag: float, fy: float) -> float:
    """Eq. E4-3, p. 46: Py = Ag Fy."""
    return ag * fy


def lambda_distortional(p_y: float, p_crd: float) -> float:
    """Eq. E4-2, p. 46: λd = √(Py/Pcrd)."""
    return math.sqrt(p_y / p_crd)


def pnd_dsm(p_y: float, lam_d: float) -> float:
    """Eq. E4-1, p. 46: Pnd = 1.2 Py (1 + 0.05 λd²)/(1 + 0.67 λd²) ≤ Py, for λd ≤ 5."""
    return min(1.2 * p_y * (1 + 0.05 * lam_d**2) / (1 + 0.67 * lam_d**2), p_y)
