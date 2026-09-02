"""Temporary repository-shaped M5 integration fixture."""

from pathlib import Path
from shutil import copy2

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    catalogs = root / "data" / "catalogs"
    project = root / "projects" / "PRJ_001"
    catalogs.mkdir(parents=True)
    project.mkdir(parents=True)
    copy2(
        REPOSITORY_ROOT / "data" / "catalogs" / "materials_catalog.xlsx",
        catalogs / "materials_catalog.xlsx",
    )
    copy2(
        REPOSITORY_ROOT / "data" / "catalogs" / "sections_catalog.xlsx",
        catalogs / "sections_catalog.xlsx",
    )
    for name in ("members.xlsx", "ETABS_results.xlsx", "project.yaml"):
        copy2(REPOSITORY_ROOT / "projects" / "PRJ_001" / name, project / name)
    return root
