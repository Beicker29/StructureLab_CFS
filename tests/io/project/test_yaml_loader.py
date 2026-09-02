"""M5 typed project.yaml loader tests."""

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from cfs_design.core.exceptions import (
    ConfigurationError,
    SchemaError,
    UnsupportedFeatureError,
)
from cfs_design.domain import DesignFormat, DesignMethod, RunMode
from cfs_design.io.project import CatalogVerificationAction, load_project_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROJECT_YAML = REPOSITORY_ROOT / "projects" / "PRJ_001" / "project.yaml"
APPROVED_PROJECT_SHA256 = (
    "759e66a3eb6829b74e3cc3f1cffbb9974a073359081a7f90c7e7ae8bc6921932"
)


def _document() -> dict[str, object]:
    return yaml.safe_load(PROJECT_YAML.read_text(encoding="utf-8"))


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_approved_project_config_is_typed_and_preserves_configured_paths() -> None:
    config = load_project_config(PROJECT_YAML)

    assert config.schema_version == "0.1.0"
    assert config.metadata.project_id == "PRJ_001"
    assert config.design_context.design_format is DesignFormat.LRFD
    assert config.design_context.methods == (DesignMethod.EWM, DesignMethod.DSM)
    assert config.design_context.run_mode is RunMode.COMPARE
    assert config.files.members.configured_path == "projects/PRJ_001/members.xlsx"
    assert config.files.members.resolved_path.is_absolute()
    assert config.catalog_verification.relative_tolerance == 0.01
    assert (
        config.catalog_verification.action_on_fail
        is CatalogVerificationAction.WARNING
    )
    assert config.etabs_import.importer.columns.p == "P"
    assert config.etabs_import.mapping.priority == (
        "etabs_unique_name",
        "etabs_story+etabs_beam",
    )
    assert config.outputs.root == "outputs/PRJ_001"
    assert config.outputs.resolved_root == (REPOSITORY_ROOT / "outputs/PRJ_001").resolve()


def test_project_yaml_path_and_sha256_are_preserved() -> None:
    config = load_project_config(PROJECT_YAML)
    assert config.source_path == PROJECT_YAML.resolve()
    assert config.file_sha256 == APPROVED_PROJECT_SHA256
    assert config.file_sha256 == sha256(PROJECT_YAML.read_bytes()).hexdigest()


def test_path_resolution_is_independent_of_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_project_config(PROJECT_YAML)
    assert config.repository_root == REPOSITORY_ROOT.resolve()
    assert config.files.etabs_results.resolved_path.is_file()


def test_explicit_repository_root_supports_yaml_outside_repository(
    tmp_path: Path,
) -> None:
    copied = _write(tmp_path, _document())
    config = load_project_config(copied, repository_root=REPOSITORY_ROOT)
    assert config.repository_root == REPOSITORY_ROOT.resolve()


def test_missing_project_yaml_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_project_config(tmp_path / "missing.yaml")


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["schema_version"] = "9.9.9"
    with pytest.raises(SchemaError, match="unsupported schema_version"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_missing_required_yaml_section_is_rejected(tmp_path: Path) -> None:
    document = _document()
    del document["files"]
    with pytest.raises(SchemaError, match="missing required sections.*files"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_invalid_enum_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["design_context"]["run_mode"] = "invalid"  # type: ignore[index]
    with pytest.raises(SchemaError, match="unknown value.*invalid"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("standard_id", "OTHER_STANDARD", "standard.id"),
        ("edition", 2022, "standard.edition"),
        ("design_format", "ASD", "only LRFD"),
    ),
)
def test_unsupported_global_design_scope_is_rejected(
    tmp_path: Path,
    field: str,
    value: object,
    match: str,
) -> None:
    document = _document()
    context = document["design_context"]  # type: ignore[index]
    if field == "standard_id":
        context["standard"]["id"] = value
    elif field == "edition":
        context["standard"]["edition"] = value
    else:
        context[field] = value
    with pytest.raises(UnsupportedFeatureError, match=match):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_run_mode_methods_must_be_consistent(tmp_path: Path) -> None:
    document = _document()
    document["design_context"]["methods"] = ["EWM"]  # type: ignore[index]
    with pytest.raises(ConfigurationError, match="run_mode='compare'.*DSM"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_missing_referenced_file_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["files"]["members"] = "projects/PRJ_001/missing.xlsx"  # type: ignore[index]
    with pytest.raises(ConfigurationError, match="files.members.*does not exist"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["files"]["members"] = "../outside.xlsx"  # type: ignore[index]
    with pytest.raises(SchemaError, match="escapes repository_root"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)


def test_unsupported_etabs_mapping_priority_is_rejected(tmp_path: Path) -> None:
    document = _document()
    document["etabs_import"]["mapping"]["priority"] = [  # type: ignore[index]
        "etabs_story+etabs_beam"
    ]
    with pytest.raises(UnsupportedFeatureError, match="mapping priority"):
        load_project_config(_write(tmp_path, document), repository_root=REPOSITORY_ROOT)
