from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def member_payload() -> dict:
    return {
        "section": {"shape": "C_LIPPED", "H": 203.2, "B": 63.5, "D": 15.9, "t": 1.519, "R": 3.2},
        "material": "ASTM A653 SS Grade 50 Class 1",
        "lengths": {"Lx": 3000, "Ly": 1000, "Lz": 1000},
        "cases": [{"name": "c1", "Pu": 18.0, "Mux": 2.1}],
    }
