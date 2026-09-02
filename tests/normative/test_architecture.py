"""Architectural guards for the deliberately narrow M7 boundary."""

import ast
from pathlib import Path
import re


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NORMATIVE_ROOT = REPOSITORY_ROOT / "src" / "cfs_design" / "normative"


def _production_sources() -> tuple[Path, ...]:
    return tuple(sorted(NORMATIVE_ROOT.rglob("*.py")))


def test_normative_package_has_no_runtime_pdf_or_pycufsm_dependency() -> None:
    forbidden_roots = {"pypdf", "PyPDF2", "pdfplumber", "fitz", "pycufsm"}
    found: set[str] = set()
    for path in _production_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(item.name.split(".")[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".")[0])

    assert found.isdisjoint(forbidden_roots)


def test_normative_dependency_direction_excludes_io_catalogs_and_mechanics() -> None:
    forbidden_prefixes = (
        "cfs_design.io",
        "cfs_design.catalogs",
        "cfs_design.mechanics",
    )
    imports: list[str] = []
    for path in _production_sources():
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


def test_m7_contains_no_design_strength_equation_identifiers() -> None:
    forbidden = re.compile(
        r"\b(?:Pn|Mn|Pcre|Pcrl|Pcrd|Mcre|Mcrl|Mcrd|"
        r"effective_width|utilization|resistance_factor)\b",
        flags=re.IGNORECASE,
    )
    violations = {
        path.relative_to(REPOSITORY_ROOT).as_posix(): forbidden.findall(
            path.read_text(encoding="utf-8")
        )
        for path in _production_sources()
        if forbidden.search(path.read_text(encoding="utf-8"))
    }

    assert violations == {}


def test_current_rules_reference_only_primary_s100_24() -> None:
    from cfs_design.normative import s100_24_reference

    reference = s100_24_reference(clause="B4.1", title="Architecture test")

    assert reference.standard_id == "ANSI_SDI_AISI_S100"
    assert reference.edition == 2024
