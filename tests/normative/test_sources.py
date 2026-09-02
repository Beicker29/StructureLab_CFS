"""M7 standard-source registry and development validation tests."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cfs_design.core.exceptions import StandardSourceError
from cfs_design.normative import (
    PRIMARY_S100_24,
    STANDARD_SOURCE_REGISTRY,
    StandardDocumentRole,
    select_primary_standard_path,
    validate_standard_sources,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_real_primary_source_identity_and_sha256_are_verified() -> None:
    registry = validate_standard_sources(REPOSITORY_ROOT)

    assert registry is STANDARD_SOURCE_REGISTRY
    assert registry.primary is PRIMARY_S100_24
    assert registry.primary.designation == "ANSI/SDI AISI S100-2024"
    assert registry.primary.edition == 2024
    assert registry.primary.sha256 == (
        "6ec32742f056d08a0823557d9ce58b69d84312e64a6e656b8ba4b3b10cf4b4ca"
    )
    assert registry.primary.role is StandardDocumentRole.PRIMARY_NORMATIVE


def test_secondary_sources_have_non_primary_roles_and_verified_identity() -> None:
    registry = validate_standard_sources(REPOSITORY_ROOT)
    identities = {item.source_id: item for item in registry.documents}

    assert identities["AISI_S100_16_R2020_S3_22"].role is (
        StandardDocumentRole.PREVIOUS_STANDARD
    )
    assert identities["AISI_S240_20"].role is StandardDocumentRole.FUTURE_SCOPE
    assert identities["AISI_S400_20"].role is StandardDocumentRole.FUTURE_SCOPE
    assert registry.by_role(StandardDocumentRole.VALIDATION_REFERENCE) == ()
    assert registry.by_role(StandardDocumentRole.COMMENTARY) == ()


def test_source_records_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        PRIMARY_S100_24.edition = 2016  # type: ignore[misc]


def test_missing_primary_source_is_rejected_without_touching_pdfs() -> None:
    with pytest.raises(StandardSourceError, match="No S100-24 primary PDF"):
        select_primary_standard_path(
            ("references/standards/AISI_previous/history.pdf",)
        )


def test_ambiguous_primary_source_is_rejected_without_touching_pdfs() -> None:
    with pytest.raises(StandardSourceError, match="Ambiguous S100-24"):
        select_primary_standard_path(
            (
                PRIMARY_S100_24.repository_relative_path,
                "references/standards/AISI_S100-24/duplicate.pdf",
            )
        )
