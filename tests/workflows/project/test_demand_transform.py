"""M5 section-axis orientation and signed transformation tests."""

from dataclasses import FrozenInstanceError
from math import cos, radians, sin

import pytest

from cfs_design.domain import DemandCombination, DemandPoint, DemandSet
from cfs_design.workflows.project import transform_demand_point, transform_demand_set


@pytest.fixture
def local_point() -> DemandPoint:
    return DemandPoint(
        point_id="LOCAL-001",
        p_n=1200.0,
        v2_n=3.0,
        v3_n=-4.0,
        t_nmm=-500.0,
        m2_nmm=-7.0,
        m3_nmm=11.0,
        station_mm=2750.0,
        step_type="Max",
        element_id="1263",
        element_station_mm=2750.0,
        location="Before",
    )


def test_zero_degrees_aligns_section_x_y_with_etabs_2_3(
    local_point: DemandPoint,
) -> None:
    transformed = transform_demand_point(local_point, 0.0)
    assert transformed.vx_n == local_point.v2_n
    assert transformed.vy_n == local_point.v3_n
    assert transformed.mx_nmm == local_point.m2_nmm
    assert transformed.my_nmm == local_point.m3_nmm


def test_positive_ninety_degrees(local_point: DemandPoint) -> None:
    transformed = transform_demand_point(local_point, 90.0)
    assert transformed.vx_n == local_point.v3_n
    assert transformed.vy_n == -local_point.v2_n
    assert transformed.mx_nmm == local_point.m3_nmm
    assert transformed.my_nmm == -local_point.m2_nmm


def test_negative_ninety_degrees(local_point: DemandPoint) -> None:
    transformed = transform_demand_point(local_point, -90.0)
    assert transformed.vx_n == -local_point.v3_n
    assert transformed.vy_n == local_point.v2_n
    assert transformed.mx_nmm == -local_point.m3_nmm
    assert transformed.my_nmm == local_point.m2_nmm


def test_arbitrary_thirty_degree_rotation_uses_documented_basis(
    local_point: DemandPoint,
) -> None:
    transformed = transform_demand_point(local_point, 30.0)
    c = cos(radians(30.0))
    s = sin(radians(30.0))
    assert transformed.vx_n == pytest.approx(local_point.v2_n * c + local_point.v3_n * s)
    assert transformed.vy_n == pytest.approx(-local_point.v2_n * s + local_point.v3_n * c)
    assert transformed.mx_nmm == pytest.approx(local_point.m2_nmm * c + local_point.m3_nmm * s)
    assert transformed.my_nmm == pytest.approx(-local_point.m2_nmm * s + local_point.m3_nmm * c)


@pytest.mark.parametrize("angle", (-123.4, -90.0, 0.0, 30.0, 90.0, 248.0))
def test_rotation_preserves_vector_norms(
    local_point: DemandPoint,
    angle: float,
) -> None:
    transformed = transform_demand_point(local_point, angle)
    assert transformed.vx_n**2 + transformed.vy_n**2 == pytest.approx(
        local_point.v2_n**2 + local_point.v3_n**2
    )
    assert transformed.mx_nmm**2 + transformed.my_nmm**2 == pytest.approx(
        local_point.m2_nmm**2 + local_point.m3_nmm**2
    )


def test_axial_torque_signs_and_source_trace_are_unchanged(
    local_point: DemandPoint,
) -> None:
    transformed = transform_demand_point(local_point, 30.0)
    assert transformed.p_n == local_point.p_n
    assert transformed.t_nmm == local_point.t_nmm
    assert transformed.source_point_id == local_point.point_id
    assert transformed.point_id == "SECTION-LOCAL-001"
    assert transformed.station_mm == local_point.station_mm
    assert transformed.location == "Before"
    assert local_point.m2_nmm == -7.0
    with pytest.raises(FrozenInstanceError):
        transformed.mx_nmm = 0.0  # type: ignore[misc]


def test_all_combinations_and_points_survive_one_to_one(
    local_point: DemandPoint,
) -> None:
    after = DemandPoint(
        point_id="LOCAL-002",
        p_n=0.0,
        v2_n=-1.0,
        v3_n=2.0,
        t_nmm=0.0,
        m2_nmm=5.0,
        m3_nmm=-6.0,
        station_mm=2750.0,
        step_type="Min",
        location="After",
    )
    demands = DemandSet(
        combinations=(
            DemandCombination("DERX", (local_point, after), "LinRespSpec"),
            DemandCombination("DERY", (local_point,), "LinRespSpec"),
        )
    )
    transformed = transform_demand_set(demands, 0.0)
    assert tuple(item.combination_id for item in transformed.combinations) == (
        "DERX",
        "DERY",
    )
    assert tuple(len(item.points) for item in transformed.combinations) == (2, 1)
    assert {item.location for item in transformed.combinations[0].points} == {
        "Before",
        "After",
    }
    assert transformed.combinations[0].case_type == "LinRespSpec"
