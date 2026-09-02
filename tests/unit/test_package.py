"""Milestone 0 package smoke tests."""

import cfs_design
from cfs_design.core.exceptions import (
    CFSDesignError,
    CatalogError,
    ConfigurationError,
    SchemaError,
    UnsupportedFeatureError,
    ValidationError,
)
from cfs_design.core.units import CANONICAL_UNIT_SYSTEM, CanonicalUnitSystem


def test_package_import_exposes_version() -> None:
    assert isinstance(cfs_design.__version__, str)
    assert cfs_design.__version__


def test_expected_exceptions_share_package_base() -> None:
    expected = (
        CatalogError,
        ConfigurationError,
        SchemaError,
        UnsupportedFeatureError,
        ValidationError,
    )
    assert all(issubclass(exception, CFSDesignError) for exception in expected)


def test_canonical_internal_unit_system_is_si() -> None:
    assert CANONICAL_UNIT_SYSTEM is CanonicalUnitSystem.SI

