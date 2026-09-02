"""Normalized simultaneous demand collection tests."""

from dataclasses import replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DemandCombination, DemandPoint, DemandSet


def test_valid_simultaneous_force_state(demand_point: DemandPoint) -> None:
    assert demand_point.point_id == "POINT_001"
    assert demand_point.station_mm == 250.0


def test_zero_forces_are_allowed() -> None:
    point = DemandPoint(
        point_id="ZERO",
        p_n=0.0,
        v2_n=0.0,
        v3_n=0.0,
        t_nmm=0.0,
        m2_nmm=0.0,
        m3_nmm=0.0,
    )
    assert point.p_n == 0.0


def test_positive_and_negative_forces_are_not_interpreted() -> None:
    point = DemandPoint(
        point_id="SIGNED",
        p_n=1.0,
        v2_n=-2.0,
        v3_n=3.0,
        t_nmm=-4.0,
        m2_nmm=5.0,
        m3_nmm=-6.0,
    )
    assert (point.p_n, point.v2_n, point.m3_nmm) == (1.0, -2.0, -6.0)


def test_optional_station_metadata_is_supported(demand_point: DemandPoint) -> None:
    point = replace(
        demand_point,
        station_mm=None,
        element_id=None,
        element_station_mm=None,
        location="End I",
    )
    assert point.station_mm is None
    assert point.location == "End I"


def test_nonfinite_force_is_rejected(demand_point: DemandPoint) -> None:
    with pytest.raises(ValidationError):
        replace(demand_point, p_n=float("nan"))


def test_multiple_demand_points_are_accepted(demand_point: DemandPoint) -> None:
    second = replace(demand_point, point_id="POINT_002", station_mm=500.0)
    combination = DemandCombination("COMB", (demand_point, second))
    assert len(combination.points) == 2


def test_duplicate_point_ids_are_rejected(demand_point: DemandPoint) -> None:
    with pytest.raises(ValidationError):
        DemandCombination("COMB", (demand_point, demand_point))


def test_empty_combination_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DemandCombination("COMB", ())


def test_multiple_combinations_are_accepted(
    demand_combination: DemandCombination,
) -> None:
    second = replace(demand_combination, combination_id="COMB_002")
    demands = DemandSet((demand_combination, second))
    assert len(demands.combinations) == 2


def test_duplicate_combination_ids_are_rejected(
    demand_combination: DemandCombination,
) -> None:
    with pytest.raises(ValidationError):
        DemandSet((demand_combination, demand_combination))


def test_empty_demand_set_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DemandSet(())


def test_mutable_demand_collections_are_rejected(demand_point: DemandPoint) -> None:
    with pytest.raises(ValidationError):
        DemandCombination("COMB", [demand_point])  # type: ignore[arg-type]

