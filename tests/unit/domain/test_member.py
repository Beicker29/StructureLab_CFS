"""Member length, restraint, and identity tests."""

from dataclasses import replace

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import (
    LengthDefinition,
    MemberCase,
    MemberGeometry,
    Restraints,
)


def test_valid_k_factor_definition(member_geometry: MemberGeometry) -> None:
    assert member_geometry.length_definition is LengthDefinition.K_FACTORS


def test_valid_explicit_effective_length_definition() -> None:
    geometry = MemberGeometry(
        l_mm=4_000.0,
        length_definition=LengthDefinition.EFFECTIVE_LENGTHS,
        lx_mm=4_000.0,
        ly_mm=3_500.0,
        lt_mm=2_000.0,
    )
    assert geometry.ly_mm == 3_500.0


@pytest.mark.parametrize("field_name", ("kx", "ky", "kt"))
def test_missing_required_k_factor_is_rejected(
    member_geometry: MemberGeometry,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        replace(member_geometry, **{field_name: None})


@pytest.mark.parametrize("field_name", ("lx_mm", "ly_mm", "lt_mm"))
def test_missing_required_effective_length_is_rejected(field_name: str) -> None:
    values = {"lx_mm": 4_000.0, "ly_mm": 4_000.0, "lt_mm": 4_000.0}
    values[field_name] = None
    with pytest.raises(ValidationError):
        MemberGeometry(
            l_mm=4_000.0,
            length_definition=LengthDefinition.EFFECTIVE_LENGTHS,
            **values,
        )


def test_invalid_physical_length_is_rejected(member_geometry: MemberGeometry) -> None:
    with pytest.raises(ValidationError):
        replace(member_geometry, l_mm=0.0)


def test_effective_lengths_contradict_k_factor_mode(
    member_geometry: MemberGeometry,
) -> None:
    with pytest.raises(ValidationError):
        replace(member_geometry, lx_mm=5_500.0)


def test_k_factors_contradict_effective_length_mode() -> None:
    with pytest.raises(ValidationError):
        MemberGeometry(
            l_mm=4_000.0,
            length_definition=LengthDefinition.EFFECTIVE_LENGTHS,
            kx=1.0,
            lx_mm=4_000.0,
            ly_mm=4_000.0,
            lt_mm=4_000.0,
        )


def test_valid_restraints(restraints: Restraints) -> None:
    assert restraints.y_translation_restrained is True


def test_invalid_brace_spacing_is_rejected(restraints: Restraints) -> None:
    with pytest.raises(ValidationError):
        replace(restraints, lateral_brace_spacing_mm=0.0)


def test_valid_member_case(member: MemberCase) -> None:
    assert member.section_id == "SEC_C200"


@pytest.mark.parametrize("field_name", ("case_id", "label", "section_id", "material_id"))
def test_blank_member_identity_is_rejected(
    member: MemberCase,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        replace(member, **{field_name: "  "})

