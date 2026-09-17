"""Independent classical-cFSM modal decomposition referenced to CUFSM v5.66.

This module re-expresses the published CUFSM mathematical workflow using
StructureLab naming. It intentionally corrects zero-based connectivity defects
identified in pyCUFSM 0.2.0 and does not call pyCUFSM's translated
``mode_class`` implementation.
"""

from dataclasses import dataclass

import numpy as np
from pycufsm.solve import cfsm
from pycufsm.solve.analysis import analysis
from scipy import linalg

from cfs_design.core.exceptions import ValidationError
from cfs_design.mechanics.sections import ResolvedSectionMechanics

from ..models import ClassicalBasisOptions, FSMMesh, ModeParticipation


@dataclass(frozen=True, slots=True)
class ProjectionResult:
    participation: ModeParticipation
    reconstruction_error: float
    basis_condition_number: float
    basis_rank: int
    basis_dimension: int
    mode_counts: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class ClassicalBasisSystem:
    """Adapter-internal matrices used for projection and solver QA."""

    basis: np.ndarray
    stiffness: np.ndarray
    geometric_stiffness: np.ndarray
    mode_counts: tuple[int, int, int, int]


def _corrected_corner_constraints(
    main_nodes: np.ndarray,
    meta_elements: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct corner x/z constraints with explicit direction flags.

    pyCUFSM 0.2.0 tests an element identifier where the original MATLAB
    formulation tests the second endpoint direction. That defect is not
    propagated here.
    """

    geometry = np.zeros((len(meta_elements), 5))
    for index, element in enumerate(meta_elements):
        start = int(element[1])
        end = int(element[2])
        dx = main_nodes[end, 1] - main_nodes[start, 1]
        dy = main_nodes[end, 2] - main_nodes[start, 2]
        width = np.hypot(dx, dy)
        geometry[index] = (
            width,
            1.0 / width,
            np.arctan2(dy, dx),
            dy / width,
            dx / width,
        )

    corner_indexes = [
        index for index, node in enumerate(main_nodes) if node[4] > 1
    ]
    r_x = np.zeros((len(corner_indexes), len(main_nodes)))
    r_z = np.zeros_like(r_x)
    for row_index, node_index in enumerate(corner_indexes):
        node = main_nodes[node_index]
        reference_1 = float(node[5])
        element_1 = int(reference_1)
        direction_1 = int(round((reference_1 - element_1) * 10))

        reference_index = 6
        while reference_index < len(node) and abs(
            np.sin(
                geometry[int(node[reference_index]), 2]
                - geometry[element_1, 2]
            )
        ) < 1.0e-14:
            reference_index += 1
        if reference_index >= len(node):
            raise ValidationError("a corner node lacks two non-collinear references")
        reference_2 = float(node[reference_index])
        element_2 = int(reference_2)
        direction_2 = int(round((reference_2 - element_2) * 10))

        node_1 = int(meta_elements[element_1, direction_1])
        node_2 = node_index
        node_3 = int(meta_elements[element_2, direction_2])
        reciprocal_1, angle_1, sine_1, cosine_1 = geometry[element_1, 1:]
        if direction_1 == 2:
            angle_1 -= np.pi
            sine_1 = -sine_1
            cosine_1 = -cosine_1
        reciprocal_2, angle_2, sine_2, cosine_2 = geometry[element_2, 1:]
        if direction_2 == 1:
            angle_2 -= np.pi
            sine_2 = -sine_2
            cosine_2 = -cosine_2
        determinant = np.sin(angle_2 - angle_1)
        if abs(determinant) < 1.0e-14:
            raise ValidationError("corner constraint is singular")

        r_x[row_index, node_1] = sine_2 * reciprocal_1 / determinant
        r_x[row_index, node_2] = (
            -sine_1 * reciprocal_2 - sine_2 * reciprocal_1
        ) / determinant
        r_x[row_index, node_3] = sine_1 * reciprocal_2 / determinant
        r_z[row_index, node_1] = -cosine_2 * reciprocal_1 / determinant
        r_z[row_index, node_2] = (
            cosine_1 * reciprocal_2 + cosine_2 * reciprocal_1
        ) / determinant
        r_z[row_index, node_3] = -cosine_1 * reciprocal_2 / determinant
    return r_x, r_z


def _global_distortional_longitudinal_basis(
    main_nodes: np.ndarray,
    r_yd: np.ndarray,
    r_ud: np.ndarray,
    mesh: FSMMesh,
    mechanics: ResolvedSectionMechanics,
) -> tuple[np.ndarray, int]:
    gross = mechanics.gross
    phi = np.deg2rad(gross.theta_p_deg)
    rotation = np.asarray(
        ((np.cos(phi), -np.sin(phi)), (np.sin(phi), np.cos(phi)))
    )
    centroid = np.asarray((gross.x_bar_mm, gross.y_bar_mm)) @ rotation
    warping = np.asarray(tuple(node.warping_mm2 for node in mesh.nodes))
    values = np.zeros((len(main_nodes), 4))
    for index, main_node in enumerate(main_nodes):
        coordinates = np.asarray((main_node[1], main_node[2])) @ rotation
        original_node_index = int(main_node[3])
        values[index] = (
            1.0,
            coordinates[1] - centroid[1],
            coordinates[0] - centroid[0],
            warping[original_node_index],
        )
    keep = np.linalg.norm(values, axis=0) > 1.0e-12
    values = values[:, keep]
    global_count = values.shape[1]
    distortional_count = int(round(np.linalg.matrix_rank(r_yd))) - global_count
    if distortional_count > 0:
        cholesky = np.linalg.cholesky(r_yd).T
        complement = linalg.null_space((cholesky @ values).T)
        mapped = np.linalg.solve(cholesky, complement)
        exclusions = np.hstack(
            (linalg.null_space(mapped.T), linalg.null_space(r_ud.T))
        )
        seed = linalg.null_space(exclusions.T)
        _, eigenvectors = linalg.eig(seed.T @ r_yd @ seed)
        values = np.hstack((values, seed @ np.real(eigenvectors)))
    return values, global_count


def _natural_basis(
    d_y: np.ndarray,
    elements: np.ndarray,
    element_properties: np.ndarray,
    half_wavelength_mm: float,
    node_properties: np.ndarray,
    main_node_count: int,
    corner_node_count: int,
    sub_node_count: int,
    global_count: int,
    distortional_count: int,
    local_count: int,
    r_x: np.ndarray,
    r_z: np.ndarray,
    r_p: np.ndarray,
    r_ys: np.ndarray,
    dof_permutation: np.ndarray,
) -> np.ndarray:
    node_count = len(node_properties)
    dof_count = 4 * node_count
    edge_count = main_node_count - corner_node_count
    gd_count = global_count + distortional_count
    basis = np.zeros((dof_count, dof_count))

    basis[:main_node_count, :gd_count] = d_y[:, :gd_count]
    basis[
        main_node_count : main_node_count + corner_node_count, :gd_count
    ] = r_x @ basis[:main_node_count, :gd_count]
    basis[
        main_node_count + corner_node_count : main_node_count + 2 * corner_node_count,
        :gd_count,
    ] = r_z @ basis[:main_node_count, :gd_count]
    basis[
        main_node_count + 2 * corner_node_count : dof_count - sub_node_count,
        :gd_count,
    ] = r_p @ basis[
        main_node_count : main_node_count + 2 * corner_node_count, :gd_count
    ]
    basis[dof_count - sub_node_count :, :gd_count] = r_ys @ basis[
        :main_node_count, :gd_count
    ]
    basis[
        main_node_count : dof_count - sub_node_count, :gd_count
    ] /= np.pi / half_wavelength_mm
    basis[:, :gd_count] /= np.linalg.norm(basis[:, :gd_count], axis=0)

    basis[
        3 * main_node_count : 4 * main_node_count,
        gd_count : gd_count + main_node_count,
    ] = np.eye(main_node_count)
    if sub_node_count:
        basis[
            4 * main_node_count + 2 * sub_node_count : 4 * main_node_count + 3 * sub_node_count,
            gd_count + main_node_count : gd_count + main_node_count + sub_node_count,
        ] = np.eye(sub_node_count)

    edge_index = 0
    for original_index, node_property in enumerate(node_properties):
        if node_property[3] != 2:
            continue
        adjacent = np.flatnonzero(
            (elements[:, 1] == original_index) | (elements[:, 2] == original_index)
        )
        alpha = element_properties[adjacent[0], 2]
        column = gd_count + main_node_count + sub_node_count + edge_index
        basis[main_node_count + 2 * corner_node_count + edge_index, column] = -np.sin(alpha)
        basis[
            main_node_count + 2 * corner_node_count + edge_count + edge_index,
            column,
        ] = np.cos(alpha)
        edge_index += 1

    if sub_node_count:
        sub_index = 0
        for original_index, node_property in enumerate(node_properties):
            if node_property[3] != 3:
                continue
            adjacent = np.flatnonzero(
                (elements[:, 1] == original_index)
                | (elements[:, 2] == original_index)
            )
            alpha = element_properties[adjacent[0], 2]
            column = (
                gd_count
                + main_node_count
                + sub_node_count
                + edge_count
                + sub_index
            )
            basis[4 * main_node_count + sub_index, column] = -np.sin(alpha)
            basis[4 * main_node_count + sub_node_count + sub_index, column] = np.cos(alpha)
            sub_index += 1

    element_count = len(elements)
    for index, element in enumerate(elements):
        alpha = element_properties[index, 2]
        node_1 = int(element[1])
        node_2 = int(element[2])
        shear_column = gd_count + local_count + index
        transverse_column = gd_count + local_count + element_count + index
        basis[2 * node_1 + 1, shear_column] = 0.5
        basis[2 * node_2 + 1, shear_column] = -0.5
        basis[2 * node_1, transverse_column] = -0.5 * np.cos(alpha)
        basis[2 * node_2, transverse_column] = 0.5 * np.cos(alpha)
        basis[2 * node_count + 2 * node_1, transverse_column] = 0.5 * np.sin(alpha)
        basis[2 * node_count + 2 * node_2, transverse_column] = -0.5 * np.sin(alpha)

    basis[:, : gd_count + local_count] = (
        dof_permutation @ basis[:, : gd_count + local_count]
    )
    return basis


def _stiffness_matrices(
    nodes: np.ndarray,
    elements: np.ndarray,
    element_properties: np.ndarray,
    properties: np.ndarray,
    half_wavelength_mm: float,
) -> tuple[np.ndarray, np.ndarray]:
    stiffness, geometric = analysis.k_kg_global(
        nodes=nodes,
        elements=elements,
        el_props=element_properties,
        props=properties,
        length=half_wavelength_mm,
        B_C="S-S",
        m_a=np.asarray((1,)),
    )
    return np.asarray(stiffness), np.asarray(geometric)


def _updated_basis(
    natural: np.ndarray,
    stiffness: np.ndarray,
    geometric: np.ndarray,
    counts: tuple[int, int, int],
    options: ClassicalBasisOptions,
) -> np.ndarray:
    global_count, distortional_count, local_count = counts
    dof_count = natural.shape[0]
    result = natural.copy()
    gdl_end = global_count + distortional_count + local_count

    if options.ospace != 1:
        complement = linalg.null_space(result[:, :gdl_end].T)
        if options.ospace == 2:
            other = np.linalg.solve(stiffness, complement)
        elif options.ospace == 3:
            other = np.linalg.solve(geometric, complement)
        else:
            other = complement
        result[:, gdl_end:] = other

    if options.ospace == 1:
        node_count = dof_count // 4
        bounds = (
            (0, global_count),
            (global_count, global_count + distortional_count),
            (global_count + distortional_count, gdl_end),
            (gdl_end, gdl_end + node_count - 1),
            (gdl_end + node_count - 1, dof_count),
        )
    else:
        bounds = (
            (0, global_count),
            (global_count, global_count + distortional_count),
            (global_count + distortional_count, gdl_end),
            (gdl_end, dof_count),
        )

    if options.orth in (2, 3):
        for start, end in bounds:
            if end <= start:
                continue
            subspace = result[:, start:end]
            k_sub = subspace.T @ stiffness @ subspace
            kg_sub = subspace.T @ geometric @ subspace
            eigenvalues, eigenvectors = linalg.eig(k_sub, kg_sub)
            order = np.argsort(np.real(eigenvalues))
            transform = np.real(eigenvectors[:, order])
            if options.norm in (2, 3):
                metric = k_sub if options.norm == 2 else kg_sub
                norms = np.sqrt(np.abs(np.diag(transform.T @ metric @ transform)))
                if np.any(norms <= 1.0e-15):
                    raise ValidationError("modal basis normalization is singular")
                transform /= norms
            result[:, start:end] = subspace @ transform

    if options.norm == 1:
        norms = np.linalg.norm(result, axis=0)
        if np.any(norms <= 1.0e-15):
            raise ValidationError("modal basis contains a zero column")
        result /= norms
    elif options.norm in (2, 3) and options.orth == 1:
        metric = stiffness if options.norm == 2 else geometric
        for column in range(dof_count):
            value = float(result[:, column].T @ metric @ result[:, column])
            if abs(value) <= 1.0e-15:
                raise ValidationError("modal basis normalization is singular")
            result[:, column] /= np.sqrt(abs(value))
    return result


def build_classical_basis_system(
    *,
    nodes: np.ndarray,
    elements: np.ndarray,
    properties: np.ndarray,
    mesh: FSMMesh,
    mechanics: ResolvedSectionMechanics,
    half_wavelength_mm: float,
    options: ClassicalBasisOptions,
) -> ClassicalBasisSystem:
    """Build the full independent classical modal basis and FSM matrices."""

    if options.couple not in (1, 2):
        raise ValidationError("unsupported classical coupling option")
    nodes_for_basis = np.asarray(nodes, dtype=float).copy()
    nodes_for_basis[:, 7] = 1.0
    elements_array = np.asarray(elements, dtype=float)
    element_properties = analysis.elem_prop(
        nodes=nodes_for_basis, elements=elements_array
    )
    (
        main_nodes,
        meta_elements,
        node_properties,
        main_node_count,
        corner_node_count,
        sub_node_count,
        reported_distortional_count,
        local_count,
        dof_permutation,
    ) = cfsm.base_properties(nodes=nodes_for_basis, elements=elements_array)
    _, _, r_yd, r_ys, r_ud = cfsm.mode_constr(
        nodes=nodes_for_basis,
        elements=elements_array,
        node_props=node_properties,
        main_nodes=main_nodes,
        meta_elements=meta_elements,
    )
    r_x, r_z = _corrected_corner_constraints(main_nodes, meta_elements)
    d_y, global_count = _global_distortional_longitudinal_basis(
        main_nodes, r_yd, r_ud, mesh, mechanics
    )
    distortional_count = d_y.shape[1] - global_count
    if distortional_count != int(reported_distortional_count):
        raise ValidationError(
            "independent distortional basis count disagrees with topology count"
        )
    r_p = cfsm.constr_planar_xz(
        nodes_for_basis,
        elements_array,
        properties,
        node_properties,
        dof_permutation,
        1.0,
        half_wavelength_mm,
        "S-S",
        element_properties,
    )
    natural = _natural_basis(
        d_y,
        elements_array,
        element_properties,
        half_wavelength_mm,
        node_properties,
        int(main_node_count),
        int(corner_node_count),
        int(sub_node_count),
        global_count,
        distortional_count,
        int(local_count),
        r_x,
        r_z,
        r_p,
        r_ys,
        dof_permutation,
    )
    stiffness, geometric = _stiffness_matrices(
        nodes_for_basis,
        elements_array,
        element_properties,
        properties,
        half_wavelength_mm,
    )
    basis = _updated_basis(
        natural,
        stiffness,
        geometric,
        (global_count, distortional_count, int(local_count)),
        options,
    )
    return ClassicalBasisSystem(
        basis=basis,
        stiffness=stiffness,
        geometric_stiffness=geometric,
        mode_counts=(
            global_count,
            distortional_count,
            int(local_count),
            basis.shape[0] - global_count - distortional_count - int(local_count),
        ),
    )


def classify_mode_shape(
    *,
    nodes: np.ndarray,
    elements: np.ndarray,
    properties: np.ndarray,
    mesh: FSMMesh,
    mechanics: ResolvedSectionMechanics,
    half_wavelength_mm: float,
    mode_shape: np.ndarray,
    options: ClassicalBasisOptions,
) -> ProjectionResult:
    """Project one unconstrained eigenvector into classical G/D/L/O spaces."""

    system = build_classical_basis_system(
        nodes=nodes,
        elements=elements,
        properties=properties,
        mesh=mesh,
        mechanics=mechanics,
        half_wavelength_mm=half_wavelength_mm,
        options=options,
    )
    basis = system.basis
    shape = np.asarray(mode_shape, dtype=float).reshape(-1)
    if len(shape) != basis.shape[0]:
        raise ValidationError("mode shape length does not match modal basis")
    coefficients, _, basis_rank, _ = np.linalg.lstsq(basis, shape, rcond=None)
    global_count, distortional_count, local_count, other_count = system.mode_counts
    g_end = global_count
    d_end = g_end + distortional_count
    l_end = d_end + local_count
    group_norms = np.asarray(
        (
            np.linalg.norm(coefficients[:g_end]),
            np.linalg.norm(coefficients[g_end:d_end]),
            np.linalg.norm(coefficients[d_end:l_end]),
            np.linalg.norm(coefficients[l_end:]),
        )
    )
    total = float(np.sum(group_norms))
    if total <= 0.0:
        raise ValidationError("modal coefficients have zero aggregate norm")
    percentages = group_norms / total * 100.0
    reconstruction = basis @ coefficients
    shape_norm = np.linalg.norm(shape)
    residual = float(np.linalg.norm(reconstruction - shape) / shape_norm)
    participation = ModeParticipation(
        global_percent=float(percentages[0]),
        distortional_percent=float(percentages[1]),
        local_percent=float(percentages[2]),
        other_percent=float(percentages[3]),
    )
    return ProjectionResult(
        participation=participation,
        reconstruction_error=residual,
        basis_condition_number=float(np.linalg.cond(basis)),
        basis_rank=int(basis_rank),
        basis_dimension=int(basis.shape[1]),
        mode_counts=system.mode_counts,
    )


__all__ = [
    "ClassicalBasisSystem",
    "ProjectionResult",
    "build_classical_basis_system",
    "classify_mode_shape",
]
