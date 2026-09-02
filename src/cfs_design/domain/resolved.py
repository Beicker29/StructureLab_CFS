"""Shared resolved inputs consumed by future EWM and DSM engines."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError

from .demand import DemandSet
from .enums import SectionFamily
from .material import Material
from .member import MemberCase
from .section import (
    CatalogSection,
    SectionGeometry,
    SectionProperties,
    StandardSectionDimensions,
)
from .section_demand import SectionDemandSet


@dataclass(frozen=True, slots=True)
class ResolvedSection:
    catalog_section: CatalogSection
    geometry: SectionGeometry
    properties: SectionProperties
    standard_dimensions: tuple[StandardSectionDimensions, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.catalog_section, CatalogSection):
            raise ValidationError("catalog_section must be a CatalogSection")
        if not isinstance(self.geometry, SectionGeometry):
            raise ValidationError("geometry must be a SectionGeometry")
        if not isinstance(self.properties, SectionProperties):
            raise ValidationError("properties must be SectionProperties")
        if self.catalog_section.geometry_id != self.geometry.geometry_id:
            raise ValidationError(
                "catalog section geometry_id does not match resolved geometry"
            )
        if self.catalog_section.section_id != self.properties.section_id:
            raise ValidationError(
                "catalog section section_id does not match resolved properties"
            )
        if self.catalog_section.family is not self.geometry.section_type:
            raise ValidationError(
                "catalog section family does not match geometry section_type"
            )
        if not isinstance(self.standard_dimensions, tuple) or any(
            not isinstance(item, StandardSectionDimensions)
            for item in self.standard_dimensions
        ):
            raise ValidationError(
                "standard_dimensions must contain StandardSectionDimensions"
            )
        keys: set[tuple[str, int]] = set()
        for dimensions in self.standard_dimensions:
            if dimensions.geometry_id != self.geometry.geometry_id:
                raise ValidationError(
                    "standard dimensions geometry_id does not match resolved geometry"
                )
            dimensions.validate_for_section_family(self.catalog_section.family)
            if (
                self.catalog_section.family is SectionFamily.C_LIPPED
                and self.geometry.flange_lip_angle_deg is None
            ):
                raise ValidationError(
                    "C_LIPPED standard dimensions require an explicit lip angle"
                )
            key = (dimensions.standard_id, dimensions.standard_edition)
            if key in keys:
                raise ValidationError(
                    "standard dimensions contain a duplicate standard/edition"
                )
            keys.add(key)

    def find_standard_dimensions(
        self,
        standard_id: str,
        standard_edition: int,
    ) -> StandardSectionDimensions | None:
        """Return an exact standard/edition match without fabricating a value."""

        return next(
            (
                item
                for item in self.standard_dimensions
                if item.standard_id == standard_id
                and item.standard_edition == standard_edition
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class ResolvedMember:
    member: MemberCase
    section: ResolvedSection
    material: Material
    demands: DemandSet | SectionDemandSet | None = None
    source_demands: DemandSet | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.member, MemberCase):
            raise ValidationError("member must be a MemberCase")
        if not isinstance(self.section, ResolvedSection):
            raise ValidationError("section must be a ResolvedSection")
        if not isinstance(self.material, Material):
            raise ValidationError("material must be a Material")
        if self.demands is not None and not isinstance(
            self.demands, (DemandSet, SectionDemandSet)
        ):
            raise ValidationError(
                "demands must be DemandSet, SectionDemandSet, or None"
            )
        if isinstance(self.demands, SectionDemandSet):
            if not isinstance(self.source_demands, DemandSet):
                raise ValidationError(
                    "section-axis demands require source_demands as a DemandSet"
                )
            source_combinations = self.source_demands.combinations
            section_combinations = self.demands.combinations
            if len(source_combinations) != len(section_combinations):
                raise ValidationError(
                    "source and section-axis demand combination counts must match"
                )
            for source, section_demands in zip(
                source_combinations, section_combinations
            ):
                if (
                    source.combination_id != section_demands.combination_id
                    or source.case_type != section_demands.case_type
                ):
                    raise ValidationError(
                        "source and section-axis demand combinations must correspond"
                    )
                source_ids = tuple(point.point_id for point in source.points)
                resolved_source_ids = tuple(
                    point.source_point_id for point in section_demands.points
                )
                if source_ids != resolved_source_ids:
                    raise ValidationError(
                        "section-axis demand points must preserve source point order"
                    )
        elif self.source_demands is not None:
            raise ValidationError(
                "source_demands is only valid when demands are section-axis demands"
            )
        if self.member.section_id != self.section.catalog_section.section_id:
            raise ValidationError("member section_id does not match resolved section")
        if self.member.material_id != self.material.material_id:
            raise ValidationError("member material_id does not match resolved material")

    @property
    def section_demands(self) -> SectionDemandSet | None:
        return self.demands if isinstance(self.demands, SectionDemandSet) else None

    @property
    def local_axis_demands(self) -> DemandSet | None:
        if self.source_demands is not None:
            return self.source_demands
        return self.demands if isinstance(self.demands, DemandSet) else None


__all__ = ["ResolvedMember", "ResolvedSection"]
