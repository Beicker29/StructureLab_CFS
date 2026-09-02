"""M8A.1 project schema migration and scope-evidence loader tests."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from cfs_design.core.exceptions import SchemaError
from cfs_design.domain import (
    EvidenceState,
    GoverningCountry,
    StructureApplication,
)
from cfs_design.io.project import load_project_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROJECT_YAML = REPOSITORY_ROOT / "projects" / "PRJ_001" / "project.yaml"


def _document() -> dict[str, object]:
    return yaml.safe_load(PROJECT_YAML.read_text(encoding="utf-8"))


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_schema_02_loads_typed_unknown_template_evidence() -> None:
    config = load_project_config(PROJECT_YAML)

    assert config.schema_version == "0.2.0"
    assert config.scope_evidence.governing_country.country is GoverningCountry.UNKNOWN
    assert (
        config.scope_evidence.structure_application.application
        is StructureApplication.UNKNOWN
    )
    assert (
        config.scope_evidence.cold_formed_to_shape.state
        is EvidenceState.UNKNOWN
    )
    assert "Project template" in config.scope_evidence.cold_formed_to_shape.basis


def test_complete_verified_scope_evidence_and_provenance_are_preserved(
    tmp_path: Path,
) -> None:
    document = _document()
    evidence = document["aisi_scope_evidence"]  # type: ignore[index]
    evidence["governing_country"] = {
        "country": "UNITED_STATES",
        "basis": "Applicable building code title sheet.",
    }
    evidence["structure_application"] = {
        "application": "BUILDING",
        "basis": "Project structural narrative.",
    }
    evidence["cold_formed_to_shape"] = {
        "state": "TRUE",
        "basis": "Approved procurement specification.",
    }
    evidence["structural_load_carrying_use"] = {
        "state": "TRUE",
        "basis": "Structural framing drawings.",
    }
    evidence["dynamic_effects_addressed"] = {
        "state": "UNKNOWN",
        "basis": "Not needed for the declared building branch.",
    }

    loaded = load_project_config(
        _write(tmp_path, document), repository_root=REPOSITORY_ROOT
    ).scope_evidence

    assert loaded.governing_country.country is GoverningCountry.UNITED_STATES
    assert loaded.cold_formed_to_shape.state is EvidenceState.TRUE
    assert loaded.cold_formed_to_shape.basis == (
        "Approved procurement specification."
    )
    with pytest.raises(FrozenInstanceError):
        loaded.governing_country.country = GoverningCountry.CANADA  # type: ignore[misc]


def test_explicit_false_is_not_rewritten_as_missing(tmp_path: Path) -> None:
    document = _document()
    evidence = document["aisi_scope_evidence"]  # type: ignore[index]
    evidence["cold_formed_to_shape"] = {
        "state": "FALSE",
        "basis": "Supplier explicitly identifies hot-formed production.",
    }

    loaded = load_project_config(
        _write(tmp_path, document), repository_root=REPOSITORY_ROOT
    ).scope_evidence

    assert loaded.cold_formed_to_shape.state is EvidenceState.FALSE


def test_invalid_governing_country_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["aisi_scope_evidence"]["governing_country"][  # type: ignore[index]
        "country"
    ] = "COLOMBIA"

    with pytest.raises(SchemaError, match="governing_country.country.*unknown value"):
        load_project_config(
            _write(tmp_path, document), repository_root=REPOSITORY_ROOT
        )


def test_schema_02_requires_explicit_evidence_section(tmp_path: Path) -> None:
    document = _document()
    del document["aisi_scope_evidence"]

    with pytest.raises(SchemaError, match="missing required key 'aisi_scope_evidence'"):
        load_project_config(
            _write(tmp_path, document), repository_root=REPOSITORY_ROOT
        )


def test_legacy_schema_loads_as_unknown_without_fabricated_declarations(
    tmp_path: Path,
) -> None:
    document = _document()
    document["schema_version"] = "0.1.0"
    del document["aisi_scope_evidence"]

    loaded = load_project_config(
        _write(tmp_path, document), repository_root=REPOSITORY_ROOT
    )

    assert loaded.schema_version == "0.1.0"
    assert loaded.scope_evidence.governing_country.country is GoverningCountry.UNKNOWN
    assert loaded.scope_evidence.cold_formed_to_shape.state is EvidenceState.UNKNOWN
    assert "Legacy project schema 0.1.0" in (
        loaded.scope_evidence.cold_formed_to_shape.basis
    )
