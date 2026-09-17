"""M10 architecture and milestone-boundary tests."""

import ast
from pathlib import Path

import cfs_design.design.comparison as comparison
import cfs_design.workflows as workflows


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPARISON_ROOT = REPOSITORY_ROOT / "src" / "cfs_design" / "design" / "comparison"


def test_public_apis_are_deliberate() -> None:
    assert "compare_compression_summaries" in comparison.__all__
    assert "CompressionComparisonResult" in comparison.__all__
    assert "design_axial_compression" in workflows.__all__
    assert "prepare_axial_compression_request" in workflows.__all__


def test_comparison_layer_has_no_io_report_or_external_solver_dependency() -> None:
    forbidden = (
        "cfs_design.io",
        "cfs_design.reports",
        "cfs_design.stability.pycufsm_adapter",
        "pycufsm",
        "numpy",
    )
    imports: list[str] = []
    for path in COMPARISON_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

    assert not any(
        imported.startswith(prefix)
        for imported in imports
        for prefix in forbidden
    )


def test_comparison_does_not_contain_resistance_equations_or_reapply_phi() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in COMPARISON_ROOT.glob("*.py")
    ).lower()

    assert "calculate_ewm_compression_resistance" not in text
    assert "calculate_dsm_compression_resistance" not in text
    assert "0.658" not in text
    assert "0.877" not in text
    assert "0.55" not in text
    assert "0.67" not in text
    assert "resistance_factor *" not in text


def test_no_flexure_or_later_milestone_module_was_added() -> None:
    names = {path.name.lower() for path in COMPARISON_ROOT.glob("*.py")}
    assert names == {"__init__.py", "models.py", "compression.py"}
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in COMPARISON_ROOT.glob("*.py")
    ).lower()
    assert "flexural resistance" not in text
    assert "p-m interaction" not in text


def test_reports_do_not_execute_m10_or_method_engines() -> None:
    reports = REPOSITORY_ROOT / "src" / "cfs_design" / "reports"
    text = "\n".join(path.read_text(encoding="utf-8") for path in reports.rglob("*.py"))

    assert "design_axial_compression" not in text
    assert "calculate_ewm_compression_resistance" not in text
    assert "calculate_dsm_compression_resistance" not in text

