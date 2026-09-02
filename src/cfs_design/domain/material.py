"""Material catalog value object."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from ._validation import (
    require_bool,
    require_non_empty,
    require_optional_positive,
    require_optional_string,
    require_positive,
)


@dataclass(frozen=True, slots=True)
class Material:
    material_id: str
    designation: str
    specification: str
    grade: str
    fy_mpa: float
    fu_mpa: float
    e_mpa: float
    nu: float
    density_kg_m3: float | None
    source_id: str
    active: bool
    notes: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "material_id",
            "designation",
            "specification",
            "grade",
            "source_id",
        ):
            require_non_empty(getattr(self, field_name), field_name)
        require_positive(self.fy_mpa, "fy_mpa")
        require_positive(self.fu_mpa, "fu_mpa")
        if self.fu_mpa < self.fy_mpa:
            raise ValidationError("fu_mpa must be greater than or equal to fy_mpa")
        require_positive(self.e_mpa, "e_mpa")
        require_positive(self.nu, "nu")
        if self.nu >= 0.5:
            raise ValidationError("nu must be less than 0.5")
        require_optional_positive(self.density_kg_m3, "density_kg_m3")
        require_bool(self.active, "active")
        require_optional_string(self.notes, "notes")

    @property
    def g_mpa(self) -> float:
        """Return isotropic shear modulus from E and Poisson ratio."""

        return self.e_mpa / (2.0 * (1.0 + self.nu))


__all__ = ["Material"]
