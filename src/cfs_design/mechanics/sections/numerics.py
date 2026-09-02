"""Shared scale-aware numerical cleanup for section mechanics."""


RELATIVE_CLEANUP_TOLERANCE = 1.0e-12


def clean_near_zero(value: float, scale: float) -> float:
    """Return exact zero only for scale-negligible floating-point residue."""

    return (
        0.0
        if abs(value) <= RELATIVE_CLEANUP_TOLERANCE * max(abs(scale), 1.0)
        else value
    )


__all__ = ["RELATIVE_CLEANUP_TOLERANCE", "clean_near_zero"]
