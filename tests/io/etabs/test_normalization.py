"""ETABS row-by-row normalization and sign-convention tests."""

from dataclasses import replace
from pathlib import Path

import pytest

from cfs_design.io.etabs import normalize_etabs_demands, read_etabs_results

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ETABS_SOURCE = REPOSITORY_ROOT / "projects" / "PRJ_001" / "ETABS_results.xlsx"


def test_first_approved_row_converts_to_canonical_units() -> None:
    read_result = read_etabs_results(ETABS_SOURCE)
    record = normalize_etabs_demands(read_result)[0]
    point = record.demand_point

    assert point.point_id == "ETABS-BE2FC3B9B9D9-R000004"
    assert point.station_mm == 250.0
    assert point.element_station_mm == 250.0
    assert point.p_n == 0.0
    assert point.v2_n == pytest.approx(12628.59 * 9.80665)
    assert point.t_nmm == pytest.approx(279.05 * 9806.65)
    assert point.m3_nmm == pytest.approx(31947.45 * 9806.65)
    assert record.raw_row is read_result.raw_rows[0]
    assert record.raw_row.v2_raw == 12628.59


def test_only_axial_force_sign_is_reversed() -> None:
    original = read_etabs_results(ETABS_SOURCE)
    signed = replace(
        original.raw_rows[0],
        p_raw=100.0,
        v2_raw=-2.0,
        v3_raw=3.0,
        t_raw=-4.0,
        m2_raw=5.0,
        m3_raw=-6.0,
    )
    read_result = replace(original, raw_rows=(signed,))
    point = normalize_etabs_demands(read_result)[0].demand_point

    assert point.p_n == pytest.approx(-100.0 * 9.80665)
    assert point.v2_n == pytest.approx(-2.0 * 9.80665)
    assert point.v3_n == pytest.approx(3.0 * 9.80665)
    assert point.t_nmm == pytest.approx(-4.0 * 9806.65)
    assert point.m2_nmm == pytest.approx(5.0 * 9806.65)
    assert point.m3_nmm == pytest.approx(-6.0 * 9806.65)

    compression = replace(signed, p_raw=-100.0)
    compression_result = replace(original, raw_rows=(compression,))
    assert normalize_etabs_demands(compression_result)[0].demand_point.p_n == pytest.approx(
        100.0 * 9.80665
    )


def test_point_ids_are_deterministic_and_source_row_based() -> None:
    result_a = normalize_etabs_demands(read_etabs_results(ETABS_SOURCE))
    result_b = normalize_etabs_demands(read_etabs_results(ETABS_SOURCE))

    ids_a = tuple(record.demand_point.point_id for record in result_a)
    ids_b = tuple(record.demand_point.point_id for record in result_b)
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a)) == 24


def test_max_min_and_blank_step_types_remain_distinct() -> None:
    original = read_etabs_results(ETABS_SOURCE)
    rows = (
        replace(original.raw_rows[0], step_type="Max"),
        replace(original.raw_rows[1], step_type="Min"),
        replace(original.raw_rows[2], step_type=None),
    )
    normalized = normalize_etabs_demands(replace(original, raw_rows=rows))

    assert tuple(record.demand_point.step_type for record in normalized) == (
        "Max",
        "Min",
        None,
    )
