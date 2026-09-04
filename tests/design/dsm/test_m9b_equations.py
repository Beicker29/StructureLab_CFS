"""Direct S100-24 E3.2, E4, and E1 equation tests for M9B."""

import json
from math import sqrt
from pathlib import Path

import pytest

from cfs_design.design.dsm.equations import (
    DISTORTIONAL_UPPER_BOUND_TRANSITION,
    DSMCalculationError,
    DSM_MAX_SLENDERNESS,
    LOCAL_UPPER_BOUND_TRANSITION,
    calculate_dsm_distortional_strength,
    calculate_dsm_local_strength,
    select_dsm_nominal_strength,
)
from cfs_design.design.dsm.models import (
    DSMDistortionalBranch,
    DSMGoverningLimitState,
    DSMLocalBranch,
)


def _local_at(slenderness: float):
    return calculate_dsm_local_strength(
        p_ne_n=1000.0,
        p_crl_n=1000.0 / slenderness**2,
    )


def _distortional_at(slenderness: float):
    return calculate_dsm_distortional_strength(
        p_y_n=1000.0,
        p_crd_n=1000.0 / slenderness**2,
    )


def test_s10024_transitions_are_derived_from_exact_upper_bound_equalities() -> None:
    assert LOCAL_UPPER_BOUND_TRANSITION == sqrt(20.0 / 43.0)
    assert DISTORTIONAL_UPPER_BOUND_TRANSITION == sqrt(20.0 / 61.0)


def test_local_below_and_at_transition_use_pne_upper_bound() -> None:
    below = _local_at(0.5)
    at = _local_at(LOCAL_UPPER_BOUND_TRANSITION)

    assert below.branch is DSMLocalBranch.PNE_UPPER_BOUND
    assert at.branch is DSMLocalBranch.PNE_UPPER_BOUND
    assert below.p_nl_n == 1000.0
    assert at.p_nl_n == 1000.0


def test_local_above_transition_uses_current_s10024_rational_reduction() -> None:
    result = _local_at(1.0)

    assert result.branch is DSMLocalBranch.LOCAL_REDUCTION
    assert result.p_nl_n == pytest.approx(1.2 * 1.10 / 1.55 * 1000.0)


def test_local_equation_is_continuous_at_transition() -> None:
    below = _local_at(LOCAL_UPPER_BOUND_TRANSITION * (1.0 - 1.0e-9))
    above = _local_at(LOCAL_UPPER_BOUND_TRANSITION * (1.0 + 1.0e-9))

    assert below.p_nl_n == pytest.approx(above.p_nl_n, rel=1.0e-9)


def test_increasing_local_slenderness_reduces_pnl_and_never_exceeds_pne() -> None:
    values = tuple(_local_at(value).p_nl_n for value in (0.5, 1.0, 2.0, 5.0))

    assert values == tuple(sorted(values, reverse=True))
    assert all(value <= 1000.0 for value in values)


def test_distortional_below_and_at_transition_use_py_upper_bound() -> None:
    below = _distortional_at(0.5)
    at = _distortional_at(DISTORTIONAL_UPPER_BOUND_TRANSITION)

    assert below.branch is DSMDistortionalBranch.PY_UPPER_BOUND
    assert at.branch is DSMDistortionalBranch.PY_UPPER_BOUND
    assert below.p_nd_n == 1000.0
    assert at.p_nd_n == 1000.0


def test_distortional_above_transition_uses_current_s10024_rational_reduction() -> None:
    result = _distortional_at(1.0)

    assert result.branch is DSMDistortionalBranch.DISTORTIONAL_REDUCTION
    assert result.p_nd_n == pytest.approx(1.2 * 1.05 / 1.67 * 1000.0)


def test_distortional_equation_is_continuous_at_transition() -> None:
    below = _distortional_at(
        DISTORTIONAL_UPPER_BOUND_TRANSITION * (1.0 - 1.0e-9)
    )
    above = _distortional_at(
        DISTORTIONAL_UPPER_BOUND_TRANSITION * (1.0 + 1.0e-9)
    )

    assert below.p_nd_n == pytest.approx(above.p_nd_n, rel=1.0e-9)


def test_increasing_distortional_slenderness_reduces_pnd_and_caps_at_py() -> None:
    values = tuple(
        _distortional_at(value).p_nd_n for value in (0.5, 1.0, 2.0, 5.0)
    )

    assert values == tuple(sorted(values, reverse=True))
    assert all(value <= 1000.0 for value in values)


@pytest.mark.parametrize("calculator", (_local_at, _distortional_at))
def test_lambda_five_is_supported_and_above_five_is_not(calculator) -> None:
    assert calculator(DSM_MAX_SLENDERNESS)
    with pytest.raises(DSMCalculationError, match="not greater than 5"):
        calculator(DSM_MAX_SLENDERNESS * (1.0 + 1.0e-9))


@pytest.mark.parametrize("value", (0.0, -1.0, float("nan"), float("inf")))
@pytest.mark.parametrize("argument", ("p_ne_n", "p_crl_n"))
def test_local_inputs_must_be_positive_and_finite(
    value: float, argument: str
) -> None:
    inputs = {"p_ne_n": 1.0, "p_crl_n": 1.0}
    inputs[argument] = value
    with pytest.raises(DSMCalculationError):
        calculate_dsm_local_strength(**inputs)


@pytest.mark.parametrize("value", (0.0, -1.0, float("nan"), float("inf")))
@pytest.mark.parametrize("argument", ("p_y_n", "p_crd_n"))
def test_distortional_inputs_must_be_positive_and_finite(
    value: float, argument: str
) -> None:
    inputs = {"p_y_n": 1.0, "p_crd_n": 1.0}
    inputs[argument] = value
    with pytest.raises(DSMCalculationError):
        calculate_dsm_distortional_strength(**inputs)


def test_e1_selects_local_distortional_and_exact_equality_deterministically() -> None:
    assert select_dsm_nominal_strength(p_nl_n=80.0, p_nd_n=100.0) == (
        80.0,
        DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION,
    )
    assert select_dsm_nominal_strength(p_nl_n=100.0, p_nd_n=80.0) == (
        80.0,
        DSMGoverningLimitState.DISTORTIONAL,
    )
    assert select_dsm_nominal_strength(p_nl_n=100.0, p_nd_n=100.0) == (
        100.0,
        DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION,
    )


def test_independent_hand_fixture_matches_s10024_equations() -> None:
    benchmark = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "validation/m9b/dsm_axial_compression_hand_fixture.json"
        ).read_text(encoding="utf-8")
    )
    inputs = benchmark["inputs_n"]
    expected = benchmark["expected"]
    local = calculate_dsm_local_strength(
        p_ne_n=inputs["Pne"], p_crl_n=inputs["Pcrl"]
    )
    distortional = calculate_dsm_distortional_strength(
        p_y_n=inputs["Py"],
        p_crd_n=inputs["Pcrd"],
    )
    nominal, governing = select_dsm_nominal_strength(
        p_nl_n=local.p_nl_n,
        p_nd_n=distortional.p_nd_n,
    )

    assert local.lambda_l == pytest.approx(expected["lambda_l"])
    assert local.p_nl_n == pytest.approx(expected["Pnl_n"])
    assert local.branch.value == expected["local_branch"]
    assert distortional.lambda_d == pytest.approx(expected["lambda_d"])
    assert distortional.p_nd_n == pytest.approx(expected["Pnd_n"])
    assert distortional.branch.value == expected["distortional_branch"]
    assert nominal == pytest.approx(expected["Pn_n"])
    assert governing is DSMGoverningLimitState.LOCAL_GLOBAL_INTERACTION
    assert governing.value == expected["governing_limit_state"]
    assert expected["phiPn_n"] == pytest.approx(expected["phi"] * nominal)
