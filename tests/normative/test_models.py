"""Typed M7 model, status, diagnostic, and eligibility tests."""

from dataclasses import FrozenInstanceError, asdict

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignMethod
from cfs_design.normative import (
    ApplicabilityCheck,
    DesignAction,
    DesignEligibility,
    NormativeApplicabilityResult,
    SOFTWARE_SCOPE_VERSION,
    SoftwareSupportCheck,
    SoftwareSupportResult,
    SoftwareSupportStatus,
    make_applicability_check_id,
    make_software_check_id,
    s100_24_reference,
)
from cfs_design.results import (
    ApplicabilityStatus,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    MetadataEntry,
)


def _normative(status: ApplicabilityStatus) -> NormativeApplicabilityResult:
    observed = (MetadataEntry("known", status is not ApplicabilityStatus.INDETERMINATE),)
    diagnostic = (
        None
        if status is ApplicabilityStatus.APPLICABLE
        else EngineeringDiagnostic(
            severity=DiagnosticSeverity.WARNING,
            code=f"NORMATIVE_{status.value}",
            message="Test-only normative diagnostic",
            context=observed,
        )
    )
    check = ApplicabilityCheck(
        check_id=make_applicability_check_id(
            method=DesignMethod.EWM,
            action=DesignAction.AXIAL_COMPRESSION,
            rule_id="TEST_RULE",
        ),
        topic="test rule",
        status=status,
        observed=observed,
        requirement="Test-only concise requirement.",
        reference=s100_24_reference(clause="A1.1", title="Test reference"),
        diagnostic=diagnostic,
    )
    return NormativeApplicabilityResult(
        method=DesignMethod.EWM,
        action=DesignAction.AXIAL_COMPRESSION,
        status=status,
        checks=(check,),
    )


def _software(status: SoftwareSupportStatus) -> SoftwareSupportResult:
    observed = (MetadataEntry("supported", status is SoftwareSupportStatus.SUPPORTED),)
    diagnostic = (
        None
        if status is SoftwareSupportStatus.SUPPORTED
        else EngineeringDiagnostic(
            severity=(
                DiagnosticSeverity.ERROR
                if status is SoftwareSupportStatus.INVALID_INPUT
                else DiagnosticSeverity.WARNING
            ),
            code=f"SOFTWARE_{status.value}",
            message="Test-only software diagnostic",
            context=observed,
        )
    )
    check = SoftwareSupportCheck(
        check_id=make_software_check_id(
            method=DesignMethod.EWM,
            action=DesignAction.AXIAL_COMPRESSION,
            capability_id="TEST_CAPABILITY",
        ),
        topic="test capability",
        status=status,
        observed=observed,
        requirement="Test-only software requirement.",
        diagnostic=diagnostic,
    )
    return SoftwareSupportResult(
        method=DesignMethod.EWM,
        action=DesignAction.AXIAL_COMPRESSION,
        status=status,
        checks=(check,),
        software_scope_version=SOFTWARE_SCOPE_VERSION,
    )


@pytest.mark.parametrize(
    "status",
    [
        ApplicabilityStatus.APPLICABLE,
        ApplicabilityStatus.NOT_APPLICABLE,
        ApplicabilityStatus.INDETERMINATE,
    ],
)
def test_normative_model_preserves_all_m7_statuses_and_references(
    status: ApplicabilityStatus,
) -> None:
    result = _normative(status)

    assert result.status is status
    assert result.references == (result.checks[0].reference,)
    assert result.diagnostics == (
        ()
        if status is ApplicabilityStatus.APPLICABLE
        else (result.checks[0].diagnostic,)
    )
    assert asdict(result)["checks"][0]["observed"][0]["value"] in (True, False)


def test_check_ids_are_deterministic_and_contextual() -> None:
    first = make_applicability_check_id(
        method=DesignMethod.DSM,
        action=DesignAction.STRONG_AXIS_FLEXURE,
        rule_id="F_SCOPE",
    )
    second = make_applicability_check_id(
        method=DesignMethod.DSM,
        action=DesignAction.STRONG_AXIS_FLEXURE,
        rule_id="F_SCOPE",
    )

    assert first == second
    assert "method=DSM" in first
    assert "action=STRONG_AXIS_FLEXURE" in first


def test_applicability_check_is_immutable() -> None:
    check = _normative(ApplicabilityStatus.APPLICABLE).checks[0]

    with pytest.raises(FrozenInstanceError):
        check.topic = "changed"  # type: ignore[misc]


def test_result_rejects_status_inconsistent_with_checks() -> None:
    check = _normative(ApplicabilityStatus.APPLICABLE).checks[0]

    with pytest.raises(ValidationError, match="does not match"):
        NormativeApplicabilityResult(
            method=DesignMethod.EWM,
            action=DesignAction.AXIAL_COMPRESSION,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            checks=(check,),
        )


@pytest.mark.parametrize(
    ("normative_status", "software_status", "expected"),
    [
        (
            ApplicabilityStatus.APPLICABLE,
            SoftwareSupportStatus.SUPPORTED,
            True,
        ),
        (
            ApplicabilityStatus.APPLICABLE,
            SoftwareSupportStatus.UNSUPPORTED,
            False,
        ),
        (
            ApplicabilityStatus.NOT_APPLICABLE,
            SoftwareSupportStatus.SUPPORTED,
            False,
        ),
        (
            ApplicabilityStatus.INDETERMINATE,
            SoftwareSupportStatus.SUPPORTED,
            False,
        ),
    ],
    ids=("A", "B", "C", "D"),
)
def test_required_normative_vs_software_cases(
    normative_status: ApplicabilityStatus,
    software_status: SoftwareSupportStatus,
    expected: bool,
) -> None:
    eligibility = DesignEligibility(
        normative=_normative(normative_status),
        software=_software(software_status),
    )

    assert eligibility.executable is expected
    assert eligibility.normative.status is normative_status
    assert eligibility.software.status is software_status
    if not expected:
        assert eligibility.diagnostics[-1].code == "DESIGN_NOT_ELIGIBLE"
