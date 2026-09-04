"""Immutable mechanics/results shared by the EWM and DSM compression routes."""

from dataclasses import dataclass
from enum import Enum


class GlobalBucklingMode(str, Enum):
    FLEXURAL_X = "FLEXURAL_X"
    FLEXURAL_Y = "FLEXURAL_Y"
    FLEXURAL_TORSIONAL = "FLEXURAL_TORSIONAL"


class ColumnCurveBranch(str, Enum):
    INELASTIC = "LAMBDA_C_LE_1_5"
    ELASTIC = "LAMBDA_C_GT_1_5"


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


__all__ = [
    "ColumnCurveBranch",
    "EffectiveLengths",
    "GlobalBucklingMode",
    "GlobalBucklingResult",
    "GlobalColumnStrength",
]
