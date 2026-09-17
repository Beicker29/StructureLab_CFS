"""Unit tests for StructureLab-owned modal evidence and review policy."""

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.stability import (
    BucklingModeFamily,
    ClassificationPolicy,
    ClassificationStatus,
    EngineeringSelection,
    ModeParticipation,
    ReviewReason,
    assess_convergence,
    classify_with_evidence,
    modal_assurance_criterion,
    normalized_vector,
    optimal_mac_assignment,
)


def _participation(g: float, d: float, l: float, o: float) -> ModeParticipation:
    return ModeParticipation(g, d, l, o)


def test_participation_requires_a_normalized_total() -> None:
    with pytest.raises(ValidationError, match="sum to 100"):
        _participation(1.0, 2.0, 3.0, 4.0)


def test_normalization_and_mac_are_sign_and_scale_invariant() -> None:
    first = (1.0, -2.0, 3.0, 4.0)
    second = tuple(-7.0 * value for value in first)

    assert normalized_vector(first) == pytest.approx(normalized_vector(second))
    assert modal_assurance_criterion(first, second) == pytest.approx(1.0)


def test_mac_tracking_follows_crossing_shapes_not_eigenvalue_order() -> None:
    previous = ((1.0, 0.0), (0.0, 1.0))
    current = ((0.0, -4.0), (3.0, 0.0))

    assignment = optimal_mac_assignment(previous, current)

    assert tuple(item[0] for item in assignment) == (1, 0)
    assert tuple(item[1] for item in assignment) == pytest.approx((1.0, 1.0))


def test_clear_mode_is_automatically_accepted_only_with_all_evidence() -> None:
    participation = _participation(1.0, 1.0, 97.0, 1.0)
    result = classify_with_evidence(
        participation,
        1.0e-13,
        policy=ClassificationPolicy(),
        previous_participation=participation,
        next_participation=participation,
        mac_to_previous=0.999,
        mac_to_next=0.999,
        mesh_converged=True,
        wavelength_converged=True,
    )

    assert result.dominant_family is BucklingModeFamily.LOCAL
    assert result.status is ClassificationStatus.AUTOMATIC_ACCEPTED
    assert result.review_reasons == ()


def test_local_distortional_transition_requires_review() -> None:
    current = _participation(1.0, 52.0, 46.0, 1.0)
    following = _participation(1.0, 8.0, 90.0, 1.0)
    result = classify_with_evidence(
        current,
        1.0e-13,
        policy=ClassificationPolicy(),
        next_participation=following,
        mac_to_next=0.98,
        mesh_converged=True,
        wavelength_converged=True,
    )

    assert result.dominant_family is BucklingModeFamily.MIXED
    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert ReviewReason.LOCAL_DISTORTIONAL_INTERACTION in result.review_reasons
    assert ReviewReason.NO_DOMINANT_FAMILY in result.review_reasons
    assert ReviewReason.CLASSIFICATION_SENSITIVE_TO_WAVELENGTH in result.review_reasons
    assert ReviewReason.SMOOTH_LOCAL_DISTORTIONAL_TRANSITION in result.review_reasons


def test_tracked_branch_transition_is_an_explicit_review_reason() -> None:
    participation = _participation(1.0, 1.0, 97.0, 1.0)
    result = classify_with_evidence(
        participation,
        0.0,
        policy=ClassificationPolicy(),
        previous_participation=participation,
        next_participation=participation,
        mac_to_previous=0.999,
        mac_to_next=0.999,
        mesh_converged=True,
        wavelength_converged=True,
        branch_transition=True,
    )

    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert result.review_reasons == (ReviewReason.BRANCH_TRANSITION,)


def test_classical_fcfsm_disagreement_is_never_silently_resolved() -> None:
    participation = _participation(1.0, 8.0, 90.0, 1.0)
    result = classify_with_evidence(
        participation,
        0.0,
        policy=ClassificationPolicy(),
        previous_participation=participation,
        next_participation=participation,
        mac_to_previous=1.0,
        mac_to_next=1.0,
        mesh_converged=True,
        wavelength_converged=True,
        reference_disagreement=True,
    )

    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert ReviewReason.REFERENCE_DISAGREEMENT in result.review_reasons


def test_rank_deficient_modal_basis_requires_review() -> None:
    participation = _participation(1.0, 97.0, 1.0, 1.0)
    result = classify_with_evidence(
        participation,
        1.0e-5,
        policy=ClassificationPolicy(),
        previous_participation=participation,
        next_participation=participation,
        mac_to_previous=1.0,
        mac_to_next=1.0,
        mesh_converged=True,
        wavelength_converged=True,
        basis_condition_number=3.0e16,
        basis_rank=147,
        basis_dimension=148,
    )

    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert ReviewReason.BASIS_SENSITIVE in result.review_reasons
    assert ReviewReason.RECONSTRUCTION_ERROR in result.review_reasons
    assert result.basis_rank == 147
    assert result.basis_dimension == 148


def test_non_unique_minimum_is_a_separate_review_reason() -> None:
    participation = _participation(1.0, 97.0, 1.0, 1.0)
    result = classify_with_evidence(
        participation,
        0.0,
        policy=ClassificationPolicy(),
        previous_participation=participation,
        next_participation=participation,
        mac_to_previous=1.0,
        mac_to_next=1.0,
        mesh_converged=True,
        wavelength_converged=True,
        non_unique_minimum=True,
    )

    assert result.dominant_family is BucklingModeFamily.DISTORTIONAL
    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert result.review_reasons == (ReviewReason.NON_UNIQUE_MINIMUM,)


def test_missing_convergence_evidence_cannot_be_accepted() -> None:
    result = classify_with_evidence(
        _participation(98.0, 1.0, 0.5, 0.5),
        0.0,
        policy=ClassificationPolicy(),
    )

    assert result.status is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
    assert ReviewReason.MESH_SENSITIVE in result.review_reasons
    assert ReviewReason.WAVELENGTH_NOT_CONVERGED in result.review_reasons


def test_mesh_and_wavelength_convergence_use_explicit_nested_limits() -> None:
    converged = assess_convergence(
        refined_stress_mpa=100.0,
        refined_wavelength_mm=200.0,
        coarse_stress_mpa=100.4,
        coarse_wavelength_mm=201.0,
        stress_limit_ratio=0.005,
        wavelength_limit_ratio=0.01,
        comparison_name="successive-mesh",
        family_agreement=True,
        mode_shape_mac=0.999,
        minimum_mode_shape_mac=0.90,
    )
    not_converged = assess_convergence(
        refined_stress_mpa=100.0,
        refined_wavelength_mm=200.0,
        coarse_stress_mpa=101.0,
        coarse_wavelength_mm=200.0,
        stress_limit_ratio=0.005,
        wavelength_limit_ratio=0.01,
        comparison_name="wavelength-grid",
        family_agreement=True,
        mode_shape_mac=0.999,
        minimum_mode_shape_mac=0.90,
    )

    assert converged.converged is True
    assert converged.stress_change_ratio == pytest.approx(0.004)
    assert converged.wavelength_change_ratio == pytest.approx(0.005)
    assert not_converged.converged is False


def test_modal_convergence_fails_on_family_or_shape_disagreement() -> None:
    family_change = assess_convergence(
        refined_stress_mpa=100.0,
        refined_wavelength_mm=200.0,
        coarse_stress_mpa=100.0,
        coarse_wavelength_mm=200.0,
        stress_limit_ratio=0.005,
        wavelength_limit_ratio=0.01,
        comparison_name="production-vs-reference-mesh",
        family_agreement=False,
        mode_shape_mac=0.999,
        minimum_mode_shape_mac=0.90,
    )
    shape_change = assess_convergence(
        refined_stress_mpa=100.0,
        refined_wavelength_mm=200.0,
        coarse_stress_mpa=100.0,
        coarse_wavelength_mm=200.0,
        stress_limit_ratio=0.005,
        wavelength_limit_ratio=0.01,
        comparison_name="production-vs-reference-mesh",
        family_agreement=True,
        mode_shape_mac=0.50,
        minimum_mode_shape_mac=0.90,
    )

    assert family_change.converged is False
    assert shape_change.converged is False


def test_engineering_selection_is_explicit_confirmed_and_auditable() -> None:
    selection = EngineeringSelection(
        family=BucklingModeFamily.DISTORTIONAL,
        half_wavelength_mm=724.4,
        critical_stress_mpa=123.0,
        critical_load_n=45600.0,
        confirmed_by="ENGINEER-001",
        reason="Reviewed L/D interaction and selected the continuous D branch.",
        candidate_eigenvector_ids=("mode-1", "mode-2"),
        engineer_confirmed=True,
        provenance=("review-record:ER-001", "solver-run:RUN-001"),
    )

    assert selection.selected_family is BucklingModeFamily.DISTORTIONAL
    assert selection.selected_half_wavelength_mm == pytest.approx(724.4)
    assert selection.selected_fcr_mpa == pytest.approx(123.0)
    assert selection.selected_pcr_n == pytest.approx(45600.0)

    with pytest.raises(ValidationError, match="engineer-confirmed"):
        EngineeringSelection(
            family=BucklingModeFamily.LOCAL,
            half_wavelength_mm=100.0,
            critical_stress_mpa=68.0,
            critical_load_n=10000.0,
            confirmed_by="ENGINEER-001",
            reason="Not actually confirmed.",
            candidate_eigenvector_ids=("mode-1",),
            engineer_confirmed=False,
            provenance=("review-record:ER-002",),
        )
