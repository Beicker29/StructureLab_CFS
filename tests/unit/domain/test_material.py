"""Material value-object tests."""

from dataclasses import replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import Material


def test_valid_material(material: Material) -> None:
    assert material.material_id == "MAT_G50"


def test_invalid_yield_stress_is_rejected(material: Material) -> None:
    with pytest.raises(ValidationError):
        replace(material, fy_mpa=0.0)


def test_ultimate_stress_below_yield_is_rejected(material: Material) -> None:
    with pytest.raises(ValidationError):
        replace(material, fu_mpa=300.0)


def test_invalid_elastic_modulus_is_rejected(material: Material) -> None:
    with pytest.raises(ValidationError):
        replace(material, e_mpa=-1.0)


@pytest.mark.parametrize("nu", (0.0, -0.1, 0.5, 0.6))
def test_invalid_poisson_ratio_is_rejected(material: Material, nu: float) -> None:
    with pytest.raises(ValidationError):
        replace(material, nu=nu)


def test_optional_density_is_accepted(material: Material) -> None:
    assert replace(material, density_kg_m3=None).density_kg_m3 is None


def test_invalid_supplied_density_is_rejected(material: Material) -> None:
    with pytest.raises(ValidationError):
        replace(material, density_kg_m3=0.0)


def test_shear_modulus_is_derived(material: Material) -> None:
    assert material.g_mpa == pytest.approx(76_923.076923)

