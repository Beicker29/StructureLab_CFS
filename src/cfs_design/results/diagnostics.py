"""Structured diagnostics preserved with traces and engineering results."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain._validation import require_non_empty

from .enums import DiagnosticSeverity
from .values import MetadataEntry, validate_metadata


@dataclass(frozen=True, slots=True)
class EngineeringDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    context: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.severity, DiagnosticSeverity):
            raise ValidationError("severity must be DiagnosticSeverity")
        require_non_empty(self.code, "code")
        require_non_empty(self.message, "message")
        validate_metadata(self.context, "context")


def validate_diagnostics(
    diagnostics: tuple[EngineeringDiagnostic, ...], field_name: str = "diagnostics"
) -> None:
    if not isinstance(diagnostics, tuple) or any(
        not isinstance(diagnostic, EngineeringDiagnostic)
        for diagnostic in diagnostics
    ):
        raise ValidationError(
            f"{field_name} must be a tuple of EngineeringDiagnostic"
        )


__all__ = ["EngineeringDiagnostic"]
