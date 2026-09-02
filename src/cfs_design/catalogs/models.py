"""Immutable catalog-layer metadata, sources, and loaded containers."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TypeVar

from cfs_design.core.exceptions import CatalogError
from cfs_design.domain import (
    CatalogSection,
    Material,
    ResolvedSection,
    SectionGeometry,
    SectionProperties,
    StandardSectionDimensions,
)


RecordType = TypeVar("RecordType")


@dataclass(frozen=True, slots=True)
class CatalogMetadata:
    name: str
    schema_version: str
    canonical_units: str
    description: str
    source_path: Path
    file_sha256: str
    additional_fields: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogSource:
    source_id: str
    source_type: str
    organization: str | None
    document_or_catalog: str
    edition_or_date: str | None
    page_or_table: str | None
    url: str | None
    notes: str | None


def _unique_index(
    records: tuple[RecordType, ...],
    id_attribute: str,
    record_name: str,
) -> Mapping[str, RecordType]:
    index: dict[str, RecordType] = {}
    for record in records:
        identifier: object = record
        for attribute in id_attribute.split("."):
            identifier = getattr(identifier, attribute)
        if not isinstance(identifier, str):
            raise CatalogError(f"{record_name} ID must be a string")
        if identifier in index:
            raise CatalogError(f"Duplicate {record_name} ID: {identifier}")
        index[identifier] = record
    return MappingProxyType(index)


def _require_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise CatalogError(f"{field_name} must be a tuple")


@dataclass(frozen=True, slots=True)
class MaterialCatalog:
    metadata: CatalogMetadata
    sources: tuple[CatalogSource, ...]
    materials: tuple[Material, ...]
    _source_index: Mapping[str, CatalogSource] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _material_index: Mapping[str, Material] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        _require_tuple(self.sources, "sources")
        _require_tuple(self.materials, "materials")
        object.__setattr__(
            self,
            "_source_index",
            _unique_index(self.sources, "source_id", "source"),
        )
        object.__setattr__(
            self,
            "_material_index",
            _unique_index(self.materials, "material_id", "material"),
        )

    def get_material(self, material_id: str) -> Material:
        try:
            return self._material_index[material_id]
        except KeyError as error:
            raise CatalogError(f"Unknown material_id: {material_id}") from error

    def get_source(self, source_id: str) -> CatalogSource:
        try:
            return self._source_index[source_id]
        except KeyError as error:
            raise CatalogError(f"Unknown source_id: {source_id}") from error

    @property
    def active_materials(self) -> tuple[Material, ...]:
        return tuple(material for material in self.materials if material.active)


@dataclass(frozen=True, slots=True)
class SectionCatalog:
    metadata: CatalogMetadata
    sources: tuple[CatalogSource, ...]
    sections: tuple[CatalogSection, ...]
    geometries: tuple[SectionGeometry, ...]
    properties: tuple[SectionProperties, ...]
    resolved_sections: tuple[ResolvedSection, ...]
    standard_dimensions: tuple[StandardSectionDimensions, ...] = ()
    _source_index: Mapping[str, CatalogSource] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _section_index: Mapping[str, ResolvedSection] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _standard_dimension_index: Mapping[
        tuple[str, str, int], StandardSectionDimensions
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        for field_name in (
            "sources",
            "sections",
            "geometries",
            "properties",
            "resolved_sections",
            "standard_dimensions",
        ):
            _require_tuple(getattr(self, field_name), field_name)
        object.__setattr__(
            self,
            "_source_index",
            _unique_index(self.sources, "source_id", "source"),
        )
        object.__setattr__(
            self,
            "_section_index",
            _unique_index(
                self.resolved_sections,
                "catalog_section.section_id",
                "section",
            ),
        )
        dimension_index: dict[
            tuple[str, str, int], StandardSectionDimensions
        ] = {}
        for dimensions in self.standard_dimensions:
            if not isinstance(dimensions, StandardSectionDimensions):
                raise CatalogError(
                    "standard_dimensions must contain StandardSectionDimensions"
                )
            if dimensions.key in dimension_index:
                raise CatalogError(
                    f"Duplicate standard dimension key: {dimensions.key!r}"
                )
            dimension_index[dimensions.key] = dimensions
        object.__setattr__(
            self,
            "_standard_dimension_index",
            MappingProxyType(dimension_index),
        )

    def get_section(self, section_id: str) -> ResolvedSection:
        try:
            return self._section_index[section_id]
        except KeyError as error:
            raise CatalogError(f"Unknown section_id: {section_id}") from error

    def get_source(self, source_id: str) -> CatalogSource:
        try:
            return self._source_index[source_id]
        except KeyError as error:
            raise CatalogError(f"Unknown source_id: {source_id}") from error

    def get_standard_dimensions(
        self,
        geometry_id: str,
        standard_id: str,
        standard_edition: int,
    ) -> StandardSectionDimensions:
        key = (geometry_id, standard_id, standard_edition)
        try:
            return self._standard_dimension_index[key]
        except KeyError as error:
            raise CatalogError(
                "Unknown standard dimensions for "
                f"geometry_id={geometry_id!r}, standard_id={standard_id!r}, "
                f"standard_edition={standard_edition!r}"
            ) from error

    @property
    def active_sections(self) -> tuple[ResolvedSection, ...]:
        return tuple(
            section
            for section in self.resolved_sections
            if section.catalog_section.active
        )


__all__ = [
    "CatalogMetadata",
    "CatalogSource",
    "MaterialCatalog",
    "SectionCatalog",
]
