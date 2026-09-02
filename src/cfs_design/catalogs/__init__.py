"""Public API for explicit catalog loading, validation, and lookup."""

from .loaders import load_material_catalog, load_section_catalog
from .models import CatalogMetadata, CatalogSource, MaterialCatalog, SectionCatalog
from .registry import CatalogRegistry

__all__ = [
    "CatalogMetadata",
    "CatalogRegistry",
    "CatalogSource",
    "MaterialCatalog",
    "SectionCatalog",
    "load_material_catalog",
    "load_section_catalog",
]
