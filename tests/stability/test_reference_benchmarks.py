"""Executable M9A parity tests against recorded official CUFSM outputs."""

from dataclasses import fields, is_dataclass, replace
import json
from pathlib import Path

import pytest

from cfs_design.domain import SectionFamily
from cfs_design.stability import (
    BucklingModeFamily,
    ClassificationPolicy,
    ClassificationStatus,
    ElasticBucklingAnalysisConfig,
    ElasticBucklingResult,
    ModeParticipation,
    ReviewReason,
    analyze_elastic_buckling,
    classify_with_evidence,
    modal_assurance_criterion,
)
from tests.design.ewm.conftest import make_design_input


ROOT = Path(__file__).resolve().parents[2]


def _reference() -> dict:
    return json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_c120x80x15x1.json").read_text(
            encoding="utf-8"
        )
    )


def _additional_classical_reference() -> dict:
    return json.loads(
        (
            ROOT
            / "validation/m9a/official_cufsm_v566_classical_additional.json"
        ).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def official_result() -> ElasticBucklingResult:
    reference = _reference()
    geometry = reference["geometry_mm"]
    design_input = make_design_input(
        family=SectionFamily.C_LIPPED,
        web_mm=geometry["web"],
        flange_1_mm=geometry["flange_1"],
        flange_2_mm=geometry["flange_2"],
        lip_1_mm=geometry["lip_1"],
        lip_2_mm=geometry["lip_2"],
    )
    material = replace(
        design_input.resolved_member.material,
        e_mpa=reference["material"]["E_mpa"],
        nu=reference["material"]["nu"],
    )
    design_input = replace(
        design_input,
        resolved_member=replace(design_input.resolved_member, material=material),
    )
    return analyze_elastic_buckling(
        design_input,
        ElasticBucklingAnalysisConfig(
            half_wavelengths_mm=tuple(
                point["half_wavelength_mm"] for point in reference["points"]
            ),
            target_strip_width_mm=geometry["maximum_strip_width"],
            eigenvalue_count=1,
            perform_mesh_convergence=False,
            perform_wavelength_refinement=False,
        ),
    )


def test_raw_unconstrained_solver_matches_official_matlab_cufsm(
    official_result: ElasticBucklingResult,
) -> None:
    reference = _reference()
    for tracked, expected in zip(official_result.tracked_modes, reference["points"]):
        assert tracked.half_wavelength_mm == pytest.approx(
            expected["half_wavelength_mm"], rel=1.0e-10
        )
        assert tracked.load_factor == pytest.approx(
            expected["unconstrained_load_factor"], rel=1.0e-7
        )


def test_structurelab_classical_participation_matches_official_matlab(
    official_result: ElasticBucklingResult,
) -> None:
    reference = _reference()
    for tracked, expected in zip(official_result.tracked_modes, reference["points"]):
        actual = tracked.classification.participation
        assert (
            actual.global_percent,
            actual.distortional_percent,
            actual.local_percent,
            actual.other_percent,
        ) == pytest.approx(expected["classical_percent"], abs=1.0e-3)
        assert tracked.classification.reconstruction_error < 1.0e-12


@pytest.mark.parametrize("case_index", (0, 1))
def test_additional_sharp_c_classical_benchmarks_match_matlab(
    case_index: int,
) -> None:
    case = _additional_classical_reference()["cases"][case_index]
    geometry = case["geometry_mm"]
    family = (
        SectionFamily.C_LIPPED
        if case["family"] == "C_LIPPED"
        else SectionFamily.C_UNLIPPED
    )
    design_input = make_design_input(
        family=family,
        web_mm=geometry["web"],
        flange_1_mm=geometry["flange_1"],
        flange_2_mm=geometry["flange_2"],
        lip_1_mm=geometry.get("lip_1", 10.0),
        lip_2_mm=geometry.get("lip_2", 10.0),
    )
    design_input = replace(
        design_input,
        resolved_member=replace(
            design_input.resolved_member,
            material=replace(
                design_input.resolved_member.material, e_mpa=210000.0, nu=0.3
            ),
        ),
    )
    result = analyze_elastic_buckling(
        design_input,
        ElasticBucklingAnalysisConfig(
            half_wavelengths_mm=tuple(
                item["half_wavelength_mm"] for item in case["points"]
            ),
            target_strip_width_mm=geometry["maximum_strip_width"],
            eigenvalue_count=1,
            perform_mesh_convergence=False,
            perform_wavelength_refinement=False,
        ),
    )

    for tracked, expected in zip(result.tracked_modes, case["points"]):
        participation = tracked.classification.participation
        actual_percent = (
            participation.global_percent,
            participation.distortional_percent,
            participation.local_percent,
            participation.other_percent,
        )
        actual_dominant = max(
            participation.structural(), key=lambda item: item[1]
        )[0].value
        assert tracked.load_factor == pytest.approx(
            expected["load_factor"], rel=1.0e-7
        )
        assert actual_percent == pytest.approx(
            expected["matlab_percent"], abs=0.01
        )
        assert actual_dominant == expected["dominant_family"]
        assert tracked.classification.reconstruction_error < 1.0e-12


def test_raw_mode_shapes_have_unit_mac_with_official_matlab_reference(
    official_result: ElasticBucklingResult,
) -> None:
    reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_mode_shapes.json").read_text(
            encoding="utf-8"
        )
    )
    by_wavelength = {
        tracked.half_wavelength_mm: tracked for tracked in official_result.tracked_modes
    }
    node_count = len(official_result.mesh.nodes)
    for item in reference["shapes"]:
        official = item["mode"]
        mapped = [0.0] * len(official)
        for old_node in range(node_count):
            new_node = node_count - 1 - old_node
            mapped[2 * new_node : 2 * new_node + 2] = official[
                2 * old_node : 2 * old_node + 2
            ]
            mapped[
                2 * node_count + 2 * new_node : 2 * node_count + 2 * new_node + 2
            ] = official[
                2 * node_count + 2 * old_node : 2 * node_count + 2 * old_node + 2
            ]
        tracked = by_wavelength[item["half_wavelength_mm"]]
        assert modal_assurance_criterion(tracked.normalized_eigenvector, mapped) > (
            1.0 - 1.0e-12
        )


def test_classical_and_fcfsm_references_agree_for_clear_modes(
    official_result: ElasticBucklingResult,
) -> None:
    expected_families = {
        20.0: BucklingModeFamily.LOCAL,
        70.2500864072: BucklingModeFamily.LOCAL,
        945.1687334: BucklingModeFamily.DISTORTIONAL,
        3466.89420016: BucklingModeFamily.GLOBAL,
        10240.0: BucklingModeFamily.GLOBAL,
    }
    for tracked in official_result.tracked_modes:
        for wavelength, family in expected_families.items():
            if tracked.half_wavelength_mm == pytest.approx(wavelength):
                assert tracked.classification.dominant_family is family

    transition = official_result.tracked_modes[2]
    assert transition.classification.dominant_family is BucklingModeFamily.MIXED
    assert ReviewReason.LOCAL_DISTORTIONAL_INTERACTION in (
        transition.classification.review_reasons
    )


def test_second_official_fcfsm_example_is_preserved_as_reference_only() -> None:
    reference = json.loads(
        (
            ROOT
            / "validation/m9a/official_cufsm_v566_fcfsm_curved_c200x90x20x2.json"
        ).read_text(encoding="utf-8")
    )
    assert reference["reference_kind"] == "FCFSM_REFERENCE"
    assert "outside" in reference["software_support_note"]
    assert max(reference["points"][0]["fcfsm_percent"][:3]) == pytest.approx(
        reference["points"][0]["fcfsm_percent"][2]
    )
    assert max(reference["points"][3]["fcfsm_percent"][:3]) == pytest.approx(
        reference["points"][3]["fcfsm_percent"][1]
    )
    assert max(reference["points"][-1]["fcfsm_percent"][:3]) == pytest.approx(
        reference["points"][-1]["fcfsm_percent"][0]
    )


def test_full_official_fcfsm_critical_validation_meets_acceptance_policy() -> None:
    reference = json.loads(
        (
            ROOT
            / "validation/m9a/official_cufsm_v566_fcfsm_critical_validation.json"
        ).read_text(encoding="utf-8")
    )
    families = reference["families"]
    assert families["LOCAL"]["acceptance"] == "VALIDATED"
    assert families["DISTORTIONAL"]["acceptance"] == "PARTIALLY_VALIDATED"
    assert families["GLOBAL"]["acceptance"] == "VALIDATED"
    for family in families.values():
        assert abs(family["load_factor_difference_percent"]) < 5.0
        assert abs(family["half_wavelength_difference_percent"]) < 2.0
        assert family["critical_mode_shape_mac"] > 0.99
        region = family["critical_region"]
        differences = [
            abs(actual / official - 1.0) * 100.0
            for actual, official in zip(
                region["structurelab_curve"], region["official_curve"]
            )
        ]
        assert max(differences) == pytest.approx(
            family["critical_region_maximum_difference_percent"], rel=1.0e-6
        )

    interaction = reference["interaction_evidence"]
    assert interaction["structurelab_disposition"] == (
        "ENGINEERING_REVIEW_REQUIRED"
    )
    assert "LOCAL_DISTORTIONAL_INTERACTION" in interaction["review_reasons"]
    assert "REFERENCE_DISAGREEMENT" in interaction["review_reasons"]


def test_pycufsm_capability_matrix_keeps_constrained_failures_separate() -> None:
    audit = json.loads(
        (
            ROOT / "validation/m9a/pycufsm_020_cfsm_capability_audit.json"
        ).read_text(encoding="utf-8")
    )
    matrix = audit["capability_matrix"]
    assert matrix["unconstrained_fsm"]["status"] == "VALIDATED"
    for family in ("LOCAL", "DISTORTIONAL", "GLOBAL"):
        orth_1 = matrix["constrained_cfsm_orth_1"][family]
        assert orth_1["status"] == "NOT_VALIDATED"
        assert abs(orth_1["load_factor_difference_percent"]) > 5.0
        assert matrix["constrained_cfsm_orth_2"][family] == "SOFTWARE_BLOCKED"
    assert "not generalized" in matrix["constrained_cfsm_orth_2"][
        "disposition"
    ]


def test_manual_dsm_guide_points_are_engineering_reference_cases() -> None:
    manual = json.loads(
        (ROOT / "validation/m9a/engineering_reference_cases.json").read_text(
            encoding="utf-8"
        )
    )
    for case in manual["cases"]:
        participation = ModeParticipation(*case["classical_percent"])
        result = classify_with_evidence(
            participation,
            0.0,
            policy=ClassificationPolicy(),
            previous_participation=participation,
            next_participation=participation,
            mac_to_previous=1.0,
            mac_to_next=1.0,
            mesh_converged=True,
            wavelength_converged=True,
        )
        assert result.status.value == case["required_workflow_status"]
        assert result.dominant_family is BucklingModeFamily.MIXED
        assert case["structurelab_unconstrained_load_factor"] == pytest.approx(
            case["unconstrained_load_factor"], rel=1.0e-7
        )
        assert case["structurelab_mode_shape_mac"] > 0.999999999999
        assert case["required_workflow_status"] == "ENGINEERING_REVIEW_REQUIRED"
        assert case["review_reasons"]


def _walk(value):
    yield value
    if is_dataclass(value):
        for field in fields(value):
            yield from _walk(getattr(value, field.name))
    elif isinstance(value, (tuple, list, dict)):
        children = value.values() if isinstance(value, dict) else value
        for child in children:
            yield from _walk(child)


def test_no_raw_pycufsm_or_numpy_objects_escape_the_adapter(
    official_result: ElasticBucklingResult,
) -> None:
    for value in _walk(official_result):
        module = type(value).__module__
        assert not module.startswith("numpy")
        assert not module.startswith("pycufsm")


def test_solver_and_reference_provenance_are_exact(
    official_result: ElasticBucklingResult,
) -> None:
    assert official_result.solver_provenance.version == "0.2.0"
    assert official_result.solver_provenance.license == "AFL-3.0"
    assert official_result.solver_provenance.numpy_version == "2.2.6"
    assert {
        item.reference_kind.value for item in official_result.matlab_validation_provenance
    } == {"CLASSICAL_CFSM_REFERENCE", "FCFSM_REFERENCE"}
    manifest = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_source_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["release"] == "v5.66"
    assert set(manifest["files"]) == {
        "analysis/cFSM/classify.m",
        "analysis/cFSM/base_column.m",
        "analysis/cFSM/base_update.m",
            "analysis/cFSM/mode_class.m",
            "analysis/stripmain.m",
            "analysis/fcFSM/SecAnal_fcFSM.m",
        "analysis/fcFSM/stripmain_fcFSM.m",
    }
    assert len(manifest["runtime_compatibility_shims"]) == 2
    assert all(
        "API spelling only" in item["effect"]
        for item in manifest["runtime_compatibility_shims"]
    )


def test_unlipped_c_is_supported_as_an_unconstrained_modal_case() -> None:
    result = analyze_elastic_buckling(
        make_design_input(family=SectionFamily.C_UNLIPPED),
        ElasticBucklingAnalysisConfig(
            half_wavelengths_mm=(20.0, 60.0, 200.0, 800.0, 3000.0),
            target_strip_width_mm=20.0,
            eigenvalue_count=1,
            perform_mesh_convergence=False,
            perform_wavelength_refinement=False,
        ),
    )
    assert result.mesh.section_id == "SYN_C_UNLIPPED"
    assert len(result.tracked_modes) == 5
    assert result.engineering_selection is None


def test_clear_local_minimum_passes_mesh_and_wavelength_acceptance_gates() -> None:
    design_input = make_design_input(
        family=SectionFamily.C_LIPPED,
        web_mm=120.0,
        flange_1_mm=80.0,
        flange_2_mm=80.0,
        lip_1_mm=15.0,
        lip_2_mm=15.0,
    )
    material = replace(design_input.resolved_member.material, e_mpa=210000.0)
    design_input = replace(
        design_input,
        resolved_member=replace(design_input.resolved_member, material=material),
    )
    result = analyze_elastic_buckling(
        design_input,
        ElasticBucklingAnalysisConfig(
            half_wavelengths_mm=(70.0, 80.0, 100.0, 105.0, 110.0, 120.0, 130.0),
            target_strip_width_mm=10.0,
            reference_strip_width_mm=7.5,
            eigenvalue_count=1,
            perform_mesh_convergence=True,
        ),
    )

    assert len(result.accepted_results) == 1
    candidate = result.accepted_results[0]
    assert candidate.family is BucklingModeFamily.LOCAL
    assert candidate.half_wavelength_mm == 100.0
    assert candidate.mesh_convergence.converged is True
    assert candidate.wavelength_convergence.converged is True
    assert candidate.mesh_convergence.family_agreement is True
    assert candidate.mesh_convergence.mode_shape_mac > 0.99
    assert candidate.wavelength_convergence.family_agreement is True
    assert candidate.wavelength_convergence.mode_shape_mac > 0.99
    assert candidate.classification.review_reasons == ()
    assert candidate.dsm_input_eligible is True
    assert result.local_result is candidate
    assert result.distortional_result is None
    assert result.wavelength_search.refinement_steps
    assert result.wavelength_search.boundary_resolution_satisfied is True


def test_recorded_production_mesh_and_wavelength_study_passes_all_gates() -> None:
    study = json.loads(
        (ROOT / "validation/m9a/mesh_wavelength_convergence.json").read_text(
            encoding="utf-8"
        )
    )
    comparison = study["mesh_study"]["practical_vs_reference"]
    for family in ("LOCAL", "DISTORTIONAL"):
        evidence = comparison[family]
        assert evidence["stress_difference_percent"] < 0.5
        assert evidence["half_wavelength_difference_percent"] < 1.0
        assert evidence["dominant_family_agreement"] is True
        assert evidence["shared_M3_vertex_mode_shape_mac"] > 0.99
    assert study["mesh_study"]["finer_mesh_limit"]["status"] == (
        "NOT_VALIDATED"
    )
    assert study["wavelength_study"]["adaptive_search"][
        "boundary_resolution_satisfied_for_LOCAL_and_DISTORTIONAL"
    ] is True
    for family in ("LOCAL", "DISTORTIONAL"):
        evidence = study["wavelength_study"][family]
        assert evidence["status"] == "AUTOMATIC_ACCEPTED"
        assert evidence["successive_grid_stress_change_ratio"] <= 0.005
        assert evidence["successive_grid_wavelength_change_ratio"] <= 0.01
        assert evidence["dominant_family_agreement"] is True
        assert evidence["mode_shape_mac"] >= 0.90


def test_falling_section_mode_boundary_expands_the_wavelength_range() -> None:
    result = analyze_elastic_buckling(
        make_design_input(
            family=SectionFamily.C_LIPPED,
            web_mm=120.0,
            flange_1_mm=80.0,
            flange_2_mm=80.0,
            lip_1_mm=15.0,
            lip_2_mm=15.0,
        ),
        ElasticBucklingAnalysisConfig(
            half_wavelengths_mm=(20.0, 30.0, 40.0),
            target_strip_width_mm=10.0,
            eigenvalue_count=1,
            perform_mesh_convergence=False,
            perform_wavelength_refinement=True,
            wavelength_refinement_limit=4,
            boundary_expansion_limit=4,
        ),
    )

    assert max(result.wavelength_search.evaluated_half_wavelengths_mm) > 40.0
    assert any(
        step.upper_boundary_expanded
        for step in result.wavelength_search.refinement_steps
    )


def test_m10b1_release_audit_preserves_exact_reproduction_decision() -> None:
    audit = json.loads(
        (
            ROOT
            / "validation/m10b/pycufsm_release_compatibility_audit.json"
        ).read_text(encoding="utf-8")
    )
    releases = {
        item["version"]: item for item in audit["official_releases_tested"]
    }
    assert set(releases) == {
        "0.1.0",
        "0.1.1",
        "0.1.2",
        "0.1.3",
        "0.1.4",
        "0.1.5",
        "0.1.6",
        "0.1.7",
        "0.2.0",
    }
    for version in ("0.1.0", "0.1.1", "0.1.2", "0.1.3", "0.1.4", "0.1.5", "0.1.6", "0.1.7"):
        release = releases[version]
        assert release["complete_145_wavelength_analysis"]["succeeds"] is True
        assert release["exactly_10_modes_at_every_wavelength"] is True
        assert set(release["returned_mode_count_at_every_wavelength"]) == {10}
        assert release["index_132"]["mode_count"] == 10
        assert release["determinism"]["deterministic"] is True

    production = releases["0.2.0"]
    assert production["complete_145_wavelength_analysis"]["succeeds"] is False
    assert production["index_132"]["mode_count"] == 9
    assert production["returned_mode_count_at_every_wavelength"] == (
        [10] * 131 + [9] * 11 + [8] * 2 + [7]
    )
    assert audit["root_cause"]["categories"]["eigenvalue_filtering"] == (
        "CONFIRMED_PRIMARY_CAUSE"
    )
    assert audit["candidate"]["release"] == "0.1.7"
    assert audit["candidate"]["candidate_dependency_upgrade"] is False
    assert audit["candidate"]["adopted"] is False
    assert audit["controls"]["production_code_modified"] is False
    assert audit["controls"]["production_dependency_modified"] is False
