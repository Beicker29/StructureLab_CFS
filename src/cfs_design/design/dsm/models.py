"""Immutable StructureLab-owned results for M9B DSM axial compression."""

from dataclasses import dataclass
from enum import Enum
from math import isclose, isfinite

from cfs_design.core.exceptions import ValidationError
from cfs_design.design.models import GlobalBucklingResult, GlobalColumnStrength
from cfs_design.domain import DesignFormat, DesignMethod
from cfs_design.normative import SoftwareSupportStatus
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationTrace,
    EngineeringDiagnostic,
    EquationReference,
)
from cfs_design.stability import BucklingModeFamily


class DSMDesignReadiness(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class DSMElasticInputBasis(str, Enum):
    AUTOMATIC = "AUTOMATIC_ELASTIC_BUCKLING_INPUT"
    ENGINEERING_SELECTED = "ENGINEERING_SELECTED_ELASTIC_BUCKLING_INPUT"
    MIXED = "MIXED_AUTOMATIC_AND_ENGINEERING_SELECTED_INPUTS"


class DSMLocalBranch(str, Enum):
    PNE_UPPER_BOUND = "PNE_UPPER_BOUND"
    LOCAL_REDUCTION = "LOCAL_REDUCTION"


class DSMDistortionalBranch(str, Enum):
    PY_UPPER_BOUND = "PY_UPPER_BOUND"
    DISTORTIONAL_REDUCTION = "DISTORTIONAL_REDUCTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DSMGoverningLimitState(str, Enum):
    LOCAL_GLOBAL_INTERACTION = "LOCAL_GLOBAL_INTERACTION"
    DISTORTIONAL = "DISTORTIONAL"


@dataclass(frozen=True, slots=True)
class DSMLocalStrengthResult:
    lambda_l: float
    p_nl_n: float
    branch: DSMLocalBranch

    def __post_init__(self) -> None:
        if not isinstance(self.branch, DSMLocalBranch):
            raise ValidationError("branch must be DSMLocalBranch")
        if not all(isfinite(value) and value > 0.0 for value in (self.lambda_l, self.p_nl_n)):
            raise ValidationError("local DSM strength values must be positive and finite")


@dataclass(frozen=True, slots=True)
class DSMDistortionalStrengthResult:
    lambda_d: float
    p_nd_n: float
    branch: DSMDistortionalBranch

    def __post_init__(self) -> None:
        if self.branch is DSMDistortionalBranch.NOT_APPLICABLE:
            raise ValidationError("a calculated distortional strength cannot be NOT_APPLICABLE")
        if not isinstance(self.branch, DSMDistortionalBranch):
            raise ValidationError("branch must be DSMDistortionalBranch")
        if not all(isfinite(value) and value > 0.0 for value in (self.lambda_d, self.p_nd_n)):
            raise ValidationError(
                "distortional DSM strength values must be positive and finite"
            )


@dataclass(frozen=True, slots=True)
class DSMElasticBucklingProvenance:
    family: BucklingModeFamily
    input_basis: DSMElasticInputBasis
    critical_stress_mpa: float
    critical_load_n: float
    half_wavelength_mm: float
    source_candidate_ids: tuple[str, ...]
    m9a_trace_id: str
    solver_package: str
    solver_version: str
    adapter_version: str
    engineer_confirmed: bool
    selection_reason: str | None = None
    confirmed_by: str | None = None
    selection_provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in (
            BucklingModeFamily.LOCAL,
            BucklingModeFamily.DISTORTIONAL,
        ):
            raise ValidationError("DSM elastic provenance requires LOCAL or DISTORTIONAL")
        if self.input_basis is DSMElasticInputBasis.MIXED:
            raise ValidationError("one elastic input provenance cannot be MIXED")
        for name in (
            "critical_stress_mpa",
            "critical_load_n",
            "half_wavelength_mm",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not isfinite(value)
                or value <= 0
            ):
                raise ValidationError(f"{name} must be positive")
        if not self.source_candidate_ids or any(
            not isinstance(value, str) or not value.strip()
            for value in self.source_candidate_ids
        ):
            raise ValidationError("source_candidate_ids must contain non-empty IDs")
        for name in (
            "m9a_trace_id",
            "solver_package",
            "solver_version",
            "adapter_version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{name} must be a non-empty string")
        selected = self.input_basis is DSMElasticInputBasis.ENGINEERING_SELECTED
        if selected != self.engineer_confirmed:
            raise ValidationError(
                "engineering-selected provenance requires explicit engineer confirmation"
            )
        if selected and (
            self.selection_reason is None
            or self.confirmed_by is None
            or not self.selection_provenance
        ):
            raise ValidationError(
                "engineering-selected provenance requires reason, confirmer, and provenance"
            )
        if not isinstance(self.selection_provenance, tuple) or any(
            not isinstance(value, str) or not value.strip()
            for value in self.selection_provenance
        ):
            raise ValidationError("selection_provenance must contain non-empty strings")
        if not selected and any(
            value is not None for value in (self.selection_reason, self.confirmed_by)
        ):
            raise ValidationError("automatic input cannot claim engineering selection")


@dataclass(frozen=True, slots=True)
class M9AUnavailable:
    """Explicit upstream unsupported state that M9B can propagate without guessing."""

    case_id: str
    reason: str
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValidationError("case_id must be a non-empty string")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValidationError("reason must be a non-empty string")
        if not self.provenance or any(
            not isinstance(value, str) or not value.strip() for value in self.provenance
        ):
            raise ValidationError("M9A unavailable provenance must not be empty")


@dataclass(frozen=True, slots=True)
class DSMCompressionResistance:
    case_id: str
    standard_id: str
    standard_edition: int
    design_method: DesignMethod
    design_format: DesignFormat
    calculation_status: CalculationStatus
    design_readiness: DSMDesignReadiness
    applicability_status: ApplicabilityStatus
    software_support_status: SoftwareSupportStatus
    global_buckling: GlobalBucklingResult | None
    global_column_strength: GlobalColumnStrength | None
    p_y_n: float | None
    p_crl_n: float | None
    lambda_l: float | None
    p_nl_n: float | None
    local_branch: DSMLocalBranch | None
    p_crd_n: float | None
    lambda_d: float | None
    p_nd_n: float | None
    distortional_branch: DSMDistortionalBranch | None
    nominal_strength_n: float | None
    resistance_factor: float | None
    design_strength_n: float | None
    governing_limit_state: DSMGoverningLimitState | None
    local_buckling_provenance: DSMElasticBucklingProvenance | None
    distortional_buckling_provenance: DSMElasticBucklingProvenance | None
    elastic_input_basis: DSMElasticInputBasis | None
    equation_references: tuple[EquationReference, ...]
    trace: CalculationTrace
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("case_id", "standard_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{name} must be a non-empty string")
        if (
            isinstance(self.standard_edition, bool)
            or not isinstance(self.standard_edition, int)
            or self.standard_edition <= 0
        ):
            raise ValidationError("standard_edition must be a positive integer")
        if self.design_method is not DesignMethod.DSM:
            raise ValidationError("DSMCompressionResistance requires method DSM")
        if not isinstance(self.design_format, DesignFormat):
            raise ValidationError("design_format must be DesignFormat")
        if not isinstance(self.calculation_status, CalculationStatus):
            raise ValidationError("calculation_status must be CalculationStatus")
        if not isinstance(self.design_readiness, DSMDesignReadiness):
            raise ValidationError("design_readiness must be DSMDesignReadiness")
        if not isinstance(self.applicability_status, ApplicabilityStatus):
            raise ValidationError("applicability_status must be ApplicabilityStatus")
        if not isinstance(self.software_support_status, SoftwareSupportStatus):
            raise ValidationError(
                "software_support_status must be SoftwareSupportStatus"
            )
        if not isinstance(self.trace, CalculationTrace):
            raise ValidationError("trace must be CalculationTrace")
        if self.trace.status is not self.calculation_status:
            raise ValidationError("trace and DSM calculation statuses must match")
        completed = self.calculation_status in (
            CalculationStatus.COMPLETED,
            CalculationStatus.COMPLETED_WITH_WARNINGS,
        )
        required = (
            self.global_buckling,
            self.global_column_strength,
            self.p_y_n,
            self.p_crl_n,
            self.lambda_l,
            self.p_nl_n,
            self.local_branch,
            self.nominal_strength_n,
            self.resistance_factor,
            self.design_strength_n,
            self.governing_limit_state,
            self.local_buckling_provenance,
            self.elastic_input_basis,
        )
        if completed and (
            self.design_format is not DesignFormat.LRFD
            or
            self.design_readiness is not DSMDesignReadiness.DESIGN_READY
            or self.applicability_status is not ApplicabilityStatus.APPLICABLE
            or self.software_support_status is not SoftwareSupportStatus.SUPPORTED
            or any(value is None for value in required)
        ):
            raise ValidationError("completed DSM result is missing required values")
        if not completed and self.design_readiness is DSMDesignReadiness.DESIGN_READY:
            raise ValidationError("a non-completed DSM result cannot be DESIGN_READY")
        if not completed and any(
            value is not None
            for value in (
                self.global_buckling,
                self.global_column_strength,
                self.p_y_n,
                self.p_crl_n,
                self.lambda_l,
                self.p_nl_n,
                self.p_crd_n,
                self.lambda_d,
                self.p_nd_n,
                self.nominal_strength_n,
                self.resistance_factor,
                self.design_strength_n,
                self.governing_limit_state,
                self.local_buckling_provenance,
                self.distortional_buckling_provenance,
                self.elastic_input_basis,
            )
        ):
            raise ValidationError("non-completed DSM result cannot claim design values")
        if completed and self.distortional_branch is DSMDistortionalBranch.NOT_APPLICABLE:
            if any(
                value is not None
                for value in (
                    self.p_crd_n,
                    self.lambda_d,
                    self.p_nd_n,
                    self.distortional_buckling_provenance,
                )
            ):
                raise ValidationError("non-applicable distortional result cannot retain values")
        elif completed and any(
            value is None
            for value in (
                self.p_crd_n,
                self.lambda_d,
                self.p_nd_n,
                self.distortional_branch,
                self.distortional_buckling_provenance,
            )
        ):
            raise ValidationError("applicable distortional result is incomplete")
        if completed:
            numeric_values = (
                self.p_y_n,
                self.p_crl_n,
                self.lambda_l,
                self.p_nl_n,
                self.nominal_strength_n,
                self.resistance_factor,
                self.design_strength_n,
            ) + (
                ()
                if self.distortional_branch
                is DSMDistortionalBranch.NOT_APPLICABLE
                else (self.p_crd_n, self.lambda_d, self.p_nd_n)
            )
            if any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not isfinite(value)
                or value <= 0.0
                for value in numeric_values
            ):
                raise ValidationError("completed DSM numeric values must be positive and finite")
            if self.p_nl_n > self.global_column_strength.p_ne_n:  # type: ignore[union-attr,operator]
                raise ValidationError("Pnl cannot exceed Pne")
            if self.p_nd_n is not None and self.p_nd_n > self.p_y_n:  # type: ignore[operator]
                raise ValidationError("Pnd cannot exceed Py")
            applicable = [self.p_nl_n]
            if self.p_nd_n is not None:
                applicable.append(self.p_nd_n)
            if self.nominal_strength_n != min(applicable):
                raise ValidationError("Pn must equal the smallest applicable nominal strength")
            if not isclose(
                self.design_strength_n,  # type: ignore[arg-type]
                self.resistance_factor * self.nominal_strength_n,  # type: ignore[operator]
                rel_tol=1.0e-15,
                abs_tol=0.0,
            ):
                raise ValidationError("phiPn must equal phi times Pn")
            expected_basis = {self.local_buckling_provenance.input_basis}  # type: ignore[union-attr]
            if self.distortional_buckling_provenance is not None:
                expected_basis.add(self.distortional_buckling_provenance.input_basis)
            combined_basis = (
                DSMElasticInputBasis.MIXED
                if len(expected_basis) > 1
                else next(iter(expected_basis))
            )
            if self.elastic_input_basis is not combined_basis:
                raise ValidationError("elastic_input_basis does not match family provenance")
        if not isinstance(self.equation_references, tuple) or not self.equation_references:
            raise ValidationError("DSM result requires equation references")
        if any(
            not isinstance(reference, EquationReference)
            for reference in self.equation_references
        ):
            raise ValidationError("equation_references must contain EquationReference values")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(value, EngineeringDiagnostic) for value in self.diagnostics
        ):
            raise ValidationError("diagnostics must contain EngineeringDiagnostic values")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(value, str) or not value.strip() for value in self.warnings
        ):
            raise ValidationError("warnings must contain non-empty strings")
        if (
            self.calculation_status is CalculationStatus.COMPLETED_WITH_WARNINGS
            and not self.warnings
        ):
            raise ValidationError("COMPLETED_WITH_WARNINGS requires warnings")

    @property
    def phi(self) -> float | None:
        return self.resistance_factor

    @property
    def phi_pn_n(self) -> float | None:
        return self.design_strength_n


__all__ = [
    "DSMCompressionResistance",
    "DSMDesignReadiness",
    "DSMDistortionalBranch",
    "DSMDistortionalStrengthResult",
    "DSMElasticBucklingProvenance",
    "DSMElasticInputBasis",
    "DSMGoverningLimitState",
    "DSMLocalBranch",
    "DSMLocalStrengthResult",
    "M9AUnavailable",
]
