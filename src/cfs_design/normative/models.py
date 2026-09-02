"""Immutable M7 applicability, support, and eligibility result models."""

from dataclasses import dataclass, field
from urllib.parse import quote

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignMethod
from cfs_design.domain._validation import require_non_empty
from cfs_design.results import (
    ApplicabilityStatus,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EquationReference,
    MetadataEntry,
    ReferenceSourceType,
)
from cfs_design.results.diagnostics import validate_diagnostics
from cfs_design.results.values import validate_metadata

from .enums import DesignAction, SoftwareSupportStatus


_NORMATIVE_STATUSES = frozenset(
    {
        ApplicabilityStatus.APPLICABLE,
        ApplicabilityStatus.NOT_APPLICABLE,
        ApplicabilityStatus.INDETERMINATE,
    }
)


def _encoded(value: str) -> str:
    return quote(value, safe="-_.~")


def make_applicability_check_id(
    *, method: DesignMethod, action: DesignAction, rule_id: str
) -> str:
    """Build a deterministic normative-check ID."""

    if not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod")
    if not isinstance(action, DesignAction):
        raise ValidationError("action must be DesignAction")
    require_non_empty(rule_id, "rule_id")
    return (
        f"applicability:method={_encoded(method.value)}:"
        f"action={_encoded(action.value)}:rule={_encoded(rule_id)}"
    )


def make_software_check_id(
    *, method: DesignMethod, action: DesignAction, capability_id: str
) -> str:
    """Build a deterministic software-support check ID."""

    if not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod")
    if not isinstance(action, DesignAction):
        raise ValidationError("action must be DesignAction")
    require_non_empty(capability_id, "capability_id")
    return (
        f"software:method={_encoded(method.value)}:"
        f"action={_encoded(action.value)}:capability={_encoded(capability_id)}"
    )


@dataclass(frozen=True, slots=True)
class ApplicabilityCheck:
    """One auditable normative condition evaluated from available domain data."""

    check_id: str
    topic: str
    status: ApplicabilityStatus
    observed: tuple[MetadataEntry, ...]
    requirement: str
    reference: EquationReference
    diagnostic: EngineeringDiagnostic | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.check_id, "check_id")
        require_non_empty(self.topic, "topic")
        require_non_empty(self.requirement, "requirement")
        if not isinstance(self.status, ApplicabilityStatus) or (
            self.status not in _NORMATIVE_STATUSES
        ):
            raise ValidationError(
                "applicability check status must be APPLICABLE, "
                "NOT_APPLICABLE, or INDETERMINATE"
            )
        validate_metadata(self.observed, "observed")
        if not isinstance(self.reference, EquationReference):
            raise ValidationError("reference must be EquationReference")
        if self.reference.source_type is not ReferenceSourceType.STANDARD:
            raise ValidationError("normative checks require a STANDARD reference")
        if self.diagnostic is not None and not isinstance(
            self.diagnostic, EngineeringDiagnostic
        ):
            raise ValidationError(
                "diagnostic must be EngineeringDiagnostic or None"
            )


def aggregate_normative_status(
    checks: tuple[ApplicabilityCheck, ...],
) -> ApplicabilityStatus:
    """Aggregate checks conservatively without converting unknowns to failures."""

    if not isinstance(checks, tuple) or not checks:
        raise ValidationError("checks must be a non-empty tuple")
    if any(not isinstance(item, ApplicabilityCheck) for item in checks):
        raise ValidationError("checks must contain ApplicabilityCheck values")
    if any(item.status is ApplicabilityStatus.NOT_APPLICABLE for item in checks):
        return ApplicabilityStatus.NOT_APPLICABLE
    if any(item.status is ApplicabilityStatus.INDETERMINATE for item in checks):
        return ApplicabilityStatus.INDETERMINATE
    return ApplicabilityStatus.APPLICABLE


@dataclass(frozen=True, slots=True)
class NormativeApplicabilityResult:
    """AISI applicability only; no statement about software capability."""

    method: DesignMethod
    action: DesignAction
    status: ApplicabilityStatus
    checks: tuple[ApplicabilityCheck, ...]
    references: tuple[EquationReference, ...] = field(init=False)
    diagnostics: tuple[EngineeringDiagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod")
        if not isinstance(self.action, DesignAction):
            raise ValidationError("action must be DesignAction")
        if not isinstance(self.status, ApplicabilityStatus):
            raise ValidationError("status must be ApplicabilityStatus")
        expected = aggregate_normative_status(self.checks)
        if self.status is not expected:
            raise ValidationError(
                f"normative status {self.status.value} does not match "
                f"aggregated check status {expected.value}"
            )
        identifiers = tuple(item.check_id for item in self.checks)
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError("normative check IDs must be unique")
        references: list[EquationReference] = []
        diagnostics: list[EngineeringDiagnostic] = []
        for check in self.checks:
            if check.reference not in references:
                references.append(check.reference)
            if check.diagnostic is not None:
                diagnostics.append(check.diagnostic)
        object.__setattr__(self, "references", tuple(references))
        object.__setattr__(self, "diagnostics", tuple(diagnostics))


@dataclass(frozen=True, slots=True)
class SoftwareSupportCheck:
    """One independent check against the approved v0.1 software envelope."""

    check_id: str
    topic: str
    status: SoftwareSupportStatus
    observed: tuple[MetadataEntry, ...]
    requirement: str
    diagnostic: EngineeringDiagnostic | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.check_id, "check_id")
        require_non_empty(self.topic, "topic")
        require_non_empty(self.requirement, "requirement")
        if not isinstance(self.status, SoftwareSupportStatus):
            raise ValidationError("status must be SoftwareSupportStatus")
        validate_metadata(self.observed, "observed")
        if self.diagnostic is not None and not isinstance(
            self.diagnostic, EngineeringDiagnostic
        ):
            raise ValidationError(
                "diagnostic must be EngineeringDiagnostic or None"
            )


def aggregate_software_status(
    checks: tuple[SoftwareSupportCheck, ...],
) -> SoftwareSupportStatus:
    """Aggregate software checks, preserving invalid input separately."""

    if not isinstance(checks, tuple) or not checks:
        raise ValidationError("checks must be a non-empty tuple")
    if any(not isinstance(item, SoftwareSupportCheck) for item in checks):
        raise ValidationError("checks must contain SoftwareSupportCheck values")
    if any(item.status is SoftwareSupportStatus.INVALID_INPUT for item in checks):
        return SoftwareSupportStatus.INVALID_INPUT
    if any(item.status is SoftwareSupportStatus.UNSUPPORTED for item in checks):
        return SoftwareSupportStatus.UNSUPPORTED
    return SoftwareSupportStatus.SUPPORTED


@dataclass(frozen=True, slots=True)
class SoftwareSupportResult:
    """Software capability only; it does not state what AISI permits."""

    method: DesignMethod
    action: DesignAction
    status: SoftwareSupportStatus
    checks: tuple[SoftwareSupportCheck, ...]
    software_scope_version: str
    diagnostics: tuple[EngineeringDiagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod")
        if not isinstance(self.action, DesignAction):
            raise ValidationError("action must be DesignAction")
        if not isinstance(self.status, SoftwareSupportStatus):
            raise ValidationError("status must be SoftwareSupportStatus")
        require_non_empty(self.software_scope_version, "software_scope_version")
        expected = aggregate_software_status(self.checks)
        if self.status is not expected:
            raise ValidationError(
                f"software status {self.status.value} does not match "
                f"aggregated check status {expected.value}"
            )
        identifiers = tuple(item.check_id for item in self.checks)
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError("software-support check IDs must be unique")
        diagnostics = tuple(
            item.diagnostic
            for item in self.checks
            if item.diagnostic is not None
        )
        object.__setattr__(self, "diagnostics", diagnostics)


@dataclass(frozen=True, slots=True)
class DesignEligibility:
    """Combined gate retaining independent normative and software reasons."""

    normative: NormativeApplicabilityResult
    software: SoftwareSupportResult
    executable: bool = field(init=False)
    diagnostics: tuple[EngineeringDiagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.normative, NormativeApplicabilityResult):
            raise ValidationError(
                "normative must be NormativeApplicabilityResult"
            )
        if not isinstance(self.software, SoftwareSupportResult):
            raise ValidationError("software must be SoftwareSupportResult")
        if self.normative.method is not self.software.method:
            raise ValidationError("normative and software methods must match")
        if self.normative.action is not self.software.action:
            raise ValidationError("normative and software actions must match")
        executable = (
            self.normative.status is ApplicabilityStatus.APPLICABLE
            and self.software.status is SoftwareSupportStatus.SUPPORTED
        )
        diagnostics = self.normative.diagnostics + self.software.diagnostics
        if not executable:
            diagnostics += (
                EngineeringDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="DESIGN_NOT_ELIGIBLE",
                    message=(
                        "Design execution is blocked by normative applicability, "
                        "software support, or both"
                    ),
                    context=(
                        MetadataEntry(
                            "normative_status", self.normative.status.value
                        ),
                        MetadataEntry("software_status", self.software.status.value),
                    ),
                ),
            )
        validate_diagnostics(diagnostics)
        object.__setattr__(self, "executable", executable)
        object.__setattr__(self, "diagnostics", diagnostics)


__all__ = [
    "ApplicabilityCheck",
    "DesignEligibility",
    "NormativeApplicabilityResult",
    "SoftwareSupportCheck",
    "SoftwareSupportResult",
    "aggregate_normative_status",
    "aggregate_software_status",
    "make_applicability_check_id",
    "make_software_check_id",
]
