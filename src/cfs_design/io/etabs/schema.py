"""Immutable schema configuration for approved native ETABS workbooks."""

from dataclasses import dataclass, field, fields

from cfs_design.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class ETABSColumnMap:
    """Expected column labels; labels are resolved by name, never position."""

    story: str = "Story"
    frame_label: str = "Beam"
    unique_name: str = "Unique Name"
    output_case: str = "Output Case"
    case_type: str = "Case Type"
    step_type: str = "Step Type"
    station: str = "Station"
    p: str = "P"
    v2: str = "V2"
    v3: str = "V3"
    t: str = "T"
    m2: str = "M2"
    m3: str = "M3"
    element: str = "Element"
    element_station: str = "Elem Station"
    location: str = "Location"

    def __post_init__(self) -> None:
        labels = tuple(getattr(self, item.name) for item in fields(self))
        if any(not isinstance(label, str) or not label.strip() for label in labels):
            raise ValidationError("ETABS column labels must be non-blank strings")
        if len(set(labels)) != len(labels):
            raise ValidationError("ETABS column labels must be unique")

    def as_dict(self) -> dict[str, str]:
        return {item.name: getattr(self, item.name) for item in fields(self)}


@dataclass(frozen=True, slots=True)
class ETABSImportConfig:
    """Workbook layout configuration for the approved native export."""

    program_control_sheet: str = "Program Control"
    forces_sheet: str = "Element Forces - Beams"
    table_title_row: int = 1
    header_row: int = 2
    units_row: int = 3
    data_start_row: int = 4
    program_data_row: int = 4
    program_name_column: str = "ProgramName"
    program_version_column: str = "Version"
    program_current_units_column: str = "CurrUnits"
    columns: ETABSColumnMap = field(default_factory=ETABSColumnMap)

    def __post_init__(self) -> None:
        for name in (
            "program_control_sheet",
            "forces_sheet",
            "program_name_column",
            "program_version_column",
            "program_current_units_column",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{name} must be a non-blank string")
        row_values = (
            self.table_title_row,
            self.header_row,
            self.units_row,
            self.data_start_row,
            self.program_data_row,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in row_values):
            raise ValidationError("ETABS worksheet row numbers must be positive integers")
        if not self.table_title_row < self.header_row < self.units_row < self.data_start_row:
            raise ValidationError(
                "ETABS force worksheet rows must satisfy title < header < units < data"
            )
        if not isinstance(self.columns, ETABSColumnMap):
            raise ValidationError("columns must be an ETABSColumnMap")


__all__ = ["ETABSColumnMap", "ETABSImportConfig"]
