"""M6 public API and report dependency-boundary inspection."""

import ast
from dataclasses import is_dataclass
from pathlib import Path

import cfs_design.results as results


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_results_public_api_is_shared_and_complete() -> None:
    expected = {
        "ApplicabilityStatus",
        "CalculationStatus",
        "CalculationStep",
        "CalculationTrace",
        "ComparisonResult",
        "DesignCheckStatus",
        "DiagnosticSeverity",
        "EngineeringDiagnostic",
        "EngineeringUnit",
        "EngineeringValue",
        "EquationReference",
        "LimitStateId",
        "LimitStateResult",
        "MemberDesignResult",
        "MetadataEntry",
        "MethodDesignResult",
        "ReferenceSourceType",
        "make_step_id",
        "make_trace_id",
    }
    assert expected <= set(results.__all__)
    assert all(hasattr(results, name) for name in expected)
    assert not hasattr(results, "EWMTrace")
    assert not hasattr(results, "DSMTrace")


def test_public_result_records_are_frozen_and_slotted_dataclasses() -> None:
    value_types = (
        results.EngineeringValue,
        results.MetadataEntry,
        results.LimitStateId,
        results.EngineeringDiagnostic,
        results.EquationReference,
        results.CalculationStep,
        results.CalculationTrace,
        results.LimitStateResult,
        results.MethodDesignResult,
        results.MemberDesignResult,
        results.ComparisonResult,
    )
    for value_type in value_types:
        assert is_dataclass(value_type)
        assert value_type.__dataclass_params__.frozen
        assert hasattr(value_type, "__slots__")


def test_reports_cannot_depend_on_calculation_or_orchestration_layers() -> None:
    """Guard the presentation boundary against calling engineering engines."""

    forbidden_prefixes = (
        "cfs_design.design",
        "cfs_design.mechanics",
        "cfs_design.stability",
        "cfs_design.workflows",
    )
    reports_root = REPOSITORY_ROOT / "src" / "cfs_design" / "reports"
    for source_path in reports_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in imported
            for prefix in forbidden_prefixes
        ), f"{source_path} crosses the report/calculation boundary"


def test_m6_reports_contain_no_implementation_to_recompute_results() -> None:
    """M6 deliberately leaves the future presentation package unimplemented."""

    reports_root = REPOSITORY_ROOT / "src" / "cfs_design" / "reports"
    for source_path in reports_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
        executable_definitions = tuple(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        assert executable_definitions == (), (
            f"{source_path} contains report implementation before the report milestone"
        )


def test_results_layer_does_not_depend_on_reports_or_method_engines() -> None:
    forbidden_prefixes = (
        "cfs_design.reports",
        "cfs_design.design.ewm",
        "cfs_design.design.dsm",
        "cfs_design.stability",
    )
    results_root = REPOSITORY_ROOT / "src" / "cfs_design" / "results"
    for source_path in results_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
        for node in ast.walk(tree):
            module_names: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                module_names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                module_names = (node.module,)
            assert not any(
                module == prefix or module.startswith(prefix + ".")
                for module in module_names
                for prefix in forbidden_prefixes
            ), f"{source_path} has a forbidden result-layer dependency"
