"""Project-level design selection metadata without normative calculations."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import require_enum, require_non_empty
from .enums import DesignFormat, DesignMethod, RunMode


@dataclass(frozen=True, slots=True)
class DesignContext:
    standard_id: str
    standard_edition: int
    design_format: DesignFormat
    methods: tuple[DesignMethod, ...]
    run_mode: RunMode
    canonical_units: str

    def __post_init__(self) -> None:
        require_non_empty(self.standard_id, "standard_id")
        if (
            isinstance(self.standard_edition, bool)
            or not isinstance(self.standard_edition, int)
            or self.standard_edition <= 0
        ):
            raise ValidationError("standard_edition must be a positive integer")
        require_enum(self.design_format, DesignFormat, "design_format")
        require_enum(self.run_mode, RunMode, "run_mode")
        require_non_empty(self.canonical_units, "canonical_units")
        if not isinstance(self.methods, tuple):
            raise ValidationError("methods must be a tuple")
        if not self.methods:
            raise ValidationError("methods must contain at least one design method")
        if any(not isinstance(method, DesignMethod) for method in self.methods):
            raise ValidationError("methods must contain only DesignMethod values")
        if len(set(self.methods)) != len(self.methods):
            raise ValidationError("methods must not contain duplicates")


__all__ = ["DesignContext"]

