"""M8B public-boundary and dependency-direction guards."""

import ast
from pathlib import Path

import cfs_design.design.ewm as ewm


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EWM_ROOT = REPOSITORY_ROOT / "src" / "cfs_design" / "design" / "ewm"


def test_capacity_public_api_is_deliberately_small() -> None:
    assert set(ewm.__all__) == {
        "EWMCompressionResistance",
        "calculate_ewm_compression_resistance",
    }


def test_ewm_has_no_io_report_dsm_or_pycufsm_dependency() -> None:
    forbidden_prefixes = (
        "cfs_design.io",
        "cfs_design.reports",
        "cfs_design.design.dsm",
        "pycufsm",
    )
    imports: list[str] = []
    for path in EWM_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

    assert not any(
        imported.startswith(prefix)
        for imported in imports
        for prefix in forbidden_prefixes
    )


def test_reports_contain_no_m8b_equation_implementation() -> None:
    reports_root = REPOSITORY_ROOT / "src" / "cfs_design" / "reports"
    if reports_root.exists():
        report_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in reports_root.rglob("*.py")
        )
        assert "calculate_ewm_compression_resistance" not in report_text
