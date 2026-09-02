"""Enumerations used by the shared EWM/DSM input domain model."""

from enum import Enum


class MemberType(str, Enum):
    COLUMN = "COLUMN"
    BEAM = "BEAM"
    BEAM_COLUMN = "BEAM_COLUMN"
    OTHER = "OTHER"


class SectionFamily(str, Enum):
    C_LIPPED = "C_LIPPED"
    C_UNLIPPED = "C_UNLIPPED"
    Z_LIPPED = "Z_LIPPED"
    Z_UNLIPPED = "Z_UNLIPPED"
    HAT = "HAT"
    TRACK = "TRACK"
    OTHER = "OTHER"


class GeometryConvention(str, Enum):
    OUT_TO_OUT = "OUT_TO_OUT"
    MIDLINE = "MIDLINE"
    FLAT_WIDTHS = "FLAT_WIDTHS"


class LengthDefinition(str, Enum):
    K_FACTORS = "K_FACTORS"
    EFFECTIVE_LENGTHS = "EFFECTIVE_LENGTHS"


class DesignFormat(str, Enum):
    LRFD = "LRFD"
    ASD = "ASD"


class DesignMethod(str, Enum):
    EWM = "EWM"
    DSM = "DSM"


class RunMode(str, Enum):
    EWM = "ewm"
    DSM = "dsm"
    COMPARE = "compare"


__all__ = [
    "DesignFormat",
    "DesignMethod",
    "GeometryConvention",
    "LengthDefinition",
    "MemberType",
    "RunMode",
    "SectionFamily",
]

