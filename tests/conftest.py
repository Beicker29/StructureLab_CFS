import dataclasses
from pathlib import Path

import pytest

from cfs_design import engine

ROOT = Path(__file__).resolve().parents[1]
TEST_DOUBLE = "TEST DOUBLE: invented values, not transcribed from any ASTM standard"


@pytest.fixture
def validated_material(monkeypatch):
    """Catalog material with invented Fu and elongation so that A3.1.1 validation passes (D15).

    Materiales.xlsx has no Fu nor elongation yet; these values only exercise the engine.
    """
    real = engine.get_material

    def fake(name: str):
        m = real(name)
        return dataclasses.replace(m, Fu=1.3 * m.Fy, elongation_pct=20.0, elongation_gage_mm=50, fu_elongation_source=TEST_DOUBLE)

    monkeypatch.setattr(engine, "get_material", fake)


@pytest.fixture
def member_payload() -> dict:
    return {
        "section": {"shape": "C_LIPPED", "H": 203.2, "B": 63.5, "D": 15.9, "t": 1.519, "R": 3.2},
        "material": "ASTM A653 SS Grade 50 Class 1",
        "lengths": {"Lx": 3000, "Ly": 1000, "Lz": 1000},
        "cases": [{"name": "c1", "Pu": 18.0, "Mux": 2.1}],
    }
