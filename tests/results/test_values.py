"""M6 engineering-value, metadata, identity, and reference tests."""

from dataclasses import FrozenInstanceError, asdict
import json

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.results import (
    EngineeringUnit,
    EngineeringValue,
    EquationReference,
    LimitStateId,
    MetadataEntry,
    ReferenceSourceType,
)


def test_engineering_value_preserves_full_finite_value_and_explicit_unit() -> None:
    value = EngineeringValue(
        name="illustrative_area",
        symbol="A",
        value=123.45678901234567,
        unit=EngineeringUnit.SQUARE_MILLIMETRE,
        description="Neutral geometry example",
    )

    assert value.value == 123.45678901234567
    assert value.unit.value == "mm2"
    assert json.dumps(asdict(value))


def test_integer_engineering_value_is_normalized_to_plain_float() -> None:
    value = EngineeringValue(
        name="count_like_scalar",
        value=2,
        unit=EngineeringUnit.DIMENSIONLESS,
    )
    assert value.value == 2.0
    assert type(value.value) is float


@pytest.mark.parametrize("value", (float("nan"), float("inf"), -float("inf"), True))
def test_engineering_value_rejects_non_finite_and_boolean_values(value: object) -> None:
    with pytest.raises(ValidationError, match="finite number"):
        EngineeringValue(
            name="invalid",
            value=value,  # type: ignore[arg-type]
            unit=EngineeringUnit.DIMENSIONLESS,
        )


def test_unit_must_use_controlled_representation() -> None:
    with pytest.raises(ValidationError, match="EngineeringUnit"):
        EngineeringValue(
            name="force",
            value=10.0,
            unit="kN",  # type: ignore[arg-type]
        )


def test_dimensionless_is_explicit_one_marker() -> None:
    ratio = EngineeringValue(
        name="neutral_ratio",
        value=0.75,
        unit=EngineeringUnit.DIMENSIONLESS,
    )
    assert ratio.unit.value == "1"


def test_engineering_value_is_frozen_and_slotted() -> None:
    value = EngineeringValue(
        name="width",
        value=100.0,
        unit=EngineeringUnit.MILLIMETRE,
    )
    with pytest.raises(FrozenInstanceError):
        value.value = 200.0  # type: ignore[misc]
    assert hasattr(EngineeringValue, "__slots__")


def test_metadata_is_flat_immutable_and_serialization_friendly() -> None:
    entries = (
        MetadataEntry("software_version", "0.1.0.dev0"),
        MetadataEntry("iteration", 2),
        MetadataEntry("verified", True),
        MetadataEntry("optional", None),
    )
    assert json.dumps([asdict(entry) for entry in entries])
    with pytest.raises(FrozenInstanceError):
        entries[0].value = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("value", (float("nan"), float("inf")))
def test_metadata_rejects_non_finite_float(value: float) -> None:
    with pytest.raises(ValidationError, match="finite number"):
        MetadataEntry("bad", value)


@pytest.mark.parametrize("value", ("GLOBAL_BUCKLING", "AREA_CHECK_2"))
def test_limit_state_id_accepts_extensible_controlled_codes(value: str) -> None:
    assert LimitStateId(value).value == value


def test_limit_state_identity_depends_on_code_not_optional_description() -> None:
    assert LimitStateId("AREA_CHECK", "First label") == LimitStateId(
        "AREA_CHECK", "Second label"
    )


@pytest.mark.parametrize("value", ("", "local_buckling", "LOCAL-BUCKLING", "2STATE"))
def test_limit_state_id_rejects_uncontrolled_codes(value: str) -> None:
    with pytest.raises(ValidationError):
        LimitStateId(value)


def test_non_normative_mechanics_reference_is_supported() -> None:
    reference = EquationReference(
        source_type=ReferenceSourceType.MECHANICS,
        title="Illustrative rectangle area identity",
        notes="Used only to test trace infrastructure",
    )
    assert reference.standard_id is None


def test_future_standard_reference_requires_standard_and_edition_together() -> None:
    reference = EquationReference(
        source_type=ReferenceSourceType.STANDARD,
        standard_id="EXAMPLE_STANDARD",
        edition=2099,
        clause="X.1",
        equation_id="Eq. X-1",
    )
    assert reference.edition == 2099

    with pytest.raises(ValidationError, match="require standard_id and edition"):
        EquationReference(
            source_type=ReferenceSourceType.STANDARD,
            title="Incomplete future reference",
        )


def test_non_standard_reference_cannot_masquerade_as_standard() -> None:
    with pytest.raises(ValidationError, match="reserved for STANDARD"):
        EquationReference(
            source_type=ReferenceSourceType.MECHANICS,
            standard_id="EXAMPLE_STANDARD",
            edition=2099,
            title="Contradictory reference",
        )
