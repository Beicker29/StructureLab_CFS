"""Catalog QA policy and immutable verification-result tests."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from cfs_design.catalogs import load_section_catalog
from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import ResolvedSection
from cfs_design.mechanics.sections import (
    AdvancedSectionProperties,
    ComputedSectionProperties,
    VerificationPolicy,
    VerificationProperty,
    VerificationStatus,
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
    verify_catalog_properties,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SECTIONS_PATH = REPOSITORY_ROOT / "data" / "catalogs" / "sections_catalog.xlsx"


@pytest.fixture
def resolved() -> ResolvedSection:
    return load_section_catalog(SECTIONS_PATH).get_section("EX_SEC_C200_70_20_2")


@pytest.fixture
def computed(resolved: ResolvedSection) -> ComputedSectionProperties:
    return compute_gross_properties(
        build_centerline_section(
            resolved.geometry,
            section_id=resolved.catalog_section.section_id,
        )
    )


@pytest.fixture
def advanced(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> AdvancedSectionProperties:
    return compute_advanced_properties(
        build_centerline_section(
            resolved.geometry,
            section_id=resolved.catalog_section.section_id,
        ),
        computed,
    )


def _policy(*properties: VerificationProperty) -> VerificationPolicy:
    return VerificationPolicy(
        relative_tolerance=1.0e-4,
        absolute_tolerance=1.0e-8,
        properties_to_check=properties,
        warning_multiplier=2.0,
    )


def test_approved_catalog_passes_strict_basic_property_verification(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    properties = (
        VerificationProperty.A,
        VerificationProperty.X_BAR,
        VerificationProperty.Y_BAR,
        VerificationProperty.IX,
        VerificationProperty.IY,
        VerificationProperty.IXY,
        VerificationProperty.SX_POS,
        VerificationProperty.SX_NEG,
        VerificationProperty.SY_POS,
        VerificationProperty.SY_NEG,
        VerificationProperty.RX,
        VerificationProperty.RY,
        VerificationProperty.J,
        VerificationProperty.I1,
    )
    before = resolved.properties

    result = verify_catalog_properties(resolved, computed, _policy(*properties))

    assert result.overall_status is VerificationStatus.PASS
    assert result.checks[-1].status is VerificationStatus.NOT_CHECKED
    assert resolved.properties is before
    assert tuple(item.property_name for item in result.checks) == properties


@pytest.mark.parametrize(
    ("computed_area", "expected"),
    (
        (771.4, VerificationStatus.WARNING),
        (780.0, VerificationStatus.FAIL),
    ),
)
def test_warning_and_fail_bands_are_explicit(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    computed_area: float,
    expected: VerificationStatus,
) -> None:
    policy = VerificationPolicy(
        relative_tolerance=0.01,
        absolute_tolerance=0.0,
        properties_to_check=(VerificationProperty.A,),
        warning_multiplier=2.0,
    )

    result = verify_catalog_properties(
        resolved,
        replace(computed, a_mm2=computed_area),
        policy,
    )

    assert result.overall_status is expected
    assert result.checks[0].status is expected
    assert result.checks[0].tolerance == pytest.approx(7.6)
    assert result.checks[0].warning_tolerance == pytest.approx(15.2)


def test_zero_catalog_property_uses_absolute_tolerance_without_infinity(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    policy = VerificationPolicy(
        relative_tolerance=0.01,
        absolute_tolerance=1.0e-6,
        properties_to_check=(VerificationProperty.IXY,),
    )
    result = verify_catalog_properties(
        resolved,
        replace(computed, ixy_mm4=5.0e-7),
        policy,
    )

    check = result.checks[0]
    assert check.status is VerificationStatus.PASS
    assert check.relative_difference == pytest.approx(0.5)
    assert check.relative_difference != float("inf")


def test_exact_zero_comparison_reports_zero_relative_difference(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    result = verify_catalog_properties(
        resolved,
        computed,
        VerificationPolicy(
            relative_tolerance=0.0,
            absolute_tolerance=0.0,
            properties_to_check=(VerificationProperty.IXY,),
        ),
    )
    assert result.checks[0].relative_difference == 0.0


def test_optional_missing_catalog_values_are_not_checked(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    result = verify_catalog_properties(
        resolved,
        computed,
        _policy(VerificationProperty.I1, VerificationProperty.I2),
    )
    assert result.overall_status is VerificationStatus.NOT_CHECKED
    assert all(
        item.status is VerificationStatus.NOT_CHECKED for item in result.checks
    )


def test_missing_catalog_advanced_values_are_not_fake_zeros(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    advanced: AdvancedSectionProperties,
) -> None:
    result = verify_catalog_properties(
        resolved,
        computed,
        _policy(
            VerificationProperty.X0,
            VerificationProperty.Y0,
            VerificationProperty.CW,
        ),
        advanced,
    )

    assert result.overall_status is VerificationStatus.NOT_CHECKED
    assert all(check.catalog_value is None for check in result.checks)
    assert tuple(check.computed_value for check in result.checks) == pytest.approx(
        (advanced.x0_mm, advanced.y0_mm, advanced.cw_mm6)
    )


def test_available_catalog_advanced_values_can_pass_verification(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    advanced: AdvancedSectionProperties,
) -> None:
    supplied = replace(
        resolved,
        properties=replace(
            resolved.properties,
            x0_mm=advanced.x0_mm,
            y0_mm=advanced.y0_mm,
            cw_mm6=advanced.cw_mm6,
        ),
    )
    result = verify_catalog_properties(
        supplied,
        computed,
        _policy(
            VerificationProperty.X0,
            VerificationProperty.Y0,
            VerificationProperty.CW,
        ),
        advanced,
    )
    assert result.overall_status is VerificationStatus.PASS
    assert all(check.status is VerificationStatus.PASS for check in result.checks)


def test_advanced_policy_requires_an_advanced_result(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    with pytest.raises(ValidationError, match="advanced result is required"):
        verify_catalog_properties(
            resolved,
            computed,
            _policy(VerificationProperty.CW),
        )


def test_verification_rejects_mismatched_advanced_result(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    advanced: AdvancedSectionProperties,
) -> None:
    with pytest.raises(ValidationError, match="advanced section_id"):
        verify_catalog_properties(
            resolved,
            computed,
            _policy(VerificationProperty.CW),
            replace(advanced, section_id="OTHER"),
        )


def test_principal_angle_comparison_respects_180_degree_equivalence(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    resolved_with_angle = replace(
        resolved,
        properties=replace(resolved.properties, theta_p_deg=89.0),
    )
    result = verify_catalog_properties(
        resolved_with_angle,
        replace(computed, theta_p_deg=-91.0),
        VerificationPolicy(
            relative_tolerance=0.0,
            absolute_tolerance=1.0e-9,
            properties_to_check=(VerificationProperty.THETA_P,),
        ),
    )
    assert result.overall_status is VerificationStatus.PASS
    assert result.checks[0].absolute_difference == pytest.approx(0.0)


@pytest.mark.parametrize(
    "changed",
    (
        {"section_id": "OTHER"},
        {"geometry_id": "OTHER"},
    ),
)
def test_verification_rejects_mismatched_traceability_ids(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    changed: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="does not match"):
        verify_catalog_properties(
            resolved,
            replace(computed, **changed),
            _policy(VerificationProperty.A),
        )


@pytest.mark.parametrize(
    "changed",
    (
        {"relative_tolerance": -0.01},
        {"absolute_tolerance": -1.0},
        {"warning_multiplier": 0.5},
        {"properties_to_check": ()},
    ),
)
def test_invalid_verification_policy_is_rejected(changed: dict[str, object]) -> None:
    values: dict[str, object] = {
        "relative_tolerance": 0.01,
        "absolute_tolerance": 1.0e-9,
        "properties_to_check": (VerificationProperty.A,),
        "warning_multiplier": 2.0,
    }
    values.update(changed)
    with pytest.raises(ValidationError):
        VerificationPolicy(**values)  # type: ignore[arg-type]


def test_computed_and_verification_results_are_immutable(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
) -> None:
    verification = verify_catalog_properties(
        resolved,
        computed,
        _policy(VerificationProperty.A),
    )
    with pytest.raises(FrozenInstanceError):
        computed.a_mm2 = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        verification.overall_status = VerificationStatus.FAIL  # type: ignore[misc]
