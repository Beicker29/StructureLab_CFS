"""Typed loader for the approved schema-0.1.0 project.yaml contract."""

from collections.abc import Mapping
from hashlib import sha256
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import TypeVar

import yaml

from cfs_design.core.exceptions import (
    ConfigurationError,
    SchemaError,
    UnsupportedFeatureError,
    ValidationError,
)
from cfs_design.domain import (
    DesignContext,
    DesignFormat,
    DesignMethod,
    ProjectMetadata,
    RunMode,
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
)
from cfs_design.io.etabs import ETABSColumnMap, ETABSImportConfig

from .models import (
    CatalogVerificationAction,
    CatalogVerificationConfig,
    ETABSDemandProcessingConfig,
    ETABSMappingConfig,
    ETABSUnitHandlingConfig,
    OutputConfig,
    ProjectConfig,
    ProjectETABSConfig,
    ProjectFileReference,
    ProjectFilesConfig,
    QualityAssuranceConfig,
)


SUPPORTED_PROJECT_SCHEMA_VERSION = "0.1.0"
SUPPORTED_STANDARD_ID = S100_24_STANDARD_ID
SUPPORTED_STANDARD_EDITION = S100_24_STANDARD_EDITION
SUPPORTED_CANONICAL_UNITS = "SI"
_REQUIRED_SECTIONS = (
    "schema_version",
    "project",
    "design_context",
    "files",
    "catalog_verification",
    "etabs_import",
    "quality_assurance",
    "outputs",
)
_EXPECTED_MAPPING_PRIORITY = (
    "etabs_unique_name",
    "etabs_story+etabs_beam",
)

EnumType = TypeVar("EnumType")


def _schema_error(source: Path, location: str, message: str) -> SchemaError:
    return SchemaError(f"{source.name}; {location}: {message}")


def _mapping(
    value: object,
    source: Path,
    location: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _schema_error(source, location, "expected a mapping")
    return value


def _required(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> object:
    if key not in mapping:
        raise _schema_error(source, location, f"missing required key {key!r}")
    return mapping[key]


def _text(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> str:
    value = _required(mapping, key, source, location)
    if not isinstance(value, str) or not value.strip():
        raise _schema_error(source, f"{location}.{key}", "expected non-blank text")
    return value


def _optional_text(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> str | None:
    if key not in mapping or mapping[key] is None:
        return None
    value = mapping[key]
    if not isinstance(value, str):
        raise _schema_error(source, f"{location}.{key}", "expected text or null")
    return value


def _boolean(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> bool:
    value = _required(mapping, key, source, location)
    if not isinstance(value, bool):
        raise _schema_error(source, f"{location}.{key}", "expected a boolean")
    return value


def _positive_row_number(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> int:
    value = _required(mapping, key, source, location)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _schema_error(
            source,
            f"{location}.{key}",
            "expected a positive integer",
        )
    return value


def _non_negative_number(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> float:
    value = _required(mapping, key, source, location)
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(value)
        or value < 0.0
    ):
        raise _schema_error(
            source,
            f"{location}.{key}",
            "expected a finite non-negative number",
        )
    return float(value)


def _string_tuple(
    mapping: Mapping[str, object],
    key: str,
    source: Path,
    location: str,
) -> tuple[str, ...]:
    value = _required(mapping, key, source, location)
    if not isinstance(value, list):
        raise _schema_error(source, f"{location}.{key}", "expected a list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise _schema_error(
            source,
            f"{location}.{key}",
            "entries must be non-blank strings",
        )
    return tuple(value)


def _enum(
    enum_type: type[EnumType],
    value: object,
    source: Path,
    location: str,
) -> EnumType:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except (TypeError, ValueError) as error:
        allowed = ", ".join(member.value for member in enum_type)  # type: ignore[attr-defined]
        raise _schema_error(
            source,
            location,
            f"unknown value {value!r}; expected one of: {allowed}",
        ) from error


def _repository_root(project_path: Path, supplied: str | Path | None) -> Path:
    if supplied is not None:
        root = Path(supplied).expanduser().resolve()
        if not root.is_dir():
            raise ConfigurationError(f"Repository root does not exist: {root}")
        return root
    for candidate in (project_path.parent, *project_path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    raise ConfigurationError(
        f"Unable to discover repository root above {project_path}; "
        "pass repository_root explicitly"
    )


def _resolve_relative_path(
    configured: str,
    root: Path,
    source: Path,
    location: str,
    *,
    require_file: bool,
) -> Path:
    relative = Path(configured)
    if relative.is_absolute():
        raise _schema_error(
            source,
            location,
            "path must be repository-root-relative",
        )
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise _schema_error(source, location, "path escapes repository_root")
    if require_file and not resolved.is_file():
        raise ConfigurationError(
            f"{source.name}; {location}: referenced file does not exist: {resolved}"
        )
    return resolved


def _project_metadata(document: Mapping[str, object], source: Path) -> ProjectMetadata:
    section = _mapping(_required(document, "project", source, "root"), source, "project")
    try:
        return ProjectMetadata(
            project_id=_text(section, "project_id", source, "project"),
            name=_text(section, "name", source, "project"),
            description=_optional_text(section, "description", source, "project"),
            engineer=_optional_text(section, "engineer", source, "project"),
            client=_optional_text(section, "client", source, "project"),
            location=_optional_text(section, "location", source, "project"),
        )
    except ValidationError as error:
        raise _schema_error(source, "project", str(error)) from error


def _design_context(document: Mapping[str, object], source: Path) -> DesignContext:
    section = _mapping(
        _required(document, "design_context", source, "root"),
        source,
        "design_context",
    )
    standard = _mapping(
        _required(section, "standard", source, "design_context"),
        source,
        "design_context.standard",
    )
    standard_id = _text(standard, "id", source, "design_context.standard")
    edition = _required(standard, "edition", source, "design_context.standard")
    if isinstance(edition, bool) or not isinstance(edition, int):
        raise _schema_error(
            source,
            "design_context.standard.edition",
            "expected an integer",
        )
    design_format = _enum(
        DesignFormat,
        _required(section, "design_format", source, "design_context"),
        source,
        "design_context.design_format",
    )
    method_values = _string_tuple(
        section, "methods", source, "design_context"
    )
    methods = tuple(
        _enum(DesignMethod, value, source, "design_context.methods")
        for value in method_values
    )
    run_mode = _enum(
        RunMode,
        _required(section, "run_mode", source, "design_context"),
        source,
        "design_context.run_mode",
    )
    canonical_units = _text(
        section, "canonical_units", source, "design_context"
    )
    try:
        context = DesignContext(
            standard_id=standard_id,
            standard_edition=edition,
            design_format=design_format,
            methods=methods,
            run_mode=run_mode,
            canonical_units=canonical_units,
        )
    except ValidationError as error:
        raise _schema_error(source, "design_context", str(error)) from error

    if standard_id != SUPPORTED_STANDARD_ID:
        raise UnsupportedFeatureError(
            f"M5 supports only standard.id={SUPPORTED_STANDARD_ID!r}; "
            f"received {standard_id!r}"
        )
    if edition != SUPPORTED_STANDARD_EDITION:
        raise UnsupportedFeatureError(
            f"M5 supports only standard.edition={SUPPORTED_STANDARD_EDITION}; "
            f"received {edition!r}"
        )
    if design_format is not DesignFormat.LRFD:
        raise UnsupportedFeatureError(
            f"M5 supports only LRFD; received {design_format.value}"
        )
    if canonical_units != SUPPORTED_CANONICAL_UNITS:
        raise UnsupportedFeatureError(
            f"M5 supports only canonical_units='SI'; received {canonical_units!r}"
        )
    required_methods = {
        RunMode.EWM: {DesignMethod.EWM},
        RunMode.DSM: {DesignMethod.DSM},
        RunMode.COMPARE: {DesignMethod.EWM, DesignMethod.DSM},
    }[run_mode]
    missing = required_methods - set(methods)
    if missing:
        names = ", ".join(sorted(method.value for method in missing))
        raise ConfigurationError(
            f"run_mode={run_mode.value!r} requires configured methods: {names}"
        )
    return context


def _file_references(
    document: Mapping[str, object],
    source: Path,
    root: Path,
) -> ProjectFilesConfig:
    section = _mapping(_required(document, "files", source, "root"), source, "files")

    def reference(key: str) -> ProjectFileReference:
        configured = _text(section, key, source, "files")
        return ProjectFileReference(
            configured_path=configured,
            resolved_path=_resolve_relative_path(
                configured,
                root,
                source,
                f"files.{key}",
                require_file=True,
            ),
        )

    return ProjectFilesConfig(
        materials_catalog=reference("materials_catalog"),
        sections_catalog=reference("sections_catalog"),
        members=reference("members"),
        etabs_results=reference("etabs_results"),
    )


def _catalog_verification(
    document: Mapping[str, object], source: Path
) -> CatalogVerificationConfig:
    section = _mapping(
        _required(document, "catalog_verification", source, "root"),
        source,
        "catalog_verification",
    )
    action = _enum(
        CatalogVerificationAction,
        _required(section, "action_on_fail", source, "catalog_verification"),
        source,
        "catalog_verification.action_on_fail",
    )
    try:
        return CatalogVerificationConfig(
            enabled=_boolean(section, "enabled", source, "catalog_verification"),
            relative_tolerance=_non_negative_number(
                section,
                "relative_tolerance",
                source,
                "catalog_verification",
            ),
            required_properties=_string_tuple(
                section,
                "required_properties",
                source,
                "catalog_verification",
            ),
            extended_properties=_string_tuple(
                section,
                "extended_properties",
                source,
                "catalog_verification",
            ),
            action_on_fail=action,
        )
    except ValidationError as error:
        raise _schema_error(source, "catalog_verification", str(error)) from error


def _etabs_config(document: Mapping[str, object], source: Path) -> ProjectETABSConfig:
    section = _mapping(
        _required(document, "etabs_import", source, "root"),
        source,
        "etabs_import",
    )
    layout = _mapping(
        _required(section, "native_layout", source, "etabs_import"),
        source,
        "etabs_import.native_layout",
    )
    columns = _mapping(
        _required(section, "columns", source, "etabs_import"),
        source,
        "etabs_import.columns",
    )
    try:
        column_map = ETABSColumnMap(
            story=_text(columns, "story", source, "etabs_import.columns"),
            frame_label=_text(
                columns, "frame_label", source, "etabs_import.columns"
            ),
            unique_name=_text(
                columns, "unique_name", source, "etabs_import.columns"
            ),
            output_case=_text(
                columns, "output_case", source, "etabs_import.columns"
            ),
            case_type=_text(
                columns, "case_type", source, "etabs_import.columns"
            ),
            step_type=_text(
                columns, "step_type", source, "etabs_import.columns"
            ),
            station=_text(columns, "station", source, "etabs_import.columns"),
            p=_text(columns, "P", source, "etabs_import.columns"),
            v2=_text(columns, "V2", source, "etabs_import.columns"),
            v3=_text(columns, "V3", source, "etabs_import.columns"),
            t=_text(columns, "T", source, "etabs_import.columns"),
            m2=_text(columns, "M2", source, "etabs_import.columns"),
            m3=_text(columns, "M3", source, "etabs_import.columns"),
            element=_text(columns, "element", source, "etabs_import.columns"),
            element_station=_text(
                columns, "element_station", source, "etabs_import.columns"
            ),
            location=_text(
                columns, "location", source, "etabs_import.columns"
            ),
        )
        importer = ETABSImportConfig(
            program_control_sheet=_text(
                section, "program_control_sheet", source, "etabs_import"
            ),
            forces_sheet=_text(section, "forces_sheet", source, "etabs_import"),
            table_title_row=_positive_row_number(
                layout,
                "table_title_row",
                source,
                "etabs_import.native_layout",
            ),
            header_row=_positive_row_number(
                layout, "header_row", source, "etabs_import.native_layout"
            ),
            units_row=_positive_row_number(
                layout, "units_row", source, "etabs_import.native_layout"
            ),
            data_start_row=_positive_row_number(
                layout,
                "data_start_row",
                source,
                "etabs_import.native_layout",
            ),
            columns=column_map,
        )
    except ValidationError as error:
        raise _schema_error(source, "etabs_import", str(error)) from error

    mapping_section = _mapping(
        _required(section, "mapping", source, "etabs_import"),
        source,
        "etabs_import.mapping",
    )
    mapping_config = ETABSMappingConfig(
        source_sheet=_text(
            mapping_section,
            "source_sheet",
            source,
            "etabs_import.mapping",
        ),
        priority=_string_tuple(
            mapping_section, "priority", source, "etabs_import.mapping"
        ),
    )
    if mapping_config.priority != _EXPECTED_MAPPING_PRIORITY:
        raise UnsupportedFeatureError(
            "M5 supports only ETABS mapping priority "
            f"{_EXPECTED_MAPPING_PRIORITY!r}; received {mapping_config.priority!r}"
        )

    processing_section = _mapping(
        _required(section, "demand_processing", source, "etabs_import"),
        source,
        "etabs_import.demand_processing",
    )
    processing = ETABSDemandProcessingConfig(
        preserve_native_rows=_boolean(
            processing_section,
            "preserve_native_rows",
            source,
            "etabs_import.demand_processing",
        ),
        preserve_station=_boolean(
            processing_section,
            "preserve_station",
            source,
            "etabs_import.demand_processing",
        ),
        preserve_step_type=_boolean(
            processing_section,
            "preserve_step_type",
            source,
            "etabs_import.demand_processing",
        ),
        componentwise_envelope=_boolean(
            processing_section,
            "componentwise_envelope",
            source,
            "etabs_import.demand_processing",
        ),
        governing_selection=_text(
            processing_section,
            "governing_selection",
            source,
            "etabs_import.demand_processing",
        ),
    )
    if not (
        processing.preserve_native_rows
        and processing.preserve_station
        and processing.preserve_step_type
        and not processing.componentwise_envelope
    ):
        raise UnsupportedFeatureError(
            "M5 requires native rows, stations, and step types to be preserved "
            "and componentwise_envelope=false"
        )

    unit_section = _mapping(
        _required(section, "unit_handling", source, "etabs_import"),
        source,
        "etabs_import.unit_handling",
    )
    unit_handling = ETABSUnitHandlingConfig(
        read_units_from_export=_boolean(
            unit_section,
            "read_units_from_export",
            source,
            "etabs_import.unit_handling",
        ),
        convert_to_canonical_si=_boolean(
            unit_section,
            "convert_to_canonical_SI",
            source,
            "etabs_import.unit_handling",
        ),
        reject_unknown_units=_boolean(
            unit_section,
            "reject_unknown_units",
            source,
            "etabs_import.unit_handling",
        ),
    )
    if not all(
        (
            unit_handling.read_units_from_export,
            unit_handling.convert_to_canonical_si,
            unit_handling.reject_unknown_units,
        )
    ):
        raise UnsupportedFeatureError(
            "M5 requires explicit source units, canonical SI conversion, and "
            "unknown-unit rejection"
        )
    return ProjectETABSConfig(
        importer=importer,
        mapping=mapping_config,
        demand_processing=processing,
        unit_handling=unit_handling,
    )


def _quality_assurance(
    document: Mapping[str, object], source: Path
) -> QualityAssuranceConfig:
    section = _mapping(
        _required(document, "quality_assurance", source, "root"),
        source,
        "quality_assurance",
    )
    return QualityAssuranceConfig(
        fail_on_duplicate_case_id=_boolean(
            section, "fail_on_duplicate_case_id", source, "quality_assurance"
        ),
        fail_on_duplicate_material_id=_boolean(
            section,
            "fail_on_duplicate_material_id",
            source,
            "quality_assurance",
        ),
        fail_on_duplicate_section_id=_boolean(
            section,
            "fail_on_duplicate_section_id",
            source,
            "quality_assurance",
        ),
        fail_on_unmapped_etabs_member=_boolean(
            section,
            "fail_on_unmapped_etabs_member",
            source,
            "quality_assurance",
        ),
        fail_on_missing_catalog_reference=_boolean(
            section,
            "fail_on_missing_catalog_reference",
            source,
            "quality_assurance",
        ),
        preserve_resolved_input_snapshot=_boolean(
            section,
            "preserve_resolved_input_snapshot",
            source,
            "quality_assurance",
        ),
    )


def _outputs(
    document: Mapping[str, object], source: Path, root: Path
) -> OutputConfig:
    section = _mapping(
        _required(document, "outputs", source, "root"), source, "outputs"
    )
    configured_root = _text(section, "root", source, "outputs")
    return OutputConfig(
        root=configured_root,
        resolved_root=_resolve_relative_path(
            configured_root,
            root,
            source,
            "outputs.root",
            require_file=False,
        ),
        write_resolved_inputs=_boolean(
            section, "write_resolved_inputs", source, "outputs"
        ),
        write_member_results=_boolean(
            section, "write_member_results", source, "outputs"
        ),
        write_comparison_results=_boolean(
            section, "write_comparison_results", source, "outputs"
        ),
        write_project_summary=_boolean(
            section, "write_project_summary", source, "outputs"
        ),
        calculation_trace=_boolean(
            section, "calculation_trace", source, "outputs"
        ),
    )


def load_project_config(
    project_yaml_path: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> ProjectConfig:
    """Load one project contract with deterministic root-relative paths."""

    supplied = Path(project_yaml_path).expanduser()
    if not supplied.is_file():
        raise ConfigurationError(f"Project YAML does not exist: {supplied}")
    source = supplied.resolve()
    try:
        source_bytes = source.read_bytes()
        document = yaml.safe_load(source_bytes.decode("utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise SchemaError(f"Unable to parse project YAML {source}: {error}") from error
    root_document = _mapping(document, source, "root")
    missing_sections = [key for key in _REQUIRED_SECTIONS if key not in root_document]
    if missing_sections:
        raise _schema_error(
            source,
            "root",
            f"missing required sections: {', '.join(missing_sections)}",
        )
    schema_version = _text(root_document, "schema_version", source, "root")
    if schema_version != SUPPORTED_PROJECT_SCHEMA_VERSION:
        raise SchemaError(
            f"{source.name}: unsupported schema_version {schema_version!r}; "
            f"supported version is {SUPPORTED_PROJECT_SCHEMA_VERSION!r}"
        )
    root = _repository_root(source, repository_root)
    try:
        return ProjectConfig(
            schema_version=schema_version,
            metadata=_project_metadata(root_document, source),
            design_context=_design_context(root_document, source),
            files=_file_references(root_document, source, root),
            catalog_verification=_catalog_verification(root_document, source),
            etabs_import=_etabs_config(root_document, source),
            quality_assurance=_quality_assurance(root_document, source),
            outputs=_outputs(root_document, source, root),
            source_path=source,
            file_sha256=sha256(source_bytes).hexdigest(),
            repository_root=root,
        )
    except ValidationError as error:
        raise _schema_error(source, "root", str(error)) from error


__all__ = ["SUPPORTED_PROJECT_SCHEMA_VERSION", "load_project_config"]
