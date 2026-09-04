"""M9B dependency, public API, and milestone-boundary guards."""

import ast
from pathlib import Path

import cfs_design.design.dsm as dsm
from cfs_design.design.dsm.compression import (
    LRFD_COMPRESSION_RESISTANCE_FACTOR as DSM_PHI_C,
)
from cfs_design.design.ewm.compression import (
    LRFD_COMPRESSION_RESISTANCE_FACTOR as EWM_PHI_C,
)
from cfs_design.normative import S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DSM_ROOT = REPOSITORY_ROOT / "src" / "cfs_design" / "design" / "dsm"


def test_dsm_public_api_is_deliberately_small() -> None:
    assert set(dsm.__all__) == {
        "DSMCompressionResistance",
        "DSMDesignReadiness",
        "DSMDistortionalBranch",
        "DSMElasticBucklingProvenance",
        "DSMElasticInputBasis",
        "DSMGoverningLimitState",
        "DSMLocalBranch",
        "M9AUnavailable",
        "calculate_dsm_compression_resistance",
    }


def test_dsm_has_no_ewm_io_report_or_direct_pycufsm_dependency() -> None:
    forbidden_prefixes = (
        "cfs_design.design.ewm",
        "cfs_design.io",
        "cfs_design.reports",
        "pycufsm",
    )
    imports: list[str] = []
    for path in DSM_ROOT.glob("*.py"):
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


def test_no_m10_or_flexural_dsm_module_was_created() -> None:
    names = {path.name.lower() for path in DSM_ROOT.glob("*.py")}
    assert names == {"__init__.py", "compression.py", "equations.py", "models.py"}
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in DSM_ROOT.glob("*.py")
    ).lower()
    assert "ewm vs dsm" not in text
    assert "utilization" not in text
    assert "flexural resistance" not in text


def test_reports_do_not_recalculate_dsm_resistance() -> None:
    reports_root = REPOSITORY_ROOT / "src" / "cfs_design" / "reports"
    if reports_root.exists():
        report_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in reports_root.rglob("*.py")
        )
        assert "calculate_dsm_compression_resistance" not in report_text


def test_ewm_and_dsm_use_the_single_normative_compression_factor() -> None:
    normative = S100_24_LRFD_COMPRESSION_RESISTANCE_FACTOR.value.value

    assert EWM_PHI_C == normative
    assert DSM_PHI_C == normative
