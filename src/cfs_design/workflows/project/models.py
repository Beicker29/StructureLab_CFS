"""Immutable project-resolution aggregates and structured QA diagnostics."""

from dataclasses import dataclass
from pathlib import Path

from cfs_design.catalogs import CatalogRegistry
from cfs_design.core.exceptions import ConfigurationError, ValidationError
from cfs_design.domain import Project, ResolvedMember
from cfs_design.domain._validation import require_non_empty, require_optional_string
from cfs_design.io.etabs import ETABSImportResult, NormalizedETABSDemand
from cfs_design.io.project import ProjectConfig
from cfs_design.mechanics.sections import (
    AdvancedSectionProperties,
    CatalogVerificationResult,
    ComputedSectionProperties,
)
from cfs_design.results import DiagnosticSeverity


@dataclass(frozen=True, slots=True)
class ProjectDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    case_id: str | None = None
    section_id: str | None = None
    context: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.severity, DiagnosticSeverity):
            raise ValidationError("severity must be DiagnosticSeverity")
        require_non_empty(self.code, "code")
        require_non_empty(self.message, "message")
        require_optional_string(self.case_id, "case_id")
        require_optional_string(self.section_id, "section_id")
        if not isinstance(self.context, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0].strip()
            for item in self.context
        ):
            raise ValidationError("context must be a tuple of named value pairs")


def _absolute_path(value: Path, field_name: str) -> None:
    if not isinstance(value, Path) or not value.is_absolute():
        raise ValidationError(f"{field_name} must be an absolute pathlib.Path")


def _sha256(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError(f"{field_name} must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class ProjectProvenance:
    project_yaml_path: Path
    project_yaml_sha256: str
    members_path: Path
    members_sha256: str
    materials_catalog_path: Path
    materials_catalog_sha256: str
    sections_catalog_path: Path
    sections_catalog_sha256: str
    etabs_path: Path
    etabs_sha256: str
    etabs_program_version: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "project_yaml_path",
            "members_path",
            "materials_catalog_path",
            "sections_catalog_path",
            "etabs_path",
        ):
            _absolute_path(getattr(self, field_name), field_name)
        for field_name in (
            "project_yaml_sha256",
            "members_sha256",
            "materials_catalog_sha256",
            "sections_catalog_sha256",
            "etabs_sha256",
        ):
            _sha256(getattr(self, field_name), field_name)
        require_optional_string(self.etabs_program_version, "etabs_program_version")


@dataclass(frozen=True, slots=True)
class ResolvedSectionMechanics:
    """One coherent M3A/M3B design-property set and its project QA gate."""

    section_id: str
    gross: ComputedSectionProperties
    advanced: AdvancedSectionProperties
    verification: CatalogVerificationResult | None
    design_use_permitted: bool
    gate_reason: str

    def __post_init__(self) -> None:
        require_non_empty(self.section_id, "section_id")
        if not isinstance(self.gross, ComputedSectionProperties):
            raise ValidationError("gross must be ComputedSectionProperties")
        if not isinstance(self.advanced, AdvancedSectionProperties):
            raise ValidationError("advanced must be AdvancedSectionProperties")
        if self.gross.section_id != self.section_id:
            raise ValidationError("gross section_id must match section_id")
        if self.advanced.section_id != self.section_id:
            raise ValidationError("advanced section_id must match section_id")
        if self.gross.geometry_id != self.advanced.geometry_id:
            raise ValidationError("M3A and M3B geometry_id values must match")
        if self.verification is not None:
            if not isinstance(self.verification, CatalogVerificationResult):
                raise ValidationError(
                    "verification must be CatalogVerificationResult or None"
                )
            if self.verification.section_id != self.section_id:
                raise ValidationError("verification section_id must match section_id")
        if not isinstance(self.design_use_permitted, bool):
            raise ValidationError("design_use_permitted must be bool")
        if self.design_use_permitted and self.verification is None:
            raise ValidationError(
                "design use cannot be permitted without catalog verification"
            )
        require_non_empty(self.gate_reason, "gate_reason")


@dataclass(frozen=True, slots=True)
class ResolvedProject:
    project: Project
    project_config: ProjectConfig
    catalog_registry: CatalogRegistry
    active_resolved_members: tuple[ResolvedMember, ...]
    section_verification_results: tuple[CatalogVerificationResult, ...]
    etabs_import: ETABSImportResult
    diagnostics: tuple[ProjectDiagnostic, ...]
    provenance: ProjectProvenance
    section_mechanics: tuple[ResolvedSectionMechanics, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.project, Project):
            raise ValidationError("project must be Project")
        if not isinstance(self.project_config, ProjectConfig):
            raise ValidationError("project_config must be ProjectConfig")
        if not isinstance(self.catalog_registry, CatalogRegistry):
            raise ValidationError("catalog_registry must be CatalogRegistry")
        if not isinstance(self.active_resolved_members, tuple) or any(
            not isinstance(member, ResolvedMember)
            for member in self.active_resolved_members
        ):
            raise ValidationError(
                "active_resolved_members must be a tuple of ResolvedMember"
            )
        if any(not member.member.active for member in self.active_resolved_members):
            raise ValidationError("active_resolved_members contains inactive member")
        identifiers = tuple(
            member.member.case_id for member in self.active_resolved_members
        )
        if len(set(identifiers)) != len(identifiers):
            raise ValidationError("active resolved member case IDs must be unique")
        project_identifiers = {member.case_id for member in self.project.members}
        if any(identifier not in project_identifiers for identifier in identifiers):
            raise ValidationError(
                "active resolved members must belong to the unresolved Project"
            )
        if self.project.metadata != self.project_config.metadata:
            raise ValidationError("project metadata must match ProjectConfig")
        if self.project.design_context != self.project_config.design_context:
            raise ValidationError("project design context must match ProjectConfig")
        if self.project.scope_evidence != self.project_config.scope_evidence:
            raise ValidationError("project scope evidence must match ProjectConfig")
        if not isinstance(self.section_verification_results, tuple) or any(
            not isinstance(result, CatalogVerificationResult)
            for result in self.section_verification_results
        ):
            raise ValidationError(
                "section_verification_results must contain CatalogVerificationResult"
            )
        verified_ids = tuple(
            result.section_id for result in self.section_verification_results
        )
        if len(set(verified_ids)) != len(verified_ids):
            raise ValidationError("section verification IDs must be unique")
        if not isinstance(self.etabs_import, ETABSImportResult):
            raise ValidationError("etabs_import must be ETABSImportResult")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, ProjectDiagnostic) for item in self.diagnostics
        ):
            raise ValidationError("diagnostics must contain ProjectDiagnostic")
        if not isinstance(self.provenance, ProjectProvenance):
            raise ValidationError("provenance must be ProjectProvenance")
        if not isinstance(self.section_mechanics, tuple) or any(
            not isinstance(item, ResolvedSectionMechanics)
            for item in self.section_mechanics
        ):
            raise ValidationError(
                "section_mechanics must contain ResolvedSectionMechanics"
            )
        mechanics_ids = tuple(item.section_id for item in self.section_mechanics)
        if len(set(mechanics_ids)) != len(mechanics_ids):
            raise ValidationError("section mechanics IDs must be unique")

    @property
    def metadata(self):
        return self.project.metadata

    @property
    def design_context(self):
        return self.project.design_context

    @property
    def scope_evidence(self):
        return self.project.scope_evidence

    @property
    def all_member_cases(self):
        return self.project.members

    @property
    def inactive_member_cases(self):
        return tuple(member for member in self.project.members if not member.active)

    @property
    def unmapped_etabs_rows(self) -> tuple[NormalizedETABSDemand, ...]:
        return self.etabs_import.unmapped_rows

    @property
    def warnings(self) -> tuple[ProjectDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.WARNING
        )

    def get_section_mechanics(self, section_id: str) -> ResolvedSectionMechanics:
        """Return the coherent M3 property set; never synthesize a catalog mix."""

        require_non_empty(section_id, "section_id")
        for mechanics in self.section_mechanics:
            if mechanics.section_id == section_id:
                return mechanics
        raise ValidationError(f"No resolved M3 mechanics for section_id {section_id!r}")

    def require_design_mechanics(
        self,
        section_id: str,
    ) -> ResolvedSectionMechanics:
        """Return the coherent set only when the project QA gate permits design."""

        mechanics = self.get_section_mechanics(section_id)
        if not mechanics.design_use_permitted:
            raise ConfigurationError(
                f"Section {section_id!r} is blocked from design use: "
                f"{mechanics.gate_reason}"
            )
        return mechanics


__all__ = [
    "DiagnosticSeverity",
    "ProjectDiagnostic",
    "ProjectProvenance",
    "ResolvedProject",
    "ResolvedSectionMechanics",
]
