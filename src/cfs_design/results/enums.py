"""Shared result identities with intentionally separate status meanings."""

from enum import Enum


class DiagnosticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CalculationStatus(str, Enum):
    """Whether a calculation was executed successfully."""

    NOT_RUN = "NOT_RUN"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class ApplicabilityStatus(str, Enum):
    """Normative applicability identity used by results and M7 rules."""

    NOT_EVALUATED = "NOT_EVALUATED"
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INDETERMINATE = "INDETERMINATE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class DesignCheckStatus(str, Enum):
    """Pass/fail identity, separate from execution and applicability."""

    NOT_EVALUATED = "NOT_EVALUATED"
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class ReferenceSourceType(str, Enum):
    STANDARD = "STANDARD"
    MECHANICS = "MECHANICS"
    SOFTWARE = "SOFTWARE"
    OTHER = "OTHER"


__all__ = [
    "ApplicabilityStatus",
    "CalculationStatus",
    "DesignCheckStatus",
    "DiagnosticSeverity",
    "ReferenceSourceType",
]
