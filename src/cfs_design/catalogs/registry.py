"""Single immutable access point for loaded material and section catalogs."""

from dataclasses import dataclass

from cfs_design.core.exceptions import CatalogError
from cfs_design.domain import (
    Material,
    ResolvedSection,
    StandardMaterialQualification,
    StandardSectionDimensions,
)

from .models import MaterialCatalog, SectionCatalog


@dataclass(frozen=True, slots=True)
class CatalogRegistry:
    material_catalog: MaterialCatalog
    section_catalog: SectionCatalog

    def __post_init__(self) -> None:
        if not isinstance(self.material_catalog, MaterialCatalog):
            raise CatalogError("material_catalog must be a MaterialCatalog")
        if not isinstance(self.section_catalog, SectionCatalog):
            raise CatalogError("section_catalog must be a SectionCatalog")

    def get_material(self, material_id: str) -> Material:
        return self.material_catalog.get_material(material_id)

    def get_section(self, section_id: str) -> ResolvedSection:
        return self.section_catalog.get_section(section_id)

    def get_standard_dimensions(
        self,
        geometry_id: str,
        standard_id: str,
        standard_edition: int,
    ) -> StandardSectionDimensions:
        return self.section_catalog.get_standard_dimensions(
            geometry_id,
            standard_id,
            standard_edition,
        )

    def find_material_qualification(
        self,
        material_id: str,
        standard_id: str,
        standard_edition: int,
    ) -> StandardMaterialQualification | None:
        return self.material_catalog.find_material_qualification(
            material_id,
            standard_id,
            standard_edition,
        )

    def get_material_qualification(
        self,
        material_id: str,
        standard_id: str,
        standard_edition: int,
    ) -> StandardMaterialQualification:
        return self.material_catalog.get_material_qualification(
            material_id,
            standard_id,
            standard_edition,
        )

    @property
    def active_materials(self) -> tuple[Material, ...]:
        return self.material_catalog.active_materials

    @property
    def active_sections(self) -> tuple[ResolvedSection, ...]:
        return self.section_catalog.active_sections


__all__ = ["CatalogRegistry"]
