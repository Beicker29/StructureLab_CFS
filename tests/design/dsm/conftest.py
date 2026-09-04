"""Controlled M9B fixtures at the frozen M8B/M9A public boundaries."""

import pytest

from cfs_design.design import MemberDesignInput
from cfs_design.domain import DesignMethod, SectionFamily
from cfs_design.results import (
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    EngineeringUnit,
    EngineeringValue,
    LimitStateId,
)
from cfs_design.stability import (
    BucklingModeFamily,
    ClassificationPolicy,
    ClassificationStatus,
    ConvergenceEvidence,
    ElasticBucklingModeResult,
    ElasticBucklingResult,
    EngineeringSelection,
    FSMMesh,
    FSMNode,
    FSMStrip,
    ModeClassification,
    ModeParticipation,
    ReviewReason,
    SolverProvenance,
    TrackedMode,
    WavelengthSearchEvidence,
)
from tests.design.ewm.conftest import make_design_input


def make_dsm_design_input(
    *,
    family: SectionFamily = SectionFamily.C_LIPPED,
    length_mm: float = 500.0,
    **kwargs,
) -> MemberDesignInput:
    return make_design_input(
        family=family,
        length_mm=length_mm,
        method=DesignMethod.DSM,
        **kwargs,
    )


def _classification(
    family: BucklingModeFamily,
    status: ClassificationStatus,
) -> ModeClassification:
    if family is BucklingModeFamily.LOCAL:
        participation = ModeParticipation(1.0, 1.0, 97.0, 1.0)
    else:
        participation = ModeParticipation(1.0, 97.0, 1.0, 1.0)
    return ModeClassification(
        dominant_family=family,
        status=status,
        participation=participation,
        separation_percent=96.0,
        reconstruction_error=1.0e-13,
        review_reasons=(
            ()
            if status is ClassificationStatus.AUTOMATIC_ACCEPTED
            else (ReviewReason.MESH_SENSITIVE,)
        ),
    )


def _candidate(
    *,
    family: BucklingModeFamily,
    status: ClassificationStatus,
    critical_load_n: float,
    gross_area_mm2: float,
    branch_id: int,
) -> ElasticBucklingModeResult:
    wavelength = 100.0 if family is BucklingModeFamily.LOCAL else 800.0
    classification = _classification(family, status)
    tracked = TrackedMode(
        branch_id=branch_id,
        mode_index=0,
        half_wavelength_mm=wavelength,
        load_factor=critical_load_n / gross_area_mm2,
        critical_stress_mpa=critical_load_n / gross_area_mm2,
        eigenvector_id=f"{family.value.lower()}-candidate",
        normalized_eigenvector=(1.0, 0.0),
        mac_to_previous=1.0,
        classification=classification,
    )
    convergence = ConvergenceEvidence(
        converged=True,
        stress_change_ratio=0.0,
        wavelength_change_ratio=0.0,
        coarse_value=critical_load_n / gross_area_mm2,
        refined_value=critical_load_n / gross_area_mm2,
        notes="Controlled M9B boundary fixture.",
        family_agreement=True,
        mode_shape_mac=1.0,
    )
    return ElasticBucklingModeResult(
        family=family,
        critical_stress_mpa=critical_load_n / gross_area_mm2,
        critical_load_n=critical_load_n,
        half_wavelength_mm=wavelength,
        classification=classification,
        tracked_mode=tracked,
        mesh_convergence=convergence,
        wavelength_convergence=convergence,
        dsm_input_eligible=(
            status is ClassificationStatus.AUTOMATIC_ACCEPTED
        ),
    )


def make_m9a_result(
    design_input: MemberDesignInput,
    *,
    local_status: ClassificationStatus = ClassificationStatus.AUTOMATIC_ACCEPTED,
    distortional_status: ClassificationStatus = (
        ClassificationStatus.AUTOMATIC_ACCEPTED
    ),
    p_crl_n: float = 100_000.0,
    p_crd_n: float = 100_000.0,
    selection_family: BucklingModeFamily | None = None,
) -> ElasticBucklingResult:
    area = design_input.section_mechanics.gross.a_mm2
    local = _candidate(
        family=BucklingModeFamily.LOCAL,
        status=local_status,
        critical_load_n=p_crl_n,
        gross_area_mm2=area,
        branch_id=0,
    )
    distortional = _candidate(
        family=BucklingModeFamily.DISTORTIONAL,
        status=distortional_status,
        critical_load_n=p_crd_n,
        gross_area_mm2=area,
        branch_id=1,
    )
    candidates = (local, distortional)
    accepted = tuple(
        candidate
        for candidate in candidates
        if candidate.classification.status
        is ClassificationStatus.AUTOMATIC_ACCEPTED
    )
    reviewed = tuple(candidate for candidate in candidates if candidate not in accepted)
    selection = None
    if selection_family is not None:
        selected = next(
            candidate for candidate in candidates if candidate.family is selection_family
        )
        selection = EngineeringSelection(
            family=selection_family,
            half_wavelength_mm=selected.half_wavelength_mm,
            critical_stress_mpa=selected.critical_stress_mpa,
            critical_load_n=selected.critical_load_n,
            confirmed_by="ENG-TEST-001",
            reason="Controlled engineering selection fixture.",
            candidate_eigenvector_ids=(selected.tracked_mode.eigenvector_id,),
            engineer_confirmed=True,
            provenance=("M9B_TEST_ENGINEERING_REVIEW",),
        )
    case_id = design_input.resolved_member.member.case_id
    trace_id = f"trace:case={case_id}:method=DSM:name=M9A_TEST"
    limit_state = LimitStateId("ELASTIC_BUCKLING", "M9A elastic buckling")
    trace = CalculationTrace(
        trace_id=trace_id,
        status=CalculationStatus.COMPLETED,
        steps=(
            CalculationStep(
                step_id=f"{trace_id}:step=001",
                name="Controlled M9A result",
                results=(
                    EngineeringValue(
                        "candidate_count",
                        2.0,
                        EngineeringUnit.DIMENSIONLESS,
                    ),
                ),
            ),
        ),
        final_values=(
            EngineeringValue(
                "candidate_count",
                2.0,
                EngineeringUnit.DIMENSIONLESS,
            ),
        ),
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=limit_state,
    )
    mesh = FSMMesh(
        section_id=design_input.section_mechanics.section_id,
        geometry_id=design_input.resolved_member.section.geometry.geometry_id,
        nodes=(
            FSMNode(0, 0.0, 0.0, 0.0),
            FSMNode(1, 1.0, 0.0, 0.0),
        ),
        strips=(FSMStrip(0, 0, 1, 1.0),),
        target_strip_width_mm=1.0,
        maximum_actual_strip_width_mm=1.0,
    )
    return ElasticBucklingResult(
        case_id=case_id,
        reference_stress_mpa=1.0,
        mesh=mesh,
        tracked_modes=(local.tracked_mode, distortional.tracked_mode),
        automatic_candidates=candidates,
        accepted_results=accepted,
        engineering_review_required_candidates=reviewed,
        wavelength_search=WavelengthSearchEvidence(
            initial_half_wavelengths_mm=(10.0, 100.0, 1000.0),
            evaluated_half_wavelengths_mm=(10.0, 100.0, 1000.0),
            refinement_steps=(),
            refinement_limit=0,
            boundary_expansion_limit=0,
            boundary_resolution_satisfied=True,
            notes="Controlled M9B boundary fixture.",
        ),
        solver_provenance=SolverProvenance(
            package="pycufsm",
            version="0.2.0",
            license="AFL-3.0",
            pypi_identity="pycufsm==0.2.0",
            upstream_repository="https://github.com/ClearCalcs/pyCUFSM",
            release_identity="v0.2.0",
            numpy_version="2.2.6",
            scipy_version="1.18.1",
            adapter_version="M9A-1",
        ),
        matlab_validation_provenance=(),
        policy=ClassificationPolicy(),
        trace=trace,
        engineering_selection=selection,
    )


@pytest.fixture
def dsm_design_input() -> MemberDesignInput:
    return make_dsm_design_input()


@pytest.fixture
def m9a_factory():
    return make_m9a_result


@pytest.fixture
def dsm_input_factory():
    return make_dsm_design_input
