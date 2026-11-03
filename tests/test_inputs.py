"""Rejection of invalid or incomplete input."""
import copy

import pytest

from cfs_design.errors import ValidationError
from cfs_design.execution import parse_member


def _with(payload: dict, **changes) -> dict:
    out = copy.deepcopy(payload)
    out.update(changes)
    return out


def test_valid_payload_parses(member_payload):
    member = parse_member(member_payload)
    assert member.method == "DSM" and member.buckling.source == "analytical"
    assert member.factors.Kx == 1.0


@pytest.mark.parametrize("change", [
    {"cases": []},
    {"cases": [{"name": "empty"}]},
    {"cases": [{"name": "a", "Pu": 1}, {"name": "a", "Pu": 2}]},
    {"method": "LRFD"},
    {"Fy": 345},
    {"section": {"name": "600S162-54", "shape": "C_LIPPED", "t": 1.4}},
    {"section": {"name": "600S162-54", "t": 1.4}},
    {"section": {"shape": "C_LIPPED", "H": 200}},
    {"section": {"shape": "C_LIPPED", "t": -1.0}},
    {"section": {"shape": "TUBE", "t": 1.0}},
    {"section": {"name": "PHR C100x50x15-2.0", "lip_angle": 90}},
    {"section": {"shape": "Z_LIPPED", "t": 2.0, "lip_angle": 120}},
    {"lengths": {"Lx": 0}},
])
def test_invalid_payloads_are_rejected(member_payload, change):
    with pytest.raises(ValidationError) as info:
        parse_member(_with(member_payload, **change))
    assert info.value.code == "VALIDATION_ERROR"
    assert info.value.details["issues"]


def test_material_cannot_be_numbers(member_payload):
    with pytest.raises(ValidationError):
        parse_member(_with(member_payload, material={"Fy": 345, "Fu": 450}))
