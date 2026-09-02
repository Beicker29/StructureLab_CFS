"""M6 immutable calculation-step and trace tests."""

from dataclasses import FrozenInstanceError, asdict
import json

import pytest

from cfs_design.core.exceptions import ValidationError
from cfs_design.domain import DesignMethod
from cfs_design.results import (
    CalculationStatus,
    CalculationStep,
    CalculationTrace,
    DiagnosticSeverity,
    EngineeringDiagnostic,
    EngineeringUnit,
    EngineeringValue,
    EquationReference,
    LimitStateId,
    MetadataEntry,
    ReferenceSourceType,
    make_step_id,
    make_trace_id,
)


def _area_trace() -> CalculationTrace:
    limit_state = LimitStateId("ILLUSTRATIVE_AREA")
    trace_id = make_trace_id(
        project_id="PRJ_TEST",
        case_id="MEMBER_1",
        combination_id="COMBO_1",
        demand_point_id="POINT_1",
        method=DesignMethod.EWM,
        limit_state=limit_state,
    )
    width = EngineeringValue("width", 100.0, EngineeringUnit.MILLIMETRE, "b")
    thickness = EngineeringValue("thickness", 2.0, EngineeringUnit.MILLIMETRE, "t")
    area = EngineeringValue("area", 200.0, EngineeringUnit.SQUARE_MILLIMETRE, "A")
    step = CalculationStep(
        step_id=make_step_id(trace_id, 1),
        name="Illustrative area",
        inputs=(width, thickness),
        expression="A = b * t",
        reference=EquationReference(
            source_type=ReferenceSourceType.MECHANICS,
            title="Neutral rectangle identity",
        ),
        results=(area,),
    )
    return CalculationTrace(
        trace_id=trace_id,
        status=CalculationStatus.COMPLETED,
        project_id="PRJ_TEST",
        case_id="MEMBER_1",
        combination_id="COMBO_1",
        demand_point_id="POINT_1",
        method=DesignMethod.EWM,
        limit_state=limit_state,
        steps=(step,),
        final_values=(area,),
        metadata=(MetadataEntry("software_version", "test"),),
    )


def test_step_records_inputs_expression_reference_and_result_without_evaluation() -> None:
    trace = _area_trace()
    step = trace.steps[0]
    assert step.expression == "A = b * t"
    assert step.result == trace.final_values[0]
    assert step.reference is not None
    assert step.reference.source_type is ReferenceSourceType.MECHANICS


def test_expression_is_documentation_only_even_if_it_looks_executable() -> None:
    marker: list[str] = []
    value = EngineeringValue("stored", 1.0, EngineeringUnit.DIMENSIONLESS)
    step = CalculationStep(
        step_id="STEP_DOC_ONLY",
        name="Documentation only",
        expression="marker.append('executed')",
        results=(value,),
    )
    assert step.expression
    assert marker == []


def test_multi_result_step_has_no_singular_result_alias() -> None:
    step = CalculationStep(
        step_id="MULTI",
        name="Two stored results",
        results=(
            EngineeringValue("x", 1.0, EngineeringUnit.MILLIMETRE),
            EngineeringValue("y", 2.0, EngineeringUnit.MILLIMETRE),
        ),
    )
    assert step.result is None


def test_step_requires_tuple_and_at_least_one_result() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        CalculationStep(step_id="EMPTY", name="Empty", results=())
    with pytest.raises(ValidationError, match="tuple"):
        CalculationStep(
            step_id="LIST",
            name="List",
            results=[  # type: ignore[arg-type]
                EngineeringValue("x", 1.0, EngineeringUnit.DIMENSIONLESS)
            ],
        )


def test_step_rejects_duplicate_input_or_result_names() -> None:
    duplicate = EngineeringValue("same", 1.0, EngineeringUnit.DIMENSIONLESS)
    with pytest.raises(ValidationError, match="names must be unique"):
        CalculationStep(
            step_id="DUP",
            name="Duplicate",
            inputs=(duplicate, duplicate),
            results=(
                EngineeringValue("result", 1.0, EngineeringUnit.DIMENSIONLESS),
            ),
        )


def test_trace_and_step_id_helpers_are_deterministic_and_ordered() -> None:
    limit_state = LimitStateId("ILLUSTRATIVE_AREA")
    first = make_trace_id(
        project_id="Project A",
        case_id="Member/1",
        method=DesignMethod.DSM,
        limit_state=limit_state,
    )
    second = make_trace_id(
        project_id="Project A",
        case_id="Member/1",
        method=DesignMethod.DSM,
        limit_state=limit_state,
    )
    assert first == second
    assert first == (
        "trace:project=Project%20A:case=Member%2F1:method=DSM:"
        "limit_state=ILLUSTRATIVE_AREA"
    )
    assert make_step_id(first, 2).endswith(":step=002")


def test_id_helpers_reject_missing_context_and_invalid_sequence() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        make_trace_id()
    with pytest.raises(ValidationError, match="positive integer"):
        make_step_id("TRACE", 0)


def test_completed_trace_requires_steps_and_final_values() -> None:
    with pytest.raises(ValidationError, match="completed traces require"):
        CalculationTrace(trace_id="TRACE", status=CalculationStatus.COMPLETED)


def test_not_run_trace_contains_no_fabricated_values() -> None:
    trace = CalculationTrace(
        trace_id="TRACE_NOT_RUN",
        status=CalculationStatus.NOT_RUN,
        case_id="MEMBER_1",
        diagnostics=(
            EngineeringDiagnostic(
                DiagnosticSeverity.INFO,
                "NOT_EXECUTED",
                "Infrastructure-only example",
            ),
        ),
    )
    assert trace.steps == ()
    assert trace.final_values == ()


def test_not_run_trace_rejects_calculated_values() -> None:
    value = EngineeringValue("value", 1.0, EngineeringUnit.DIMENSIONLESS)
    with pytest.raises(ValidationError, match="NOT_RUN"):
        CalculationTrace(
            trace_id="TRACE_NOT_RUN",
            status=CalculationStatus.NOT_RUN,
            final_values=(value,),
        )


def test_trace_rejects_duplicate_step_ids_and_final_names() -> None:
    trace = _area_trace()
    with pytest.raises(ValidationError, match="step IDs"):
        CalculationTrace(
            trace_id="DUP_STEPS",
            status=CalculationStatus.COMPLETED,
            steps=(trace.steps[0], trace.steps[0]),
            final_values=trace.final_values,
        )
    with pytest.raises(ValidationError, match="final_values names"):
        CalculationTrace(
            trace_id="DUP_FINAL",
            status=CalculationStatus.COMPLETED,
            steps=trace.steps,
            final_values=(trace.final_values[0], trace.final_values[0]),
        )


def test_trace_preserves_structured_diagnostics_and_metadata() -> None:
    source = _area_trace()
    diagnostic = EngineeringDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        code="ILLUSTRATIVE_WARNING",
        message="Stored for a future report",
        context=(MetadataEntry("threshold", 0.5),),
    )
    trace = CalculationTrace(
        trace_id=source.trace_id,
        status=CalculationStatus.COMPLETED_WITH_WARNINGS,
        steps=source.steps,
        final_values=source.final_values,
        diagnostics=(diagnostic,),
        metadata=(MetadataEntry("engine", "neutral-test"),),
    )
    assert trace.diagnostics[0].context[0].value == 0.5
    assert trace.metadata[0].value == "neutral-test"


def test_trace_tree_is_frozen_and_json_serialization_ready() -> None:
    trace = _area_trace()
    with pytest.raises(FrozenInstanceError):
        trace.trace_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        trace.steps[0].name = "changed"  # type: ignore[misc]
    encoded = json.dumps(asdict(trace), sort_keys=True)
    assert "ILLUSTRATIVE_AREA" in encoded
    assert "A = b * t" in encoded

