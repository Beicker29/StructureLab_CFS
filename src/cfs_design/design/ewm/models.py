"""Immutable engineering records for M8B axial-compression EWM."""

from dataclasses import dataclass
from enum import Enum

from cfs_design.core.exceptions import ValidationError
from cfs_design.results import (
    ApplicabilityStatus,
    CalculationStatus,
    CalculationTrace,
    EngineeringDiagnostic,
)


class GlobalBucklingMode(str, Enum):
    FLEXURAL_X = "FLEXURAL_X"
    FLEXURAL_Y = "FLEXURAL_Y"
    FLEXURAL_TORSIONAL = "FLEXURAL_TORSIONAL"


class ColumnCurveBranch(str, Enum):
    INELASTIC = "LAMBDA_C_LE_1_5"
    ELASTIC = "LAMBDA_C_GT_1_5"


class PlateElementId(str, Enum):
    WEB = "WEB"
    FLANGE_1 = "FLANGE_1"
    FLANGE_2 = "FLANGE_2"
    LIP_1 = "LIP_1"
    LIP_2 = "LIP_2"


class PlateClassification(str, Enum):
    UNIFORMLY_COMPRESSED_STIFFENED = "UNIFORMLY_COMPRESSED_STIFFENED"
    UNIFORMLY_COMPRESSED_UNSTIFFENED = "UNIFORMLY_COMPRESSED_UNSTIFFENED"
    SIMPLE_LIP_EDGE_STIFFENED_FLANGE = "SIMPLE_LIP_EDGE_STIFFENED_FLANGE"
    SIMPLE_LIP_STIFFENER = "SIMPLE_LIP_STIFFENER"


class NominalLimitState(str, Enum):
    E2_YIELDING_GLOBAL = "E2_YIELDING_GLOBAL"
    E3_1_LOCAL_GLOBAL = "E3_1_LOCAL_GLOBAL"
    E4_DISTORTIONAL = "E4_DISTORTIONAL"


@dataclass(frozen=True, slots=True)
class EffectiveLengths:
    lx_mm: float
    ly_mm: float
    lt_mm: float
    source: str


@dataclass(frozen=True, slots=True)
class GlobalBucklingResult:
    effective_lengths: EffectiveLengths
    ro_mm: float
    p_ex_n: float
    p_ey_n: float
    p_t_n: float
    beta: float
    p_flexural_n: float
    flexural_mode: GlobalBucklingMode
    p_flexural_torsional_n: float
    p_cre_n: float
    f_cre_mpa: float
    governing_mode: GlobalBucklingMode


@dataclass(frozen=True, slots=True)
class GlobalColumnStrength:
    lambda_c: float
    fn_mpa: float
    p_ne_n: float
    branch: ColumnCurveBranch


@dataclass(frozen=True, slots=True)
class EffectiveWidthResult:
    element_id: PlateElementId
    classification: PlateClassification
    full_width_mm: float
    effective_width_mm: float
    plate_coefficient: float | None
    f_crl_mpa: float | None
    slenderness: float | None
    reduction_factor: float | None
    flange_b1_mm: float | None = None
    flange_b2_mm: float | None = None
    s_parameter: float | None = None
    ia_mm4: float | None = None
    is_mm4: float | None = None
    stiffener_ratio: float | None = None
    exponent_n: float | None = None
    d_over_w: float | None = None
    interpretation_id: str | None = None

    def __post_init__(self) -> None:
        if self.effective_width_mm <= 0.0 or self.full_width_mm <= 0.0:
            raise ValidationError("effective and full widths must be positive")
        if self.effective_width_mm > self.full_width_mm:
            raise ValidationError("effective width cannot exceed full width")
        paired = (self.flange_b1_mm, self.flange_b2_mm)
        if any(value is not None for value in paired) and not all(
            value is not None for value in paired
        ):
            raise ValidationError("flange b1 and b2 must be supplied together")


@dataclass(frozen=True, slots=True)
class EffectiveAreaContribution:
    element_id: PlateElementId
    effective_width_mm: float
    thickness_mm: float
    area_mm2: float


@dataclass(frozen=True, slots=True)
class EffectiveAreaResult:
    contributions: tuple[EffectiveAreaContribution, ...]
    ae_mm2: float
    ag_mm2: float

    def __post_init__(self) -> None:
        if not self.contributions:
            raise ValidationError("effective area requires element contributions")
        if self.ae_mm2 <= 0.0 or self.ag_mm2 <= 0.0:
            raise ValidationError("effective and gross areas must be positive")


@dataclass(frozen=True, slots=True)
class FlangeLipProperties:
    af_mm2: float
    jf_mm4: float
    ixf_mm4: float
    iyf_mm4: float
    ixyf_mm4: float
    cwf_mm6: float
    xof_mm: float
    xhf_mm: float
    yof_mm: float
    yhf_mm: float


@dataclass(frozen=True, slots=True)
class DistortionalBucklingResult:
    flange: FlangeLipProperties
    l_crd_mm: float
    l_m_mm: float
    l_d_mm: float
    k_phi_fe_n: float
    k_phi_we_n: float
    k_phi_n: float
    k_phi_fg_mm2: float
    k_phi_wg_mm2: float
    f_crd_mpa: float
    p_crd_n: float


@dataclass(frozen=True, slots=True)
class E4StrengthResult:
    buckling: DistortionalBucklingResult
    p_y_n: float
    lambda_d: float
    p_nd_n: float


@dataclass(frozen=True, slots=True)
class NominalStrengthCandidate:
    limit_state: NominalLimitState
    nominal_strength_n: float
    resistance_factor: float
    design_strength_n: float

    def __post_init__(self) -> None:
        if self.nominal_strength_n <= 0.0:
            raise ValidationError("nominal strength must be positive")
        if not 0.0 < self.resistance_factor <= 1.0:
            raise ValidationError("resistance factor must be in (0, 1]")
        if self.design_strength_n <= 0.0:
            raise ValidationError("design strength must be positive")


@dataclass(frozen=True, slots=True)
class EWMCompressionResistance:
    case_id: str
    calculation_status: CalculationStatus
    applicability_status: ApplicabilityStatus
    global_buckling: GlobalBucklingResult | None
    global_column_strength: GlobalColumnStrength | None
    effective_width_elements: tuple[EffectiveWidthResult, ...]
    effective_area: EffectiveAreaResult | None
    e4_result: E4StrengthResult | None
    candidate_strengths: tuple[NominalStrengthCandidate, ...]
    governing_limit_state: NominalLimitState | None
    nominal_strength_n: float | None
    resistance_factor: float | None
    design_strength_n: float | None
    trace: CalculationTrace
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.trace.status is not self.calculation_status:
            raise ValidationError("trace and resistance calculation statuses must match")
        completed = self.calculation_status in {
            CalculationStatus.COMPLETED,
            CalculationStatus.COMPLETED_WITH_WARNINGS,
        }
        required = (
            self.global_buckling,
            self.global_column_strength,
            self.effective_area,
            self.governing_limit_state,
            self.nominal_strength_n,
            self.resistance_factor,
            self.design_strength_n,
        )
        if completed and (
            any(value is None for value in required)
            or not self.candidate_strengths
            or not self.effective_width_elements
        ):
            raise ValidationError("completed EWM resistance is missing required results")
        if not completed and any(value is not None for value in required):
            raise ValidationError("non-completed EWM resistance cannot claim strength")
        if not completed and self.candidate_strengths:
            raise ValidationError("non-completed EWM resistance cannot retain candidates")
        if not completed and self.effective_width_elements:
            raise ValidationError(
                "non-completed EWM resistance cannot retain effective widths"
            )


__all__ = [
    "ColumnCurveBranch",
    "DistortionalBucklingResult",
    "E4StrengthResult",
    "EWMCompressionResistance",
    "EffectiveAreaContribution",
    "EffectiveAreaResult",
    "EffectiveLengths",
    "EffectiveWidthResult",
    "FlangeLipProperties",
    "GlobalBucklingMode",
    "GlobalBucklingResult",
    "GlobalColumnStrength",
    "NominalLimitState",
    "NominalStrengthCandidate",
    "PlateClassification",
    "PlateElementId",
]
