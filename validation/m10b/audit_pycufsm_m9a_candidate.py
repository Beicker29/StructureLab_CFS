"""Focused numerical M9A regression probe for an audited pyCUFSM release."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import platform
from typing import Any

import numpy as np
from pycufsm.fsm import strip


ROOT = Path(__file__).resolve().parents[2]
N_EIGS = 10


def _mesh(vertices: list[tuple[float, float]], width: float) -> np.ndarray:
    points: list[np.ndarray] = []
    for start, end in zip(vertices, vertices[1:]):
        start_array = np.asarray(start, dtype=float)
        end_array = np.asarray(end, dtype=float)
        divisions = int(np.ceil(np.linalg.norm(end_array - start_array) / width))
        for index in range(divisions):
            points.append(start_array + (end_array - start_array) * index / divisions)
    points.append(np.asarray(vertices[-1], dtype=float))
    return np.asarray(points)


def _solve(points: np.ndarray, length: float) -> tuple[np.ndarray, np.ndarray]:
    elastic_modulus = 210000.0
    poisson_ratio = 0.3
    props = np.asarray(
        [[0, elastic_modulus, elastic_modulus, poisson_ratio, poisson_ratio,
          elastic_modulus / (2.0 * (1.0 + poisson_ratio))]]
    )
    nodes = np.asarray(
        [[index, x, y, 1, 1, 1, 1, 1.0]
         for index, (x, y) in enumerate(points)]
    )
    elements = np.asarray(
        [[index, index, index + 1, 1.0, 0] for index in range(len(points) - 1)]
    )
    config = {
        "glob": [0], "dist": [0], "local": [0], "other": [0],
        "o_space": 1, "couple": 1, "orth": 2, "norm": 1,
    }
    section = {
        "A": 1.0, "cx": 0.0, "cy": 0.0, "Ixx": 1.0, "Iyy": 1.0,
        "Ixy": 0.0, "phi": 0.0, "I11": 1.0, "I22": 1.0, "J": 1.0,
        "x0": 0.0, "y0": 0.0, "Cw": 1.0, "B1": 0.0, "B2": 0.0,
        "wn": np.array([]),
    }
    _, curve, shapes = strip(
        props, nodes, elements, np.asarray([length]), np.array([]), np.array([]),
        config, "S-S", np.ones((1, 1)), N_EIGS, section,
    )
    curve_array = np.asarray(curve)
    shape_array = np.squeeze(np.asarray(shapes), axis=0)
    mode_count = int(curve_array.shape[-1])
    if shape_array.shape == (4 * len(points), mode_count):
        first_mode = shape_array[:, 0]
    elif shape_array.shape == (mode_count, 4 * len(points)):
        first_mode = shape_array[0, :]
    else:
        raise ValueError(f"unrecognized shape array {shape_array.shape}")
    return np.ravel(curve_array), first_mode


def _point_result(
    points: np.ndarray,
    length: float,
    expected: float | None,
) -> dict[str, Any]:
    curve, mode = _solve(points, length)
    result: dict[str, Any] = {
        "half_wavelength_mm": length,
        "mode_count": int(curve.size),
        "first_load_factor": float(curve[0]),
        "first_mode": mode.tolist(),
    }
    if expected is not None:
        result["official_matlab_load_factor"] = expected
        result["relative_difference_percent"] = (float(curve[0]) / expected - 1.0) * 100.0
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    c120_reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_c120x80x15x1.json")
        .read_text(encoding="utf-8")
    )
    c100_reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_classical_additional.json")
        .read_text(encoding="utf-8")
    )
    critical_reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_fcfsm_critical_validation.json")
        .read_text(encoding="utf-8")
    )

    cases: list[dict[str, Any]] = []
    c120_points = _mesh(
        [(80.0, 15.0), (80.0, 0.0), (0.0, 0.0), (0.0, 120.0),
         (80.0, 120.0), (80.0, 105.0)],
        20.0,
    )
    expected_c120 = {
        float(point["half_wavelength_mm"]): float(point["unconstrained_load_factor"])
        for point in c120_reference["points"]
    }
    c120_lengths = sorted(
        set(expected_c120)
        | {
            float(family["structurelab_critical_half_wavelength_mm"])
            for family in critical_reference["families"].values()
        }
    )
    c120_results = [
        _point_result(c120_points, length, expected_c120.get(length))
        for length in c120_lengths
    ]
    critical: dict[str, Any] = {}
    for family_name, family in critical_reference["families"].items():
        length = float(family["structurelab_critical_half_wavelength_mm"])
        actual = next(
            item["first_load_factor"]
            for item in c120_results
            if item["half_wavelength_mm"] == length
        )
        approved = float(family["structurelab_critical_load_factor"])
        critical[family_name] = {
            "half_wavelength_mm": length,
            "candidate_critical_stress_mpa": actual,
            "approved_m9a_critical_stress_mpa": approved,
            "stress_relative_difference_percent": (actual / approved - 1.0) * 100.0,
            "candidate_critical_load_n": actual * 310.0,
            "approved_m9a_critical_load_n": approved * 310.0,
        }
    cases.append(
        {
            "case_id": "C120X80X15X1",
            "node_count": int(len(c120_points)),
            "element_count": int(len(c120_points) - 1),
            "points": c120_results,
            "critical_results": critical,
        }
    )

    for reference in c100_reference["cases"]:
        geometry = reference["geometry_mm"]
        web = float(geometry["web"])
        flange = float(geometry["flange_1"])
        lip = float(geometry.get("lip_1", 0.0))
        vertices = (
            [(flange, lip), (flange, 0.0), (0.0, 0.0), (0.0, web),
             (flange, web), (flange, web - lip)]
            if lip
            else [(flange, 0.0), (0.0, 0.0), (0.0, web), (flange, web)]
        )
        points = _mesh(vertices, float(geometry["maximum_strip_width"]))
        cases.append(
            {
                "case_id": reference["case_id"],
                "node_count": int(len(points)),
                "element_count": int(len(points) - 1),
                "points": [
                    _point_result(
                        points,
                        float(point["half_wavelength_mm"]),
                        float(point["load_factor"]),
                    )
                    for point in reference["points"]
                ],
            }
        )

    output = {
        "release": version("pycufsm"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "requested_eigenvalue_count": N_EIGS,
        "cases": cases,
    }
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
