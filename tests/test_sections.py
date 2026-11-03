"""Sections (M1): catalog vs geometry engine, closed-form control, resolution and blocking.

No independent oracle yet: validation against the AISI Manual is pending (docs/chapter-sections.md).
The catalog comparison checks consistency between the two sources of DC-7, not normative accuracy.
"""
import dataclasses
import json

import pytest

from cfs_design.errors import IncompleteDataError, RuleNotImplementedError, SectionNotFoundError, ValidationError
from cfs_design.execution import execute_payload
from cfs_design.models import SectionInput
from cfs_design.sections import _geometric, catalog, resolve_section

ENTRIES = [e for e in catalog.catalog().values() if e.t_design is not None]


def test_catalog_loads_c_and_z_families():
    entries = catalog.catalog().values()
    assert len(entries) == 125
    assert {e.sheet for e in entries} == {"PHR-C", "PHR-Z", "PAG-C", "PAG-Z"}
    assert {e.shape for e in entries} == {"C_LIPPED", "Z_LIPPED"}


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e.name)
def test_geometry_engine_reproduces_catalog(entry):
    """D4: every catalog row within ±0.5 % of the geometry engine (same method D1, same t_design)."""
    props, _ = _geometric(entry.shape, entry.H, entry.B, entry.D, entry.t_design, entry.R, entry.lip_angle)
    for key, value in entry.properties.items():
        if value == 0:
            assert abs(props[key]) < 1e-6 * props["A"], key
        else:
            assert props[key] == pytest.approx(value, rel=5e-3), key


def test_sharp_corner_c_closed_form():
    """R = 0, mitred corners: union of rectangles (web 2x100, flanges 48x2, lips 2x13), by hand."""
    props, elements = _geometric("C_LIPPED", 100, 50, 15, 2, 0, 90)
    ix = 2 * 100**3 / 12 + 2 * (48 * 2**3 / 12 + 96 * 49**2) + 2 * (2 * 13**3 / 12 + 26 * 41.5**2)
    assert props["A"] == pytest.approx(444.0, rel=1e-12)
    assert props["Ix"] == pytest.approx(ix, rel=1e-12)
    assert props["J"] == pytest.approx(444.0 * 4 / 3, rel=1e-12)
    assert props["Zx"] == pytest.approx(2 * 2 * 50**2 / 2 + 2 * 96 * 49 + 2 * 26 * 41.5, rel=1e-9)
    # plastic axis at x = 7.5 (web 200 mm² + flanges 4 mm²/mm x 5.5 mm = 222 mm² = A/2)
    assert props["Zy"] == pytest.approx(200 * 6.5 + 4 * 5.5**2 / 2 + 4 * 42.5**2 / 2 + 52 * 41.5, rel=1e-9)
    assert (elements["h"], elements["b"], elements["d"]) == pytest.approx((96.0, 46.0, 13.0), rel=1e-12)


def test_rounded_c_flat_widths():
    _, elements = _geometric("C_LIPPED", 100, 50, 15, 2, 5, 90)
    assert (elements["h"], elements["b"], elements["d"]) == pytest.approx((86.0, 36.0, 8.0), rel=1e-12)
    assert elements["w"] == elements["h"] and elements["R_t"] == 2.5 and elements["do_bo"] == 0.3


def test_z_is_point_symmetric():
    props, _ = _geometric("Z_LIPPED", 203, 67, 19, 2, 5, 45)
    assert abs(props["xo"]) < 1e-9 and abs(props["j_asym"]) < 1e-9
    assert props["Ixy"] > 0


def test_catalog_section_reports_its_source():
    section = resolve_section(SectionInput(name="phr z203x67x19-2.0")).to_dict()
    assert section["source"] == "catalog" and section["name"] == "PHR Z203x67x19-2.0"
    assert section["properties"]["Ix"] == 4543680.0           # taken from the catalog, not recomputed
    assert section["dimensions"]["t"] == 2.0
    i1, i2 = section["properties"]["I1"], section["properties"]["I2"]
    assert i1 + i2 == pytest.approx(section["properties"]["Ix"] + section["properties"]["Iy"], rel=1e-12)
    assert section["properties"]["Zx"] > section["properties"]["Sx"]


def test_geometric_section_reports_its_source():
    section = resolve_section(SectionInput(shape="C_LIPPED", H=203.2, B=63.5, D=15.9, t=1.519, R=3.2)).to_dict()
    assert section["source"] == "geometry" and section["dimensions"]["lip_angle"] == 90.0
    props = section["properties"]
    assert props["Sy_web"] == pytest.approx(props["Iy"] / props["xcent"], rel=1e-12)
    assert props["Sy_tip"] == pytest.approx(props["Sy"], rel=1e-12)
    assert props["xo"] < 0


def test_unknown_section_is_invalid_input(member_payload):
    with pytest.raises(SectionNotFoundError):
        execute_payload({**member_payload, "section": {"name": "PHR C999x1x1-9.9"}})


@pytest.mark.parametrize("section, error", [
    ({"shape": "Z_LIPPED", "H": 160, "B": 60, "D": 20, "t": 2, "R": 5}, IncompleteDataError),
    ({"shape": "C_LIPPED", "H": 160, "B": 60, "D": 20, "t": 2}, IncompleteDataError),
    ({"shape": "C_LIPPED", "H": 160, "B": 60, "D": 20, "t": 2, "R": 5, "lip_angle": 60}, ValidationError),
    ({"shape": "C_LIPPED", "H": 160, "B": 12, "D": 20, "t": 2, "R": 5}, ValidationError),
    ({"shape": "HAT", "H": 160, "B": 60, "D": 20, "t": 2, "R": 5}, RuleNotImplementedError),
])
def test_resolution_errors(section, error):
    with pytest.raises(error):
        resolve_section(SectionInput(**section))


def test_output_keys_are_unique_ignoring_case():
    section = resolve_section(SectionInput(name="PHR C100x50x15-2.0")).to_dict()
    keys = [k.lower() for k in section["properties"]]
    assert len(keys) == len(set(keys)) and "j_asym" in section["properties"]
    assert json.loads(json.dumps(section))["properties"]["J"] == section["properties"]["J"]


@pytest.mark.parametrize("section, code", [
    ({"name": "PHR C100x50x15-2.0"}, "INCOMPLETE_DATA"),                        # t_design_mm emptied below
    ({"shape": "HAT", "H": 160, "B": 60, "D": 20, "t": 2, "R": 5}, "RULE_NOT_IMPLEMENTED"),  # DC-9
])
def test_blocked_section_makes_the_member_incomplete(member_payload, monkeypatch, section, code):
    entry = catalog.find("PHR C100x50x15-2.0")
    monkeypatch.setattr(catalog, "find", lambda name: dataclasses.replace(entry, t_design=None))
    result = execute_payload({**member_payload, "section": section})
    assert result["status"] == "INCOMPLETE" and result["section"] is None
    assert result["errors"][0]["code"] == code
    assert all(check["errors"][0]["code"] == code for case in result["cases"] for check in case["checks"])
