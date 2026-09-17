"""Public M9A adapter: unconstrained solve, owned classification, normalization."""

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, sqrt

from cfs_design.core.exceptions import UnsupportedFeatureError, ValidationError
from cfs_design.core.units import EngineeringUnit
from cfs_design.design import MemberDesignInput
from cfs_design.domain import DesignMethod, SectionFamily
from cfs_design.mechanics.sections import build_centerline_section
from cfs_design.results import (
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EngineeringValue,
    EquationReference,
    LimitStateId,
    MetadataEntry,
    ReferenceSourceType,
    make_step_id,
    make_trace_id,
)

from ..modal import (
    assess_convergence,
    classify_with_evidence,
    modal_assurance_criterion,
    normalized_vector,
    optimal_mac_assignment,
)
from ..models import (
    BucklingModeFamily,
    ClassificationMethod,
    ClassificationPolicy,
    ClassificationStatus,
    ClassicalBasisOptions,
    ConvergenceEvidence,
    ElasticBucklingModeResult,
    ElasticBucklingResult,
    FSMMesh,
    MATLABValidationProvenance,
    ModeClassification,
    ModeParticipation,
    TrackedMode,
    WavelengthRefinementStep,
    WavelengthSearchEvidence,
)
from ._classical import classify_mode_shape
from ._solver import RawSolverRun, run_unconstrained, solver_provenance
from .mesh import build_fsm_mesh


_VALIDATED_OPTIONS = ClassicalBasisOptions(ospace=1, couple=1, orth=2, norm=1)
_SOURCE_ARCHIVE_SHA256 = (
    "e43d66ccc5b024ea40ba48c369f88b92c60fb7f0e11c6ce8e06b06f6b62b9104"
)


@dataclass(frozen=True, slots=True)
class ElasticBucklingAnalysisConfig:
    """Explicit analysis discretization and auditable classification policy."""

    half_wavelengths_mm: tuple[float, ...]
    target_strip_width_mm: float
    eigenvalue_count: int = 3
    reference_stress_mpa: float = 1.0
    basis_options: ClassicalBasisOptions = _VALIDATED_OPTIONS
    policy: ClassificationPolicy = ClassificationPolicy()
    perform_mesh_convergence: bool = True
    reference_strip_width_mm: float | None = None
    perform_wavelength_refinement: bool = True
    wavelength_refinement_limit: int = 4
    boundary_expansion_limit: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.half_wavelengths_mm, tuple) or len(
            self.half_wavelengths_mm
        ) < 3:
            raise ValidationError(
                "half_wavelengths_mm must be a tuple containing at least three values"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0.0
            for value in self.half_wavelengths_mm
        ):
            raise ValidationError("half-wavelengths must be finite and positive")
        normalized = tuple(float(value) for value in self.half_wavelengths_mm)
        if tuple(sorted(set(normalized))) != normalized:
            raise ValidationError("half-wavelengths must be strictly increasing")
        object.__setattr__(self, "half_wavelengths_mm", normalized)
        if self.target_strip_width_mm <= 0.0:
            raise ValidationError("target_strip_width_mm must be positive")
        if (
            isinstance(self.eigenvalue_count, bool)
            or not isinstance(self.eigenvalue_count, int)
            or self.eigenvalue_count < 1
        ):
            raise ValidationError("eigenvalue_count must be a positive integer")
        if self.reference_stress_mpa <= 0.0:
            raise ValidationError("reference_stress_mpa must be positive")
        if not isinstance(self.basis_options, ClassicalBasisOptions):
            raise ValidationError("basis_options must be ClassicalBasisOptions")
        if not isinstance(self.policy, ClassificationPolicy):
            raise ValidationError("policy must be ClassificationPolicy")
        if not isinstance(self.perform_mesh_convergence, bool):
            raise ValidationError("perform_mesh_convergence must be bool")
        if self.reference_strip_width_mm is not None:
            if (
                isinstance(self.reference_strip_width_mm, bool)
                or not isinstance(self.reference_strip_width_mm, (int, float))
                or not isfinite(self.reference_strip_width_mm)
                or self.reference_strip_width_mm <= 0.0
            ):
                raise ValidationError("reference_strip_width_mm must be positive")
            if self.reference_strip_width_mm >= self.target_strip_width_mm:
                raise ValidationError(
                    "reference_strip_width_mm must be finer than "
                    "target_strip_width_mm"
                )
        if not isinstance(self.perform_wavelength_refinement, bool):
            raise ValidationError("perform_wavelength_refinement must be bool")
        for name in ("wavelength_refinement_limit", "boundary_expansion_limit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class _Point:
    branch_id: int
    mode_index: int
    wavelength_index: int
    half_wavelength_mm: float
    load_factor: float
    critical_stress_mpa: float
    vector: tuple[float, ...]
    eigenvector_id: str
    mac_to_previous: float | None
    participation: ModeParticipation
    reconstruction_error: float
    basis_condition_number: float | None
    basis_rank: int
    basis_dimension: int


@dataclass(frozen=True, slots=True)
class _CurveAnalysis:
    mesh: FSMMesh
    points: tuple[_Point, ...]


@dataclass(frozen=True, slots=True)
class _WavelengthSearchRun:
    analysis: _CurveAnalysis
    previous_analysis: _CurveAnalysis | None
    evidence: WavelengthSearchEvidence


def _matlab_validation_provenance() -> tuple[MATLABValidationProvenance, ...]:
    common = {
        "implementation": "Official MATLAB CUFSM source executed for M9A reference generation",
        "release_identity": "CUFSM v5.66",
        "upstream_repository": "https://github.com/thinwalled/cufsm-git",
        "source_archive_sha256": _SOURCE_ARCHIVE_SHA256,
        "execution_runtime": "GNU Octave 4.4.1 compatible execution of official MATLAB .m source",
        "runtime_compatibility_note": (
            "Temporary Octave-only eigs display-option shims were applied to "
            "stripmain.m and stripmain_fcFSM.m; the downloaded source archive "
            "remained pristine, the mathematical formulation was unchanged, "
            "and no pyCUFSM source was modified."
        ),
    }
    return (
        MATLABValidationProvenance(
            reference_kind=ClassificationMethod.CLASSICAL_CFSM_REFERENCE,
            functions=(
                "stripmain.m",
                "classify.m",
                "base_column.m",
                "base_update.m",
                "mode_class.m",
            ),
            **common,
        ),
        MATLABValidationProvenance(
            reference_kind=ClassificationMethod.FCFSM_REFERENCE,
            functions=(
                "stripmain_fcFSM.m",
                "SecAnal_fcFSM.m",
                "base_column.m",
                "base_update.m",
            ),
            **common,
        ),
    )


def _raw_analysis(
    design_input: MemberDesignInput,
    mesh: FSMMesh,
    config: ElasticBucklingAnalysisConfig,
    wavelengths: tuple[float, ...],
) -> RawSolverRun:
    material = design_input.resolved_member.material
    return run_unconstrained(
        mesh=mesh,
        mechanics=design_input.section_mechanics,
        elastic_modulus_mpa=material.e_mpa,
        poisson_ratio=material.nu,
        half_wavelengths_mm=wavelengths,
        eigenvalue_count=config.eigenvalue_count,
        reference_stress_mpa=config.reference_stress_mpa,
    )


def _vector_id(wavelength: float, branch: int, vector: tuple[float, ...]) -> str:
    payload = ",".join(f"{value:.17g}" for value in vector)
    digest = sha256(payload.encode("ascii")).hexdigest()[:16]
    return f"mode:L={wavelength:.12g}:branch={branch}:sha256={digest}"


def _classify_curve(
    *,
    design_input: MemberDesignInput,
    mesh: FSMMesh,
    config: ElasticBucklingAnalysisConfig,
    wavelengths: tuple[float, ...],
) -> _CurveAnalysis:
    raw = _raw_analysis(design_input, mesh, config, wavelengths)
    raw_participations: list[
        list[tuple[ModeParticipation, float, float | None, int, int]]
    ] = []
    for wavelength_index, wavelength in enumerate(raw.lengths):
        per_mode: list[
            tuple[ModeParticipation, float, float | None, int, int]
        ] = []
        for mode_index in range(config.eigenvalue_count):
            projection = classify_mode_shape(
                nodes=raw.nodes_old,
                elements=raw.elements_old,
                properties=raw.properties_old,
                mesh=mesh,
                mechanics=design_input.section_mechanics,
                half_wavelength_mm=float(wavelength),
                mode_shape=raw.shapes[wavelength_index, mode_index],
                options=config.basis_options,
            )
            per_mode.append(
                (
                    projection.participation,
                    projection.reconstruction_error,
                    (
                        projection.basis_condition_number
                        if isfinite(projection.basis_condition_number)
                        else None
                    ),
                    projection.basis_rank,
                    projection.basis_dimension,
                )
            )
        raw_participations.append(per_mode)

    ordered_mode_indexes: list[tuple[int, ...]] = [
        tuple(range(config.eigenvalue_count))
    ]
    mac_values: list[tuple[float | None, ...]] = [
        tuple(None for _ in range(config.eigenvalue_count))
    ]
    previous_vectors = tuple(
        tuple(float(value) for value in raw.shapes[0, mode_index])
        for mode_index in ordered_mode_indexes[0]
    )
    for wavelength_index in range(1, len(wavelengths)):
        current_vectors = tuple(
            tuple(float(value) for value in raw.shapes[wavelength_index, mode_index])
            for mode_index in range(config.eigenvalue_count)
        )
        assignment = optimal_mac_assignment(previous_vectors, current_vectors)
        indexes = tuple(item[0] for item in assignment)
        ordered_mode_indexes.append(indexes)
        mac_values.append(tuple(item[1] for item in assignment))
        previous_vectors = tuple(current_vectors[index] for index in indexes)

    points: list[_Point] = []
    for wavelength_index, wavelength in enumerate(raw.lengths):
        for branch_id, mode_index in enumerate(ordered_mode_indexes[wavelength_index]):
            vector = normalized_vector(raw.shapes[wavelength_index, mode_index])
            (
                participation,
                residual,
                basis_condition_number,
                basis_rank,
                basis_dimension,
            ) = raw_participations[wavelength_index][mode_index]
            points.append(
                _Point(
                    branch_id=branch_id,
                    mode_index=mode_index,
                    wavelength_index=wavelength_index,
                    half_wavelength_mm=float(wavelength),
                    load_factor=float(raw.curve[wavelength_index, mode_index]),
                    critical_stress_mpa=float(
                        raw.curve[wavelength_index, mode_index]
                        * config.reference_stress_mpa
                    ),
                    vector=vector,
                    eigenvector_id=_vector_id(float(wavelength), branch_id, vector),
                    mac_to_previous=mac_values[wavelength_index][branch_id],
                    participation=participation,
                    reconstruction_error=residual,
                    basis_condition_number=basis_condition_number,
                    basis_rank=basis_rank,
                    basis_dimension=basis_dimension,
                )
            )
    return _CurveAnalysis(mesh=mesh, points=tuple(points))


def _leading_structural_family(participation: ModeParticipation) -> BucklingModeFamily:
    return max(participation.structural(), key=lambda item: item[1])[0]


def _candidate_points(analysis: _CurveAnalysis) -> tuple[_Point, ...]:
    candidates: list[_Point] = []
    branches = sorted({point.branch_id for point in analysis.points})
    for branch_id in branches:
        branch = tuple(
            point for point in analysis.points if point.branch_id == branch_id
        )
        for index in range(1, len(branch) - 1):
            current = branch[index]
            if (
                current.critical_stress_mpa <= branch[index - 1].critical_stress_mpa
                and current.critical_stress_mpa <= branch[index + 1].critical_stress_mpa
                and (
                    current.critical_stress_mpa < branch[index - 1].critical_stress_mpa
                    or current.critical_stress_mpa < branch[index + 1].critical_stress_mpa
                )
            ):
                candidates.append(current)
        for endpoint in (branch[0], branch[-1]):
            if _leading_structural_family(endpoint.participation) is BucklingModeFamily.GLOBAL:
                candidates.append(endpoint)

    by_family: dict[BucklingModeFamily, _Point] = {}
    for point in candidates:
        family = _leading_structural_family(point.participation)
        existing = by_family.get(family)
        if existing is None or point.critical_stress_mpa < existing.critical_stress_mpa:
            by_family[family] = point
    return tuple(by_family[family] for family in sorted(by_family, key=lambda item: item.value))


def _find_family_candidate(
    analysis: _CurveAnalysis,
    family: BucklingModeFamily,
) -> _Point | None:
    return next(
        (
            point
            for point in _candidate_points(analysis)
            if _leading_structural_family(point.participation) is family
        ),
        None,
    )


def _branch_points(
    analysis: _CurveAnalysis,
) -> dict[int, tuple[_Point, ...]]:
    return {
        branch: tuple(point for point in analysis.points if point.branch_id == branch)
        for branch in sorted({point.branch_id for point in analysis.points})
    }


def _unresolved_section_boundaries(
    analysis: _CurveAnalysis,
) -> tuple[bool, bool]:
    """Return lower/upper flags when an L/D branch is still falling at a boundary."""

    lower = False
    upper = False
    for branch in _branch_points(analysis).values():
        if len(branch) < 2:
            continue
        first_family = _leading_structural_family(branch[0].participation)
        last_family = _leading_structural_family(branch[-1].participation)
        if (
            first_family
            in (BucklingModeFamily.LOCAL, BucklingModeFamily.DISTORTIONAL)
            and branch[0].critical_stress_mpa <= branch[1].critical_stress_mpa
        ):
            lower = True
        if (
            last_family
            in (BucklingModeFamily.LOCAL, BucklingModeFamily.DISTORTIONAL)
            and branch[-1].critical_stress_mpa <= branch[-2].critical_stress_mpa
        ):
            upper = True
    return lower, upper


def _refinement_additions(
    analysis: _CurveAnalysis,
    wavelengths: tuple[float, ...],
    *,
    allow_lower_expansion: bool,
    allow_upper_expansion: bool,
) -> tuple[tuple[float, ...], tuple[BucklingModeFamily, ...], bool, bool]:
    additions: set[float] = set()
    families: set[BucklingModeFamily] = set()
    branches = _branch_points(analysis)
    for candidate in _candidate_points(analysis):
        family = _leading_structural_family(candidate.participation)
        if family not in (
            BucklingModeFamily.LOCAL,
            BucklingModeFamily.DISTORTIONAL,
        ):
            continue
        branch = branches[candidate.branch_id]
        index = branch.index(candidate)
        if not 0 < index < len(branch) - 1:
            continue
        families.add(family)
        additions.add(
            sqrt(
                branch[index - 1].half_wavelength_mm
                * candidate.half_wavelength_mm
            )
        )
        additions.add(
            sqrt(
                candidate.half_wavelength_mm
                * branch[index + 1].half_wavelength_mm
            )
        )

    lower_unresolved, upper_unresolved = _unresolved_section_boundaries(analysis)
    lower_expanded = lower_unresolved and allow_lower_expansion
    upper_expanded = upper_unresolved and allow_upper_expansion
    if lower_expanded:
        additions.add(wavelengths[0] * wavelengths[0] / wavelengths[1])
    if upper_expanded:
        additions.add(wavelengths[-1] * wavelengths[-1] / wavelengths[-2])
    additions.difference_update(wavelengths)
    return (
        tuple(sorted(additions)),
        tuple(sorted(families, key=lambda item: item.value)),
        lower_expanded,
        upper_expanded,
    )


def _shared_node_mode_shape(
    point: _Point,
    mesh: FSMMesh,
    coordinates: tuple[tuple[float, float], ...],
) -> tuple[float, ...]:
    by_coordinate = {
        (round(node.x_mm, 10), round(node.y_mm, 10)): node.index
        for node in mesh.nodes
    }
    node_count = len(mesh.nodes)
    values: list[float] = []
    for coordinate in coordinates:
        index = by_coordinate[coordinate]
        values.extend(point.vector[2 * index : 2 * index + 2])
        values.extend(
            point.vector[
                2 * node_count + 2 * index : 2 * node_count + 2 * index + 2
            ]
        )
    return tuple(values)


def _comparison_mac(
    refined: _Point,
    refined_mesh: FSMMesh,
    coarse: _Point,
    coarse_mesh: FSMMesh,
) -> float:
    if refined_mesh == coarse_mesh:
        return modal_assurance_criterion(refined.vector, coarse.vector)
    refined_coordinates = {
        (round(node.x_mm, 10), round(node.y_mm, 10)) for node in refined_mesh.nodes
    }
    coarse_coordinates = {
        (round(node.x_mm, 10), round(node.y_mm, 10)) for node in coarse_mesh.nodes
    }
    shared = tuple(sorted(refined_coordinates.intersection(coarse_coordinates)))
    if len(shared) < 2:
        raise ValidationError(
            "successive FSM meshes do not retain enough shared M3 vertices"
        )
    return modal_assurance_criterion(
        _shared_node_mode_shape(refined, refined_mesh, shared),
        _shared_node_mode_shape(coarse, coarse_mesh, shared),
    )


def _wavelength_candidates_converged(
    refined: _CurveAnalysis,
    coarse: _CurveAnalysis,
    policy: ClassificationPolicy,
) -> bool:
    candidates = tuple(
        point
        for point in _candidate_points(refined)
        if _leading_structural_family(point.participation)
        in (BucklingModeFamily.LOCAL, BucklingModeFamily.DISTORTIONAL)
    )
    if not candidates:
        return False
    return all(
        _convergence(
            refined=point,
            coarse=_find_family_candidate(
                coarse, _leading_structural_family(point.participation)
            ),
            policy=policy,
            kind="wavelength-grid",
            refined_mesh=refined.mesh,
            coarse_mesh=coarse.mesh,
        ).converged
        for point in candidates
    )


def _refine_wavelength_search(
    *,
    design_input: MemberDesignInput,
    mesh: FSMMesh,
    config: ElasticBucklingAnalysisConfig,
) -> _WavelengthSearchRun:
    initial = config.half_wavelengths_mm
    current_wavelengths = initial
    current = _classify_curve(
        design_input=design_input,
        mesh=mesh,
        config=config,
        wavelengths=current_wavelengths,
    )
    previous: _CurveAnalysis | None = None
    steps: list[WavelengthRefinementStep] = []
    lower_expansions = 0
    upper_expansions = 0

    if config.perform_wavelength_refinement:
        for iteration in range(1, config.wavelength_refinement_limit + 1):
            additions, families, lower_expanded, upper_expanded = (
                _refinement_additions(
                    current,
                    current_wavelengths,
                    allow_lower_expansion=(
                        lower_expansions < config.boundary_expansion_limit
                    ),
                    allow_upper_expansion=(
                        upper_expansions < config.boundary_expansion_limit
                    ),
                )
            )
            if not additions:
                break
            lower_expansions += int(lower_expanded)
            upper_expansions += int(upper_expanded)
            refined_wavelengths = tuple(sorted(set(current_wavelengths + additions)))
            refined = _classify_curve(
                design_input=design_input,
                mesh=mesh,
                config=config,
                wavelengths=refined_wavelengths,
            )
            steps.append(
                WavelengthRefinementStep(
                    iteration=iteration,
                    added_half_wavelengths_mm=additions,
                    candidate_families=families,
                    lower_boundary_expanded=lower_expanded,
                    upper_boundary_expanded=upper_expanded,
                )
            )
            previous = current
            current = refined
            current_wavelengths = refined_wavelengths
            lower_unresolved, upper_unresolved = _unresolved_section_boundaries(
                current
            )
            if (
                not lower_unresolved
                and not upper_unresolved
                and _wavelength_candidates_converged(current, previous, config.policy)
            ):
                break

    lower_unresolved, upper_unresolved = _unresolved_section_boundaries(current)
    boundary_satisfied = not lower_unresolved and not upper_unresolved
    evidence = WavelengthSearchEvidence(
        initial_half_wavelengths_mm=initial,
        evaluated_half_wavelengths_mm=current_wavelengths,
        refinement_steps=tuple(steps),
        refinement_limit=config.wavelength_refinement_limit,
        boundary_expansion_limit=config.boundary_expansion_limit,
        boundary_resolution_satisfied=boundary_satisfied,
        notes=(
            "Broad input grid with geometric critical-neighborhood refinement; "
            "LOCAL/DISTORTIONAL falling boundary minima trigger geometric range "
            "expansion. GLOBAL boundary behavior is diagnostic and remains M8B-owned."
        ),
    )
    return _WavelengthSearchRun(
        analysis=current,
        previous_analysis=previous,
        evidence=evidence,
    )


def _convergence(
    *,
    refined: _Point,
    coarse: _Point | None,
    policy: ClassificationPolicy,
    kind: str,
    refined_mesh: FSMMesh,
    coarse_mesh: FSMMesh | None,
) -> ConvergenceEvidence:
    is_mesh = kind == "production-vs-reference-mesh"
    family_agreement = (
        (
            _leading_structural_family(refined.participation)
            is _leading_structural_family(coarse.participation)
        )
        if coarse is not None
        else None
    )
    mode_shape_mac = (
        _comparison_mac(refined, refined_mesh, coarse, coarse_mesh)
        if coarse is not None and coarse_mesh is not None
        else None
    )
    return assess_convergence(
        refined_stress_mpa=refined.critical_stress_mpa,
        refined_wavelength_mm=refined.half_wavelength_mm,
        coarse_stress_mpa=(coarse.critical_stress_mpa if coarse else None),
        coarse_wavelength_mm=(coarse.half_wavelength_mm if coarse else None),
        stress_limit_ratio=(
            policy.max_mesh_stress_change_ratio
            if is_mesh
            else policy.max_wavelength_stress_change_ratio
        ),
        wavelength_limit_ratio=(
            policy.max_mesh_wavelength_change_ratio
            if is_mesh
            else policy.max_wavelength_location_change_ratio
        ),
        comparison_name=kind,
        family_agreement=family_agreement,
        mode_shape_mac=mode_shape_mac,
        minimum_mode_shape_mac=policy.min_tracking_mac,
    )


def _placeholder_classification(
    point: _Point,
    config: ElasticBucklingAnalysisConfig,
) -> ModeClassification:
    return classify_with_evidence(
        point.participation,
        point.reconstruction_error,
        policy=config.policy,
        mac_to_previous=point.mac_to_previous,
        mesh_converged=False,
        wavelength_converged=False,
        basis_condition_number=point.basis_condition_number,
        basis_rank=point.basis_rank,
        basis_dimension=point.basis_dimension,
    )


def _tracked_mode(
    point: _Point,
    classification: ModeClassification,
) -> TrackedMode:
    return TrackedMode(
        branch_id=point.branch_id,
        mode_index=point.mode_index,
        half_wavelength_mm=point.half_wavelength_mm,
        load_factor=point.load_factor,
        critical_stress_mpa=point.critical_stress_mpa,
        eigenvector_id=point.eigenvector_id,
        normalized_eigenvector=point.vector,
        mac_to_previous=point.mac_to_previous,
        classification=classification,
    )


def _trace(
    *,
    design_input: MemberDesignInput,
    mesh: FSMMesh,
    config: ElasticBucklingAnalysisConfig,
    candidates: tuple[ElasticBucklingModeResult, ...],
    wavelength_search: WavelengthSearchEvidence,
) -> CalculationTrace:
    case_id = design_input.resolved_member.member.case_id
    limit_state = LimitStateId("ELASTIC_BUCKLING")
    trace_id = make_trace_id(
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=limit_state,
        trace_name="M9A_UNCONSTRAINED_FSM_MODAL_IDENTIFICATION",
    )
    review_count = sum(
        candidate.classification.status
        is ClassificationStatus.ENGINEERING_REVIEW_REQUIRED
        for candidate in candidates
    )
    diagnostic = (
        EngineeringDiagnostic(
            severity=DiagnosticSeverity.WARNING,
            code="M9A_ENGINEERING_REVIEW_REQUIRED",
            message=(
                f"{review_count} elastic-buckling candidate(s) require explicit "
                "engineering review; no PcrL/PcrD is fabricated."
            ),
        ),
    ) if review_count else ()
    steps = (
        CalculationStep(
            step_id=make_step_id(trace_id, 1),
            name="Deterministic FSM mesh",
            inputs=(
                EngineeringValue(
                    "target_strip_width",
                    config.target_strip_width_mm,
                    EngineeringUnit.MILLIMETRE,
                ),
            )
            + (
                (
                    EngineeringValue(
                        "reference_strip_width",
                        config.reference_strip_width_mm,
                        EngineeringUnit.MILLIMETRE,
                    ),
                )
                if config.reference_strip_width_mm is not None
                else ()
            ),
            results=(
                EngineeringValue(
                    "fsm_node_count",
                    float(len(mesh.nodes)),
                    EngineeringUnit.DIMENSIONLESS,
                ),
            ),
            reference=EquationReference(
                source_type=ReferenceSourceType.MECHANICS,
                title="StructureLab deterministic M3 centerline subdivision",
            ),
        ),
        CalculationStep(
            step_id=make_step_id(trace_id, 2),
            name="Unconstrained FSM eigensolution",
            inputs=(
                EngineeringValue(
                    "reference_stress",
                    config.reference_stress_mpa,
                    EngineeringUnit.MEGAPASCAL,
                ),
            ),
            results=(
                EngineeringValue(
                    "wavelength_count",
                    float(len(wavelength_search.evaluated_half_wavelengths_mm)),
                    EngineeringUnit.DIMENSIONLESS,
                ),
            ),
            reference=EquationReference(
                source_type=ReferenceSourceType.SOFTWARE,
                title="pyCUFSM 0.2.0 unconstrained strip_new eigensolver",
            ),
        ),
        CalculationStep(
            step_id=make_step_id(trace_id, 3),
            name="StructureLab classical cFSM-referenced modal identification",
            results=(
                EngineeringValue(
                    "candidate_count",
                    float(len(candidates)),
                    EngineeringUnit.DIMENSIONLESS,
                ),
            ),
            reference=EquationReference(
                source_type=ReferenceSourceType.SOFTWARE,
                title=(
                    "Independent StructureLab implementation referenced to "
                    "CUFSM v5.66 classify/base_column/base_update/mode_class"
                ),
            ),
            diagnostics=diagnostic,
        ),
        CalculationStep(
            step_id=make_step_id(trace_id, 4),
            name="Adaptive half-wavelength search",
            inputs=(
                EngineeringValue(
                    "initial_wavelength_count",
                    float(len(wavelength_search.initial_half_wavelengths_mm)),
                    EngineeringUnit.DIMENSIONLESS,
                ),
            ),
            results=(
                EngineeringValue(
                    "refinement_iteration_count",
                    float(len(wavelength_search.refinement_steps)),
                    EngineeringUnit.DIMENSIONLESS,
                ),
                EngineeringValue(
                    "boundary_resolution_satisfied",
                    1.0 if wavelength_search.boundary_resolution_satisfied else 0.0,
                    EngineeringUnit.DIMENSIONLESS,
                ),
            ),
            reference=EquationReference(
                source_type=ReferenceSourceType.SOFTWARE,
                title=(
                    "StructureLab nested geometric critical-neighborhood and "
                    "boundary-expansion search"
                ),
            ),
            diagnostics=diagnostic,
        ),
    )
    return CalculationTrace(
        trace_id=trace_id,
        status=(
            CalculationStatus.COMPLETED_WITH_WARNINGS
            if review_count
            else CalculationStatus.COMPLETED
        ),
        steps=steps,
        final_values=(
            EngineeringValue(
                "automatic_candidate_count",
                float(len(candidates) - review_count),
                EngineeringUnit.DIMENSIONLESS,
            ),
            EngineeringValue(
                "engineering_review_candidate_count",
                float(review_count),
                EngineeringUnit.DIMENSIONLESS,
            ),
        ),
        case_id=case_id,
        method=DesignMethod.DSM,
        limit_state=limit_state,
        diagnostics=diagnostic,
        metadata=(
            MetadataEntry("classification_policy_id", config.policy.policy_id),
            MetadataEntry("automatic_classification_only", True),
            MetadataEntry("engineering_selection_present", False),
            MetadataEntry(
                "wavelength_refinement_iterations",
                len(wavelength_search.refinement_steps),
            ),
            MetadataEntry(
                "wavelength_boundary_resolution_satisfied",
                wavelength_search.boundary_resolution_satisfied,
            ),
            MetadataEntry(
                "reference_strip_width_mm",
                (
                    config.reference_strip_width_mm
                    if config.reference_strip_width_mm is not None
                    else "NOT_SUPPLIED"
                ),
            ),
        ),
    )


def analyze_elastic_buckling(
    design_input: MemberDesignInput,
    config: ElasticBucklingAnalysisConfig,
) -> ElasticBucklingResult:
    """Return normalized elastic buckling evidence; never calculate DSM strength."""

    if not isinstance(design_input, MemberDesignInput):
        raise ValidationError("design_input must be MemberDesignInput")
    if not isinstance(config, ElasticBucklingAnalysisConfig):
        raise ValidationError("config must be ElasticBucklingAnalysisConfig")
    section = design_input.resolved_member.section
    if section.catalog_section.family not in (
        SectionFamily.C_LIPPED,
        SectionFamily.C_UNLIPPED,
    ):
        raise UnsupportedFeatureError("M9A supports only lipped and unlipped C sections")
    if not design_input.section_mechanics.design_use_permitted:
        raise ValidationError("section mechanics is blocked by its QA gate")

    centerline = build_centerline_section(
        section.geometry,
        section_id=section.catalog_section.section_id,
    )
    fine_mesh = build_fsm_mesh(
        centerline,
        design_input.section_mechanics.advanced,
        target_strip_width_mm=config.target_strip_width_mm,
    )
    wavelength_search = _refine_wavelength_search(
        design_input=design_input,
        mesh=fine_mesh,
        config=config,
    )
    fine = wavelength_search.analysis
    wavelength_coarse = wavelength_search.previous_analysis

    mesh_reference: _CurveAnalysis | None = None
    if config.perform_mesh_convergence and config.reference_strip_width_mm:
        reference_mesh = build_fsm_mesh(
            centerline,
            design_input.section_mechanics.advanced,
            target_strip_width_mm=config.reference_strip_width_mm,
        )
        mesh_reference = _classify_curve(
            design_input=design_input,
            mesh=reference_mesh,
            config=config,
            wavelengths=wavelength_search.evidence.evaluated_half_wavelengths_mm,
        )

    fine_candidates = _candidate_points(fine)
    candidate_results: list[ElasticBucklingModeResult] = []
    final_classifications: dict[str, ModeClassification] = {}
    by_branch = {
        branch: tuple(point for point in fine.points if point.branch_id == branch)
        for branch in sorted({point.branch_id for point in fine.points})
    }
    all_local_minima = tuple(
        point
        for branch in by_branch.values()
        for index, point in enumerate(branch)
        if 0 < index < len(branch) - 1
        and point.critical_stress_mpa <= branch[index - 1].critical_stress_mpa
        and point.critical_stress_mpa <= branch[index + 1].critical_stress_mpa
    )
    for point in fine_candidates:
        family = _leading_structural_family(point.participation)
        wavelength_convergence = _convergence(
            refined=point,
            coarse=(
                _find_family_candidate(wavelength_coarse, family)
                if wavelength_coarse is not None
                else None
            ),
            policy=config.policy,
            kind="wavelength-grid",
            refined_mesh=fine.mesh,
            coarse_mesh=(wavelength_coarse.mesh if wavelength_coarse else None),
        )
        mesh_convergence = (
            _convergence(
                refined=point,
                coarse=(
                    _find_family_candidate(mesh_reference, family)
                    if mesh_reference is not None
                    else None
                ),
                policy=config.policy,
                kind="production-vs-reference-mesh",
                refined_mesh=fine.mesh,
                coarse_mesh=(mesh_reference.mesh if mesh_reference else None),
            )
            if config.perform_mesh_convergence and mesh_reference is not None
            else ConvergenceEvidence(
                converged=False,
                stress_change_ratio=None,
                wavelength_change_ratio=None,
                coarse_value=None,
                refined_value=point.critical_stress_mpa,
                notes=(
                    "A finer reference mesh was not supplied; production-mesh "
                    "acceptance is unavailable."
                ),
            )
        )
        branch = by_branch[point.branch_id]
        branch_index = branch.index(point)
        previous_point = branch[branch_index - 1] if branch_index > 0 else None
        next_point = branch[branch_index + 1] if branch_index + 1 < len(branch) else None
        competing = tuple(
            item
            for item in all_local_minima
            if item is not point
            and _leading_structural_family(item.participation) is family
            and abs(item.critical_stress_mpa - point.critical_stress_mpa)
            / point.critical_stress_mpa
            <= config.policy.non_unique_minimum_stress_ratio
        )
        classification = classify_with_evidence(
            point.participation,
            point.reconstruction_error,
            policy=config.policy,
            previous_participation=(
                previous_point.participation if previous_point is not None else None
            ),
            next_participation=(
                next_point.participation if next_point is not None else None
            ),
            mac_to_previous=point.mac_to_previous,
            mac_to_next=(next_point.mac_to_previous if next_point is not None else None),
            mesh_converged=mesh_convergence.converged,
            wavelength_converged=wavelength_convergence.converged,
            non_unique_minimum=bool(competing),
            basis_configuration_validated=config.basis_options == _VALIDATED_OPTIONS,
            branch_transition=(
                (
                    previous_point is not None
                    and previous_point.mode_index != point.mode_index
                )
                or (
                    next_point is not None
                    and next_point.mode_index != point.mode_index
                )
            ),
            basis_condition_number=point.basis_condition_number,
            basis_rank=point.basis_rank,
            basis_dimension=point.basis_dimension,
        )
        final_classifications[point.eigenvector_id] = classification
        tracked = _tracked_mode(point, classification)
        candidate_results.append(
            ElasticBucklingModeResult(
                family=family,
                critical_stress_mpa=point.critical_stress_mpa,
                critical_load_n=(
                    point.critical_stress_mpa
                    * design_input.section_mechanics.gross.a_mm2
                ),
                half_wavelength_mm=point.half_wavelength_mm,
                classification=classification,
                tracked_mode=tracked,
                mesh_convergence=mesh_convergence,
                wavelength_convergence=wavelength_convergence,
                dsm_input_eligible=(
                    family in (
                        BucklingModeFamily.LOCAL,
                        BucklingModeFamily.DISTORTIONAL,
                    )
                    and classification.status
                    is ClassificationStatus.AUTOMATIC_ACCEPTED
                ),
                diagnostics=(
                    "GLOBAL remains solver QA only; M8B/AISI E2 is design-authoritative."
                    if family is BucklingModeFamily.GLOBAL
                    else "Automatic modal evidence; DSM resistance is outside M9A."
                ,),
            )
        )

    tracked_modes = tuple(
        _tracked_mode(
            point,
            final_classifications.get(
                point.eigenvector_id,
                _placeholder_classification(point, config),
            ),
        )
        for point in fine.points
    )
    candidates = tuple(candidate_results)
    accepted = tuple(
        item
        for item in candidates
        if item.classification.status is ClassificationStatus.AUTOMATIC_ACCEPTED
    )
    review = tuple(item for item in candidates if item not in accepted)
    trace = _trace(
        design_input=design_input,
        mesh=fine_mesh,
        config=config,
        candidates=candidates,
        wavelength_search=wavelength_search.evidence,
    )
    return ElasticBucklingResult(
        case_id=design_input.resolved_member.member.case_id,
        reference_stress_mpa=config.reference_stress_mpa,
        mesh=fine_mesh,
        tracked_modes=tracked_modes,
        automatic_candidates=candidates,
        accepted_results=accepted,
        engineering_review_required_candidates=review,
        wavelength_search=wavelength_search.evidence,
        solver_provenance=solver_provenance(),
        matlab_validation_provenance=_matlab_validation_provenance(),
        policy=config.policy,
        trace=trace,
        engineering_selection=None,
    )


__all__ = ["ElasticBucklingAnalysisConfig", "analyze_elastic_buckling"]
