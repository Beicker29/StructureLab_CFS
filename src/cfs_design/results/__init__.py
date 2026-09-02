"""Public generic trace/result infrastructure shared by future EWM and DSM."""

from cfs_design.core.units import EngineeringUnit

from .comparison import ComparisonResult
from .diagnostics import EngineeringDiagnostic
from .enums import (
    ApplicabilityStatus,
    CalculationStatus,
    DesignCheckStatus,
    DiagnosticSeverity,
    ReferenceSourceType,
)
from .limit_states import LimitStateResult
from .member import MemberDesignResult, MethodDesignResult
from .trace import (
    CalculationStep,
    CalculationTrace,
    EquationReference,
    make_step_id,
    make_trace_id,
)
from .values import EngineeringValue, LimitStateId, MetadataEntry, MetadataScalar

__all__ = [
    "ApplicabilityStatus",
    "CalculationStatus",
    "CalculationStep",
    "CalculationTrace",
    "ComparisonResult",
    "DesignCheckStatus",
    "DiagnosticSeverity",
    "EngineeringDiagnostic",
    "EngineeringUnit",
    "EngineeringValue",
    "EquationReference",
    "LimitStateId",
    "LimitStateResult",
    "MemberDesignResult",
    "MetadataEntry",
    "MetadataScalar",
    "MethodDesignResult",
    "ReferenceSourceType",
    "make_step_id",
    "make_trace_id",
]
