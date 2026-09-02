"""M4 unit-boundary conversion tests."""

import math

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import (
    KGF_M_TO_NMM,
    KGF_TO_N,
    M_TO_MM,
    convert_force_to_n,
    convert_length_to_mm,
    convert_moment_to_nmm,
)


def test_approved_etabs_unit_factors_are_exact() -> None:
    assert M_TO_MM == 1000.0
    assert KGF_TO_N == 9.80665
    assert KGF_M_TO_NMM == 9806.65
    assert convert_length_to_mm(1.25, "m") == 1250.0
    assert convert_force_to_n(2.0, "kgf") == 19.6133
    assert convert_moment_to_nmm(2.0, "kgf-m") == 19613.3


@pytest.mark.parametrize(
    ("converter", "unit"),
    (
        (convert_length_to_mm, "ft"),
        (convert_force_to_n, "kN"),
        (convert_moment_to_nmm, "kN-m"),
        (convert_force_to_n, "KGF"),
        (convert_force_to_n, ""),
    ),
)
def test_unknown_or_ambiguous_source_units_are_rejected(
    converter: object,
    unit: str,
) -> None:
    with pytest.raises(ValidationError):
        converter(1.0, unit)  # type: ignore[operator]


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf, True, "1"))
def test_non_finite_or_non_numeric_values_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError, match="finite number"):
        convert_force_to_n(value, "kgf")  # type: ignore[arg-type]
