"""Immutable StructureLab-owned elastic-buckling result models.

The classes in this module deliberately contain only Python scalars and tuples.
Raw ``pyCUFSM`` and NumPy objects are confined to the adapter implementation.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real

from cfs_design.core.exceptions import ValidationError
from cfs_design.results import CalculationTrace


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    return float(value)


def _positive(value: float, name: str) -> float:
    result = _finite(value, name)
    if result <= 0.0:
        raise ValidationError(f"{name} must be greater than zero")
    return result


def _non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


class BucklingModeFamily(str, Enum):
    GLOBAL = "GLOBAL"
    DISTORTIONAL = "DISTORTIONAL"
    LOCAL = "LOCAL"
    MIXED = "MIXED"
    UNCLASSIFIED = "UNCLASSIFIED"


class ClassificationStatus(str, Enum):
    AUTOMATIC_ACCEPTED = "AUTOMATIC_ACCEPTED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"


class ClassificationMethod(str, Enum):
    CLASSICAL_CFSM_REFERENCE = "CLASSICAL_CFSM_REFERENCE"
    FCFSM_REFERENCE = "FCFSM_REFERENCE"
    ENGINEERING_SELECTION = "ENGINEERING_SELECTION"


class ReviewReason(str, Enum):
    LOCAL_DISTORTIONAL_INTERACTION = "LOCAL_DISTORTIONAL_INTERACTION"
    NO_DOMINANT_FAMILY = "NO_DOMINANT_FAMILY"
    CLASSIFICATION_SENSITIVE_TO_WAVELENGTH = (
        "CLASSIFICATION_SENSITIVE_TO_WAVELENGTH"
    )
    MODE_CROSSING = "MODE_CROSSING"
    BRANCH_TRANSITION = "BRANCH_TRANSITION"
    NON_UNIQUE_MINIMUM = "NON_UNIQUE_MINIMUM"
    SMOOTH_LOCAL_DISTORTIONAL_TRANSITION = (
        "SMOOTH_LOCAL_DISTORTIONAL_TRANSITION"
    )
    BASIS_SENSITIVE = "BASIS_SENSITIVE"
    BASIS_CONFIGURATION_NOT_VALIDATED = "BASIS_CONFIGURATION_NOT_VALIDATED"
    RECONSTRUCTION_ERROR = "RECONSTRUCTION_ERROR"
    MESH_SENSITIVE = "MESH_SENSITIVE"
    WAVELENGTH_NOT_CONVERGED = "WAVELENGTH_NOT_CONVERGED"
    REFERENCE_DISAGREEMENT = "REFERENCE_DISAGREEMENT"


@dataclass(frozen=True, slots=True)
class ClassicalBasisOptions:
    """Numeric CUFSM option codes retained for reference traceability.

    The validated production configuration is ``(1, 1, 2, 1)``: ST other
    space, uncoupled basis, axial modal orthogonalization, vector norm.
    """

    ospace: int = 1
    couple: int = 1
    orth: int = 2
    norm: int = 1

    def __post_init__(self) -> None:
        if self.ospace not in (1, 2, 3, 4):
            raise ValidationError("ospace must be one of 1, 2, 3, or 4")
        if self.couple not in (1, 2):
            raise ValidationError("couple must be 1 or 2")
        if self.orth not in (1, 2, 3):
            raise ValidationError("orth must be 1, 2, or 3")
        if self.norm not in (0, 1, 2, 3):
            raise ValidationError("norm must be 0, 1, 2, or 3")


@dataclass(frozen=True, slots=True)
class ClassificationPolicy:
    """Transparent non-normative QA gates for automatic classification.

    These values are evidence gates, not AISI coefficients. A caller may
    adopt a different reviewed policy, but the complete policy is preserved
    in every result through ``policy_id`` and the individual scalar fields.
    """

    policy_id: str = "M9A_CONSERVATIVE_QA_1"
    dominant_min_percent: float = 90.0
    separation_min_percent: float = 50.0
    neighboring_family_min_percent: float = 80.0
    max_neighbor_change_percent: float = 15.0
    min_tracking_mac: float = 0.90
    max_reconstruction_error: float = 1.0e-8
    max_mesh_stress_change_ratio: float = 0.005
    max_mesh_wavelength_change_ratio: float = 0.01
    max_wavelength_stress_change_ratio: float = 0.005
    max_wavelength_location_change_ratio: float = 0.01
    non_unique_minimum_stress_ratio: float = 0.005

    def __post_init__(self) -> None:
        _non_empty(self.policy_id, "policy_id")
        for name in (
            "dominant_min_percent",
            "separation_min_percent",
            "neighboring_family_min_percent",
            "max_neighbor_change_percent",
        ):
            value = _finite(getattr(self, name), name)
            if not 0.0 <= value <= 100.0:
                raise ValidationError(f"{name} must be between 0 and 100")
        for name in (
            "min_tracking_mac",
            "max_reconstruction_error",
            "max_mesh_stress_change_ratio",
            "max_mesh_wavelength_change_ratio",
            "max_wavelength_stress_change_ratio",
            "max_wavelength_location_change_ratio",
            "non_unique_minimum_stress_ratio",
        ):
            value = _finite(getattr(self, name), name)
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ModeParticipation:
    global_percent: float
    distortional_percent: float
    local_percent: float
    other_percent: float

    def __post_init__(self) -> None:
        values = tuple(
            _finite(getattr(self, name), name)
            for name in (
                "global_percent",
                "distortional_percent",
                "local_percent",
                "other_percent",
            )
        )
        if any(value < 0.0 or value > 100.0 for value in values):
            raise ValidationError("modal participation values must be in [0, 100]")
        if abs(sum(values) - 100.0) > 1.0e-6:
            raise ValidationError("modal participation must sum to 100 percent")

    def structural(self) -> tuple[tuple[BucklingModeFamily, float], ...]:
        return (
            (BucklingModeFamily.GLOBAL, self.global_percent),
            (BucklingModeFamily.DISTORTIONAL, self.distortional_percent),
            (BucklingModeFamily.LOCAL, self.local_percent),
        )


@dataclass(frozen=True, slots=True)
class ModeClassification:
    dominant_family: BucklingModeFamily
    status: ClassificationStatus
    participation: ModeParticipation
    separation_percent: float
    reconstruction_error: float
    review_reasons: tuple[ReviewReason, ...]
    method: ClassificationMethod = ClassificationMethod.CLASSICAL_CFSM_REFERENCE
    basis_condition_number: float | None = None
    basis_rank: int | None = None
    basis_dimension: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dominant_family, BucklingModeFamily):
            raise ValidationError("dominant_family must be BucklingModeFamily")
        if not isinstance(self.status, ClassificationStatus):
            raise ValidationError("status must be ClassificationStatus")
        if not isinstance(self.participation, ModeParticipation):
            raise ValidationError("participation must be ModeParticipation")
        separation = _finite(self.separation_percent, "separation_percent")
        if separation < 0.0 or separation > 100.0:
            raise ValidationError("separation_percent must be in [0, 100]")
        residual = _finite(self.reconstruction_error, "reconstruction_error")
        if residual < 0.0:
            raise ValidationError("reconstruction_error must be non-negative")
        if not isinstance(self.review_reasons, tuple) or any(
            not isinstance(item, ReviewReason) for item in self.review_reasons
        ):
            raise ValidationError("review_reasons must be a tuple of ReviewReason")
        if len(set(self.review_reasons)) != len(self.review_reasons):
            raise ValidationError("review_reasons must not contain duplicates")
        if not isinstance(self.method, ClassificationMethod):
            raise ValidationError("method must be ClassificationMethod")
        if self.basis_condition_number is not None:
            condition = _finite(
                self.basis_condition_number, "basis_condition_number"
            )
            if condition < 1.0:
                raise ValidationError("basis_condition_number must be at least one")
        if (self.basis_rank is None) != (self.basis_dimension is None):
            raise ValidationError(
                "basis_rank and basis_dimension must be supplied together"
            )
        if self.basis_rank is not None and self.basis_dimension is not None:
            for name in ("basis_rank", "basis_dimension"):
                value = getattr(self, name)
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    raise ValidationError(f"{name} must be a positive integer")
            if self.basis_rank > self.basis_dimension:
                raise ValidationError("basis_rank cannot exceed basis_dimension")
        if self.status is ClassificationStatus.AUTOMATIC_ACCEPTED and (
            self.review_reasons
            or self.dominant_family
            in (BucklingModeFamily.MIXED, BucklingModeFamily.UNCLASSIFIED)
        ):
            raise ValidationError(
                "automatic classifications cannot retain review reasons or a mixed label"
            )


@dataclass(frozen=True, slots=True)
class FSMNode:
    index: int
    x_mm: float
    y_mm: float
    warping_mm2: float

    def __post_init__(self) -> None:
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ValidationError("node index must be a non-negative integer")
        for name in ("x_mm", "y_mm", "warping_mm2"):
            _finite(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class FSMStrip:
    index: int
    start_node: int
    end_node: int
    thickness_mm: float

    def __post_init__(self) -> None:
        for name in ("index", "start_node", "end_node"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{name} must be a non-negative integer")
        if self.start_node == self.end_node:
            raise ValidationError("a strip must connect two different nodes")
        _positive(self.thickness_mm, "thickness_mm")


@dataclass(frozen=True, slots=True)
class FSMMesh:
    section_id: str
    geometry_id: str
    nodes: tuple[FSMNode, ...]
    strips: tuple[FSMStrip, ...]
    target_strip_width_mm: float
    maximum_actual_strip_width_mm: float
    mesh_version: str = "STRUCTURELAB_FSM_MESH_1"

    def __post_init__(self) -> None:
        _non_empty(self.section_id, "section_id")
        _non_empty(self.geometry_id, "geometry_id")
        _non_empty(self.mesh_version, "mesh_version")
        if not isinstance(self.nodes, tuple) or len(self.nodes) < 2:
            raise ValidationError("nodes must contain at least two FSMNode values")
        if any(not isinstance(item, FSMNode) for item in self.nodes):
            raise ValidationError("nodes must contain only FSMNode values")
        if tuple(node.index for node in self.nodes) != tuple(range(len(self.nodes))):
            raise ValidationError("node indexes must be contiguous from zero")
        if not isinstance(self.strips, tuple) or not self.strips:
            raise ValidationError("strips must be a non-empty tuple")
        if any(not isinstance(item, FSMStrip) for item in self.strips):
            raise ValidationError("strips must contain only FSMStrip values")
        if tuple(strip.index for strip in self.strips) != tuple(range(len(self.strips))):
            raise ValidationError("strip indexes must be contiguous from zero")
        if any(strip.end_node >= len(self.nodes) for strip in self.strips):
            raise ValidationError("strip connectivity references an unknown node")
        _positive(self.target_strip_width_mm, "target_strip_width_mm")
        _positive(
            self.maximum_actual_strip_width_mm,
            "maximum_actual_strip_width_mm",
        )


@dataclass(frozen=True, slots=True)
class TrackedMode:
    branch_id: int
    mode_index: int
    half_wavelength_mm: float
    load_factor: float
    critical_stress_mpa: float
    eigenvector_id: str
    normalized_eigenvector: tuple[float, ...]
    mac_to_previous: float | None
    classification: ModeClassification

    def __post_init__(self) -> None:
        for name in ("branch_id", "mode_index"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{name} must be a non-negative integer")
        for name in ("half_wavelength_mm", "load_factor", "critical_stress_mpa"):
            _positive(getattr(self, name), name)
        _non_empty(self.eigenvector_id, "eigenvector_id")
        if not isinstance(self.normalized_eigenvector, tuple) or not self.normalized_eigenvector:
            raise ValidationError("normalized_eigenvector must be a non-empty tuple")
        if any(not isfinite(value) for value in self.normalized_eigenvector):
            raise ValidationError("normalized_eigenvector must contain finite values")
        if self.mac_to_previous is not None:
            mac = _finite(self.mac_to_previous, "mac_to_previous")
            if mac < 0.0 or mac > 1.0 + 1.0e-12:
                raise ValidationError("mac_to_previous must be in [0, 1]")
        if not isinstance(self.classification, ModeClassification):
            raise ValidationError("classification must be ModeClassification")


@dataclass(frozen=True, slots=True)
class ConvergenceEvidence:
    converged: bool
    stress_change_ratio: float | None
    wavelength_change_ratio: float | None
    coarse_value: float | None
    refined_value: float | None
    notes: str
    family_agreement: bool | None = None
    mode_shape_mac: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.converged, bool):
            raise ValidationError("converged must be bool")
        for name in (
            "stress_change_ratio",
            "wavelength_change_ratio",
            "coarse_value",
            "refined_value",
        ):
            value = getattr(self, name)
            if value is not None and _finite(value, name) < 0.0:
                raise ValidationError(f"{name} must be non-negative or None")
        _non_empty(self.notes, "notes")
        if self.family_agreement is not None and not isinstance(
            self.family_agreement, bool
        ):
            raise ValidationError("family_agreement must be bool or None")
        if self.mode_shape_mac is not None:
            mac = _finite(self.mode_shape_mac, "mode_shape_mac")
            if mac < 0.0 or mac > 1.0 + 1.0e-12:
                raise ValidationError("mode_shape_mac must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class WavelengthRefinementStep:
    iteration: int
    added_half_wavelengths_mm: tuple[float, ...]
    candidate_families: tuple[BucklingModeFamily, ...]
    lower_boundary_expanded: bool
    upper_boundary_expanded: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.iteration, bool)
            or not isinstance(self.iteration, int)
            or self.iteration < 1
        ):
            raise ValidationError("iteration must be a positive integer")
        if not isinstance(self.added_half_wavelengths_mm, tuple) or not (
            self.added_half_wavelengths_mm
        ):
            raise ValidationError(
                "added_half_wavelengths_mm must be a non-empty tuple"
            )
        if any(
            _positive(value, "added_half_wavelengths_mm") <= 0.0
            for value in self.added_half_wavelengths_mm
        ):
            raise ValidationError("refined half-wavelengths must be positive")
        if tuple(sorted(set(self.added_half_wavelengths_mm))) != (
            self.added_half_wavelengths_mm
        ):
            raise ValidationError("refined half-wavelengths must be unique and sorted")
        if not isinstance(self.candidate_families, tuple) or any(
            family not in (
                BucklingModeFamily.LOCAL,
                BucklingModeFamily.DISTORTIONAL,
            )
            for family in self.candidate_families
        ):
            raise ValidationError(
                "candidate_families must contain LOCAL or DISTORTIONAL values"
            )
        if not isinstance(self.lower_boundary_expanded, bool) or not isinstance(
            self.upper_boundary_expanded, bool
        ):
            raise ValidationError("boundary expansion flags must be bool")


@dataclass(frozen=True, slots=True)
class WavelengthSearchEvidence:
    initial_half_wavelengths_mm: tuple[float, ...]
    evaluated_half_wavelengths_mm: tuple[float, ...]
    refinement_steps: tuple[WavelengthRefinementStep, ...]
    refinement_limit: int
    boundary_expansion_limit: int
    boundary_resolution_satisfied: bool
    notes: str

    def __post_init__(self) -> None:
        for name in (
            "initial_half_wavelengths_mm",
            "evaluated_half_wavelengths_mm",
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) < 3:
                raise ValidationError(f"{name} must contain at least three values")
            if any(_positive(value, name) <= 0.0 for value in values):
                raise ValidationError(f"{name} values must be positive")
            if tuple(sorted(set(values))) != values:
                raise ValidationError(f"{name} must be unique and sorted")
        if not isinstance(self.refinement_steps, tuple) or any(
            not isinstance(item, WavelengthRefinementStep)
            for item in self.refinement_steps
        ):
            raise ValidationError(
                "refinement_steps must contain WavelengthRefinementStep"
            )
        for name in ("refinement_limit", "boundary_expansion_limit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{name} must be a non-negative integer")
        if not isinstance(self.boundary_resolution_satisfied, bool):
            raise ValidationError("boundary_resolution_satisfied must be bool")
        _non_empty(self.notes, "notes")


@dataclass(frozen=True, slots=True)
class SolverProvenance:
    package: str
    version: str
    license: str
    pypi_identity: str
    upstream_repository: str
    release_identity: str
    numpy_version: str
    scipy_version: str
    adapter_version: str

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _non_empty(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class MATLABValidationProvenance:
    reference_kind: ClassificationMethod
    implementation: str
    release_identity: str
    upstream_repository: str
    source_archive_sha256: str
    functions: tuple[str, ...]
    execution_runtime: str
    runtime_compatibility_note: str

    def __post_init__(self) -> None:
        if self.reference_kind not in (
            ClassificationMethod.CLASSICAL_CFSM_REFERENCE,
            ClassificationMethod.FCFSM_REFERENCE,
        ):
            raise ValidationError("reference_kind must identify a MATLAB reference")
        for name in (
            "implementation",
            "release_identity",
            "upstream_repository",
            "source_archive_sha256",
            "execution_runtime",
            "runtime_compatibility_note",
        ):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.functions, tuple) or not self.functions:
            raise ValidationError("functions must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.functions):
            raise ValidationError("functions must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class ElasticBucklingModeResult:
    family: BucklingModeFamily
    critical_stress_mpa: float
    critical_load_n: float
    half_wavelength_mm: float
    classification: ModeClassification
    tracked_mode: TrackedMode
    mesh_convergence: ConvergenceEvidence
    wavelength_convergence: ConvergenceEvidence
    dsm_input_eligible: bool
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in (
            BucklingModeFamily.GLOBAL,
            BucklingModeFamily.DISTORTIONAL,
            BucklingModeFamily.LOCAL,
        ):
            raise ValidationError("a candidate result requires a structural mode family")
        for name in ("critical_stress_mpa", "critical_load_n", "half_wavelength_mm"):
            _positive(getattr(self, name), name)
        if not isinstance(self.classification, ModeClassification):
            raise ValidationError("classification must be ModeClassification")
        if not isinstance(self.tracked_mode, TrackedMode):
            raise ValidationError("tracked_mode must be TrackedMode")
        if not isinstance(self.mesh_convergence, ConvergenceEvidence):
            raise ValidationError("mesh_convergence must be ConvergenceEvidence")
        if not isinstance(self.wavelength_convergence, ConvergenceEvidence):
            raise ValidationError("wavelength_convergence must be ConvergenceEvidence")
        if not isinstance(self.dsm_input_eligible, bool):
            raise ValidationError("dsm_input_eligible must be bool")
        expected_eligibility = (
            self.family in (BucklingModeFamily.LOCAL, BucklingModeFamily.DISTORTIONAL)
            and self.classification.status is ClassificationStatus.AUTOMATIC_ACCEPTED
        )
        if self.dsm_input_eligible is not expected_eligibility:
            raise ValidationError(
                "DSM input eligibility requires an automatically accepted LOCAL or "
                "DISTORTIONAL result; GLOBAL remains M8B-authoritative"
            )
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.diagnostics
        ):
            raise ValidationError("diagnostics must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class EngineeringSelection:
    family: BucklingModeFamily
    half_wavelength_mm: float
    critical_stress_mpa: float
    critical_load_n: float
    confirmed_by: str
    reason: str
    candidate_eigenvector_ids: tuple[str, ...]
    engineer_confirmed: bool
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.family not in (
            BucklingModeFamily.GLOBAL,
            BucklingModeFamily.DISTORTIONAL,
            BucklingModeFamily.LOCAL,
        ):
            raise ValidationError("engineering selection requires a structural family")
        for name in ("half_wavelength_mm", "critical_stress_mpa", "critical_load_n"):
            _positive(getattr(self, name), name)
        _non_empty(self.confirmed_by, "confirmed_by")
        _non_empty(self.reason, "reason")
        if not isinstance(self.candidate_eigenvector_ids, tuple) or not self.candidate_eigenvector_ids:
            raise ValidationError("candidate_eigenvector_ids must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.candidate_eigenvector_ids):
            raise ValidationError("candidate_eigenvector_ids contains an invalid ID")
        if self.engineer_confirmed is not True:
            raise ValidationError(
                "an EngineeringSelection must be explicitly engineer-confirmed"
            )
        if not isinstance(self.provenance, tuple) or not self.provenance:
            raise ValidationError("engineering selection provenance must not be empty")
        if any(not isinstance(item, str) or not item.strip() for item in self.provenance):
            raise ValidationError("engineering selection provenance is invalid")

    @property
    def selected_family(self) -> BucklingModeFamily:
        return self.family

    @property
    def selected_half_wavelength_mm(self) -> float:
        return self.half_wavelength_mm

    @property
    def selected_fcr_mpa(self) -> float:
        return self.critical_stress_mpa

    @property
    def selected_pcr_n(self) -> float:
        return self.critical_load_n


@dataclass(frozen=True, slots=True)
class ElasticBucklingResult:
    case_id: str
    reference_stress_mpa: float
    mesh: FSMMesh
    tracked_modes: tuple[TrackedMode, ...]
    automatic_candidates: tuple[ElasticBucklingModeResult, ...]
    accepted_results: tuple[ElasticBucklingModeResult, ...]
    engineering_review_required_candidates: tuple[ElasticBucklingModeResult, ...]
    wavelength_search: WavelengthSearchEvidence
    solver_provenance: SolverProvenance
    matlab_validation_provenance: tuple[MATLABValidationProvenance, ...]
    policy: ClassificationPolicy
    trace: CalculationTrace
    engineering_selection: EngineeringSelection | None = None

    def __post_init__(self) -> None:
        _non_empty(self.case_id, "case_id")
        _positive(self.reference_stress_mpa, "reference_stress_mpa")
        if not isinstance(self.mesh, FSMMesh):
            raise ValidationError("mesh must be FSMMesh")
        if not isinstance(self.tracked_modes, tuple) or any(
            not isinstance(item, TrackedMode) for item in self.tracked_modes
        ):
            raise ValidationError("tracked_modes must be a tuple of TrackedMode")
        for name in (
            "automatic_candidates",
            "accepted_results",
            "engineering_review_required_candidates",
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(
                not isinstance(item, ElasticBucklingModeResult) for item in values
            ):
                raise ValidationError(f"{name} must contain ElasticBucklingModeResult")
        if set(self.accepted_results).intersection(
            self.engineering_review_required_candidates
        ):
            raise ValidationError("accepted and review-required candidates must be disjoint")
        if set(self.automatic_candidates) != set(self.accepted_results).union(
            self.engineering_review_required_candidates
        ):
            raise ValidationError(
                "accepted and review-required candidates must partition "
                "automatic_candidates"
            )
        if not isinstance(self.solver_provenance, SolverProvenance):
            raise ValidationError("solver_provenance must be SolverProvenance")
        if not isinstance(self.wavelength_search, WavelengthSearchEvidence):
            raise ValidationError("wavelength_search must be WavelengthSearchEvidence")
        if not isinstance(self.matlab_validation_provenance, tuple) or any(
            not isinstance(item, MATLABValidationProvenance)
            for item in self.matlab_validation_provenance
        ):
            raise ValidationError(
                "matlab_validation_provenance must contain MATLABValidationProvenance"
            )
        if not isinstance(self.policy, ClassificationPolicy):
            raise ValidationError("policy must be ClassificationPolicy")
        if not isinstance(self.trace, CalculationTrace):
            raise ValidationError("trace must be CalculationTrace")
        if self.engineering_selection is not None and not isinstance(
            self.engineering_selection, EngineeringSelection
        ):
            raise ValidationError(
                "engineering_selection must be EngineeringSelection or None"
            )
        if self.engineering_selection is not None:
            candidate_ids = {
                item.tracked_mode.eigenvector_id for item in self.automatic_candidates
            }
            if not set(
                self.engineering_selection.candidate_eigenvector_ids
            ).issubset(candidate_ids):
                raise ValidationError(
                    "engineering selection must reference recorded automatic candidates"
                )

    @property
    def local_result(self) -> ElasticBucklingModeResult | None:
        return next(
            (
                item
                for item in self.accepted_results
                if item.family is BucklingModeFamily.LOCAL
            ),
            None,
        )

    @property
    def distortional_result(self) -> ElasticBucklingModeResult | None:
        return next(
            (
                item
                for item in self.accepted_results
                if item.family is BucklingModeFamily.DISTORTIONAL
            ),
            None,
        )

    @property
    def global_diagnostic(self) -> ElasticBucklingModeResult | None:
        return next(
            (
                item
                for item in self.automatic_candidates
                if item.family is BucklingModeFamily.GLOBAL
            ),
            None,
        )


__all__ = [
    "BucklingModeFamily",
    "ClassificationMethod",
    "ClassificationPolicy",
    "ClassificationStatus",
    "ClassicalBasisOptions",
    "ConvergenceEvidence",
    "ElasticBucklingModeResult",
    "ElasticBucklingResult",
    "EngineeringSelection",
    "FSMMesh",
    "FSMNode",
    "FSMStrip",
    "MATLABValidationProvenance",
    "ModeClassification",
    "ModeParticipation",
    "ReviewReason",
    "SolverProvenance",
    "TrackedMode",
    "WavelengthRefinementStep",
    "WavelengthSearchEvidence",
]
