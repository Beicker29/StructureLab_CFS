"""M9A deterministic mesh, dependency boundary, and contract tests."""

import ast
from pathlib import Path

import pytest

from cfs_design.domain import SectionFamily
from cfs_design.mechanics.sections import build_centerline_section
from cfs_design.mechanics.sections import (
    CenterlineSection,
    Point2D,
    ResolvedSectionMechanics,
    StraightSegment,
    compute_advanced_properties,
    compute_gross_properties,
)
from cfs_design.stability import ClassicalBasisOptions, build_fsm_mesh
from cfs_design.stability.pycufsm_adapter._classical import classify_mode_shape
from cfs_design.stability.pycufsm_adapter._solver import run_unconstrained
from tests.design.ewm.conftest import make_design_input


ROOT = Path(__file__).resolve().parents[2]


def test_mesh_is_deterministic_and_preserves_m3_endpoints_and_thickness() -> None:
    design_input = make_design_input(
        family=SectionFamily.C_LIPPED,
        web_mm=120.0,
        flange_1_mm=80.0,
        flange_2_mm=80.0,
        lip_1_mm=15.0,
        lip_2_mm=15.0,
    )
    section = design_input.resolved_member.section
    centerline = build_centerline_section(
        section.geometry, section_id=section.catalog_section.section_id
    )
    first = build_fsm_mesh(
        centerline,
        design_input.section_mechanics.advanced,
        target_strip_width_mm=20.0,
    )
    second = build_fsm_mesh(
        centerline,
        design_input.section_mechanics.advanced,
        target_strip_width_mm=20.0,
    )

    assert first == second
    assert len(first.nodes) == 17
    assert len(first.strips) == 16
    assert first.nodes[0].x_mm == pytest.approx(centerline.primitives[0].start.x_mm)
    assert first.nodes[-1].y_mm == pytest.approx(centerline.primitives[-1].end.y_mm)
    assert all(strip.thickness_mm == 1.0 for strip in first.strips)
    assert first.maximum_actual_strip_width_mm <= 20.0


def _transformed_centerline(
    original: CenterlineSection,
    *,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    mirror_x: bool = False,
) -> CenterlineSection:
    def point(source: Point2D) -> Point2D:
        x = -source.x_mm if mirror_x else source.x_mm
        return Point2D(x + offset_x, source.y_mm + offset_y)

    return CenterlineSection(
        section_id=original.section_id,
        geometry_id=original.geometry_id,
        family=original.family,
        thickness_mm=original.thickness_mm,
        primitives=tuple(
            StraightSegment(point(item.start), point(item.end))
            for item in original.primitives
        ),
        geometry_method=original.geometry_method,
        metadata=original.metadata,
    )


def _projection(centerline: CenterlineSection):
    gross = compute_gross_properties(centerline)
    advanced = compute_advanced_properties(centerline, gross)
    mechanics = ResolvedSectionMechanics(
        section_id=centerline.section_id,
        gross=gross,
        advanced=advanced,
        verification=None,
        design_use_permitted=False,
        gate_reason="Controlled modal-invariance fixture; not a design input.",
    )
    mesh = build_fsm_mesh(centerline, advanced, target_strip_width_mm=20.0)
    raw = run_unconstrained(
        mesh=mesh,
        mechanics=mechanics,
        elastic_modulus_mpa=210000.0,
        poisson_ratio=0.3,
        half_wavelengths_mm=(945.1687334,),
        eigenvalue_count=1,
        reference_stress_mpa=1.0,
    )
    projection = classify_mode_shape(
        nodes=raw.nodes_old,
        elements=raw.elements_old,
        properties=raw.properties_old,
        mesh=mesh,
        mechanics=mechanics,
        half_wavelength_mm=945.1687334,
        mode_shape=raw.shapes[0, 0],
        options=ClassicalBasisOptions(),
    )
    return float(raw.curve[0, 0]), projection


def test_modal_classification_is_translation_and_mirror_invariant() -> None:
    design_input = make_design_input(
        family=SectionFamily.C_LIPPED,
        web_mm=120.0,
        flange_1_mm=80.0,
        flange_2_mm=80.0,
        lip_1_mm=15.0,
        lip_2_mm=15.0,
    )
    section = design_input.resolved_member.section
    original = build_centerline_section(
        section.geometry, section_id=section.catalog_section.section_id
    )
    translated = _transformed_centerline(
        original, offset_x=137.0, offset_y=-419.0
    )
    mirrored = _transformed_centerline(original, mirror_x=True)

    reference_load, reference = _projection(original)
    translated_load, translated_result = _projection(translated)
    mirrored_load, mirrored_result = _projection(mirrored)

    assert translated_load == pytest.approx(reference_load, rel=1.0e-11)
    assert mirrored_load == pytest.approx(reference_load, rel=1.0e-9)
    assert (
        translated_result.participation.global_percent,
        translated_result.participation.distortional_percent,
        translated_result.participation.local_percent,
        translated_result.participation.other_percent,
    ) == pytest.approx(
        (
            reference.participation.global_percent,
            reference.participation.distortional_percent,
            reference.participation.local_percent,
            reference.participation.other_percent,
        ),
        abs=3.0e-4,
    )
    assert (
        mirrored_result.participation.global_percent,
        mirrored_result.participation.distortional_percent,
        mirrored_result.participation.local_percent,
        mirrored_result.participation.other_percent,
    ) == pytest.approx(
        (
            reference.participation.global_percent,
            reference.participation.distortional_percent,
            reference.participation.local_percent,
            reference.participation.other_percent,
        ),
        abs=3.0e-4,
    )


def test_pycufsm_imports_are_confined_to_the_adapter_package() -> None:
    source_root = ROOT / "src/cfs_design"
    offenders: list[Path] = []
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports_pycufsm = any(
            (
                isinstance(node, ast.Import)
                and any(alias.name == "pycufsm" or alias.name.startswith("pycufsm.") for alias in node.names)
            )
            or (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (node.module == "pycufsm" or node.module.startswith("pycufsm."))
            )
            for node in ast.walk(tree)
        )
        if imports_pycufsm and "pycufsm_adapter" not in path.parts:
            offenders.append(path)
    assert offenders == []


def test_reproducible_dependency_versions_are_pinned() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert '"pycufsm==0.2.0"' in pyproject
    assert '"numpy==2.2.6"' in pyproject
    assert "pyCUFSM 0.2.0" in notices
    assert "AFL-3.0" in notices
    assert "LGPL" not in notices
