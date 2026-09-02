"""Minimal smoke test for the approved project YAML contract."""

from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_YAML_PATH = REPOSITORY_ROOT / "projects" / "PRJ_001" / "project.yaml"

REQUIRED_TOP_LEVEL_SECTIONS = {
    "schema_version",
    "project",
    "design_context",
    "files",
    "catalog_verification",
    "etabs_import",
    "quality_assurance",
    "outputs",
}


def test_project_yaml_parses_with_approved_high_level_sections() -> None:
    assert PROJECT_YAML_PATH.is_file(), "The approved project.yaml has not been supplied"
    with PROJECT_YAML_PATH.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    assert isinstance(document, dict)
    assert REQUIRED_TOP_LEVEL_SECTIONS <= document.keys()


def test_project_yaml_declares_approved_m0_context() -> None:
    with PROJECT_YAML_PATH.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)

    assert document["schema_version"] == "0.2.0"
    assert document["project"]["project_id"] == "PRJ_001"
    assert document["design_context"]["standard"] == {
        "id": "ANSI_SDI_AISI_S100",
        "edition": 2024,
    }
    assert document["design_context"]["design_format"] == "LRFD"
    assert document["design_context"]["canonical_units"] == "SI"
    assert document["etabs_import"]["demand_processing"][
        "componentwise_envelope"
    ] is False


def test_project_yaml_referenced_input_files_exist() -> None:
    with PROJECT_YAML_PATH.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)

    missing = [
        relative_path
        for relative_path in document["files"].values()
        if not (REPOSITORY_ROOT / relative_path).is_file()
    ]
    assert not missing, f"project.yaml references missing input files: {missing}"
