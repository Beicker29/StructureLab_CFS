"""Project metadata and unresolved physical-member collection."""

from dataclasses import dataclass, field

from cfs_design.core.exceptions import ValidationError

from ._validation import require_non_empty, require_optional_string
from .design_context import DesignContext
from .member import MemberCase
from .scope import AISIProjectScopeEvidence, unspecified_scope_evidence


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    project_id: str
    name: str
    description: str | None = None
    engineer: str | None = None
    client: str | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.project_id, "project_id")
        require_non_empty(self.name, "name")
        for field_name in ("description", "engineer", "client", "location"):
            require_optional_string(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class Project:
    metadata: ProjectMetadata
    design_context: DesignContext
    members: tuple[MemberCase, ...]
    scope_evidence: AISIProjectScopeEvidence = field(
        default_factory=unspecified_scope_evidence
    )

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ProjectMetadata):
            raise ValidationError("metadata must be ProjectMetadata")
        if not isinstance(self.design_context, DesignContext):
            raise ValidationError("design_context must be DesignContext")
        if not isinstance(self.members, tuple):
            raise ValidationError("members must be a tuple")
        if not self.members:
            raise ValidationError("members must contain at least one MemberCase")
        if any(not isinstance(member, MemberCase) for member in self.members):
            raise ValidationError("members must contain only MemberCase objects")
        case_ids = tuple(member.case_id for member in self.members)
        if len(set(case_ids)) != len(case_ids):
            raise ValidationError("case_id values must be unique within a Project")
        if not isinstance(self.scope_evidence, AISIProjectScopeEvidence):
            raise ValidationError(
                "scope_evidence must be AISIProjectScopeEvidence"
            )


__all__ = ["Project", "ProjectMetadata"]
