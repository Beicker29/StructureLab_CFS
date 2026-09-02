"""Immutable identities for the engineering-standard files audited in M7."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain._validation import require_non_empty
from cfs_design.domain.standards import (
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
)
from cfs_design.results import EquationReference, ReferenceSourceType

from .enums import StandardDocumentRole


SOURCE_AUTHORITY_ORDER = (
    StandardDocumentRole.PRIMARY_NORMATIVE,
    StandardDocumentRole.VALIDATION_REFERENCE,
    StandardDocumentRole.PREVIOUS_STANDARD,
    StandardDocumentRole.COMMENTARY,
    StandardDocumentRole.FUTURE_SCOPE,
)


def _validate_sha256(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValidationError("sha256 must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class StandardDocument:
    """Identity and provenance metadata; the referenced document is authoritative."""

    source_id: str
    designation: str
    title: str
    edition: int
    organization: str
    role: StandardDocumentRole
    repository_relative_path: str
    sha256: str

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "designation",
            "title",
            "organization",
            "repository_relative_path",
        ):
            require_non_empty(getattr(self, field_name), field_name)
        if (
            isinstance(self.edition, bool)
            or not isinstance(self.edition, int)
            or self.edition <= 0
        ):
            raise ValidationError("edition must be a positive integer")
        if not isinstance(self.role, StandardDocumentRole):
            raise ValidationError("role must be StandardDocumentRole")
        path = PurePosixPath(self.repository_relative_path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.suffix.lower() != ".pdf"
            or self.repository_relative_path != path.as_posix()
        ):
            raise ValidationError(
                "repository_relative_path must be a normalized relative PDF path"
            )
        _validate_sha256(self.sha256)


@dataclass(frozen=True, slots=True)
class StandardSourceRegistry:
    """The single typed registry for locally approved standard documents."""

    documents: tuple[StandardDocument, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.documents, tuple) or not self.documents:
            raise ValidationError("documents must be a non-empty tuple")
        if any(not isinstance(item, StandardDocument) for item in self.documents):
            raise ValidationError("documents must contain StandardDocument values")
        source_ids = tuple(item.source_id for item in self.documents)
        paths = tuple(item.repository_relative_path for item in self.documents)
        if len(set(source_ids)) != len(source_ids):
            raise ValidationError("standard source_id values must be unique")
        if len(set(paths)) != len(paths):
            raise ValidationError("standard document paths must be unique")
        primary = self.by_role(StandardDocumentRole.PRIMARY_NORMATIVE)
        if len(primary) != 1:
            raise ValidationError(
                "standard source registry requires exactly one primary authority"
            )

    def by_role(
        self, role: StandardDocumentRole
    ) -> tuple[StandardDocument, ...]:
        if not isinstance(role, StandardDocumentRole):
            raise ValidationError("role must be StandardDocumentRole")
        return tuple(item for item in self.documents if item.role is role)

    @property
    def primary(self) -> StandardDocument:
        return self.by_role(StandardDocumentRole.PRIMARY_NORMATIVE)[0]


PRIMARY_S100_24 = StandardDocument(
    source_id="ANSI_SDI_AISI_S100_2024",
    designation="ANSI/SDI AISI S100-2024",
    title=(
        "North American Specification for the Design of Cold-Formed Steel "
        "Structural Members"
    ),
    edition=S100_24_STANDARD_EDITION,
    organization="Steel Deck Institute",
    role=StandardDocumentRole.PRIMARY_NORMATIVE,
    repository_relative_path=(
        "references/standards/AISI_S100-24/"
        "ANSI-SDI-AISI-S100-2024-SDI-AISI-S100-2024-C.pdf"
    ),
    sha256="6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca",
)

PREVIOUS_S100_16_S3_22 = StandardDocument(
    source_id="AISI_S100_16_R2020_S3_22",
    designation="AISI S100-16 (2020) w/S3-22",
    title=(
        "North American Specification for the Design of Cold-Formed Steel "
        "Structural Members, 2016 Edition (Reaffirmed 2020), With Supplement 3"
    ),
    edition=2016,
    organization="American Iron and Steel Institute",
    role=StandardDocumentRole.PREVIOUS_STANDARD,
    repository_relative_path=(
        "references/standards/AISI_previous/AISI-S100-16-2020-wS3-22.pdf"
    ),
    sha256="706a4bfaf030768d6382324a8d1916acdb749a0e739ef20fa0d7638ba8a9f03a",
)

FUTURE_S240_20 = StandardDocument(
    source_id="AISI_S240_20",
    designation="AISI S240-20",
    title="North American Standard for Cold-Formed Steel Structural Framing",
    edition=2020,
    organization="American Iron and Steel Institute",
    role=StandardDocumentRole.FUTURE_SCOPE,
    repository_relative_path=(
        "references/standards/future_scope/AISI-S240-20.pdf"
    ),
    sha256="c8bd8d62bf35878388b38a31f603478590ee744bd2b15eb77a74dbaae9d1e93e",
)

FUTURE_S400_20 = StandardDocument(
    source_id="AISI_S400_20",
    designation="AISI S400-20",
    title=(
        "North American Standard for Seismic Design of Cold-Formed Steel "
        "Structural Systems"
    ),
    edition=2020,
    organization="American Iron and Steel Institute",
    role=StandardDocumentRole.FUTURE_SCOPE,
    repository_relative_path=(
        "references/standards/future_scope/AISI-S400-20.pdf"
    ),
    sha256="97b7891ae9bc0af54e78074f7a7ddc9d6cdb9b3fdff71140c2b80630e1859b2b",
)

STANDARD_SOURCE_REGISTRY = StandardSourceRegistry(
    documents=(
        PRIMARY_S100_24,
        PREVIOUS_S100_16_S3_22,
        FUTURE_S240_20,
        FUTURE_S400_20,
    )
)


def s100_24_reference(
    *, clause: str | None = None, title: str
) -> EquationReference:
    """Create a clause-level M6 reference with the audited source fingerprint."""

    return EquationReference(
        source_type=ReferenceSourceType.STANDARD,
        standard_id=S100_24_STANDARD_ID,
        edition=PRIMARY_S100_24.edition,
        clause=clause,
        title=title,
        notes=(
            f"source_id={PRIMARY_S100_24.source_id}; "
            f"sha256={PRIMARY_S100_24.sha256}"
        ),
    )


__all__ = [
    "FUTURE_S240_20",
    "FUTURE_S400_20",
    "PREVIOUS_S100_16_S3_22",
    "PRIMARY_S100_24",
    "S100_24_STANDARD_ID",
    "S100_24_STANDARD_EDITION",
    "SOURCE_AUTHORITY_ORDER",
    "STANDARD_SOURCE_REGISTRY",
    "StandardDocument",
    "StandardSourceRegistry",
    "s100_24_reference",
]
