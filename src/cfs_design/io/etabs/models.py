"""Immutable raw, normalized, mapping, and result models for ETABS IO."""

from dataclasses import dataclass
from pathlib import Path

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DemandPoint, DemandSet
from cfs_design.domain._validation import (
    require_bool,
    require_finite,
    require_non_empty,
    require_optional_string,
)


def _require_tuple(value: object, item_type: type, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise ValidationError(f"{field_name} must be a tuple")
    if any(not isinstance(item, item_type) for item in value):
        raise ValidationError(
            f"{field_name} must contain only {item_type.__name__} objects"
        )


@dataclass(frozen=True, slots=True)
class ETABSSourceUnits:
    station: str
    p: str
    v2: str
    v3: str
    t: str
    m2: str
    m3: str
    element_station: str

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ETABSImportMetadata:
    source_path: Path
    file_sha256: str
    force_sheet: str
    header_row: int
    units_row: int
    data_start_row: int
    source_units: ETABSSourceUnits
    program_name: str | None = None
    program_version: str | None = None
    current_units: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise ValidationError("source_path must be an absolute pathlib.Path")
        if (
            not isinstance(self.file_sha256, str)
            or len(self.file_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.file_sha256)
        ):
            raise ValidationError("file_sha256 must be a lowercase SHA-256 digest")
        require_non_empty(self.force_sheet, "force_sheet")
        for field_name in ("header_row", "units_row", "data_start_row"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(f"{field_name} must be a positive integer")
        if not isinstance(self.source_units, ETABSSourceUnits):
            raise ValidationError("source_units must be ETABSSourceUnits")
        for field_name in ("program_name", "program_version", "current_units"):
            require_optional_string(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ETABSRawForceRow:
    """One untouched, simultaneous native ETABS force-table row."""

    worksheet: str
    source_row: int
    story: str
    frame_label: str
    unique_name: str
    output_case: str
    case_type: str
    step_type: str | None
    station_raw: float
    p_raw: float
    v2_raw: float
    v3_raw: float
    t_raw: float
    m2_raw: float
    m3_raw: float
    element: str
    element_station_raw: float
    location: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "worksheet",
            "story",
            "frame_label",
            "unique_name",
            "output_case",
            "case_type",
            "element",
        ):
            require_non_empty(getattr(self, field_name), field_name)
        if isinstance(self.source_row, bool) or not isinstance(self.source_row, int) or self.source_row < 1:
            raise ValidationError("source_row must be a positive integer")
        require_optional_string(self.step_type, "step_type")
        require_optional_string(self.location, "location")
        for field_name in (
            "station_raw",
            "p_raw",
            "v2_raw",
            "v3_raw",
            "t_raw",
            "m2_raw",
            "m3_raw",
            "element_station_raw",
        ):
            require_finite(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ETABSReadResult:
    metadata: ETABSImportMetadata
    raw_rows: tuple[ETABSRawForceRow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ETABSImportMetadata):
            raise ValidationError("metadata must be ETABSImportMetadata")
        _require_tuple(self.raw_rows, ETABSRawForceRow, "raw_rows")


@dataclass(frozen=True, slots=True)
class NormalizedETABSDemand:
    raw_row: ETABSRawForceRow
    demand_point: DemandPoint

    def __post_init__(self) -> None:
        if not isinstance(self.raw_row, ETABSRawForceRow):
            raise ValidationError("raw_row must be ETABSRawForceRow")
        if not isinstance(self.demand_point, DemandPoint):
            raise ValidationError("demand_point must be DemandPoint")


@dataclass(frozen=True, slots=True)
class ETABSMappingRow:
    source_row: int
    case_id: str
    etabs_unique_name: str | None
    etabs_story: str | None
    etabs_beam: str | None
    etabs_element: str | None
    mapping_enabled: bool
    notes: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.source_row, bool) or not isinstance(self.source_row, int) or self.source_row < 1:
            raise ValidationError("source_row must be a positive integer")
        require_non_empty(self.case_id, "case_id")
        for field_name in (
            "etabs_unique_name",
            "etabs_story",
            "etabs_beam",
            "etabs_element",
            "notes",
        ):
            require_optional_string(getattr(self, field_name), field_name)
        require_bool(self.mapping_enabled, "mapping_enabled")


@dataclass(frozen=True, slots=True)
class ETABSMappingTable:
    source_path: Path
    file_sha256: str
    worksheet: str
    rows: tuple[ETABSMappingRow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise ValidationError("source_path must be an absolute pathlib.Path")
        if (
            not isinstance(self.file_sha256, str)
            or len(self.file_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.file_sha256)
        ):
            raise ValidationError("file_sha256 must be a lowercase SHA-256 digest")
        require_non_empty(self.worksheet, "worksheet")
        _require_tuple(self.rows, ETABSMappingRow, "rows")

    @property
    def enabled_rows(self) -> tuple[ETABSMappingRow, ...]:
        return tuple(row for row in self.rows if row.mapping_enabled)


@dataclass(frozen=True, slots=True)
class MappedMemberDemands:
    case_id: str
    demand_set: DemandSet
    records: tuple[NormalizedETABSDemand, ...]

    def __post_init__(self) -> None:
        require_non_empty(self.case_id, "case_id")
        if not isinstance(self.demand_set, DemandSet):
            raise ValidationError("demand_set must be DemandSet")
        _require_tuple(self.records, NormalizedETABSDemand, "records")
        if not self.records:
            raise ValidationError("records must not be empty")


@dataclass(frozen=True, slots=True)
class ETABSImportResult:
    metadata: ETABSImportMetadata
    raw_rows: tuple[ETABSRawForceRow, ...]
    normalized_rows: tuple[NormalizedETABSDemand, ...]
    mapped_members: tuple[MappedMemberDemands, ...]
    unmapped_rows: tuple[NormalizedETABSDemand, ...]
    warnings: tuple[str, ...]
    mapping: ETABSMappingTable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ETABSImportMetadata):
            raise ValidationError("metadata must be ETABSImportMetadata")
        _require_tuple(self.raw_rows, ETABSRawForceRow, "raw_rows")
        _require_tuple(self.normalized_rows, NormalizedETABSDemand, "normalized_rows")
        _require_tuple(self.mapped_members, MappedMemberDemands, "mapped_members")
        _require_tuple(self.unmapped_rows, NormalizedETABSDemand, "unmapped_rows")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(warning, str) for warning in self.warnings
        ):
            raise ValidationError("warnings must be a tuple of strings")
        if self.mapping is not None and not isinstance(self.mapping, ETABSMappingTable):
            raise ValidationError("mapping must be ETABSMappingTable or None")


__all__ = [
    "ETABSImportMetadata",
    "ETABSImportResult",
    "ETABSMappingRow",
    "ETABSMappingTable",
    "ETABSRawForceRow",
    "ETABSReadResult",
    "ETABSSourceUnits",
    "MappedMemberDemands",
    "NormalizedETABSDemand",
]
