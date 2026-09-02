"""Immutable typed configuration and Members-workbook result models."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Real
from pathlib import Path

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    AISIProjectScopeEvidence,
    DesignContext,
    MemberCase,
    ProjectMetadata,
)
from cfs_design.domain._validation import require_bool, require_non_empty
from cfs_design.io.etabs import ETABSImportConfig


class CatalogVerificationAction(str, Enum):
    WARNING = "warning"
    ERROR = "error"


def _require_sha256(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError(f"{field_name} must be a lowercase SHA-256 digest")


def _require_absolute_path(value: Path, field_name: str) -> None:
    if not isinstance(value, Path) or not value.is_absolute():
        raise ValidationError(f"{field_name} must be an absolute pathlib.Path")


def _require_string_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise ValidationError(f"{field_name} must be a tuple")
    for item in value:
        require_non_empty(item, field_name)
    if len(set(value)) != len(value):
        raise ValidationError(f"{field_name} must not contain duplicates")


@dataclass(frozen=True, slots=True)
class ProjectFileReference:
    configured_path: str
    resolved_path: Path

    def __post_init__(self) -> None:
        require_non_empty(self.configured_path, "configured_path")
        _require_absolute_path(self.resolved_path, "resolved_path")


@dataclass(frozen=True, slots=True)
class ProjectFilesConfig:
    materials_catalog: ProjectFileReference
    sections_catalog: ProjectFileReference
    members: ProjectFileReference
    etabs_results: ProjectFileReference

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if not isinstance(getattr(self, field_name), ProjectFileReference):
                raise ValidationError(
                    f"{field_name} must be a ProjectFileReference"
                )


@dataclass(frozen=True, slots=True)
class CatalogVerificationConfig:
    enabled: bool
    relative_tolerance: float
    required_properties: tuple[str, ...]
    extended_properties: tuple[str, ...]
    action_on_fail: CatalogVerificationAction

    def __post_init__(self) -> None:
        require_bool(self.enabled, "enabled")
        if (
            isinstance(self.relative_tolerance, bool)
            or not isinstance(self.relative_tolerance, Real)
            or not isfinite(self.relative_tolerance)
            or self.relative_tolerance < 0.0
        ):
            raise ValidationError(
                "relative_tolerance must be a finite non-negative number"
            )
        _require_string_tuple(self.required_properties, "required_properties")
        _require_string_tuple(self.extended_properties, "extended_properties")
        overlap = set(self.required_properties) & set(self.extended_properties)
        if overlap:
            raise ValidationError(
                "required_properties and extended_properties must be disjoint"
            )
        if self.enabled and not (
            self.required_properties or self.extended_properties
        ):
            raise ValidationError(
                "enabled catalog verification requires at least one property"
            )
        if not isinstance(self.action_on_fail, CatalogVerificationAction):
            raise ValidationError(
                "action_on_fail must be a CatalogVerificationAction"
            )


@dataclass(frozen=True, slots=True)
class ETABSMappingConfig:
    source_sheet: str
    priority: tuple[str, ...]

    def __post_init__(self) -> None:
        require_non_empty(self.source_sheet, "source_sheet")
        _require_string_tuple(self.priority, "priority")


@dataclass(frozen=True, slots=True)
class ETABSDemandProcessingConfig:
    preserve_native_rows: bool
    preserve_station: bool
    preserve_step_type: bool
    componentwise_envelope: bool
    governing_selection: str

    def __post_init__(self) -> None:
        for field_name in (
            "preserve_native_rows",
            "preserve_station",
            "preserve_step_type",
            "componentwise_envelope",
        ):
            require_bool(getattr(self, field_name), field_name)
        require_non_empty(self.governing_selection, "governing_selection")


@dataclass(frozen=True, slots=True)
class ETABSUnitHandlingConfig:
    read_units_from_export: bool
    convert_to_canonical_si: bool
    reject_unknown_units: bool

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            require_bool(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ProjectETABSConfig:
    importer: ETABSImportConfig
    mapping: ETABSMappingConfig
    demand_processing: ETABSDemandProcessingConfig
    unit_handling: ETABSUnitHandlingConfig

    def __post_init__(self) -> None:
        if not isinstance(self.importer, ETABSImportConfig):
            raise ValidationError("importer must be ETABSImportConfig")
        if not isinstance(self.mapping, ETABSMappingConfig):
            raise ValidationError("mapping must be ETABSMappingConfig")
        if not isinstance(self.demand_processing, ETABSDemandProcessingConfig):
            raise ValidationError(
                "demand_processing must be ETABSDemandProcessingConfig"
            )
        if not isinstance(self.unit_handling, ETABSUnitHandlingConfig):
            raise ValidationError("unit_handling must be ETABSUnitHandlingConfig")


@dataclass(frozen=True, slots=True)
class QualityAssuranceConfig:
    fail_on_duplicate_case_id: bool
    fail_on_duplicate_material_id: bool
    fail_on_duplicate_section_id: bool
    fail_on_unmapped_etabs_member: bool
    fail_on_missing_catalog_reference: bool
    preserve_resolved_input_snapshot: bool

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            require_bool(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class OutputConfig:
    root: str
    resolved_root: Path
    write_resolved_inputs: bool
    write_member_results: bool
    write_comparison_results: bool
    write_project_summary: bool
    calculation_trace: bool

    def __post_init__(self) -> None:
        require_non_empty(self.root, "root")
        _require_absolute_path(self.resolved_root, "resolved_root")
        for field_name in (
            "write_resolved_inputs",
            "write_member_results",
            "write_comparison_results",
            "write_project_summary",
            "calculation_trace",
        ):
            require_bool(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    schema_version: str
    metadata: ProjectMetadata
    design_context: DesignContext
    scope_evidence: AISIProjectScopeEvidence
    files: ProjectFilesConfig
    catalog_verification: CatalogVerificationConfig
    etabs_import: ProjectETABSConfig
    quality_assurance: QualityAssuranceConfig
    outputs: OutputConfig
    source_path: Path
    file_sha256: str
    repository_root: Path

    def __post_init__(self) -> None:
        require_non_empty(self.schema_version, "schema_version")
        if not isinstance(self.metadata, ProjectMetadata):
            raise ValidationError("metadata must be ProjectMetadata")
        if not isinstance(self.design_context, DesignContext):
            raise ValidationError("design_context must be DesignContext")
        if not isinstance(self.scope_evidence, AISIProjectScopeEvidence):
            raise ValidationError(
                "scope_evidence must be AISIProjectScopeEvidence"
            )
        if not isinstance(self.files, ProjectFilesConfig):
            raise ValidationError("files must be ProjectFilesConfig")
        if not isinstance(self.catalog_verification, CatalogVerificationConfig):
            raise ValidationError(
                "catalog_verification must be CatalogVerificationConfig"
            )
        if not isinstance(self.etabs_import, ProjectETABSConfig):
            raise ValidationError("etabs_import must be ProjectETABSConfig")
        if not isinstance(self.quality_assurance, QualityAssuranceConfig):
            raise ValidationError("quality_assurance must be QualityAssuranceConfig")
        if not isinstance(self.outputs, OutputConfig):
            raise ValidationError("outputs must be OutputConfig")
        _require_absolute_path(self.source_path, "source_path")
        _require_sha256(self.file_sha256, "file_sha256")
        _require_absolute_path(self.repository_root, "repository_root")


@dataclass(frozen=True, slots=True)
class MembersWorkbookMetadata:
    name: str
    schema_version: str
    canonical_units: str
    source_path: Path
    file_sha256: str
    additional_fields: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("name", "schema_version", "canonical_units"):
            require_non_empty(getattr(self, field_name), field_name)
        _require_absolute_path(self.source_path, "source_path")
        _require_sha256(self.file_sha256, "file_sha256")
        if not isinstance(self.additional_fields, tuple):
            raise ValidationError("additional_fields must be a tuple")


@dataclass(frozen=True, slots=True)
class MembersLoadResult:
    metadata: MembersWorkbookMetadata
    members: tuple[MemberCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MembersWorkbookMetadata):
            raise ValidationError("metadata must be MembersWorkbookMetadata")
        if not isinstance(self.members, tuple) or any(
            not isinstance(member, MemberCase) for member in self.members
        ):
            raise ValidationError("members must be a tuple of MemberCase")
        if not self.members:
            raise ValidationError("members must contain at least one MemberCase")
        identifiers = tuple(member.case_id for member in self.members)
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError("member case_id values must be unique")

    @property
    def active_members(self) -> tuple[MemberCase, ...]:
        return tuple(member for member in self.members if member.active)


__all__ = [
    "CatalogVerificationAction",
    "CatalogVerificationConfig",
    "ETABSDemandProcessingConfig",
    "ETABSMappingConfig",
    "ETABSUnitHandlingConfig",
    "MembersLoadResult",
    "MembersWorkbookMetadata",
    "OutputConfig",
    "ProjectConfig",
    "ProjectETABSConfig",
    "ProjectFileReference",
    "ProjectFilesConfig",
    "QualityAssuranceConfig",
]
