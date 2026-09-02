"""Catalog section identity, mechanical geometry, and sourced value objects."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_bool,
    require_enum,
    require_finite,
    require_non_empty,
    require_non_negative,
    require_optional_finite,
    require_optional_non_negative,
    require_optional_positive,
    require_optional_string,
    require_positive,
)
from .enums import GeometryConvention, SectionFamily


def _require_physical_angle(value: float, field_name: str) -> None:
    require_finite(value, field_name)
    if not 0 < value < 180:
        raise ValidationError(f"{field_name} must be between 0 and 180 degrees")


@dataclass(frozen=True, slots=True)
class CatalogSection:
    section_id: str
    designation: str
    family: SectionFamily
    manufacturer: str | None
    geometry_id: str
    source_id: str
    active: bool
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("section_id", "designation", "geometry_id", "source_id"):
            require_non_empty(getattr(self, field_name), field_name)
        require_enum(self.family, SectionFamily, "family")
        require_optional_string(self.manufacturer, "manufacturer")
        require_bool(self.active, "active")
        require_optional_string(self.notes, "notes")


@dataclass(frozen=True, slots=True)
class SectionGeometry:
    geometry_id: str
    section_type: SectionFamily
    h_mm: float
    b1_mm: float
    t_mm: float
    ri_mm: float
    web_flange_angle_deg: float
    geometry_convention: GeometryConvention
    b2_mm: float | None = None
    d1_mm: float | None = None
    d2_mm: float | None = None
    flange_lip_angle_deg: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.geometry_id, "geometry_id")
        require_enum(self.section_type, SectionFamily, "section_type")
        require_enum(
            self.geometry_convention,
            GeometryConvention,
            "geometry_convention",
        )
        require_positive(self.h_mm, "h_mm")
        require_positive(self.b1_mm, "b1_mm")
        require_positive(self.t_mm, "t_mm")
        require_non_negative(self.ri_mm, "ri_mm")
        for field_name in ("b2_mm", "d1_mm", "d2_mm"):
            require_optional_positive(getattr(self, field_name), field_name)
        _require_physical_angle(
            self.web_flange_angle_deg,
            "web_flange_angle_deg",
        )
        if self.flange_lip_angle_deg is not None:
            _require_physical_angle(
                self.flange_lip_angle_deg,
                "flange_lip_angle_deg",
            )
        require_optional_string(self.notes, "notes")


@dataclass(frozen=True, slots=True)
class StandardSectionDimensions:
    """Explicit edition-specific design dimensions, never inferred from geometry."""

    geometry_id: str
    standard_id: str
    standard_edition: int
    web_flat_width_mm: float
    flange_1_flat_width_mm: float
    flange_2_flat_width_mm: float
    source_id: str
    web_out_to_out_depth_mm: float | None = None
    flange_1_out_to_out_width_mm: float | None = None
    flange_2_out_to_out_width_mm: float | None = None
    lip_1_flat_width_mm: float | None = None
    lip_2_flat_width_mm: float | None = None
    lip_1_out_to_out_width_mm: float | None = None
    lip_2_out_to_out_width_mm: float | None = None
    lip_1_overall_depth_mm: float | None = None
    lip_2_overall_depth_mm: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("geometry_id", "standard_id", "source_id"):
            require_non_empty(getattr(self, field_name), field_name)
        if (
            isinstance(self.standard_edition, bool)
            or not isinstance(self.standard_edition, int)
            or self.standard_edition <= 0
        ):
            raise ValidationError("standard_edition must be a positive integer")
        for field_name in (
            "web_flat_width_mm",
            "flange_1_flat_width_mm",
            "flange_2_flat_width_mm",
        ):
            require_positive(getattr(self, field_name), field_name)
        lipped_fields = (
            "web_out_to_out_depth_mm",
            "flange_1_out_to_out_width_mm",
            "flange_2_out_to_out_width_mm",
            "lip_1_flat_width_mm",
            "lip_2_flat_width_mm",
            "lip_1_out_to_out_width_mm",
            "lip_2_out_to_out_width_mm",
            "lip_1_overall_depth_mm",
            "lip_2_overall_depth_mm",
        )
        for field_name in lipped_fields:
            require_optional_positive(getattr(self, field_name), field_name)
        populated = tuple(getattr(self, field_name) is not None for field_name in lipped_fields)
        if any(populated) and not all(populated):
            raise ValidationError(
                "lipped-section AISI dimensions must be supplied as one complete set"
            )
        require_optional_string(self.notes, "notes")

    @property
    def key(self) -> tuple[str, str, int]:
        return self.geometry_id, self.standard_id, self.standard_edition

    @property
    def has_lipped_dimensions(self) -> bool:
        return self.web_out_to_out_depth_mm is not None

    def validate_for_section_family(self, family: SectionFamily) -> None:
        """Validate the family-dependent completeness rule in one domain location."""

        require_enum(family, SectionFamily, "family")
        if family is SectionFamily.C_LIPPED and not self.has_lipped_dimensions:
            raise ValidationError(
                "C_LIPPED standard dimensions require the complete lipped set"
            )
        if family is SectionFamily.C_UNLIPPED and self.has_lipped_dimensions:
            raise ValidationError(
                "C_UNLIPPED standard dimensions must omit lipped-only fields"
            )


@dataclass(frozen=True, slots=True)
class SectionProperties:
    section_id: str
    a_mm2: float
    x_bar_mm: float
    y_bar_mm: float
    ix_mm4: float
    iy_mm4: float
    sx_pos_mm3: float
    sx_neg_mm3: float
    sy_pos_mm3: float
    sy_neg_mm3: float
    rx_mm: float
    ry_mm: float
    j_mm4: float
    property_basis: str
    source_id: str
    ixy_mm4: float | None = None
    i1_mm4: float | None = None
    i2_mm4: float | None = None
    theta_p_deg: float | None = None
    cw_mm6: float | None = None
    x0_mm: float | None = None
    y0_mm: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.section_id, "section_id")
        require_non_empty(self.property_basis, "property_basis")
        require_non_empty(self.source_id, "source_id")
        for field_name in (
            "a_mm2",
            "ix_mm4",
            "iy_mm4",
            "sx_pos_mm3",
            "sx_neg_mm3",
            "sy_pos_mm3",
            "sy_neg_mm3",
            "rx_mm",
            "ry_mm",
            "j_mm4",
        ):
            require_positive(getattr(self, field_name), field_name)
        require_finite(self.x_bar_mm, "x_bar_mm")
        require_finite(self.y_bar_mm, "y_bar_mm")
        require_optional_finite(self.ixy_mm4, "ixy_mm4")
        require_optional_positive(self.i1_mm4, "i1_mm4")
        require_optional_positive(self.i2_mm4, "i2_mm4")
        require_optional_finite(self.theta_p_deg, "theta_p_deg")
        require_optional_non_negative(self.cw_mm6, "cw_mm6")
        require_optional_finite(self.x0_mm, "x0_mm")
        require_optional_finite(self.y0_mm, "y0_mm")
        require_optional_string(self.notes, "notes")


__all__ = [
    "CatalogSection",
    "SectionGeometry",
    "SectionProperties",
    "StandardSectionDimensions",
]
