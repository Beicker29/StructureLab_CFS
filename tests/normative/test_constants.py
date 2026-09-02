"""S100-24 normative elastic constants remain centralized and traceable."""

from dataclasses import FrozenInstanceError

import pytest

import cfs_design.normative as normative_api
import cfs_design.normative.constants as constants_module
from cfs_design.core.units import EngineeringUnit
from cfs_design.domain import Material
from cfs_design.normative import S100_24_ELASTIC_CONSTANTS


def test_s100_24_elastic_constants_have_exact_values_units_and_references() -> None:
    constants = S100_24_ELASTIC_CONSTANTS

    assert constants.elastic_modulus.value.value == 203000.0
    assert constants.elastic_modulus.value.unit is EngineeringUnit.MEGAPASCAL
    assert constants.shear_modulus.value.value == 78000.0
    assert constants.shear_modulus.value.unit is EngineeringUnit.MEGAPASCAL
    assert constants.poisson_ratio.value.value == 0.30
    assert constants.poisson_ratio.value.unit is EngineeringUnit.DIMENSIONLESS
    for constant in (
        constants.elastic_modulus,
        constants.shear_modulus,
        constants.poisson_ratio,
    ):
        assert constant.reference.standard_id == "ANSI_SDI_AISI_S100"
        assert constant.reference.edition == 2024
        assert constant.reference.clause is not None


def test_s100_24_elastic_constants_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        S100_24_ELASTIC_CONSTANTS.elastic_modulus = (  # type: ignore[misc]
            S100_24_ELASTIC_CONSTANTS.elastic_modulus
        )


def test_public_api_reuses_the_single_constant_object() -> None:
    assert (
        normative_api.S100_24_ELASTIC_CONSTANTS
        is constants_module.S100_24_ELASTIC_CONSTANTS
    )


def test_normative_constants_are_not_derived_from_material() -> None:
    material = Material(
        material_id="SYNTHETIC_TEST_MATERIAL",
        designation="Synthetic",
        specification="TEST_ONLY",
        grade="TEST_ONLY",
        fy_mpa=345.0,
        fu_mpa=450.0,
        e_mpa=200000.0,
        nu=0.3,
        density_kg_m3=None,
        source_id="SYNTHETIC_TEST_SOURCE",
        active=True,
    )

    assert material.e_mpa == 200000.0
    assert material.g_mpa != S100_24_ELASTIC_CONSTANTS.shear_modulus.value.value
    assert (
        material.e_mpa
        != S100_24_ELASTIC_CONSTANTS.elastic_modulus.value.value
    )
