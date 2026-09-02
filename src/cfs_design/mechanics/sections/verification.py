"""Comparison of supplied catalog claims with already computed M3A results."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import ResolvedSection

from .models import (
    AdvancedSectionProperties,
    CatalogVerificationResult,
    ComputedSectionProperties,
    PropertyVerification,
    VerificationPolicy,
    VerificationProperty,
    VerificationStatus,
)


@dataclass(frozen=True, slots=True)
class _PropertySpec:
    catalog_attribute: str
    computed_attribute: str
    unit: str
    angular: bool = False
    advanced: bool = False


_PROPERTY_SPECS = {
    VerificationProperty.A: _PropertySpec("a_mm2", "a_mm2", "mm^2"),
    VerificationProperty.X_BAR: _PropertySpec("x_bar_mm", "x_bar_mm", "mm"),
    VerificationProperty.Y_BAR: _PropertySpec("y_bar_mm", "y_bar_mm", "mm"),
    VerificationProperty.IX: _PropertySpec("ix_mm4", "ix_mm4", "mm^4"),
    VerificationProperty.IY: _PropertySpec("iy_mm4", "iy_mm4", "mm^4"),
    VerificationProperty.IXY: _PropertySpec("ixy_mm4", "ixy_mm4", "mm^4"),
    VerificationProperty.I1: _PropertySpec("i1_mm4", "i1_mm4", "mm^4"),
    VerificationProperty.I2: _PropertySpec("i2_mm4", "i2_mm4", "mm^4"),
    VerificationProperty.THETA_P: _PropertySpec(
        "theta_p_deg", "theta_p_deg", "deg", angular=True
    ),
    VerificationProperty.SX_POS: _PropertySpec(
        "sx_pos_mm3", "sx_pos_mm3", "mm^3"
    ),
    VerificationProperty.SX_NEG: _PropertySpec(
        "sx_neg_mm3", "sx_neg_mm3", "mm^3"
    ),
    VerificationProperty.SY_POS: _PropertySpec(
        "sy_pos_mm3", "sy_pos_mm3", "mm^3"
    ),
    VerificationProperty.SY_NEG: _PropertySpec(
        "sy_neg_mm3", "sy_neg_mm3", "mm^3"
    ),
    VerificationProperty.RX: _PropertySpec("rx_mm", "rx_mm", "mm"),
    VerificationProperty.RY: _PropertySpec("ry_mm", "ry_mm", "mm"),
    VerificationProperty.J: _PropertySpec("j_mm4", "j_mm4", "mm^4"),
    VerificationProperty.X0: _PropertySpec(
        "x0_mm", "x0_mm", "mm", advanced=True
    ),
    VerificationProperty.Y0: _PropertySpec(
        "y0_mm", "y0_mm", "mm", advanced=True
    ),
    VerificationProperty.CW: _PropertySpec(
        "cw_mm6", "cw_mm6", "mm^6", advanced=True
    ),
}


def _absolute_difference(catalog: float, computed: float, *, angular: bool) -> float:
    if not angular:
        return abs(computed - catalog)
    return abs((computed - catalog + 90.0) % 180.0 - 90.0)


def _relative_difference(
    absolute_difference: float,
    catalog_value: float,
    absolute_tolerance: float,
) -> float | None:
    denominator = max(abs(catalog_value), absolute_tolerance)
    if denominator > 0.0:
        return absolute_difference / denominator
    return 0.0 if absolute_difference == 0.0 else None


def _check_property(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    property_name: VerificationProperty,
    policy: VerificationPolicy,
    advanced: AdvancedSectionProperties | None,
) -> PropertyVerification:
    spec = _PROPERTY_SPECS[property_name]
    catalog_value = getattr(resolved.properties, spec.catalog_attribute)
    if spec.advanced:
        if advanced is None:
            raise ValidationError(
                f"advanced result is required to verify {property_name.value}"
            )
        computed_value = getattr(advanced, spec.computed_attribute)
    else:
        computed_value = getattr(computed, spec.computed_attribute)
    if catalog_value is None:
        return PropertyVerification(
            property_name=property_name,
            catalog_value=None,
            computed_value=computed_value,
            absolute_difference=None,
            relative_difference=None,
            tolerance=None,
            warning_tolerance=None,
            unit=spec.unit,
            status=VerificationStatus.NOT_CHECKED,
        )

    difference = _absolute_difference(
        catalog_value,
        computed_value,
        angular=spec.angular,
    )
    pass_tolerance = max(
        policy.absolute_tolerance,
        policy.relative_tolerance * abs(catalog_value),
    )
    warning_tolerance = pass_tolerance * policy.warning_multiplier
    if difference <= pass_tolerance:
        status = VerificationStatus.PASS
    elif difference <= warning_tolerance:
        status = VerificationStatus.WARNING
    else:
        status = VerificationStatus.FAIL
    return PropertyVerification(
        property_name=property_name,
        catalog_value=catalog_value,
        computed_value=computed_value,
        absolute_difference=difference,
        relative_difference=_relative_difference(
            difference,
            catalog_value,
            policy.absolute_tolerance,
        ),
        tolerance=pass_tolerance,
        warning_tolerance=warning_tolerance,
        unit=spec.unit,
        status=status,
    )


def _overall_status(
    checks: tuple[PropertyVerification, ...],
) -> VerificationStatus:
    statuses = {check.status for check in checks}
    if VerificationStatus.FAIL in statuses:
        return VerificationStatus.FAIL
    if VerificationStatus.WARNING in statuses:
        return VerificationStatus.WARNING
    if VerificationStatus.PASS in statuses:
        return VerificationStatus.PASS
    return VerificationStatus.NOT_CHECKED


def verify_catalog_properties(
    resolved: ResolvedSection,
    computed: ComputedSectionProperties,
    policy: VerificationPolicy,
    advanced: AdvancedSectionProperties | None = None,
) -> CatalogVerificationResult:
    """Compare values without recalculating or mutating either input object."""

    if not isinstance(resolved, ResolvedSection):
        raise ValidationError("resolved must be a ResolvedSection")
    if not isinstance(computed, ComputedSectionProperties):
        raise ValidationError("computed must be ComputedSectionProperties")
    if not isinstance(policy, VerificationPolicy):
        raise ValidationError("policy must be a VerificationPolicy")
    section_id = resolved.catalog_section.section_id
    if computed.section_id != section_id:
        raise ValidationError(
            "computed section_id does not match the resolved catalog section"
        )
    if computed.geometry_id != resolved.geometry.geometry_id:
        raise ValidationError(
            "computed geometry_id does not match the resolved catalog geometry"
        )
    if advanced is not None:
        if not isinstance(advanced, AdvancedSectionProperties):
            raise ValidationError("advanced must be AdvancedSectionProperties or None")
        if advanced.section_id != section_id:
            raise ValidationError(
                "advanced section_id does not match the resolved catalog section"
            )
        if advanced.geometry_id != resolved.geometry.geometry_id:
            raise ValidationError(
                "advanced geometry_id does not match the resolved catalog geometry"
            )
    checks = tuple(
        _check_property(resolved, computed, property_name, policy, advanced)
        for property_name in policy.properties_to_check
    )
    return CatalogVerificationResult(
        section_id=section_id,
        method=computed.method,
        checks=checks,
        overall_status=_overall_status(checks),
    )


__all__ = ["verify_catalog_properties"]
