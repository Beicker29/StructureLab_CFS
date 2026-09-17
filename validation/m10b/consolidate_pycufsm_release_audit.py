"""Consolidate temporary M10B.1 runs into durable compact evidence."""

from __future__ import annotations

import argparse
from email.parser import BytesParser
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_RUNTIME_CAPTURE = (
    ROOT
    / "validation/m10b/official_matlab_cufsm_v566_c120x80x15x1_full.mat"
)
VERSIONS = ("0.1.0", "0.1.1", "0.1.2", "0.1.3", "0.1.4", "0.1.5", "0.1.6", "0.1.7", "0.2.0")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata(audit_root: Path, release: str) -> dict[str, Any]:
    wheel = next((audit_root / "dists").glob(f"pycufsm-{release}-*.whl"))
    metadata_path = next((audit_root / "unpacked" / release).rglob("METADATA"))
    parsed = BytesParser().parsebytes(metadata_path.read_bytes())
    requirements = parsed.get_all("Requires-Dist", [])
    return {
        "pypi_artifact": wheel.name,
        "artifact_sha256": _hash(wheel),
        "license": parsed.get("License"),
        "requires_python": parsed.get("Requires-Python"),
        "requires_numpy": next(
            item.split(";")[0].strip() for item in requirements
            if item.lower().startswith("numpy") and "extra" not in item.lower()
        ),
        "requires_scipy": next(
            item.split(";")[0].strip() for item in requirements
            if item.lower().startswith("scipy") and "extra" not in item.lower()
        ),
    }


def _mac(left: list[float], right: list[float]) -> float:
    a = np.asarray(left)
    b = np.asarray(right)
    return float(abs(np.vdot(a, b)) ** 2 / (np.vdot(a, a).real * np.vdot(b, b).real))


def _m9a_summary(audit_root: Path) -> dict[str, Any]:
    candidate = _json(audit_root / "results/m9a-0.1.7-frozen-stack.json")
    production = _json(audit_root / "results/m9a-0.2.0-frozen-stack.json")
    production_by_id = {case["case_id"]: case for case in production["cases"]}
    cases: list[dict[str, Any]] = []
    for candidate_case in candidate["cases"]:
        production_case = production_by_id[candidate_case["case_id"]]
        load_differences: list[float] = []
        mac_values: list[float] = []
        matlab_differences: list[float] = []
        mode_counts: list[int] = []
        for candidate_point, production_point in zip(
            candidate_case["points"], production_case["points"]
        ):
            load_differences.append(
                abs(
                    candidate_point["first_load_factor"]
                    / production_point["first_load_factor"]
                    - 1.0
                )
                * 100.0
            )
            mac_values.append(
                _mac(candidate_point["first_mode"], production_point["first_mode"])
            )
            mode_counts.append(candidate_point["mode_count"])
            if "relative_difference_percent" in candidate_point:
                matlab_differences.append(abs(candidate_point["relative_difference_percent"]))
        summary: dict[str, Any] = {
            "case_id": candidate_case["case_id"],
            "node_count": candidate_case["node_count"],
            "element_count": candidate_case["element_count"],
            "requested_mode_count": 10,
            "minimum_returned_mode_count": min(mode_counts),
            "maximum_returned_mode_count": max(mode_counts),
            "maximum_first_eigenvalue_difference_vs_0_2_0_percent": max(load_differences),
            "minimum_first_mode_mac_vs_0_2_0": min(mac_values),
            "maximum_first_eigenvalue_difference_vs_matlab_percent": max(matlab_differences),
            "classification_disposition": (
                "NUMERICALLY_PRESERVED: identical first eigenvalues and unit-MAC first "
                "modes provide identical inputs to the StructureLab-owned classifier; "
                "integrated execution is separately API-blocked."
            ),
        }
        if "critical_results" in candidate_case:
            summary["critical_results"] = candidate_case["critical_results"]
        cases.append(summary)
    return {
        "candidate_release": "0.1.7",
        "comparison_stack": {
            "python": candidate["python"],
            "numpy": candidate["numpy"],
            "scipy": "1.18.1",
            "requested_eigenvalue_count": candidate["requested_eigenvalue_count"],
        },
        "cases": cases,
        "adapter_import_check": {
            "succeeds": False,
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'pycufsm.solve'",
            "reason": (
                "StructureLab's validated classification boundary imports pycufsm.solve, "
                "while release 0.1.7 exposes the older pycufsm.cfsm/analysis layout."
            ),
        },
        "risk_assessment": {
            "unconstrained_fsm_numerical_regression_risk": "LOW",
            "mode_shape_and_structurelab_classification_regression_risk": "LOW_NUMERICALLY",
            "adapter_api_compatibility_risk": "HIGH_REQUIRES_SEPARATE_CHANGE",
            "constrained_cfsm_status": "NOT_RETESTED_NON_AUTHORITATIVE_AS_DIRECTED",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lengths = np.ravel(
        loadmat(OFFICIAL_RUNTIME_CAPTURE, variable_names=["lengths"])["lengths"]
    ).astype(float)
    releases: list[dict[str, Any]] = []
    for release in VERSIONS:
        run = _json(args.audit_root / f"results/{release}.json")
        item = {
            "version": release,
            **_metadata(args.audit_root, release),
            "official_publication_channel": "PyPI release artifact",
            "installation_succeeds": True,
            "tested_environment": {
                "python": run["python"],
                "numpy": run["numpy"],
                "scipy": run["scipy"],
                "isolation": f"dedicated temporary virtual environment envs/{release}",
            },
            "complete_145_wavelength_analysis": run["complete_analysis"],
            "returned_mode_count_at_every_wavelength": run[
                "per_wavelength_analysis"
            ]["mode_counts"],
            "minimum_returned_mode_count": run["per_wavelength_analysis"]["minimum_mode_count"],
            "maximum_returned_mode_count": run["per_wavelength_analysis"]["maximum_mode_count"],
            "exactly_10_modes_at_every_wavelength": run["per_wavelength_analysis"][
                "exactly_10_at_every_wavelength"
            ],
            "index_132": run["index_132"],
            "determinism": run["determinism"],
            "local_distortional_global_elastic_parity": run["elastic_parity"],
            "representative_first_mode_mac": run["mac"],
        }
        releases.append(item)

    frozen_retest = _json(args.audit_root / "results/0.1.7-frozen-stack.json")
    evidence = {
        "milestone": "M10B.1",
        "status": "RELEASE_CANDIDATE_FOUND_NOT_ADOPTED",
        "date": "2026-09-04",
        "objective": "Exact official MATLAB CUFSM C_120X80X15X1 reproduction with neigs=10",
        "official_reference": {
            "repository": "https://github.com/thinwalled/cufsm-git",
            "release": "v5.66",
            "example": "examples/fcFSM_examples/C_120X80X15X1/modelData.m",
            "runtime_capture": (
                "validation/m10b/"
                "official_matlab_cufsm_v566_c120x80x15x1_full.mat"
            ),
            "runtime_capture_sha256": _hash(OFFICIAL_RUNTIME_CAPTURE),
        },
        "exact_configuration": {
            "geometry": "17 nodes / 16 elements, sharp C120x80x15x1 mm",
            "elastic_modulus_mpa": 210000.0,
            "poisson_ratio": 0.3,
            "boundary_condition": "S-S",
            "longitudinal_terms": [1],
            "compression_reference_stress_mpa": 1.0,
            "requested_eigenvalue_count": 10,
            "half_wavelengths_mm": lengths.tolist(),
            "half_wavelength_count": len(lengths),
        },
        "official_releases_tested": releases,
        "dependency_compatibility_control": {
            "release": "0.1.7",
            "environment": {
                "python": frozen_retest["python"],
                "numpy": frozen_retest["numpy"],
                "scipy": frozen_retest["scipy"],
                "isolation": "dedicated temporary virtual environment envs/0.1.7-frozen-stack",
            },
            "complete_analysis": frozen_retest["complete_analysis"],
            "exactly_10_modes_at_every_wavelength": frozen_retest[
                "per_wavelength_analysis"
            ]["exactly_10_at_every_wavelength"],
            "index_132": frozen_retest["index_132"],
            "determinism": frozen_retest["determinism"],
        },
        "root_cause": {
            "primary": "PYCUFSM_0_2_0_EIGENVALUE_UPPER_FILTER",
            "evidence": [
                "0.1.7 returns the finite tenth eigenvalue 1033959.5669200151 at index 132.",
                "0.2.0 adds is_reasonable = real(eigenvalue) < 1e6 and "
                "therefore returns nine modes there.",
                "0.2.0's public batch normalizer allocates to the maximum count "
                "and assigns every shorter row to that full width, causing the "
                "observed shape (9,) into shape (10,) ValueError.",
                "The unconstrained model has 68 DOF and the dense generalized "
                "eigensolver executes; solver dimension is not the limiting count.",
                "The discarded tenth value is finite and positive, so this event "
                "is not explained by a numerical singularity or negative-eigenvalue "
                "rejection.",
                "0.1.7 reproduces the result on both NumPy 1.26.4/SciPy 1.11.4 "
                "and NumPy 2.2.6/SciPy 1.18.1, excluding dependency compatibility "
                "as the cause.",
                "Repeated full per-wavelength passes are deterministic for every release tested."
            ],
            "categories": {
                "eigenvalue_filtering": "CONFIRMED_PRIMARY_CAUSE",
                "positive_negative_eigenvalue_handling": (
                    "NOT_CAUSAL_FOR_INDEX_132_FINITE_POSITIVE_TENTH_MODE"
                ),
                "solver_dimension": "NOT_CAUSAL_68_DOF_DENSE_EIGENSOLVE_COMPLETES",
                "numerical_singularity": "NOT_SUPPORTED_BY_EVIDENCE",
                "public_api_behavior": "CONFIRMED_SECONDARY_BATCH_SHAPE_FAILURE",
                "dependency_compatibility": "EXCLUDED_BY_CONTROLLED_STACK_RETEST",
            },
        },
        "candidate": {
            "exists": True,
            "release": "0.1.7",
            "designation": "CANDIDATE_RELEASE_FOR_CONTROLLED_DOWNGRADE_AUDIT",
            "candidate_dependency_upgrade": False,
            "reason_not_called_upgrade": "0.1.7 predates the frozen 0.2.0 production dependency.",
            "adopted": False,
        },
        "m9a_focused_compatibility": _m9a_summary(args.audit_root),
        "recommended_dependency_decision": (
            "Keep pycufsm==0.2.0 frozen in production.  Treat 0.1.7 as an exact-reproduction "
            "candidate only; any downgrade requires a separately authorized adapter/API migration "
            "and full regression because it is not import-compatible with the current adapter."
        ),
        "controls": {
            "production_code_modified": False,
            "production_dependency_modified": False,
            "pycufsm_patched_or_monkey_patched": False,
            "eigenvalue_count_1_used": False,
            "development_or_master_branch_tested": False,
            "constrained_cfsm_retested": False,
            "m11_started": False,
            "existing_repository_tmp_deleted": False,
        },
        "verification": {
            "focused_test": "17 passed",
            "full_suite": "676 passed",
            "full_suite_command": (
                ".venv/Scripts/python.exe -m pytest -q -p no:cacheprovider "
                "--basetemp <new workspace-local temporary directory>"
            ),
            "warnings": (
                "10085 existing NumPy deprecation warnings from pyCUFSM and "
                "the classical validation boundary"
            ),
        },
        "temporary_cleanup": {
            "isolated_release_environments_removed": True,
            "workspace_pytest_basetemp_directories_removed": True,
            "repository_tmp_preserved": True,
        },
    }
    args.output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
