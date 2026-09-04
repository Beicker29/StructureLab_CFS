"""Raw pyCUFSM 0.2.0 calls confined to the adapter boundary."""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from math import radians

import numpy as np
from pycufsm import helpers, strip_new

from cfs_design.core.exceptions import ConfigurationError, ValidationError
from cfs_design.mechanics.sections import ResolvedSectionMechanics

from ..models import FSMMesh, SolverProvenance


PYCUFSM_VERSION = "0.2.0"
NUMPY_VERSION = "2.2.6"
ADAPTER_VERSION = "M9A-1"


@dataclass(frozen=True, slots=True)
class RawSolverRun:
    curve: np.ndarray
    shapes: np.ndarray
    lengths: np.ndarray
    nodes_old: np.ndarray
    elements_old: np.ndarray
    properties_old: np.ndarray


def solver_provenance() -> SolverProvenance:
    """Validate and return exact released-artifact provenance."""

    try:
        pycufsm_version = version("pycufsm")
        numpy_version = version("numpy")
        scipy_version = version("scipy")
    except PackageNotFoundError as exc:
        raise ConfigurationError(f"missing M9A solver dependency: {exc.name}") from exc
    if pycufsm_version != PYCUFSM_VERSION:
        raise ConfigurationError(
            f"M9A requires pycufsm=={PYCUFSM_VERSION}; found {pycufsm_version}"
        )
    if numpy_version != NUMPY_VERSION:
        raise ConfigurationError(
            f"M9A requires numpy=={NUMPY_VERSION}; found {numpy_version}"
        )
    return SolverProvenance(
        package="pycufsm",
        version=pycufsm_version,
        license="AFL-3.0",
        pypi_identity=f"pycufsm=={pycufsm_version}",
        upstream_repository="https://github.com/ClearCalcs/pyCUFSM",
        release_identity="v0.2.0 / PyPI 0.2.0",
        numpy_version=numpy_version,
        scipy_version=scipy_version,
        adapter_version=ADAPTER_VERSION,
    )


def _section_properties(
    mechanics: ResolvedSectionMechanics,
) -> dict[str, float | None]:
    gross = mechanics.gross
    advanced = mechanics.advanced
    return {
        "A": gross.a_mm2,
        "cx": gross.x_bar_mm,
        "cy": gross.y_bar_mm,
        "Ixx": gross.ix_mm4,
        "Iyy": gross.iy_mm4,
        "Ixy": gross.ixy_mm4,
        "phi": radians(gross.theta_p_deg),
        "I11": gross.i1_mm4,
        "I22": gross.i2_mm4,
        "J": gross.j_mm4,
        "x0": gross.x_bar_mm + advanced.x0_mm,
        "y0": gross.y_bar_mm + advanced.y0_mm,
        "Cw": advanced.cw_mm6,
        "B1": 0.0,
        "B2": 0.0,
        "wn": None,
    }


def run_unconstrained(
    *,
    mesh: FSMMesh,
    mechanics: ResolvedSectionMechanics,
    elastic_modulus_mpa: float,
    poisson_ratio: float,
    half_wavelengths_mm: tuple[float, ...],
    eigenvalue_count: int,
    reference_stress_mpa: float,
) -> RawSolverRun:
    """Run only the unconstrained simply-supported pyCUFSM eigensolver."""

    solver_provenance()
    if eigenvalue_count < 1:
        raise ValidationError("eigenvalue_count must be positive")
    if not half_wavelengths_mm or any(value <= 0.0 for value in half_wavelengths_mm):
        raise ValidationError("half_wavelengths_mm must contain positive values")
    if tuple(sorted(set(half_wavelengths_mm))) != half_wavelengths_mm:
        raise ValidationError("half_wavelengths_mm must be strictly increasing")
    if elastic_modulus_mpa <= 0.0 or not 0.0 < poisson_ratio < 0.5:
        raise ValidationError("invalid isotropic elastic material properties")
    if reference_stress_mpa <= 0.0:
        raise ValidationError("reference_stress_mpa must be positive")

    material_name = "STRUCTURELAB_MATERIAL"
    properties = {
        material_name: {"E": elastic_modulus_mpa, "nu": poisson_ratio}
    }
    nodes = [
        [node.x_mm, node.y_mm, reference_stress_mpa] for node in mesh.nodes
    ]
    elements = [
        {
            "nodes": "all",
            "t": mesh.strips[0].thickness_mm,
            "mat": material_name,
        }
    ]
    section_properties = _section_properties(mechanics)
    _, curve, shapes, _, returned_lengths = strip_new(
        props=properties,
        nodes=nodes,
        elements=elements,
        sect_props=section_properties,
        lengths=half_wavelengths_mm,
        analysis_config={"B_C": "S-S", "n_eigs": eigenvalue_count},
        cfsm_config=None,
    )
    converted = helpers.inputs_new_to_old(
        props=properties,
        nodes=nodes,
        elements=elements,
        lengths=half_wavelengths_mm,
    )
    properties_old, nodes_old, elements_old = converted[:3]
    curve_array = np.asarray(curve, dtype=float)
    shapes_array = np.asarray(shapes, dtype=float)
    lengths_array = np.asarray(returned_lengths, dtype=float)
    expected_shape = (len(half_wavelengths_mm), eigenvalue_count)
    if curve_array.shape != expected_shape:
        raise ValidationError(
            f"pyCUFSM curve shape {curve_array.shape} differs from {expected_shape}"
        )
    if shapes_array.shape != (
        len(half_wavelengths_mm),
        eigenvalue_count,
        4 * len(mesh.nodes),
    ):
        raise ValidationError("pyCUFSM returned an unexpected eigenvector shape")
    if not np.all(np.isfinite(curve_array)) or np.any(curve_array <= 0.0):
        raise ValidationError("pyCUFSM returned non-positive or non-finite eigenvalues")
    if not np.all(np.isfinite(shapes_array)):
        raise ValidationError("pyCUFSM returned non-finite eigenvectors")
    return RawSolverRun(
        curve=curve_array,
        shapes=shapes_array,
        lengths=lengths_array,
        nodes_old=np.asarray(nodes_old, dtype=float),
        elements_old=np.asarray(elements_old, dtype=float),
        properties_old=np.asarray(properties_old, dtype=float),
    )


__all__ = [
    "ADAPTER_VERSION",
    "NUMPY_VERSION",
    "PYCUFSM_VERSION",
    "RawSolverRun",
    "run_unconstrained",
    "solver_provenance",
]
