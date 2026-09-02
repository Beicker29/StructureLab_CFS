"""Immutable calculation-step and calculation-trace records."""

from dataclasses import dataclass
from urllib.parse import quote

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignMethod
from cfs_design.domain._validation import require_non_empty

from .diagnostics import EngineeringDiagnostic, validate_diagnostics
from .enums import CalculationStatus, ReferenceSourceType
from .values import (
    EngineeringValue,
    LimitStateId,
    MetadataEntry,
    validate_engineering_values,
    validate_metadata,
)


def _optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_empty(value, field_name)


@dataclass(frozen=True, slots=True)
class EquationReference:
    """A normative, mechanics, software, or other documentary reference."""

    source_type: ReferenceSourceType
    standard_id: str | None = None
    edition: int | None = None
    clause: str | None = None
    equation_id: str | None = None
    title: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, ReferenceSourceType):
            raise ValidationError("source_type must be ReferenceSourceType")
        for field_name in (
            "standard_id",
            "clause",
            "equation_id",
            "title",
            "notes",
        ):
            _optional_non_empty(getattr(self, field_name), field_name)
        if self.edition is not None and (
            isinstance(self.edition, bool)
            or not isinstance(self.edition, int)
            or self.edition <= 0
        ):
            raise ValidationError("edition must be a positive integer or None")
        if (self.standard_id is None) != (self.edition is None):
            raise ValidationError(
                "standard_id and edition must be supplied together"
            )
        if self.source_type is ReferenceSourceType.STANDARD and (
            self.standard_id is None or self.edition is None
        ):
            raise ValidationError(
                "STANDARD references require standard_id and edition"
            )
        if self.source_type is not ReferenceSourceType.STANDARD and (
            self.standard_id is not None or self.edition is not None
        ):
            raise ValidationError(
                "standard_id and edition are reserved for STANDARD references"
            )
        if not any((self.standard_id, self.clause, self.equation_id, self.title)):
            raise ValidationError("reference must identify at least one source field")


@dataclass(frozen=True, slots=True)
class CalculationStep:
    """One recorded operation; ``expression`` is never executed by this package."""

    step_id: str
    name: str
    results: tuple[EngineeringValue, ...]
    inputs: tuple[EngineeringValue, ...] = ()
    description: str | None = None
    expression: str | None = None
    reference: EquationReference | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        require_non_empty(self.step_id, "step_id")
        require_non_empty(self.name, "name")
        _optional_non_empty(self.description, "description")
        _optional_non_empty(self.expression, "expression")
        validate_engineering_values(self.inputs, "inputs")
        validate_engineering_values(
            self.results,
            "results",
            require_non_empty_collection=True,
        )
        if self.reference is not None and not isinstance(
            self.reference, EquationReference
        ):
            raise ValidationError("reference must be EquationReference or None")
        validate_diagnostics(self.diagnostics)

    @property
    def result(self) -> EngineeringValue | None:
        """Convenience for a single-result step; multi-result steps return None."""

        return self.results[0] if len(self.results) == 1 else None


def _encoded(value: str) -> str:
    return quote(value, safe="-_.~")


def make_trace_id(
    *,
    project_id: str | None = None,
    case_id: str | None = None,
    combination_id: str | None = None,
    demand_point_id: str | None = None,
    method: DesignMethod | None = None,
    limit_state: LimitStateId | None = None,
    trace_name: str | None = None,
) -> str:
    """Build a readable deterministic ID from a fixed identity-field order."""

    for field_name, value in (
        ("project_id", project_id),
        ("case_id", case_id),
        ("combination_id", combination_id),
        ("demand_point_id", demand_point_id),
        ("trace_name", trace_name),
    ):
        _optional_non_empty(value, field_name)
    if method is not None and not isinstance(method, DesignMethod):
        raise ValidationError("method must be DesignMethod or None")
    if limit_state is not None and not isinstance(limit_state, LimitStateId):
        raise ValidationError("limit_state must be LimitStateId or None")
    components: tuple[tuple[str, str | None], ...] = (
        ("project", project_id),
        ("case", case_id),
        ("combination", combination_id),
        ("point", demand_point_id),
        ("method", method.value if method is not None else None),
        ("limit_state", limit_state.value if limit_state is not None else None),
        ("name", trace_name),
    )
    populated = tuple(
        f"{key}={_encoded(value)}" for key, value in components if value is not None
    )
    if not populated:
        raise ValidationError("trace identity requires at least one context field")
    return "trace:" + ":".join(populated)


def make_step_id(trace_id: str, sequence: int) -> str:
    """Build a deterministic one-based step identifier."""

    require_non_empty(trace_id, "trace_id")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValidationError("sequence must be a positive integer")
    return f"{trace_id}:step={sequence:03d}"


@dataclass(frozen=True, slots=True)
class CalculationTrace:
    """Completed or explicitly non-completed engineering calculation record."""

    trace_id: str
    status: CalculationStatus
    steps: tuple[CalculationStep, ...] = ()
    final_values: tuple[EngineeringValue, ...] = ()
    project_id: str | None = None
    case_id: str | None = None
    combination_id: str | None = None
    demand_point_id: str | None = None
    method: DesignMethod | None = None
    limit_state: LimitStateId | None = None
    diagnostics: tuple[EngineeringDiagnostic, ...] = ()
    metadata: tuple[MetadataEntry, ...] = ()

    def __post_init__(self) -> None:
        require_non_empty(self.trace_id, "trace_id")
        if not isinstance(self.status, CalculationStatus):
            raise ValidationError("status must be CalculationStatus")
        for field_name in (
            "project_id",
            "case_id",
            "combination_id",
            "demand_point_id",
        ):
            _optional_non_empty(getattr(self, field_name), field_name)
        if self.method is not None and not isinstance(self.method, DesignMethod):
            raise ValidationError("method must be DesignMethod or None")
        if self.limit_state is not None and not isinstance(
            self.limit_state, LimitStateId
        ):
            raise ValidationError("limit_state must be LimitStateId or None")
        if not isinstance(self.steps, tuple) or any(
            not isinstance(step, CalculationStep) for step in self.steps
        ):
            raise ValidationError("steps must be a tuple of CalculationStep")
        step_ids = tuple(step.step_id for step in self.steps)
        if len(set(step_ids)) != len(step_ids):
            raise ValidationError("step IDs must be unique within a trace")
        validate_engineering_values(self.final_values, "final_values")
        if self.status in (
            CalculationStatus.COMPLETED,
            CalculationStatus.COMPLETED_WITH_WARNINGS,
        ) and (not self.steps or not self.final_values):
            raise ValidationError(
                "completed traces require at least one step and final value"
            )
        if self.status is CalculationStatus.NOT_RUN and (
            self.steps or self.final_values
        ):
            raise ValidationError("NOT_RUN traces cannot contain calculated values")
        validate_diagnostics(self.diagnostics)
        validate_metadata(self.metadata)


__all__ = [
    "CalculationStep",
    "CalculationTrace",
    "EquationReference",
    "make_step_id",
    "make_trace_id",
]
