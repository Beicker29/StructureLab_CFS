"""Single immutable source for S100-24-prescribed elastic constants."""

from dataclasses import dataclass

from cfs_design.core.exceptions import ValidationError
from cfs_design.core.units import EngineeringUnit
from cfs_design.results import EngineeringValue, EquationReference

from .sources import (
    S100_24_STANDARD_EDITION,
    S100_24_STANDARD_ID,
    s100_24_reference,
)


@dataclass(frozen=True, slots=True)
class NormativeConstant:
    value: EngineeringValue
    reference: EquationReference

    def __post_init__(self) -> None:
        if not isinstance(self.value, EngineeringValue):
            raise ValidationError("value must be EngineeringValue")
        if not isinstance(self.reference, EquationReference):
            raise ValidationError("reference must be EquationReference")
        if (
            self.reference.standard_id != S100_24_STANDARD_ID
            or self.reference.edition != S100_24_STANDARD_EDITION
        ):
            raise ValidationError("constant reference must identify S100-24")


@dataclass(frozen=True, slots=True)
class S100ElasticConstants:
    elastic_modulus: NormativeConstant
    shear_modulus: NormativeConstant
    poisson_ratio: NormativeConstant

    def __post_init__(self) -> None:
        values = (self.elastic_modulus, self.shear_modulus, self.poisson_ratio)
        if any(not isinstance(item, NormativeConstant) for item in values):
            raise ValidationError("elastic constants must be NormativeConstant values")
        names = tuple(item.value.name for item in values)
        if len(set(names)) != len(names):
            raise ValidationError("normative elastic constant names must be unique")


S100_24_ELASTIC_CONSTANTS = S100ElasticConstants(
    elastic_modulus=NormativeConstant(
        value=EngineeringValue(
            name="s100_elastic_modulus",
            symbol="E",
            value=203000.0,
            unit=EngineeringUnit.MEGAPASCAL,
            description="S100-24 prescribed elastic modulus",
        ),
        reference=s100_24_reference(
            clause="Symbols; Appendix 2 Section 2.3.1",
            title="Prescribed elastic modulus",
        ),
    ),
    shear_modulus=NormativeConstant(
        value=EngineeringValue(
            name="s100_shear_modulus",
            symbol="G",
            value=78000.0,
            unit=EngineeringUnit.MEGAPASCAL,
            description="S100-24 prescribed shear modulus",
        ),
        reference=s100_24_reference(
            clause="Symbols; Appendix 2 Section 2.3.1",
            title="Prescribed shear modulus",
        ),
    ),
    poisson_ratio=NormativeConstant(
        value=EngineeringValue(
            name="s100_poisson_ratio",
            symbol="mu",
            value=0.30,
            unit=EngineeringUnit.DIMENSIONLESS,
            description="S100-24 prescribed Poisson ratio",
        ),
        reference=s100_24_reference(
            clause="Symbols",
            title="Prescribed Poisson ratio",
        ),
    ),
)

__all__ = [
    "NormativeConstant",
    "S100ElasticConstants",
    "S100_24_ELASTIC_CONSTANTS",
]
