"""Coherent M3A/M3B mechanics bundle approved for design input."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain._validation import require_non_empty

from .models import AdvancedSectionProperties, ComputedSectionProperties
from .verification import CatalogVerificationResult


@dataclass(frozen=True, slots=True)
class ResolvedSectionMechanics:
    """One coherent M3A/M3B property set and its project QA gate."""

    section_id: str
    gross: ComputedSectionProperties
    advanced: AdvancedSectionProperties
    verification: CatalogVerificationResult | None
    design_use_permitted: bool
    gate_reason: str

    def __post_init__(self) -> None:
        require_non_empty(self.section_id, "section_id")
        if not isinstance(self.gross, ComputedSectionProperties):
            raise ValidationError("gross must be ComputedSectionProperties")
        if not isinstance(self.advanced, AdvancedSectionProperties):
            raise ValidationError("advanced must be AdvancedSectionProperties")
        if self.gross.section_id != self.section_id:
            raise ValidationError("gross section_id must match section_id")
        if self.advanced.section_id != self.section_id:
            raise ValidationError("advanced section_id must match section_id")
        if self.gross.geometry_id != self.advanced.geometry_id:
            raise ValidationError("M3A and M3B geometry_id values must match")
        if self.verification is not None:
            if not isinstance(self.verification, CatalogVerificationResult):
                raise ValidationError(
                    "verification must be CatalogVerificationResult or None"
                )
            if self.verification.section_id != self.section_id:
                raise ValidationError("verification section_id must match section_id")
        if not isinstance(self.design_use_permitted, bool):
            raise ValidationError("design_use_permitted must be bool")
        if self.design_use_permitted and self.verification is None:
            raise ValidationError(
                "design use cannot be permitted without catalog verification"
            )
        require_non_empty(self.gate_reason, "gate_reason")


__all__ = ["ResolvedSectionMechanics"]
