"""Immutable M3A/M3B mechanics and catalog-verification result models."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real

from cfs_design.core.exceptions import ValidationError


class GeometryMethod(str, Enum):
    """Implemented conversion from catalog dimensions to centerline geometry."""

    MIDLINE_SHARP_CORNER = "MIDLINE_SHARP_CORNER"


class GrossPropertyMethod(str, Enum):
    THIN_WALL_CENTERLINE = "THIN_WALL_CENTERLINE"


class AdvancedPropertyMethod(str, Enum):
    SECTORIAL_THIN_WALL_CENTERLINE = "SECTORIAL_THIN_WALL_CENTERLINE"


class ExtremeFiberMethod(str, Enum):
    CENTERLINE_EXTENTS = "CENTERLINE_EXTENTS"


class VerificationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


class VerificationProperty(str, Enum):
    A = "A"
    X_BAR = "x_bar"
    Y_BAR = "y_bar"
    IX = "Ix"
    IY = "Iy"
    IXY = "Ixy"
    I1 = "I1"
    I2 = "I2"
    THETA_P = "theta_p"
    SX_POS = "Sx_pos"
    SX_NEG = "Sx_neg"
    SY_POS = "Sy_pos"
    SY_NEG = "Sy_neg"
    RX = "rx"
    RY = "ry"
    J = "J"
    X0 = "x0"
    Y0 = "y0"
    CW = "Cw"


def _require_finite(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValidationError(f"{field_name} must be a finite number")


def _require_non_negative(value: float, field_name: str) -> None:
    _require_finite(value, field_name)
    if value < 0.0:
        raise ValidationError(f"{field_name} must be greater than or equal to zero")


@dataclass(frozen=True, slots=True)
class ComputedSectionProperties:
    """Gross properties calculated from a canonical centerline geometry."""

    section_id: str | None
    geometry_id: str
    method: GrossPropertyMethod
    extreme_fiber_method: ExtremeFiberMethod
    a_mm2: float
    x_bar_mm: float
    y_bar_mm: float
    ix_mm4: float
    iy_mm4: float
    ixy_mm4: float
    i1_mm4: float
    i2_mm4: float
    theta_p_deg: float
    sx_pos_mm3: float
    sx_neg_mm3: float
    sy_pos_mm3: float
    sy_neg_mm3: float
    rx_mm: float
    ry_mm: float
    j_mm4: float
    geometry_model_version: str = "M3A-1"

    def __post_init__(self) -> None:
        if self.section_id is not None and (
            not isinstance(self.section_id, str) or not self.section_id.strip()
        ):
            raise ValidationError("section_id must be a non-empty string or None")
        if not isinstance(self.geometry_id, str) or not self.geometry_id.strip():
            raise ValidationError("geometry_id must be a non-empty string")
        if not isinstance(self.method, GrossPropertyMethod):
            raise ValidationError("method must be a GrossPropertyMethod")
        if not isinstance(self.extreme_fiber_method, ExtremeFiberMethod):
            raise ValidationError("extreme_fiber_method must be an ExtremeFiberMethod")
        if (
            not isinstance(self.geometry_model_version, str)
            or not self.geometry_model_version.strip()
        ):
            raise ValidationError("geometry_model_version must be non-empty")
        for field_name in (
            "a_mm2",
            "ix_mm4",
            "iy_mm4",
            "i1_mm4",
            "i2_mm4",
            "sx_pos_mm3",
            "sx_neg_mm3",
            "sy_pos_mm3",
            "sy_neg_mm3",
            "rx_mm",
            "ry_mm",
            "j_mm4",
        ):
            _require_non_negative(getattr(self, field_name), field_name)
        if self.a_mm2 <= 0.0:
            raise ValidationError("a_mm2 must be greater than zero")
        for field_name in ("x_bar_mm", "y_bar_mm", "ixy_mm4", "theta_p_deg"):
            _require_finite(getattr(self, field_name), field_name)
        if self.i1_mm4 < self.i2_mm4:
            raise ValidationError("i1_mm4 must be the major principal inertia")


@dataclass(frozen=True, slots=True)
class SectorialNode:
    """Auditable sectorial values at one ordered centerline contour node."""

    node_index: int
    x_centroid_mm: float
    y_centroid_mm: float
    omega_centroid_raw_mm2: float
    omega_shear_raw_mm2: float
    omega_normalized_mm2: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.node_index, bool)
            or not isinstance(self.node_index, int)
            or self.node_index < 0
        ):
            raise ValidationError("node_index must be a non-negative integer")
        for field_name in (
            "x_centroid_mm",
            "y_centroid_mm",
            "omega_centroid_raw_mm2",
            "omega_shear_raw_mm2",
            "omega_normalized_mm2",
        ):
            _require_finite(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class SectorialProperties:
    """Exact thin-wall sectorial integrals and normalized node field."""

    shear_center_offset_x_mm: float
    shear_center_offset_y_mm: float
    i_omega_x_mm5: float
    i_omega_y_mm5: float
    inertia_determinant_mm8: float
    normalization_mean_mm2: float
    normalized_first_moment_mm4: float
    cw_mm6: float
    nodes: tuple[SectorialNode, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "shear_center_offset_x_mm",
            "shear_center_offset_y_mm",
            "i_omega_x_mm5",
            "i_omega_y_mm5",
            "inertia_determinant_mm8",
            "normalization_mean_mm2",
            "normalized_first_moment_mm4",
            "cw_mm6",
        ):
            _require_finite(getattr(self, field_name), field_name)
        if self.inertia_determinant_mm8 < 0.0:
            raise ValidationError("inertia_determinant_mm8 must be non-negative")
        if self.cw_mm6 < 0.0:
            raise ValidationError("cw_mm6 must be non-negative")
        if not isinstance(self.nodes, tuple) or len(self.nodes) < 2:
            raise ValidationError("nodes must be an ordered tuple with at least 2 nodes")
        if any(not isinstance(item, SectorialNode) for item in self.nodes):
            raise ValidationError("nodes entries must be SectorialNode values")
        if tuple(item.node_index for item in self.nodes) != tuple(
            range(len(self.nodes))
        ):
            raise ValidationError("SectorialNode indexes must be contiguous from zero")


@dataclass(frozen=True, slots=True)
class AdvancedSectionProperties:
    """M3B shear-center and warping result tied to one M3A geometry."""

    section_id: str | None
    geometry_id: str
    method: AdvancedPropertyMethod
    sectorial: SectorialProperties
    geometry_model_version: str = "M3B-1"

    def __post_init__(self) -> None:
        if self.section_id is not None and (
            not isinstance(self.section_id, str) or not self.section_id.strip()
        ):
            raise ValidationError("section_id must be a non-empty string or None")
        if not isinstance(self.geometry_id, str) or not self.geometry_id.strip():
            raise ValidationError("geometry_id must be a non-empty string")
        if not isinstance(self.method, AdvancedPropertyMethod):
            raise ValidationError("method must be an AdvancedPropertyMethod")
        if not isinstance(self.sectorial, SectorialProperties):
            raise ValidationError("sectorial must be SectorialProperties")
        if (
            not isinstance(self.geometry_model_version, str)
            or not self.geometry_model_version.strip()
        ):
            raise ValidationError("geometry_model_version must be non-empty")

    @property
    def x0_mm(self) -> float:
        return self.sectorial.shear_center_offset_x_mm

    @property
    def y0_mm(self) -> float:
        return self.sectorial.shear_center_offset_y_mm

    @property
    def cw_mm6(self) -> float:
        return self.sectorial.cw_mm6


@dataclass(frozen=True, slots=True)
class VerificationPolicy:
    """Explicit QA thresholds supplied to catalog verification.

    ``relative_tolerance`` and ``absolute_tolerance`` define the PASS band.
    ``warning_multiplier`` expands that band for WARNING; values outside it
    FAIL. A multiplier of 1 disables the warning band.
    """

    relative_tolerance: float
    absolute_tolerance: float
    properties_to_check: tuple[VerificationProperty, ...]
    warning_multiplier: float = 2.0

    def __post_init__(self) -> None:
        _require_non_negative(self.relative_tolerance, "relative_tolerance")
        _require_non_negative(self.absolute_tolerance, "absolute_tolerance")
        _require_finite(self.warning_multiplier, "warning_multiplier")
        if self.warning_multiplier < 1.0:
            raise ValidationError("warning_multiplier must be at least 1")
        if not isinstance(self.properties_to_check, tuple):
            raise ValidationError("properties_to_check must be a tuple")
        if not self.properties_to_check:
            raise ValidationError("properties_to_check must not be empty")
        if any(
            not isinstance(item, VerificationProperty)
            for item in self.properties_to_check
        ):
            raise ValidationError(
                "properties_to_check entries must be VerificationProperty values"
            )
        if len(set(self.properties_to_check)) != len(self.properties_to_check):
            raise ValidationError("properties_to_check must not contain duplicates")


@dataclass(frozen=True, slots=True)
class PropertyVerification:
    property_name: VerificationProperty
    catalog_value: float | None
    computed_value: float
    absolute_difference: float | None
    relative_difference: float | None
    tolerance: float | None
    warning_tolerance: float | None
    unit: str
    status: VerificationStatus


@dataclass(frozen=True, slots=True)
class CatalogVerificationResult:
    section_id: str
    method: GrossPropertyMethod
    checks: tuple[PropertyVerification, ...]
    overall_status: VerificationStatus

    def __post_init__(self) -> None:
        if not isinstance(self.section_id, str) or not self.section_id.strip():
            raise ValidationError("section_id must be a non-empty string")
        if not isinstance(self.method, GrossPropertyMethod):
            raise ValidationError("method must be a GrossPropertyMethod")
        if not isinstance(self.checks, tuple) or not self.checks:
            raise ValidationError("checks must be a non-empty tuple")
        if any(not isinstance(item, PropertyVerification) for item in self.checks):
            raise ValidationError("checks entries must be PropertyVerification values")
        if not isinstance(self.overall_status, VerificationStatus):
            raise ValidationError("overall_status must be a VerificationStatus")


__all__ = [
    "AdvancedPropertyMethod",
    "AdvancedSectionProperties",
    "CatalogVerificationResult",
    "ComputedSectionProperties",
    "ExtremeFiberMethod",
    "GeometryMethod",
    "GrossPropertyMethod",
    "PropertyVerification",
    "SectorialNode",
    "SectorialProperties",
    "VerificationPolicy",
    "VerificationProperty",
    "VerificationStatus",
]
