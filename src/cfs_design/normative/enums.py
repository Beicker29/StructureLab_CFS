"""Controlled identities for M7 applicability and source provenance."""

from enum import Enum


class DesignAction(str, Enum):
    """Explicit member action requested from a design method."""

    AXIAL_COMPRESSION = "AXIAL_COMPRESSION"
    STRONG_AXIS_FLEXURE = "STRONG_AXIS_FLEXURE"
    SHEAR = "SHEAR"
    COMBINED_AXIAL_FLEXURE = "COMBINED_AXIAL_FLEXURE"


class SoftwareSupportStatus(str, Enum):
    """Whether the approved v0.1 software envelope supports an input."""

    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


class DesignExecutionPurpose(str, Enum):
    """Small execution boundary between resistance and demand checking."""

    CAPACITY = "CAPACITY"
    DEMAND_CHECK = "DEMAND_CHECK"


class StandardDocumentRole(str, Enum):
    """Authority role assigned to a locally registered standards document."""

    PRIMARY_NORMATIVE = "PRIMARY_NORMATIVE"
    VALIDATION_REFERENCE = "VALIDATION_REFERENCE"
    PREVIOUS_STANDARD = "PREVIOUS_STANDARD"
    COMMENTARY = "COMMENTARY"
    FUTURE_SCOPE = "FUTURE_SCOPE"


__all__ = [
    "DesignAction",
    "DesignExecutionPurpose",
    "SoftwareSupportStatus",
    "StandardDocumentRole",
]
