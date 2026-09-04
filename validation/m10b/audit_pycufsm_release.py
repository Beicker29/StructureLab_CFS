"""Run the M10B.1 release audit in one isolated pyCUFSM environment.

This is validation tooling, not a production adapter.  It deliberately calls
the published low-level ``pycufsm.fsm.strip`` API so the same legacy input
contract can be exercised across every official release from 0.1.0 to 0.2.0.
"""

from __future__ import annotations

import argparse
from importlib.metadata import metadata, version
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
import scipy
from scipy.io import loadmat
from pycufsm.fsm import strip


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_RUNTIME_CAPTURE = (
    ROOT
    / "validation/m10b/official_matlab_cufsm_v566_c120x80x15x1_full.mat"
)
N_EIGS = 10
INDEX_132_ZERO_BASED = 131


def _inputs(lengths: np.ndarray) -> tuple[Any, ...]:
    coordinates = (
        (80.0, 15.0),
        (80.0, 0.0),
        (60.0, 0.0),
        (40.0, 0.0),
        (20.0, 0.0),
        (0.0, 0.0),
        (0.0, 20.0),
        (0.0, 40.0),
        (0.0, 60.0),
        (0.0, 80.0),
        (0.0, 100.0),
        (0.0, 120.0),
        (20.0, 120.0),
        (40.0, 120.0),
        (60.0, 120.0),
        (80.0, 120.0),
        (80.0, 105.0),
    )
    elastic_modulus = 210000.0
    poisson_ratio = 0.3
    props = np.array(
        [[0, elastic_modulus, elastic_modulus, poisson_ratio, poisson_ratio,
          elastic_modulus / (2.0 * (1.0 + poisson_ratio))]],
        dtype=float,
    )
    nodes = np.array(
        [[index, x, y, 1, 1, 1, 1, 1.0]
         for index, (x, y) in enumerate(coordinates)],
        dtype=float,
    )
    elements = np.array(
        [[index, index, index + 1, 1.0, 0]
         for index in range(len(coordinates) - 1)],
        dtype=float,
    )
    gbt_con = {
        "glob": [0],
        "dist": [0],
        "local": [0],
        "other": [0],
        "o_space": 1,
        "couple": 1,
        "orth": 2,
        "norm": 1,
    }
    # Not read by pyCUFSM when every cFSM selector is zero.  The complete
    # public contract is nevertheless supplied, without invoking CUTWP.
    sect_props = {
        "A": 1.0,
        "cx": 0.0,
        "cy": 0.0,
        "Ixx": 1.0,
        "Iyy": 1.0,
        "Ixy": 0.0,
        "phi": 0.0,
        "I11": 1.0,
        "I22": 1.0,
        "J": 1.0,
        "x0": 0.0,
        "y0": 0.0,
        "Cw": 1.0,
        "B1": 0.0,
        "B2": 0.0,
        "wn": np.array([]),
    }
    return (
        props,
        nodes,
        elements,
        lengths,
        np.array([]),
        np.array([]),
        gbt_con,
        "S-S",
        np.ones((len(lengths), 1)),
        N_EIGS,
        sect_props,
    )


def _solve(lengths: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    signature, curve, shapes = strip(*_inputs(lengths))
    return np.asarray(signature), np.asarray(curve), np.asarray(shapes)


def _exception(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def _mode_count(curve: np.ndarray) -> int:
    if curve.ndim == 1:
        return int(curve.size)
    return int(curve.shape[-1])


def _first_mode(shapes: np.ndarray, mode_count: int) -> np.ndarray:
    squeezed = _shape_matrix(shapes, mode_count)
    return squeezed[:, 0]


def _shape_matrix(shapes: np.ndarray, mode_count: int) -> np.ndarray:
    squeezed = np.squeeze(shapes, axis=0)
    if squeezed.shape == (68, mode_count):
        return squeezed
    if squeezed.shape == (mode_count, 68):
        return squeezed.T
    raise ValueError(f"unrecognized single-wavelength shape {shapes.shape}")


def _mac(left: np.ndarray, right: np.ndarray) -> float:
    numerator = abs(np.vdot(left, right)) ** 2
    denominator = float(np.vdot(left, left).real * np.vdot(right, right).real)
    return float(numerator / denominator)


def _reference_checks(
    lengths: np.ndarray,
    first_values: list[float | None],
    first_modes: dict[int, np.ndarray],
) -> dict[str, Any]:
    curve_reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_c120x80x15x1.json")
        .read_text(encoding="utf-8")
    )
    mode_reference = json.loads(
        (ROOT / "validation/m9a/official_cufsm_v566_mode_shapes.json")
        .read_text(encoding="utf-8")
    )
    clear_family = {
        20.0: "LOCAL",
        70.2500864072: "LOCAL",
        945.1687334: "DISTORTIONAL",
        3466.89420016: "GLOBAL",
        10240.0: "GLOBAL",
    }
    parity: dict[str, list[dict[str, float]]] = {
        "LOCAL": [],
        "DISTORTIONAL": [],
        "GLOBAL": [],
    }
    for point in curve_reference["points"]:
        target = float(point["half_wavelength_mm"])
        if target not in clear_family:
            continue
        index = int(np.argmin(abs(lengths - target)))
        actual = first_values[index]
        if actual is None:
            continue
        expected = float(point["unconstrained_load_factor"])
        parity[clear_family[target]].append(
            {
                "half_wavelength_mm": float(lengths[index]),
                "actual_load_factor": actual,
                "official_load_factor": expected,
                "relative_difference_percent": (actual / expected - 1.0) * 100.0,
            }
        )
    mac: list[dict[str, float]] = []
    for point in mode_reference["shapes"]:
        target = float(point["half_wavelength_mm"])
        index = int(np.argmin(abs(lengths - target)))
        if index in first_modes:
            mac.append(
                {
                    "half_wavelength_mm": float(lengths[index]),
                    "first_mode_mac": _mac(
                        first_modes[index], np.asarray(point["mode"], dtype=float)
                    ),
                }
            )
    return {"elastic_parity": parity, "mac": mac}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package_metadata = metadata("pycufsm")
    lengths = np.ravel(
        loadmat(OFFICIAL_RUNTIME_CAPTURE, variable_names=["lengths"])[
            "lengths"
        ]
    ).astype(float)
    result: dict[str, Any] = {
        "package": "pycufsm",
        "version": version("pycufsm"),
        "license": package_metadata.get("License"),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "configuration": {
            "node_count": 17,
            "element_count": 16,
            "elastic_modulus_mpa": 210000.0,
            "poisson_ratio": 0.3,
            "boundary_condition": "S-S",
            "longitudinal_terms": [1],
            "half_wavelength_count": 145,
            "first_half_wavelength_mm": float(lengths[0]),
            "last_half_wavelength_mm": float(lengths[-1]),
            "requested_eigenvalue_count": N_EIGS,
        },
    }
    started = time.perf_counter()
    try:
        signature, curve, shapes = _solve(lengths)
        result["complete_analysis"] = {
            "succeeds": True,
            "signature_shape": list(signature.shape),
            "curve_shape": list(curve.shape),
            "shapes_shape": list(shapes.shape),
            "exactly_10_modes": curve.shape == (145, 10),
        }
    except BaseException as exc:  # validation evidence must retain upstream failure
        result["complete_analysis"] = {
            "succeeds": False,
            "exception": _exception(exc),
            "exactly_10_modes": False,
        }

    counts: list[int | None] = []
    first_values: list[float | None] = []
    errors: list[dict[str, Any]] = []
    first_modes: dict[int, np.ndarray] = {}
    for index, length in enumerate(lengths):
        try:
            _, curve, shapes = _solve(np.array([length]))
            count = _mode_count(curve)
            counts.append(count)
            first_values.append(float(np.ravel(curve)[0]))
            if index in {0, 89, 144}:
                first_modes[index] = _first_mode(shapes, count)
        except BaseException as exc:
            counts.append(None)
            first_values.append(None)
            errors.append(
                {"index_1_based": index + 1, "half_wavelength_mm": float(length),
                 "exception": _exception(exc)}
            )

    # A second complete independent per-wavelength pass tests output-shape and
    # first-eigenvalue determinism even when the public batched API fails.
    second_counts: list[int | None] = []
    second_first_values: list[float | None] = []
    for length in lengths:
        try:
            _, curve, _ = _solve(np.array([length]))
            second_counts.append(_mode_count(curve))
            second_first_values.append(float(np.ravel(curve)[0]))
        except BaseException:
            second_counts.append(None)
            second_first_values.append(None)
    comparable = [
        (first, second)
        for first, second in zip(first_values, second_first_values)
        if first is not None and second is not None
    ]
    deterministic_values = all(
        np.isclose(first, second, rtol=1.0e-12, atol=1.0e-12)
        for first, second in comparable
    )
    result["per_wavelength_analysis"] = {
        "all_succeed": not errors,
        "mode_counts": counts,
        "minimum_mode_count": min(item for item in counts if item is not None),
        "maximum_mode_count": max(item for item in counts if item is not None),
        "exactly_10_at_every_wavelength": all(item == 10 for item in counts),
        "errors": errors,
    }
    _, index_curve, index_shapes = _solve(
        np.array([lengths[INDEX_132_ZERO_BASED]])
    )
    index_eigenvalues = np.ravel(index_curve)
    index_modes = _shape_matrix(index_shapes, len(index_eigenvalues))
    official_mat = loadmat(
        OFFICIAL_RUNTIME_CAPTURE,
        variable_names=["curve", "shapes"],
    )
    official_eigenvalues = np.asarray(
        official_mat["curve"].ravel()[INDEX_132_ZERO_BASED]
    )[:, 1]
    official_modes = np.asarray(
        official_mat["shapes"].ravel()[INDEX_132_ZERO_BASED]
    )
    compared_mode_count = min(len(index_eigenvalues), len(official_eigenvalues))
    result["index_132"] = {
        "index_1_based": 132,
        "index_0_based": INDEX_132_ZERO_BASED,
        "half_wavelength_mm": float(lengths[INDEX_132_ZERO_BASED]),
        "mode_count": counts[INDEX_132_ZERO_BASED],
        "eigenvalues": index_eigenvalues.tolist(),
        "official_matlab_eigenvalues": official_eigenvalues.tolist(),
        "eigenvalue_relative_difference_percent": [
            (float(index_eigenvalues[index]) / float(official_eigenvalues[index]) - 1.0)
            * 100.0
            for index in range(compared_mode_count)
        ],
        "mode_mac_against_official_matlab": [
            _mac(index_modes[:, index], official_modes[:, index])
            for index in range(compared_mode_count)
        ],
    }
    result["determinism"] = {
        "mode_counts_identical": counts == second_counts,
        "first_eigenvalues_identical_within_rtol_1e-12": deterministic_values,
        "deterministic": counts == second_counts and deterministic_values,
    }
    result.update(_reference_checks(lengths, first_values, first_modes))
    result["elapsed_seconds"] = time.perf_counter() - started
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
