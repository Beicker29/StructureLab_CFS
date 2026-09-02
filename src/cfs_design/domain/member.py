"""Physical member, length-definition, and restraint value objects."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_bool,
    require_enum,
    require_finite,
    require_non_empty,
    require_optional_positive,
    require_optional_string,
    require_positive,
)
from .enums import LengthDefinition, MemberType


@dataclass(frozen=True, slots=True)
class MemberGeometry:
    l_mm: float
    length_definition: LengthDefinition
    kx: float | None = None
    ky: float | None = None
    kt: float | None = None
    lx_mm: float | None = None
    ly_mm: float | None = None
    lt_mm: float | None = None
    lb_mm: float | None = None
    orientation_deg: float = 0.0

    def __post_init__(self) -> None:
        require_positive(self.l_mm, "l_mm")
        require_enum(self.length_definition, LengthDefinition, "length_definition")
        require_optional_positive(self.lb_mm, "lb_mm")
        require_finite(self.orientation_deg, "orientation_deg")

        k_values = {"kx": self.kx, "ky": self.ky, "kt": self.kt}
        effective_lengths = {
            "lx_mm": self.lx_mm,
            "ly_mm": self.ly_mm,
            "lt_mm": self.lt_mm,
        }
        if self.length_definition is LengthDefinition.K_FACTORS:
            self._require_complete_positive(k_values, "K-factor")
            self._require_absent(effective_lengths, "effective lengths")
        else:
            self._require_complete_positive(effective_lengths, "effective-length")
            self._require_absent(k_values, "K factors")

    @staticmethod
    def _require_complete_positive(
        values: dict[str, float | None],
        definition_name: str,
    ) -> None:
        missing = [name for name, value in values.items() if value is None]
        if missing:
            raise ValidationError(
                f"{definition_name} definition is missing: {', '.join(missing)}"
            )
        for name, value in values.items():
            if value is not None:
                require_positive(value, name)

    @staticmethod
    def _require_absent(
        values: dict[str, float | None],
        group_name: str,
    ) -> None:
        supplied = [name for name, value in values.items() if value is not None]
        if supplied:
            raise ValidationError(
                f"contradictory {group_name} supplied: {', '.join(supplied)}"
            )


@dataclass(frozen=True, slots=True)
class Restraints:
    x_translation_restrained: bool
    y_translation_restrained: bool
    torsion_restrained: bool
    warping_restrained: bool
    lateral_brace_spacing_mm: float | None = None
    distortional_unbraced_length_mm: float | None = None
    distortional_restraint_source: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "x_translation_restrained",
            "y_translation_restrained",
            "torsion_restrained",
            "warping_restrained",
        ):
            require_bool(getattr(self, field_name), field_name)
        require_optional_positive(
            self.lateral_brace_spacing_mm,
            "lateral_brace_spacing_mm",
        )
        require_optional_positive(
            self.distortional_unbraced_length_mm,
            "distortional_unbraced_length_mm",
        )
        require_optional_string(
            self.distortional_restraint_source,
            "distortional_restraint_source",
        )
        length_supplied = self.distortional_unbraced_length_mm is not None
        source_supplied = self.distortional_restraint_source is not None
        if length_supplied != source_supplied:
            raise ValidationError(
                "distortional_unbraced_length_mm and "
                "distortional_restraint_source must be supplied together"
            )
        if source_supplied:
            require_non_empty(
                self.distortional_restraint_source,
                "distortional_restraint_source",
            )


@dataclass(frozen=True, slots=True)
class MemberCase:
    case_id: str
    label: str
    member_type: MemberType
    section_id: str
    material_id: str
    geometry: MemberGeometry
    restraints: Restraints
    active: bool
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("case_id", "label", "section_id", "material_id"):
            require_non_empty(getattr(self, field_name), field_name)
        require_enum(self.member_type, MemberType, "member_type")
        if not isinstance(self.geometry, MemberGeometry):
            raise ValidationError("geometry must be a MemberGeometry")
        if not isinstance(self.restraints, Restraints):
            raise ValidationError("restraints must be Restraints")
        require_bool(self.active, "active")
        require_optional_string(self.notes, "notes")


__all__ = ["MemberCase", "MemberGeometry", "Restraints"]
