"""Project context, project collection, and resolved-member tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    DemandSet,
    DesignContext,
    DesignMethod,
    Material,
    MemberCase,
    Project,
    ProjectMetadata,
    ResolvedMember,
    ResolvedSection,
)


def test_valid_project_metadata(project_metadata: ProjectMetadata) -> None:
    assert project_metadata.project_id == "PRJ_001"


@pytest.mark.parametrize("field_name", ("project_id", "name"))
def test_blank_required_project_metadata_is_rejected(
    project_metadata: ProjectMetadata,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        replace(project_metadata, **{field_name: ""})


def test_valid_design_context(design_context: DesignContext) -> None:
    assert design_context.methods == (DesignMethod.EWM, DesignMethod.DSM)


def test_empty_design_methods_are_rejected(design_context: DesignContext) -> None:
    with pytest.raises(ValidationError):
        replace(design_context, methods=())


def test_duplicate_design_methods_are_rejected(design_context: DesignContext) -> None:
    with pytest.raises(ValidationError):
        replace(design_context, methods=(DesignMethod.EWM, DesignMethod.EWM))


def test_nonpositive_standard_edition_is_rejected(
    design_context: DesignContext,
) -> None:
    with pytest.raises(ValidationError):
        replace(design_context, standard_edition=0)


def test_multiple_members_are_accepted(
    project_metadata: ProjectMetadata,
    design_context: DesignContext,
    member: MemberCase,
) -> None:
    second = replace(member, case_id="MEMBER_002")
    project = Project(project_metadata, design_context, (member, second))
    assert len(project.members) == 2


def test_duplicate_case_ids_are_rejected(
    project_metadata: ProjectMetadata,
    design_context: DesignContext,
    member: MemberCase,
) -> None:
    with pytest.raises(ValidationError):
        Project(project_metadata, design_context, (member, member))


def test_empty_project_is_rejected(
    project_metadata: ProjectMetadata,
    design_context: DesignContext,
) -> None:
    with pytest.raises(ValidationError):
        Project(project_metadata, design_context, ())


def test_valid_resolved_member(
    member: MemberCase,
    resolved_section: ResolvedSection,
    material: Material,
    demand_set: DemandSet,
) -> None:
    resolved = ResolvedMember(member, resolved_section, material, demand_set)
    assert resolved.section is resolved_section


def test_mismatched_member_section_reference_is_rejected(
    member: MemberCase,
    resolved_section: ResolvedSection,
    material: Material,
    demand_set: DemandSet,
) -> None:
    with pytest.raises(ValidationError):
        ResolvedMember(
            replace(member, section_id="OTHER"),
            resolved_section,
            material,
            demand_set,
        )


def test_mismatched_member_material_reference_is_rejected(
    member: MemberCase,
    resolved_section: ResolvedSection,
    material: Material,
    demand_set: DemandSet,
) -> None:
    with pytest.raises(ValidationError):
        ResolvedMember(
            replace(member, material_id="OTHER"),
            resolved_section,
            material,
            demand_set,
        )


def test_core_value_objects_are_immutable(material: Material) -> None:
    with pytest.raises(FrozenInstanceError):
        material.fy_mpa = 300.0  # type: ignore[misc]

