"""Current v0.1 software capability matrix tests."""

from dataclasses import replace

import pytest

from cfs_design.domain import (
    DesignFormat,
    DesignMethod,
    GeometryConvention,
    MemberType,
    RunMode,
    SectionFamily,
)
from cfs_design.normative import (
    DesignAction,
    SoftwareSupportStatus,
    UNSUPPORTED_V01_FEATURES,
    evaluate_software_support,
)


@pytest.mark.parametrize("method", [DesignMethod.EWM, DesignMethod.DSM])
def test_lipped_c_lrfd_strong_axis_flexure_is_in_v01_scope(
    resolved_member, design_context, method: DesignMethod
) -> None:
    result = evaluate_software_support(
        resolved_member,
        design_context,
        method,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.SUPPORTED
    strong_axis = next(
        item for item in result.checks if "RESOLVED_STRONG_AXIS" in item.check_id
    )
    assert {item.key: item.value for item in strong_axis.observed}[
        "strong_section_axis"
    ] == "X"


def test_unlipped_c_is_supported(resolved_member, design_context) -> None:
    section = resolved_member.section
    unlipped = replace(
        resolved_member,
        section=replace(
            section,
            catalog_section=replace(
                section.catalog_section, family=SectionFamily.C_UNLIPPED
            ),
            geometry=replace(
                section.geometry,
                section_type=SectionFamily.C_UNLIPPED,
                d1_mm=None,
                d2_mm=None,
                flange_lip_angle_deg=None,
            ),
        ),
    )

    result = evaluate_software_support(
        unlipped,
        design_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.SUPPORTED


def test_axial_compression_is_supported_for_explicit_column(
    compression_member, design_context
) -> None:
    result = evaluate_software_support(
        compression_member,
        design_context,
        DesignMethod.DSM,
        DesignAction.AXIAL_COMPRESSION,
    )

    assert result.status is SoftwareSupportStatus.SUPPORTED


def test_unsupported_section_family_is_software_only(
    resolved_member, design_context
) -> None:
    section = resolved_member.section
    z_member = replace(
        resolved_member,
        section=replace(
            section,
            catalog_section=replace(
                section.catalog_section, family=SectionFamily.Z_LIPPED
            ),
            geometry=replace(
                section.geometry, section_type=SectionFamily.Z_LIPPED
            ),
        ),
    )

    result = evaluate_software_support(
        z_member,
        design_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED
    assert any(
        item.diagnostic is not None
        and item.diagnostic.code == "UNSUPPORTED_SECTION_FAMILY"
        for item in result.checks
    )


def test_asd_is_software_unsupported_not_invalid(
    resolved_member, design_context
) -> None:
    asd_context = replace(design_context, design_format=DesignFormat.ASD)

    result = evaluate_software_support(
        resolved_member,
        asd_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED


def test_other_standard_is_software_unsupported(
    resolved_member, design_context
) -> None:
    other_context = replace(
        design_context, standard_id="OTHER_STANDARD", standard_edition=2020
    )

    result = evaluate_software_support(
        resolved_member,
        other_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED


@pytest.mark.parametrize(
    "action", [DesignAction.SHEAR, DesignAction.COMBINED_AXIAL_FLEXURE]
)
def test_future_actions_are_software_unsupported(
    resolved_member, design_context, action: DesignAction
) -> None:
    result = evaluate_software_support(
        resolved_member, design_context, DesignMethod.DSM, action
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED


@pytest.mark.parametrize(
    "convention",
    [GeometryConvention.FLAT_WIDTHS, GeometryConvention.OUT_TO_OUT],
)
def test_unimplemented_geometry_conventions_are_software_unsupported(
    resolved_member, design_context, convention: GeometryConvention
) -> None:
    section = replace(
        resolved_member.section,
        geometry=replace(
            resolved_member.section.geometry,
            geometry_convention=convention,
        ),
    )
    member = replace(resolved_member, section=section)

    result = evaluate_software_support(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED


@pytest.mark.parametrize(
    "geometry_updates",
    [{"ri_mm": 2.0}, {"web_flange_angle_deg": 89.0}],
)
def test_curved_or_nonorthogonal_geometry_is_unsupported(
    resolved_member, design_context, geometry_updates: dict[str, float]
) -> None:
    geometry = replace(resolved_member.section.geometry, **geometry_updates)
    member = replace(
        resolved_member,
        section=replace(resolved_member.section, geometry=geometry),
    )

    result = evaluate_software_support(
        member,
        design_context,
        DesignMethod.DSM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.UNSUPPORTED


def test_inactive_record_is_invalid_input(resolved_member, design_context) -> None:
    member = replace(
        resolved_member,
        member=replace(resolved_member.member, active=False),
    )

    result = evaluate_software_support(
        member,
        design_context,
        DesignMethod.EWM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.INVALID_INPUT


def test_method_not_selected_is_invalid_input(
    resolved_member, design_context
) -> None:
    ewm_context = replace(
        design_context,
        methods=(DesignMethod.EWM,),
        run_mode=RunMode.EWM,
    )

    result = evaluate_software_support(
        resolved_member,
        ewm_context,
        DesignMethod.DSM,
        DesignAction.STRONG_AXIS_FLEXURE,
    )

    assert result.status is SoftwareSupportStatus.INVALID_INPUT


def test_explicit_exclusion_registry_covers_required_v01_boundaries() -> None:
    assert {
        "SHEAR_DESIGN",
        "COMBINED_AXIAL_FLEXURE_INTERACTION",
        "HOLES_OR_OPENINGS",
        "BUILT_UP_MEMBERS",
        "CONNECTIONS",
        "WEB_CRIPPLING",
        "SEISMIC_SYSTEM_DESIGN",
        "SAP2000_IMPORT",
        "ASD",
        "FLAT_WIDTHS_GEOMETRY",
        "OUT_TO_OUT_GEOMETRY",
        "NONZERO_BEND_RADII",
        "NON_ORTHOGONAL_GEOMETRY",
    } <= set(UNSUPPORTED_V01_FEATURES)
