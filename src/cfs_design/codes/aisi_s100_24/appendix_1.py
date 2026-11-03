"""AISI S100-24 Appendix 1: plate buckling coefficients k used by the local buckling of Appendix 2.3.2."""

K_STIFFENED = 4.0
"""1.1, p. 1-1: stiffened element supported by a web on each longitudinal edge."""

K_UNSTIFFENED = 0.43
"""1.2.1, p. 1-9: uniformly compressed unstiffened element."""


def k_web_compression_tension(psi: float) -> float:
    """1.1.2(a)(1), Eq. 1.1.2-2, p. 1-4: web with f1 in compression and f2 in tension, psi = |f2/f1| (Eq. 1.1.2-1)."""
    return 4 + 2 * (1 + psi) ** 3 + 2 * (1 + psi)


def k_stiffened_both_compression(psi: float) -> float:
    """1.1.2(a)(2), Eq. 1.1.2-8, p. 1-4: other stiffened element with f1 and f2 in compression, psi = |f2/f1|."""
    return 4 + 2 * (1 - psi) ** 3 + 2 * (1 - psi)


def k_unstiffened_decreasing_to_free_edge(psi: float) -> float:
    """1.2.2(a)(1), Eq. 1.2.2-2, p. 1-10: unstiffened element, both edges in compression, stress decreasing
    toward the unsupported edge, psi = |f2/f1| (Eq. 1.2.2-1)."""
    return 0.578 / (psi + 0.34)


def k_unstiffened_increasing_to_free_edge(psi: float) -> float:
    """1.2.2(a)(1), Eq. 1.2.2-3, p. 1-10: unstiffened element, both edges in compression, stress increasing
    toward the unsupported edge, psi = |f2/f1|."""
    return 0.57 - 0.21 * psi + 0.07 * psi**2
