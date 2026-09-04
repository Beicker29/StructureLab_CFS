"""Backward-compatible M8B exports for shared global-compression mechanics."""

from cfs_design.design.global_compression import (
    GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE,
    calculate_global_buckling,
    resolve_effective_lengths,
)

__all__ = [
    "GLOBAL_DISCRIMINANT_RELATIVE_CLEANUP_TOLERANCE",
    "calculate_global_buckling",
    "resolve_effective_lengths",
]
