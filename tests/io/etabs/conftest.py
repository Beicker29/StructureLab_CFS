"""Shared approved-workbook paths and writable ETABS test copies."""

from pathlib import Path
from shutil import copy2

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROJECT_PATH = REPOSITORY_ROOT / "projects" / "PRJ_001"
ETABS_SOURCE = PROJECT_PATH / "ETABS_results.xlsx"
MEMBERS_SOURCE = PROJECT_PATH / "members.xlsx"


@pytest.fixture
def etabs_copy(tmp_path: Path) -> Path:
    target = tmp_path / "ETABS_results.xlsx"
    copy2(ETABS_SOURCE, target)
    return target


@pytest.fixture
def members_copy(tmp_path: Path) -> Path:
    target = tmp_path / "members.xlsx"
    copy2(MEMBERS_SOURCE, target)
    return target
