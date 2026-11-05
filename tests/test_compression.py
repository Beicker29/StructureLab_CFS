"""Compression by DSM (M3), AISI S100-24 Chapter E.

No independent oracle yet (DC-10): hand checks of the transcribed equations, limiting cases,
applicability and statuses. The engine tests use a material test double (conftest.validated_material).
"""
import math

import pytest

from cfs_design.codes.aisi_s100_24 import compression as e
from cfs_design.execution import execute_payload


@pytest.fixture
def column(member_payload, validated_material):
    return {**member_payload, "cases": [{"name": "c", "Pu": 10.0}]}


def _check(payload, index=0):
    return execute_payload(payload)["cases"][0]["checks"][index]


def test_fn_e2_by_hand():
    assert e.fn_global(340.0, 1.0) == pytest.approx(0.658 * 340.0)
    assert e.fn_global(340.0, 2.0) == pytest.approx(0.877 / 4 * 340.0)
    assert e.fn_global(340.0, 1.5) == pytest.approx(e.fn_global(340.0, 1.5 + 1e-12), rel=1e-3)   # E2-2 meets E2-3


def test_pnl_e3_2_and_pnd_e4_use_the_2024_coefficients():
    assert e.pnl_dsm(100.0, 1.0) == pytest.approx(1.2 * 100 * 1.10 / 1.55)
    assert e.pnd_dsm(100.0, 1.0) == pytest.approx(1.2 * 100 * 1.05 / 1.67)
    assert e.pnl_dsm(100.0, 0.1) == 100.0 and e.pnd_dsm(100.0, 0.1) == 100.0           # capped at Pne and Py


def test_compression_capacity_is_phi_times_the_smallest_nominal(column):
    check = _check(column)
    r = check["result"]
    nominal = {"E2": r["E2"]["Pne_kN"], "E3": r["E3"]["Pnl_kN"], "E4": r["E4"]["Pnd_kN"]}
    assert r["governing"] == min(nominal, key=nominal.get)
    assert check["capacity"] == pytest.approx(0.85 * min(nominal.values()), rel=1e-12)
    assert check["ratio"] == pytest.approx(10.0 / check["capacity"]) and check["status"] == "PASS"
    assert check["method"] == "DSM" and set(r["B4_1"]) == {"w_t", "b_t", "d_t", "R_t", "do_bo", "Fy"}
    # hand check of E2 from the reported Fcre
    lam = math.sqrt(340.0 / r["E2"]["Fcre_MPa"])
    assert r["E2"]["Pne_kN"] == pytest.approx(r["Ag_mm2"] * e.fn_global(340.0, lam) / 1e3, rel=1e-12)


def test_demand_above_capacity_fails(column):
    capacity = _check(column)["capacity"]
    check = _check({**column, "cases": [{"name": "c", "Pu": 1.01 * capacity}]})
    assert check["status"] == "FAIL" and check["ratio"] > 1


def test_missing_lm_takes_lcrd_and_reports_it(column):
    r = _check({**column, "buckling": {}})["result"]["E4"]
    assert r["Lm_source"].startswith("D14") and "Pnd_kN" in r


@pytest.mark.parametrize("section, variable", [
    ({"shape": "C_LIPPED", "H": 1200, "B": 60, "D": 15, "t": 1.0, "R": 2}, "w_t"),
    ({"shape": "C_LIPPED", "H": 200, "B": 60, "D": 50, "t": 0.7, "R": 1}, "d_t"),
    ({"shape": "C_LIPPED", "H": 200, "B": 60, "D": 50, "t": 2.0, "R": 2}, "do_bo"),
])
def test_outside_table_b4_1_is_out_of_method_scope(column, section, variable):
    check = _check({**column, "section": section})
    assert check["status"] == "OUT_OF_METHOD_SCOPE" and check["capacity"] is None
    details = check["errors"][0]["details"]
    assert details["reference"] == "B4.2" and variable in {v["variable"] for v in details["violations"]}


def test_local_slenderness_above_5_is_out_of_method_scope(column):
    section = {"shape": "C_LIPPED", "H": 460, "B": 100, "D": 20, "t": 1.0, "R": 2}      # w/t ≈ 454 ≤ 500
    check = _check({**column, "section": section, "lengths": {"Lx": 300, "Ly": 300, "Lz": 300}})
    assert check["status"] == "OUT_OF_METHOD_SCOPE" and check["capacity"] is None
    assert check["result"]["E3"]["lambda_l"] > 5 and "Pnl_kN" not in check["result"]["E3"]


def test_both_methods_give_one_check_each(column):
    checks = execute_payload({**column, "method": "both"})["cases"][0]["checks"]
    assert [c["method"] for c in checks] == ["DSM", "EWM"]
    assert checks[0]["status"] == "PASS"
    assert checks[1]["status"] == "INCOMPLETE" and checks[1]["errors"][0]["details"]["milestone"] == "M7"


def test_missing_global_length_makes_the_check_incomplete_without_capacity(column):
    check = _check({**column, "lengths": {"Lx": 3000, "Ly": 1000}})
    assert check["status"] == "INCOMPLETE" and check["capacity"] is None
    assert check["result"]["missing_obligations"] == ["E2", "E3"]
    assert "Pnd_kN" in check["result"]["E4"]
