"""Immutable engineering values, limit-state identities, and flat metadata."""

from dataclasses import dataclass, field
from numbers import Real
from typing import TypeAlias

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import EngineeringUnit
from cfs_design.domain._validation import require_finite, require_non_empty


MetadataScalar: TypeAlias = str | int | float | bool | None


def _optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_empty(value, field_name)


@dataclass(frozen=True, slots=True)
class MetadataEntry:
    """One serialization-friendly provenance or diagnostic context value."""

    key: str
    value: MetadataScalar

    def __post_init__(self) -> None:
        require_non_empty(self.key, "key")
        if self.value is not None and not isinstance(
            self.value, (str, int, float, bool)
        ):
            raise ValidationError(
                "metadata value must be a string, integer, float, bool, or None"
            )
        if isinstance(self.value, Real) and not isinstance(self.value, (bool, int)):
            require_finite(self.value, "metadata value")


def validate_metadata(
    entries: tuple[MetadataEntry, ...], field_name: str = "metadata"
) -> None:
    if not isinstance(entries, tuple) or any(
        not isinstance(entry, MetadataEntry) for entry in entries
    ):
        raise ValidationError(f"{field_name} must be a tuple of MetadataEntry")
    keys = tuple(entry.key for entry in entries)
    if len(set(keys)) != len(keys):
        raise ValidationError(f"{field_name} keys must be unique")


@dataclass(frozen=True, slots=True)
class EngineeringValue:
    """One finite, already-normalized engineering scalar with an explicit unit."""

    name: str
    value: float
    unit: EngineeringUnit
    symbol: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.name, "name")
        require_finite(self.value, "value")
        object.__setattr__(self, "value", float(self.value))
        if not isinstance(self.unit, EngineeringUnit):
            raise ValidationError("unit must be an EngineeringUnit")
        _optional_non_empty(self.symbol, "symbol")
        _optional_non_empty(self.description, "description")


@dataclass(frozen=True, slots=True)
class LimitStateId:
    """Extensible controlled identifier without speculative AISI enumeration."""

    value: str
    description: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        require_non_empty(self.value, "value")
        if not self.value[0].isalpha() or any(
            not (character.isupper() or character.isdigit() or character == "_")
            for character in self.value
        ):
            raise ValidationError(
                "limit-state value must use uppercase letters, digits, and underscores"
            )
        _optional_non_empty(self.description, "description")


def validate_engineering_values(
    values: tuple[EngineeringValue, ...],
    field_name: str,
    *,
    require_non_empty_collection: bool = False,
) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(value, EngineeringValue) for value in values
    ):
        raise ValidationError(f"{field_name} must be a tuple of EngineeringValue")
    if require_non_empty_collection and not values:
        raise ValidationError(f"{field_name} must not be empty")
    names = tuple(value.name for value in values)
    if len(set(names)) != len(names):
        raise ValidationError(f"{field_name} names must be unique")


__all__ = [
    "EngineeringValue",
    "LimitStateId",
    "MetadataEntry",
    "MetadataScalar",
]
