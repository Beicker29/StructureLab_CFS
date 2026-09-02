"""Verified S100-24 applicability behavior without design calculations."""

from dataclasses import replace

import pytest

from cfs_design.domain import DesignMethod, StandardSectionDimensions
from cfs_design.normative import (
    DesignAction,
    evaluate_normative_applicability,
)
from cfs_design.results import ApplicabilityStatus


@pytest.mark.parametrize("method", [DesignMethod.EWM, DesignMethod.DSM])
@pytest.mark.parametrize(
    "action",
    [DesignAction.AXIAL_COMPRESSION, DesignAction.STRONG_AXIS_FLEXURE],
)
def test_current_domain_remains_indeterminate_without_unmodeled_normative_facts(
    resolved_member,
    design_context,
    method: DesignMethod,
    action: DesignAction,
) -> None:
    result = evaluate_normative_applicability(
        resolved_member, design_context, method, action
    )

    assert result.status is ApplicabilityStatus.INDETERMINATE
    assert {item.reference.standard_id for item in result.checks} == {
        "ANSI_SDI_AISI_S100"
    }
    assert {item.reference.edition for item in result.checks} == {2024}
    assert all(item.reference.equation_id is None for item in result.checks)
    assert any(
        item.check_id.endswith("rule=B4_1_ELEMENT_DIMENSIONS")
        and item.status is ApplicabilityStatus.INDETERMINATE
        for item in result.checks
    )


def test_explicit_aisi_dimensions_make_b4_dimension_check_evaluable(
    resolved_member,
    design_context,
) -> None:
    dimensions = StandardSectionDimensions(
        geometry_id=resolved_member.section.geometry.geometry_id,
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        web_flat_width_mm=196.0,
        flange_1_flat_width_mm=66.0,
        flange_2_flat_width_mm=66.0,
        web_out_to_out_depth_mm=204.0,
        flange_1_out_to_out_width_mm=72.0,
        flange_2_out_to_out_width_mm=72.0,
        lip_1_flat_width_mm=16.0,
        lip_2_flat_width_mm=16.0,
        lip_1_out_to_out_width_mm=20.0,
        lip_2_out_to_out_width_mm=20.0,
        lip_1_overall_depth_mm=20.0,
        lip_2_overall_depth_mm=20.0,
        source_id="SYNTHETIC_TEST_SOURCE",
        notes="SYNTHETIC_TEST_DATA",
    )
    section = replace(
        resolved_member.section,
        standard_dimensions=(dimensions,),
    )
    member = replace(resolved_member, section=section)

    result = evaluate_normative_applicability(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )
    dimension_check = next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=B4_1_ELEMENT_DIMENSIONS")
    )

    assert dimension_check.status is ApplicabilityStatus.APPLICABLE
    assert dict(
        (item.key, item.value) for item in dimension_check.observed
    )["dimension_source"] == "SYNTHETIC_TEST_SOURCE"


def test_midline_only_still_leaves_b4_dimension_check_indeterminate(
    resolved_member,
    design_context,
) -> None:
    assert resolved_member.section.standard_dimensions == ()

    result = evaluate_normative_applicability(
        resolved_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )
    dimension_check = next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=B4_1_ELEMENT_DIMENSIONS")
    )

    assert dimension_check.status is ApplicabilityStatus.INDETERMINATE
    assert dimension_check.diagnostic is not None
    assert dimension_check.diagnostic.code == "AISI_B4_DIMENSION_BASIS_UNAVAILABLE"


def test_ewm_b4_yield_limit_can_establish_not_applicable(
    resolved_member, design_context
) -> None:
    high_yield = replace(
        resolved_member,
        material=replace(resolved_member.material, fy_mpa=600.0, fu_mpa=650.0),
    )

    result = evaluate_normative_applicability(
        high_yield,
        design_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is ApplicabilityStatus.NOT_APPLICABLE
    assert any(item.reference.clause == "B4.2" for item in result.checks)
    assert any(
        item.diagnostic.code == "AISI_B4_2_NOT_EVALUATED"
        for item in result.checks
        if item.diagnostic is not None
    )


def test_dsm_has_independently_verified_higher_b4_yield_limit(
    resolved_member, design_context
) -> None:
    material = replace(
        resolved_member.material, fy_mpa=600.0, fu_mpa=650.0
    )
    member = replace(resolved_member, material=material)

    result = evaluate_normative_applicability(
        member,
        design_context,
        DesignMethod.DSM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )
    yield_check = next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=B4_1_YIELD_STRESS")
    )

    assert yield_check.status is ApplicabilityStatus.APPLICABLE
    assert result.status is ApplicabilityStatus.INDETERMINATE


def test_thickness_outside_a1_1_is_not_applicable(
    resolved_member, design_context
) -> None:
    geometry = replace(resolved_member.section.geometry, t_mm=26.0)
    section = replace(resolved_member.section, geometry=geometry)
    member = replace(resolved_member, section=section)

    result = evaluate_normative_applicability(
        member,
        design_context,
        DesignMethod.DSM,
        DesignAction.AXIAL_COMPRESSION,
    )

    assert result.status is ApplicabilityStatus.NOT_APPLICABLE
    assert any(
        item.reference.clause == "A1.1"
        and item.status is ApplicabilityStatus.NOT_APPLICABLE
        for item in result.checks
    )


def test_future_action_is_not_mislabeled_as_normatively_prohibited(
    resolved_member, design_context
) -> None:
    result = evaluate_normative_applicability(
        resolved_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.SHEAR,
    )

    assert result.status is ApplicabilityStatus.INDETERMINATE
    action_check = next(
        item
        for item in result.checks
        if item.check_id.endswith("rule=B3_3_ACTION_ROUTE_NOT_EVALUATED")
    )
    assert action_check.status is ApplicabilityStatus.INDETERMINATE


def test_other_standard_is_not_evaluated_with_s100_24_rules(
    resolved_member, design_context
) -> None:
    other_context = replace(
        design_context, standard_id="OTHER_STANDARD", standard_edition=2020
    )

    result = evaluate_normative_applicability(
        resolved_member,
        other_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is ApplicabilityStatus.INDETERMINATE
    assert len(result.checks) == 1
