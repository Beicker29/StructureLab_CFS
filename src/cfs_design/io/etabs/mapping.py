"""Read and apply the approved members.xlsx ETABS mapping contract."""

from pathlib import Path

from cfs_design.core.exceptions import ETABSImportError, ValidationError
from cfs_design.domain import DemandCombination, DemandSet

from ._excel import ExcelRow, ExcelWorkbookPair, is_blank, unresolved_formula
from .models import (
    ETABSImportResult,
    ETABSMappingRow,
    ETABSMappingTable,
    ETABSReadResult,
    MappedMemberDemands,
    NormalizedETABSDemand,
)


MAPPING_WORKSHEET = "ETABS_Mapping"
MAPPING_HEADERS = (
    "case_id",
    "etabs_unique_name",
    "etabs_story",
    "etabs_beam",
    "etabs_element",
    "mapping_enabled",
    "notes",
)


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


def _required_boolean(row: ExcelRow, field: str) -> bool:
    value = row.values[field]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "TRUE":
            return True
        if normalized == "FALSE":
            return False
    unresolved_formula(row, field)
    raise row.error(field, f"invalid boolean value: {value!r}")


def _key(value: str) -> str:
    """Controlled matching normalization: surrounding whitespace only."""

    return value.strip()


def load_etabs_mapping(
    path: str | Path,
    *,
    worksheet: str = MAPPING_WORKSHEET,
    header_row: int = 1,
    data_start_row: int = 2,
) -> ETABSMappingTable:
    """Read only the ETABS_Mapping sheet; Members is intentionally untouched."""

    if not isinstance(worksheet, str) or not worksheet.strip():
        raise ValidationError("worksheet must be a non-blank string")
    if (
        isinstance(header_row, bool)
        or not isinstance(header_row, int)
        or header_row < 1
        or isinstance(data_start_row, bool)
        or not isinstance(data_start_row, int)
        or data_start_row <= header_row
    ):
        raise ValidationError(
            "mapping rows must be positive and data_start_row must follow header_row"
        )

    with ExcelWorkbookPair(path) as workbook:
        workbook.require_sheets(worksheet)
        positions = workbook.header_positions(
            worksheet, header_row, MAPPING_HEADERS
        )
        rows = tuple(
            _parse_mapping_row(row)
            for row in workbook.rows(worksheet, data_start_row, positions)
        )
        table = ETABSMappingTable(
            source_path=workbook.source_path,
            file_sha256=workbook.file_sha256,
            worksheet=worksheet,
            rows=rows,
        )
    _validate_enabled_mapping(table)
    return table


def _parse_mapping_row(row: ExcelRow) -> ETABSMappingRow:
    return ETABSMappingRow(
        source_row=row.row_number,
        case_id=_required_text(row, "case_id"),
        etabs_unique_name=_optional_text(row, "etabs_unique_name"),
        etabs_story=_optional_text(row, "etabs_story"),
        etabs_beam=_optional_text(row, "etabs_beam"),
        etabs_element=_optional_text(row, "etabs_element"),
        mapping_enabled=_required_boolean(row, "mapping_enabled"),
        notes=_optional_text(row, "notes"),
    )


def _validate_enabled_mapping(table: ETABSMappingTable) -> None:
    case_ids: dict[str, ETABSMappingRow] = {}
    unique_names: dict[str, ETABSMappingRow] = {}
    story_beams: dict[tuple[str, str], ETABSMappingRow] = {}
    for row in table.enabled_rows:
        case_key = _key(row.case_id)
        if case_key in case_ids:
            prior = case_ids[case_key]
            raise ETABSImportError(
                f"{table.source_path.name}; worksheet {table.worksheet!r}: enabled "
                f"case_id {row.case_id!r} is duplicated at rows "
                f"{prior.source_row} and {row.source_row}"
            )
        case_ids[case_key] = row

        has_story = row.etabs_story is not None
        has_beam = row.etabs_beam is not None
        if has_story != has_beam:
            raise ETABSImportError(
                f"{table.source_path.name}; worksheet {table.worksheet!r}; row "
                f"{row.source_row}: etabs_story and etabs_beam must be supplied together"
            )
        if row.etabs_unique_name is None and not (has_story and has_beam):
            raise ETABSImportError(
                f"{table.source_path.name}; worksheet {table.worksheet!r}; row "
                f"{row.source_row}: enabled mapping requires etabs_unique_name or "
                "the complete etabs_story + etabs_beam fallback"
            )

        if row.etabs_unique_name is not None:
            unique_key = _key(row.etabs_unique_name)
            if unique_key in unique_names:
                prior = unique_names[unique_key]
                raise ETABSImportError(
                    f"{table.source_path.name}; worksheet {table.worksheet!r}: "
                    f"ETABS Unique Name {row.etabs_unique_name!r} maps more than once "
                    f"(rows {prior.source_row} and {row.source_row})"
                )
            unique_names[unique_key] = row

        if row.etabs_story is not None and row.etabs_beam is not None:
            pair_key = (_key(row.etabs_story), _key(row.etabs_beam))
            if pair_key in story_beams:
                prior = story_beams[pair_key]
                raise ETABSImportError(
                    f"{table.source_path.name}; worksheet {table.worksheet!r}: "
                    f"ETABS Story + Beam {pair_key!r} maps more than once "
                    f"(rows {prior.source_row} and {row.source_row})"
                )
            story_beams[pair_key] = row


def map_etabs_demands(
    read_result: ETABSReadResult,
    normalized_rows: tuple[NormalizedETABSDemand, ...],
    mapping: ETABSMappingTable | None = None,
) -> ETABSImportResult:
    """Map normalized rows by Unique Name, then exact Story + Beam fallback."""

    if not isinstance(read_result, ETABSReadResult):
        raise ValidationError("read_result must be ETABSReadResult")
    if not isinstance(normalized_rows, tuple) or any(
        not isinstance(row, NormalizedETABSDemand) for row in normalized_rows
    ):
        raise ValidationError(
            "normalized_rows must be a tuple of NormalizedETABSDemand"
        )
    if len(normalized_rows) != len(read_result.raw_rows) or any(
        normalized.raw_row != raw
        for normalized, raw in zip(normalized_rows, read_result.raw_rows)
    ):
        raise ValidationError(
            "normalized_rows must correspond in order to read_result.raw_rows"
        )
    if mapping is not None and not isinstance(mapping, ETABSMappingTable):
        raise ValidationError("mapping must be ETABSMappingTable or None")

    warnings: list[str] = []
    if mapping is None:
        if normalized_rows:
            warnings.append(
                f"No ETABS mapping supplied; {len(normalized_rows)} demand rows remain unmapped"
            )
        return ETABSImportResult(
            metadata=read_result.metadata,
            raw_rows=read_result.raw_rows,
            normalized_rows=normalized_rows,
            mapped_members=(),
            unmapped_rows=normalized_rows,
            warnings=tuple(warnings),
            mapping=None,
        )

    _validate_enabled_mapping(mapping)
    unique_index = {
        _key(row.etabs_unique_name): row
        for row in mapping.enabled_rows
        if row.etabs_unique_name is not None
    }
    fallback_index = {
        (_key(row.etabs_story), _key(row.etabs_beam)): row
        for row in mapping.enabled_rows
        if row.etabs_story is not None and row.etabs_beam is not None
    }
    grouped: dict[str, list[NormalizedETABSDemand]] = {
        _key(row.case_id): [] for row in mapping.enabled_rows
    }
    original_case_ids = {
        _key(row.case_id): row.case_id for row in mapping.enabled_rows
    }
    unmapped: list[NormalizedETABSDemand] = []

    for record in normalized_rows:
        raw = record.raw_row
        unique_match = unique_index.get(_key(raw.unique_name))
        fallback_match = fallback_index.get(
            (_key(raw.story), _key(raw.frame_label))
        )
        if (
            unique_match is not None
            and fallback_match is not None
            and _key(unique_match.case_id) != _key(fallback_match.case_id)
        ):
            raise ETABSImportError(
                f"Ambiguous ETABS mapping for {raw.worksheet!r} row {raw.source_row}: "
                f"Unique Name selects {unique_match.case_id!r}, while Story + Beam "
                f"selects {fallback_match.case_id!r}"
            )
        selected = unique_match or fallback_match
        if selected is None:
            unmapped.append(record)
        else:
            grouped[_key(selected.case_id)].append(record)

    mapped_members: list[MappedMemberDemands] = []
    for case_key, records in grouped.items():
        if not records:
            warnings.append(
                f"Enabled mapping case_id {original_case_ids[case_key]!r} matched no ETABS rows"
            )
            continue
        matched_unique_names = {
            _key(record.raw_row.unique_name) for record in records
        }
        if len(matched_unique_names) != 1:
            raise ETABSImportError(
                f"case_id {original_case_ids[case_key]!r} matched multiple ETABS "
                f"frame objects by Unique Name: {sorted(matched_unique_names)}; "
                "one-to-many aggregation is not supported"
            )
        combinations: dict[str, list[NormalizedETABSDemand]] = {}
        case_types: dict[str, str] = {}
        for record in records:
            output_case = record.raw_row.output_case
            case_type = record.raw_row.case_type
            if output_case in case_types and case_types[output_case] != case_type:
                raise ETABSImportError(
                    f"case_id {original_case_ids[case_key]!r}, Output Case "
                    f"{output_case!r} has inconsistent Case Type values: "
                    f"{case_types[output_case]!r} and {case_type!r}"
                )
            case_types[output_case] = case_type
            combinations.setdefault(output_case, []).append(record)
        demand_set = DemandSet(
            combinations=tuple(
                DemandCombination(
                    combination_id=output_case,
                    case_type=case_types[output_case],
                    points=tuple(item.demand_point for item in case_records),
                )
                for output_case, case_records in combinations.items()
            )
        )
        mapped_members.append(
            MappedMemberDemands(
                case_id=original_case_ids[case_key],
                demand_set=demand_set,
                records=tuple(records),
            )
        )

    if unmapped:
        warnings.append(f"Unmapped ETABS demand rows: {len(unmapped)}")
    return ETABSImportResult(
        metadata=read_result.metadata,
        raw_rows=read_result.raw_rows,
        normalized_rows=normalized_rows,
        mapped_members=tuple(mapped_members),
        unmapped_rows=tuple(unmapped),
        warnings=tuple(warnings),
        mapping=mapping,
    )


__all__ = ["load_etabs_mapping", "map_etabs_demands"]
