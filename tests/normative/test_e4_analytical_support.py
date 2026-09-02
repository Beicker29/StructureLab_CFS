"""Software-only gate for the future analytical E4 route."""

from dataclasses import replace

from cfs_design.domain import DesignMethod, StandardSectionDimensions
from cfs_design.normative import (
    DesignAction,
    SoftwareSupportStatus,
    evaluate_normative_applicability,
    evaluate_software_support,
)
from cfs_design.results import ApplicabilityStatus


def _dimensions(member, *, unequal: bool = False) -> StandardSectionDimensions:
    return StandardSectionDimensions(
        geometry_id=member.section.geometry.geometry_id,
        standard_id="ANSI_SDI_AISI_S100",
        standard_edition=2024,
        web_flat_width_mm=196.0,
        flange_1_flat_width_mm=66.0,
        flange_2_flat_width_mm=64.0 if unequal else 66.0,
        web_out_to_out_depth_mm=204.0,
        flange_1_out_to_out_width_mm=72.0,
        flange_2_out_to_out_width_mm=70.0 if unequal else 72.0,
        lip_1_flat_width_mm=16.0,
        lip_2_flat_width_mm=15.0 if unequal else 16.0,
        lip_1_out_to_out_width_mm=20.0,
        lip_2_out_to_out_width_mm=19.0 if unequal else 20.0,
        lip_1_overall_depth_mm=20.0,
        lip_2_overall_depth_mm=19.0 if unequal else 20.0,
        source_id="SYNTHETIC_TEST_SOURCE",
        notes="SYNTHETIC_TEST_DATA",
    )


def _with_e4_inputs(member, *, unequal: bool = False, lm: bool = True):
    section = replace(
        member.section,
        standard_dimensions=(_dimensions(member, unequal=unequal),),
    )
    restraints = replace(
        member.member.restraints,
        distortional_unbraced_length_mm=1800.0 if lm else None,
        distortional_restraint_source=(
            "Synthetic discrete distortional-restraint schedule."
            if lm
            else None
        ),
    )
    return replace(
        member,
        member=replace(member.member, restraints=restraints),
        section=section,
    )


def _check(result, capability: str):
    return next(
        item
        for item in result.checks
        if item.check_id.endswith(f"capability={capability}")
    )


def test_equal_lipped_c_with_explicit_lm_is_potentially_supported(
    compression_member,
    design_context,
) -> None:
    member = _with_e4_inputs(compression_member)

    result = evaluate_software_support(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )

    route = _check(result, "E4_ANALYTICAL_GEOMETRY")
    assert route.status is SoftwareSupportStatus.SUPPORTED
    assert result.status is SoftwareSupportStatus.SUPPORTED
    observed = {item.key: item.value for item in route.observed}
    assert observed["midline_pairs_equal"] is True
    assert observed["standard_dimension_pairs_equal"] is True
    assert observed["exact_equality_tolerance_mm"] == 0.0


def test_unequal_lipped_c_requires_unimplemented_numerical_route(
    compression_member,
    design_context,
) -> None:
    member = _with_e4_inputs(compression_member, unequal=True)

    software = evaluate_software_support(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )
    route = _check(software, "E4_ANALYTICAL_GEOMETRY")

    assert route.status is SoftwareSupportStatus.UNSUPPORTED
    assert route.diagnostic is not None
    assert route.diagnostic.code == "E4_NUMERICAL_ROUTE_UNSUPPORTED"
    assert software.status is SoftwareSupportStatus.UNSUPPORTED

    normative = evaluate_normative_applicability(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )
    dimension_check = next(
        item
        for item in normative.checks
        if item.check_id.endswith("rule=B4_1_ELEMENT_DIMENSIONS")
    )
    assert dimension_check.status is ApplicabilityStatus.APPLICABLE
    assert normative.status is ApplicabilityStatus.INDETERMINATE


def test_missing_explicit_lm_blocks_future_e4_execution(
    compression_member,
    design_context,
) -> None:
    member = _with_e4_inputs(compression_member, lm=False)

    result = evaluate_software_support(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.AXIAL_COMPRESSION,
    )
    lm_check = _check(result, "E4_DISTORTIONAL_RESTRAINT_LENGTH")

    assert lm_check.status is SoftwareSupportStatus.INVALID_INPUT
    assert result.status is SoftwareSupportStatus.INVALID_INPUT
    observed = {item.key: item.value for item in lm_check.observed}
    assert observed["distortional_unbraced_length_mm"] is None
    assert observed["lb_mm"] == 2750.0
    assert observed["lateral_brace_spacing_mm"] == 2750.0
