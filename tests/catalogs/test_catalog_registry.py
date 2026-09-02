"""Catalog container and registry lookup/immutability tests."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cfs_design.catalogs import (
    CatalogRegistry,
    load_material_catalog,
    load_section_catalog,
)
from cfs_design.core.exceptions import CatalogError
from cfs_design.domain import Material, ResolvedSection


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_PATH = REPOSITORY_ROOT / "data" / "catalogs" / "materials_catalog.xlsx"
SECTIONS_PATH = REPOSITORY_ROOT / "data" / "catalogs" / "sections_catalog.xlsx"


@pytest.fixture
def registry() -> CatalogRegistry:
    return CatalogRegistry(
        load_material_catalog(MATERIALS_PATH),
        load_section_catalog(SECTIONS_PATH),
    )


def test_registry_construction(registry: CatalogRegistry) -> None:
    assert len(registry.material_catalog.materials) == 2
    assert len(registry.section_catalog.resolved_sections) == 2


def test_known_material_lookup(registry: CatalogRegistry) -> None:
    material = registry.get_material("EX_MAT_G50")
    assert isinstance(material, Material)
    assert material.material_id == "EX_MAT_G50"


def test_known_section_lookup(registry: CatalogRegistry) -> None:
    section = registry.get_section("EX_SEC_C200_70_20_2")
    assert isinstance(section, ResolvedSection)
    assert section.catalog_section.section_id == "EX_SEC_C200_70_20_2"


def test_unknown_material_fails_clearly(registry: CatalogRegistry) -> None:
    with pytest.raises(CatalogError, match="Unknown material_id: UNKNOWN"):
        registry.get_material("UNKNOWN")


def test_unknown_section_fails_clearly(registry: CatalogRegistry) -> None:
    with pytest.raises(CatalogError, match="Unknown section_id: UNKNOWN"):
        registry.get_section("UNKNOWN")


def test_inactive_items_remain_accessible(registry: CatalogRegistry) -> None:
    assert registry.get_material("EX_MAT_G33").active is False
    assert registry.get_section("EX_SEC_C150_50_15_1P5").catalog_section.active is False
    assert registry.active_materials == ()
    assert registry.active_sections == ()


def test_catalog_collections_are_immutable_tuples(registry: CatalogRegistry) -> None:
    assert isinstance(registry.material_catalog.materials, tuple)
    assert isinstance(registry.section_catalog.resolved_sections, tuple)
    with pytest.raises(TypeError):
        registry.material_catalog.materials[0] = registry.material_catalog.materials[1]  # type: ignore[index]


def test_registry_is_immutable(registry: CatalogRegistry) -> None:
    with pytest.raises(FrozenInstanceError):
        registry.material_catalog = registry.material_catalog  # type: ignore[misc]

