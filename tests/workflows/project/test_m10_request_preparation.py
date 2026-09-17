"""Production M10 request preparation from one resolved project member."""

from cfs_design.design.dsm import M9AUnavailable
from cfs_design.workflows import prepare_axial_compression_request
from cfs_design.workflows.project import resolve_project
from tests.workflows.project.test_resolver import _activate_example, _project_yaml


def test_prepare_request_selects_one_existing_point_and_shared_physical_input(
    project_root,
) -> None:
    _activate_example(project_root)
    resolved = resolve_project(
        _project_yaml(project_root), repository_root=project_root
    )
    member = resolved.active_resolved_members[0]
    combination = member.section_demands.combinations[0]
    point = combination.points[0]
    unavailable = M9AUnavailable(
        case_id=member.member.case_id,
        reason="Preparation-only controlled M9A state.",
        provenance=("M10_PREPARATION_TEST",),
    )

    request = prepare_axial_compression_request(
        resolved,
        member.member.case_id,
        combination.combination_id,
        point.point_id,
        elastic_buckling=unavailable,
    )

    assert request.demand.point is point
    assert request.demand.combination_id == combination.combination_id
    assert request.demand.case_type == combination.case_type
    assert request.ewm_input.resolved_member is member
    assert request.dsm_input.resolved_member is member
    assert request.ewm_input.section_mechanics is request.dsm_input.section_mechanics
    assert request.ewm_input.design_context is request.dsm_input.design_context

