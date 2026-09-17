"""StructureLab-owned modal diagnostics independent of the external solver."""

from functools import lru_cache
from math import isfinite, sqrt
from numbers import Real
from typing import Sequence

from cfs_design.core.exceptions import ValidationError

from .models import (
    BucklingModeFamily,
    ClassificationPolicy,
    ClassificationStatus,
    ConvergenceEvidence,
    ModeClassification,
    ModeParticipation,
    ReviewReason,
)


def _vector(values: Sequence[float], name: str) -> tuple[float, ...]:
    result = tuple(values)
    if not result:
        raise ValidationError(f"{name} must not be empty")
    if any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(value)
        for value in result
    ):
        raise ValidationError(f"{name} must contain only finite numbers")
    if sum(float(value) ** 2 for value in result) == 0.0:
        raise ValidationError(f"{name} must not be a zero vector")
    return tuple(float(value) for value in result)


def normalized_vector(values: Sequence[float]) -> tuple[float, ...]:
    """Return a deterministic unit vector, including deterministic sign."""

    vector = _vector(values, "values")
    norm = sqrt(sum(value * value for value in vector))
    normalized = tuple(value / norm for value in vector)
    pivot = max(range(len(normalized)), key=lambda index: abs(normalized[index]))
    if normalized[pivot] < 0.0:
        normalized = tuple(-value for value in normalized)
    return normalized


def modal_assurance_criterion(
    first: Sequence[float],
    second: Sequence[float],
) -> float:
    """Return the real-vector MAC, invariant to sign and nonzero scale."""

    a = _vector(first, "first")
    b = _vector(second, "second")
    if len(a) != len(b):
        raise ValidationError("MAC vectors must have the same length")
    dot = sum(left * right for left, right in zip(a, b))
    norm_a = sum(value * value for value in a)
    norm_b = sum(value * value for value in b)
    value = (dot * dot) / (norm_a * norm_b)
    return min(1.0, max(0.0, value))


def optimal_mac_assignment(
    previous: Sequence[Sequence[float]],
    current: Sequence[Sequence[float]],
) -> tuple[tuple[int, float], ...]:
    """Map each previous branch to a unique current mode by maximum total MAC.

    The dynamic-programming assignment avoids assuming that eigenvalue order is
    a branch identity. Ties are resolved lexicographically for reproducibility.
    """

    previous_vectors = tuple(tuple(item) for item in previous)
    current_vectors = tuple(tuple(item) for item in current)
    if not previous_vectors or len(previous_vectors) != len(current_vectors):
        raise ValidationError(
            "previous and current must contain the same nonzero number of modes"
        )
    matrix = tuple(
        tuple(modal_assurance_criterion(left, right) for right in current_vectors)
        for left in previous_vectors
    )
    count = len(matrix)

    @lru_cache(maxsize=None)
    def best(row: int, used_mask: int) -> tuple[float, tuple[int, ...]]:
        if row == count:
            return 0.0, ()
        candidates: list[tuple[float, tuple[int, ...]]] = []
        for column in range(count):
            if used_mask & (1 << column):
                continue
            remainder_score, remainder_columns = best(
                row + 1, used_mask | (1 << column)
            )
            candidates.append(
                (
                    matrix[row][column] + remainder_score,
                    (column,) + remainder_columns,
                )
            )
        return min(candidates, key=lambda item: (-item[0], item[1]))

    _, columns = best(0, 0)
    return tuple((column, matrix[row][column]) for row, column in enumerate(columns))


def dominant_family(
    participation: ModeParticipation,
    policy: ClassificationPolicy,
) -> tuple[BucklingModeFamily, float]:
    """Determine the leading family and leading-to-runner-up separation."""

    structural = sorted(
        participation.structural(), key=lambda item: (-item[1], item[0].value)
    )
    leader, leader_value = structural[0]
    runner_value = structural[1][1]
    separation = leader_value - runner_value
    if participation.other_percent >= leader_value:
        return BucklingModeFamily.UNCLASSIFIED, separation
    if (
        leader_value < policy.dominant_min_percent
        or separation < policy.separation_min_percent
    ):
        return BucklingModeFamily.MIXED, separation
    return leader, separation


def classify_with_evidence(
    participation: ModeParticipation,
    reconstruction_error: float,
    *,
    policy: ClassificationPolicy,
    previous_participation: ModeParticipation | None = None,
    next_participation: ModeParticipation | None = None,
    mac_to_previous: float | None = None,
    mac_to_next: float | None = None,
    mesh_converged: bool | None = None,
    wavelength_converged: bool | None = None,
    non_unique_minimum: bool = False,
    basis_sensitive: bool = False,
    basis_configuration_validated: bool = True,
    reference_disagreement: bool = False,
    branch_transition: bool = False,
    basis_condition_number: float | None = None,
    basis_rank: int | None = None,
    basis_dimension: int | None = None,
) -> ModeClassification:
    """Apply explicit multi-evidence QA gates to one modal participation result."""

    if not isinstance(participation, ModeParticipation):
        raise ValidationError("participation must be ModeParticipation")
    if not isinstance(policy, ClassificationPolicy):
        raise ValidationError("policy must be ClassificationPolicy")
    if not isinstance(reconstruction_error, Real) or not isfinite(reconstruction_error):
        raise ValidationError("reconstruction_error must be finite")
    if reconstruction_error < 0.0:
        raise ValidationError("reconstruction_error must be non-negative")

    family, separation = dominant_family(participation, policy)
    current_leader = max(participation.structural(), key=lambda item: item[1])[0]
    reasons: list[ReviewReason] = []
    if family in (BucklingModeFamily.MIXED, BucklingModeFamily.UNCLASSIFIED):
        reasons.append(ReviewReason.NO_DOMINANT_FAMILY)

    ld_floor = 100.0 - policy.dominant_min_percent
    if (
        participation.local_percent > ld_floor
        and participation.distortional_percent > ld_floor
    ):
        reasons.append(ReviewReason.LOCAL_DISTORTIONAL_INTERACTION)

    if reconstruction_error > policy.max_reconstruction_error:
        reasons.append(ReviewReason.RECONSTRUCTION_ERROR)

    neighbors = tuple(
        value
        for value in (previous_participation, next_participation)
        if value is not None
    )
    for neighbor in neighbors:
        neighbor_family, _ = dominant_family(neighbor, policy)
        neighbor_leader = max(neighbor.structural(), key=lambda item: item[1])[0]
        if neighbor_family is not family:
            reasons.append(ReviewReason.CLASSIFICATION_SENSITIVE_TO_WAVELENGTH)
            if {neighbor_leader, current_leader} == {
                BucklingModeFamily.LOCAL,
                BucklingModeFamily.DISTORTIONAL,
            }:
                reasons.append(ReviewReason.SMOOTH_LOCAL_DISTORTIONAL_TRANSITION)
        if family in (
            BucklingModeFamily.GLOBAL,
            BucklingModeFamily.DISTORTIONAL,
            BucklingModeFamily.LOCAL,
        ):
            current_value = dict(participation.structural())[family]
            neighbor_value = dict(neighbor.structural())[family]
            if (
                neighbor_value < policy.neighboring_family_min_percent
                or abs(neighbor_value - current_value)
                > policy.max_neighbor_change_percent
            ):
                reasons.append(ReviewReason.CLASSIFICATION_SENSITIVE_TO_WAVELENGTH)

    for mac in (mac_to_previous, mac_to_next):
        if mac is not None:
            if not isinstance(mac, Real) or not isfinite(mac) or not 0.0 <= mac <= 1.0:
                raise ValidationError("MAC evidence must be in [0, 1]")
            if mac < policy.min_tracking_mac:
                reasons.append(ReviewReason.MODE_CROSSING)

    if mesh_converged is not True:
        reasons.append(ReviewReason.MESH_SENSITIVE)
    if wavelength_converged is not True:
        reasons.append(ReviewReason.WAVELENGTH_NOT_CONVERGED)
    if non_unique_minimum:
        reasons.append(ReviewReason.NON_UNIQUE_MINIMUM)
    if basis_sensitive:
        reasons.append(ReviewReason.BASIS_SENSITIVE)
    if not basis_configuration_validated:
        reasons.append(ReviewReason.BASIS_CONFIGURATION_NOT_VALIDATED)
    if reference_disagreement:
        reasons.append(ReviewReason.REFERENCE_DISAGREEMENT)
    if branch_transition:
        reasons.append(ReviewReason.BRANCH_TRANSITION)
    if (basis_rank is None) != (basis_dimension is None):
        raise ValidationError(
            "basis_rank and basis_dimension must be supplied together"
        )
    if basis_rank is not None and basis_dimension is not None:
        if (
            isinstance(basis_rank, bool)
            or not isinstance(basis_rank, int)
            or isinstance(basis_dimension, bool)
            or not isinstance(basis_dimension, int)
            or basis_rank < 1
            or basis_dimension < 1
            or basis_rank > basis_dimension
        ):
            raise ValidationError("invalid modal-basis rank evidence")
        if basis_rank < basis_dimension:
            reasons.append(ReviewReason.BASIS_SENSITIVE)
    if basis_condition_number is not None and (
        isinstance(basis_condition_number, bool)
        or not isinstance(basis_condition_number, Real)
        or not isfinite(basis_condition_number)
        or basis_condition_number < 1.0
    ):
        raise ValidationError("basis_condition_number must be finite and at least one")

    unique_reasons = tuple(dict.fromkeys(reasons))
    status = (
        ClassificationStatus.AUTOMATIC_ACCEPTED
        if not unique_reasons
        else ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    )
    return ModeClassification(
        dominant_family=family,
        status=status,
        participation=participation,
        separation_percent=separation,
        reconstruction_error=float(reconstruction_error),
        review_reasons=unique_reasons,
        basis_condition_number=(
            float(basis_condition_number)
            if basis_condition_number is not None
            else None
        ),
        basis_rank=basis_rank,
        basis_dimension=basis_dimension,
    )


def assess_convergence(
    *,
    refined_stress_mpa: float,
    refined_wavelength_mm: float,
    coarse_stress_mpa: float | None,
    coarse_wavelength_mm: float | None,
    stress_limit_ratio: float,
    wavelength_limit_ratio: float,
    comparison_name: str,
    family_agreement: bool | None = None,
    mode_shape_mac: float | None = None,
    minimum_mode_shape_mac: float | None = None,
) -> ConvergenceEvidence:
    """Assess one nested discretization comparison with explicit limits."""

    for name, value in (
        ("refined_stress_mpa", refined_stress_mpa),
        ("refined_wavelength_mm", refined_wavelength_mm),
        ("stress_limit_ratio", stress_limit_ratio),
        ("wavelength_limit_ratio", wavelength_limit_ratio),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(value)
            or value <= 0.0
        ):
            raise ValidationError(f"{name} must be finite and positive")
    if not isinstance(comparison_name, str) or not comparison_name.strip():
        raise ValidationError("comparison_name must be a non-empty string")
    if (coarse_stress_mpa is None) != (coarse_wavelength_mm is None):
        raise ValidationError("coarse stress and wavelength must be supplied together")
    if family_agreement is not None and not isinstance(family_agreement, bool):
        raise ValidationError("family_agreement must be bool or None")
    if mode_shape_mac is not None:
        if (
            isinstance(mode_shape_mac, bool)
            or not isinstance(mode_shape_mac, Real)
            or not isfinite(mode_shape_mac)
            or not 0.0 <= mode_shape_mac <= 1.0
        ):
            raise ValidationError("mode_shape_mac must be in [0, 1]")
    if minimum_mode_shape_mac is not None:
        if (
            isinstance(minimum_mode_shape_mac, bool)
            or not isinstance(minimum_mode_shape_mac, Real)
            or not isfinite(minimum_mode_shape_mac)
            or not 0.0 <= minimum_mode_shape_mac <= 1.0
        ):
            raise ValidationError("minimum_mode_shape_mac must be in [0, 1]")
        if mode_shape_mac is None and coarse_stress_mpa is not None:
            raise ValidationError(
                "mode_shape_mac is required with minimum_mode_shape_mac"
            )
    if coarse_stress_mpa is None:
        return ConvergenceEvidence(
            converged=False,
            stress_change_ratio=None,
            wavelength_change_ratio=None,
            coarse_value=None,
            refined_value=float(refined_stress_mpa),
            notes=(
                f"{comparison_name} comparison did not identify the same modal family."
            ),
            family_agreement=family_agreement,
            mode_shape_mac=mode_shape_mac,
        )
    if coarse_stress_mpa <= 0.0 or coarse_wavelength_mm <= 0.0:
        raise ValidationError("coarse stress and wavelength must be positive")
    stress_change = abs(refined_stress_mpa - coarse_stress_mpa) / refined_stress_mpa
    wavelength_change = (
        abs(refined_wavelength_mm - coarse_wavelength_mm) / refined_wavelength_mm
    )
    return ConvergenceEvidence(
        converged=(
            stress_change <= stress_limit_ratio
            and wavelength_change <= wavelength_limit_ratio
            and family_agreement is not False
            and (
                minimum_mode_shape_mac is None
                or (
                    mode_shape_mac is not None
                    and mode_shape_mac >= minimum_mode_shape_mac
                )
            )
        ),
        stress_change_ratio=stress_change,
        wavelength_change_ratio=wavelength_change,
        coarse_value=float(coarse_stress_mpa),
        refined_value=float(refined_stress_mpa),
        notes=(
            f"{comparison_name} nested comparison; limits are "
            f"{stress_limit_ratio:.6g} stress and "
            f"{wavelength_limit_ratio:.6g} wavelength"
            + (
                f", {minimum_mode_shape_mac:.6g} MAC."
                if minimum_mode_shape_mac is not None
                else "."
            )
        ),
        family_agreement=family_agreement,
        mode_shape_mac=mode_shape_mac,
    )


__all__ = [
    "assess_convergence",
    "classify_with_evidence",
    "dominant_family",
    "modal_assurance_criterion",
    "normalized_vector",
    "optimal_mac_assignment",
]
