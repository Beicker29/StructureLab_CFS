"""Steel catalog: values transcribed from AISI S100-24 Table A3.1.1-1; Fu pending (DC-8)."""
import dataclasses

import pytest

from cfs_design.errors import IncompleteDataError, MaterialNotFoundError, RuleNotImplementedError
from cfs_design.materials import catalog, get_material, validate_a3_1_1

# Metric Fy in parentheses in Table A3.1.1-1 (pp. 15-16), read independently of the workbook loader.
TABLE_A311 = {
    "ASTM A653 SS Grade 33": 230, "ASTM A653 SS Grade 37": 255, "ASTM A653 SS Grade 40": 275,
    "ASTM A653 SS Grade 50 Class 1": 340, "ASTM A653 SS Grade 55": 380,
    "ASTM A1003 ST Grade 33H": 230, "ASTM A1003 ST Grade 50H": 340,
    "ASTM A1011 SS Grade 33": 230, "ASTM A1011 SS Grade 36 Type 1": 250,
    "ASTM A1011 SS Grade 40": 275, "ASTM A1011 SS Grade 50": 340,
}


def test_catalog_matches_table_a3_1_1():
    assert {name: m.Fy for name, m in catalog().items()} == TABLE_A311


def test_all_entries_are_elongation_group_a3_1_1_and_cite_the_table():
    for material in catalog().values():
        assert material.elongation_group == "A3.1.1"
        assert "A3.1.1-1" in material.source


def test_fu_is_not_assumed():
    assert all(m.Fu is None for m in catalog().values())


def test_catalog_cannot_be_validated_until_fu_and_elongation_are_transcribed():
    for material in catalog().values():
        with pytest.raises(IncompleteDataError) as info:
            validate_a3_1_1(material)
        assert "Fu_MPa" in info.value.details["missing"]


@pytest.mark.parametrize("fu_fy, elongation, gage, ok", [
    (1.08, 10.0, 50, True),
    (1.07, 20.0, 50, False),        # A3.1.1(a)
    (1.30, 9.0, 50, False),         # A3.1.1(b), 50 mm gage
    (1.30, 7.0, 200, True),         # A3.1.1(b), 200 mm gage
    (1.30, 6.5, 200, False),
])
def test_a3_1_1_conditions(fu_fy, elongation, gage, ok):
    m = dataclasses.replace(get_material("ASTM A653 SS Grade 50 Class 1"), Fu=fu_fy * 340, elongation_pct=elongation,
                            elongation_gage_mm=gage, fu_elongation_source="TEST DOUBLE")
    if ok:
        validate_a3_1_1(m)
    else:
        with pytest.raises(RuleNotImplementedError):
            validate_a3_1_1(m)


def test_lookup_is_case_insensitive():
    assert get_material("astm a653 ss grade 50 class 1").Fy == 340


def test_unknown_material():
    with pytest.raises(MaterialNotFoundError) as info:
        get_material("ASTM A36")
    assert "ASTM A653 SS Grade 33" in info.value.details["available"]
