"""Validated reader for the approved native ETABS Excel export."""

from math import isfinite
from numbers import Real
from pathlib import Path

from cfs_design.core.exceptions import ETABSImportError, ValidationError
from cfs_design.core.units import (
    convert_force_to_n,
    convert_length_to_mm,
    convert_moment_to_nmm,
)

from ._excel import ExcelRow, ExcelWorkbookPair, is_blank, unresolved_formula
from .models import (
    ETABSImportMetadata,
    ETABSRawForceRow,
    ETABSReadResult,
    ETABSSourceUnits,
)
from .schema import ETABSImportConfig


def _required_text(row: ExcelRow, field: str) -> str:
    value = row.values[field]
    if not isinstance(value, str) or not value.strip():
        unresolved_formula(row, field)
        raise row.error(field, f"invalid required text value: {value!r}")
    return value


def _optional_text(row: ExcelRow, field: str) -> str | None:
    value = row.values[field]
    if is_blank(value):
        unresolved_formula(row, field)
        return None
    if not isinstance(value, str):
        raise row.error(field, f"invalid text value: {value!r}")
    return value


def _required_number(row: ExcelRow, field: str) -> float:
    value = row.values[field]
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        unresolved_formula(row, field)
        raise row.error(field, f"invalid numeric value: {value!r}")
    return float(value)


def _optional_metadata_text(row: ExcelRow, field: str) -> str | None:
    value = row.values[field]
    if is_blank(value):
        unresolved_formula(row, field)
        return None
    if not isinstance(value, str):
        raise row.error(field, f"invalid metadata text value: {value!r}")
    return value


def _validate_source_units(units: ETABSSourceUnits) -> None:
    """Exercise the central unit registry before any force row is accepted."""

    try:
        convert_length_to_mm(1.0, units.station)
        convert_length_to_mm(1.0, units.element_station)
        for unit in (units.p, units.v2, units.v3):
            convert_force_to_n(1.0, unit)
        for unit in (units.t, units.m2, units.m3):
            convert_moment_to_nmm(1.0, unit)
    except ValidationError as error:
        raise ETABSImportError(f"Unsupported ETABS force-table units: {error}") from error


def read_etabs_results(
    path: str | Path,
    *,
    config: ETABSImportConfig | None = None,
) -> ETABSReadResult:
    """Read native force rows without unit conversion or sign modification."""

    resolved_config = config or ETABSImportConfig()
    if not isinstance(resolved_config, ETABSImportConfig):
        raise ValidationError("config must be ETABSImportConfig or None")

    with ExcelWorkbookPair(path) as workbook:
        workbook.require_sheets(
            resolved_config.program_control_sheet,
            resolved_config.forces_sheet,
        )
        program_headers = (
            resolved_config.program_name_column,
            resolved_config.program_version_column,
            resolved_config.program_current_units_column,
        )
        program_positions = workbook.header_positions(
            resolved_config.program_control_sheet,
            resolved_config.header_row,
            program_headers,
        )
        program_row = workbook.one_row(
            resolved_config.program_control_sheet,
            resolved_config.program_data_row,
            program_positions,
        )

        column_map = resolved_config.columns.as_dict()
        force_positions = workbook.header_positions(
            resolved_config.forces_sheet,
            resolved_config.header_row,
            tuple(column_map.values()),
        )
        units_row = workbook.one_row(
            resolved_config.forces_sheet,
            resolved_config.units_row,
            force_positions,
        )
        units = ETABSSourceUnits(
            station=_required_text(units_row, column_map["station"]),
            p=_required_text(units_row, column_map["p"]),
            v2=_required_text(units_row, column_map["v2"]),
            v3=_required_text(units_row, column_map["v3"]),
            t=_required_text(units_row, column_map["t"]),
            m2=_required_text(units_row, column_map["m2"]),
            m3=_required_text(units_row, column_map["m3"]),
            element_station=_required_text(
                units_row, column_map["element_station"]
            ),
        )
        _validate_source_units(units)

        raw_rows = tuple(
            _parse_force_row(row, column_map)
            for row in workbook.rows(
                resolved_config.forces_sheet,
                resolved_config.data_start_row,
                force_positions,
            )
        )
        metadata = ETABSImportMetadata(
            source_path=workbook.source_path,
            file_sha256=workbook.file_sha256,
            force_sheet=resolved_config.forces_sheet,
            header_row=resolved_config.header_row,
            units_row=resolved_config.units_row,
            data_start_row=resolved_config.data_start_row,
            source_units=units,
            program_name=_optional_metadata_text(
                program_row, resolved_config.program_name_column
            ),
            program_version=_optional_metadata_text(
                program_row, resolved_config.program_version_column
            ),
            current_units=_optional_metadata_text(
                program_row, resolved_config.program_current_units_column
            ),
        )
    return ETABSReadResult(metadata=metadata, raw_rows=raw_rows)


def _parse_force_row(
    row: ExcelRow,
    columns: dict[str, str],
) -> ETABSRawForceRow:
    return ETABSRawForceRow(
        worksheet=row.worksheet,
        source_row=row.row_number,
        story=_required_text(row, columns["story"]),
        frame_label=_required_text(row, columns["frame_label"]),
        unique_name=_required_text(row, columns["unique_name"]),
        output_case=_required_text(row, columns["output_case"]),
        case_type=_required_text(row, columns["case_type"]),
        step_type=_optional_text(row, columns["step_type"]),
        station_raw=_required_number(row, columns["station"]),
        p_raw=_required_number(row, columns["p"]),
        v2_raw=_required_number(row, columns["v2"]),
        v3_raw=_required_number(row, columns["v3"]),
        t_raw=_required_number(row, columns["t"]),
        m2_raw=_required_number(row, columns["m2"]),
        m3_raw=_required_number(row, columns["m3"]),
        element=_required_text(row, columns["element"]),
        element_station_raw=_required_number(row, columns["element_station"]),
        location=_optional_text(row, columns["location"]),
    )


__all__ = ["read_etabs_results"]
