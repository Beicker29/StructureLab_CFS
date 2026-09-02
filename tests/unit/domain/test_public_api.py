"""Public domain API and architectural representation tests."""

from dataclasses import is_dataclass

import cfs_design.domain as domain


def test_principal_domain_types_are_publicly_exposed() -> None:
    expected = {
        "CatalogSection",
        "DemandCombination",
        "DemandPoint",
        "DemandSet",
        "DesignContext",
        "Material",
        "MemberCase",
        "MemberGeometry",
        "Project",
        "ProjectMetadata",
        "ResolvedMember",
        "ResolvedSection",
        "Restraints",
        "SectionGeometry",
        "SectionProperties",
        "StandardSectionDimensions",
    }
    assert expected <= set(domain.__all__)
    assert all(hasattr(domain, name) for name in expected)


def test_future_section_families_are_representable_without_claiming_support() -> None:
    assert domain.SectionFamily.Z_LIPPED.value == "Z_LIPPED"
    assert domain.SectionFamily.HAT.value == "HAT"


def test_public_domain_dataclasses_are_frozen_and_slotted() -> None:
    value_object_types = (
        domain.CatalogSection,
        domain.DemandCombination,
        domain.DemandPoint,
        domain.DemandSet,
        domain.DesignContext,
        domain.Material,
        domain.MemberCase,
        domain.MemberGeometry,
        domain.Project,
        domain.ProjectMetadata,
        domain.ResolvedMember,
        domain.ResolvedSection,
        domain.Restraints,
        domain.SectionGeometry,
        domain.SectionProperties,
        domain.StandardSectionDimensions,
    )
    for value_object_type in value_object_types:
        assert is_dataclass(value_object_type)
        assert value_object_type.__dataclass_params__.frozen
        assert hasattr(value_object_type, "__slots__")
