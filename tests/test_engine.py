"""Engine: demand to chapter, per-method checks, status precedence, blocking by section or material."""
import pytest

from cfs_design import engine
from cfs_design.engine import DEMAND_CHAPTERS, demanded_checks
from cfs_design.execution import execute_payload, parse_member
from cfs_design.models import Status


@pytest.mark.parametrize("demand, expected", [
    ({"Pu": 10}, ["compression"]),
    ({"Pu": -10}, ["tension"]),
    ({"Mux": 1}, ["flexure_x"]),
    ({"Mux": 1, "Muy": 1}, ["flexure_x", "flexure_y", "interaction"]),
    ({"Pu": 10, "Mux": 1}, ["compression", "flexure_x", "interaction"]),
    ({"Pu": -10, "Muy": -1}, ["tension", "flexure_y", "interaction"]),
    ({"Mux": 1, "Vuy": 2}, ["flexure_x", "shear_y", "interaction"]),
    ({"Mux": 1, "Pw": 2}, ["flexure_x", "web_crippling", "interaction"]),
    ({"Mux": 1, "Bu": 2}, ["flexure_x", "torsion", "interaction"]),
    ({"Vux": 3}, ["shear_x"]),
])
def test_demanded_checks(member_payload, demand, expected):
    member = parse_member({**member_payload, "cases": [{"name": "c", **demand}]})
    assert [name for name, _ in demanded_checks(member.cases[0])] == expected


def test_unimplemented_chapters_are_incomplete_with_their_milestone(member_payload, validated_material):
    payload = {**member_payload, "cases": [
        {"name": "a", "Pu": 18.0, "Mux": 2.1},
        {"name": "b", "Pu": -5.0, "Muy": 0.4, "Vux": 1.0, "Vuy": 1.0, "Pw": 3.0, "Bu": 0.1},
    ]}
    result = execute_payload(payload)
    assert result["status"] == Status.INCOMPLETE.value
    seen = set()
    for case in result["cases"]:
        assert case["status"] == "INCOMPLETE"
        for check in case["checks"]:
            chapter, milestone = DEMAND_CHAPTERS[check["check"]]
            assert check["chapter"] == chapter
            seen.add(check["check"])
            if check["check"] == "compression":
                continue
            assert check["capacity"] is None
            assert check["errors"][0]["code"] == "RULE_NOT_IMPLEMENTED"
            assert check["errors"][0]["details"]["milestone"] == milestone
    assert seen == set(DEMAND_CHAPTERS)


def test_unvalidated_material_blocks_every_check(member_payload):
    """Materiales.xlsx has no Fu nor elongation yet: no capacity until A3.1.1 can be validated (D15)."""
    result = execute_payload(member_payload)
    assert result["status"] == "INCOMPLETE" and result["section"] is not None and result["buckling"] is not None
    assert result["errors"][0]["details"]["decision"] == "D15"
    assert all(c["capacity"] is None for case in result["cases"] for c in case["checks"])


@pytest.mark.parametrize("statuses, expected", [
    (["PASS", "FAIL"], "FAIL"),
    (["FAIL", "OUT_OF_METHOD_SCOPE"], "OUT_OF_METHOD_SCOPE"),
    (["OUT_OF_METHOD_SCOPE", "INCOMPLETE", "PASS"], "INCOMPLETE"),
    (["NOT_APPLICABLE", "PASS"], "PASS"),
    (["NOT_APPLICABLE"], "NOT_APPLICABLE"),
])
def test_status_precedence(statuses, expected):
    assert engine._aggregate([Status(s) for s in statuses]) == Status(expected)


def test_demands_are_reported_as_magnitudes(member_payload):
    result = execute_payload({**member_payload, "cases": [{"name": "t", "Pu": -12.5}]})
    check = result["cases"][0]["checks"][0]
    assert check["check"] == "tension" and check["demand"] == 12.5


def test_result_carries_the_material(member_payload):
    result = execute_payload(member_payload)
    assert result["material"]["Fy_MPa"] == 340 and result["material"]["Fu_MPa"] is None
