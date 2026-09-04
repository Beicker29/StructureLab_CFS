from __future__ import annotations

from math import ceil, radians

import numpy as np
from pycufsm import fsm, helpers
from pycufsm.solve import cfsm

from cfs_design.domain import GeometryConvention, SectionFamily, SectionGeometry
from cfs_design.mechanics.sections import (
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
)


def model(max_width: float):
    geometry = SectionGeometry(
        geometry_id="G",
        section_type=SectionFamily.C_LIPPED,
        h_mm=100.0,
        b1_mm=40.0,
        b2_mm=40.0,
        d1_mm=10.0,
        d2_mm=10.0,
        t_mm=1.0,
        ri_mm=0.0,
        web_flange_angle_deg=90.0,
        flange_lip_angle_deg=90.0,
        geometry_convention=GeometryConvention.MIDLINE,
    )
    centerline = build_centerline_section(geometry, section_id="S")
    gross = compute_gross_properties(centerline)
    advanced = compute_advanced_properties(centerline, gross)
    nodes: list[list[float]] = []
    for primitive_index, primitive in enumerate(centerline.primitives):
        count = ceil(primitive.length_mm / max_width)
        for index in range(count + 1):
            if primitive_index and index == 0:
                continue
            ratio = index / count
            nodes.append(
                [
                    primitive.start.x_mm
                    + ratio * (primitive.end.x_mm - primitive.start.x_mm),
                    primitive.start.y_mm
                    + ratio * (primitive.end.y_mm - primitive.start.y_mm),
                    1.0,
                ]
            )
    elements = [{"nodes": "all", "t": 1.0, "mat": "steel"}]
    props = {
        "steel": {
            "E_x": 203_000.0,
            "E_y": 203_000.0,
            "nu_x": 0.3,
            "nu_y": 0.3,
            "G_bulk": 78_000.0,
        }
    }
    sp = {
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
    converted = helpers.inputs_new_to_old(
        props=props,
        nodes=nodes,
        elements=elements,
        lengths=[50.0],
    )
    props_old, nodes_old, elements_old = converted[:3]
    bp = cfsm.base_properties(nodes=nodes_old, elements=elements_old)
    n_dist, n_local = bp[6], bp[7]
    return nodes, elements, props, sp, n_dist, n_local


def run(mode: str, widths=(5.0, 2.5, 1.25)):
    if mode == "local":
        lengths = np.geomspace(55.0, 80.0, 13)
    elif mode == "global" or mode == "unconstrained":
        lengths = np.array([2500.0])
    else:
        lengths = np.geomspace(250.0, 500.0, 13)
    for width in widths:
        nodes, elements, props, sp, n_dist, n_local = model(width)
        selected = {
            "glob_modes": [1] * 4 if mode == "global" else [0] * 4,
            "dist_modes": [1] * n_dist if mode == "dist" else [0] * n_dist,
            "local_modes": [1] * n_local if mode == "local" else [0] * n_local,
            "other_modes": [0] * (2 * (len(nodes) - 1)),
            "null_space": "ST",
            "normalization": "none",
            "coupled": False,
            "orthogonality": "natural",
        }
        if mode == "unconstrained":
            selected = None
        signature, _, _, _, actual_lengths = fsm.strip_new(
            props=props,
            nodes=nodes,
            elements=elements,
            sect_props=sp,
            lengths=lengths,
            analysis_config={"B_C": "S-S", "n_eigs": 1},
            cfsm_config=selected,
        )
        idx = int(np.argmin(signature))
        print(
            mode,
            width,
            len(nodes),
            n_dist,
            n_local,
            actual_lengths[idx],
            signature[idx],
            flush=True,
        )


if __name__ == "__main__":
    import sys

    run(sys.argv[1], tuple(float(v) for v in sys.argv[2:]) or (5.0, 2.5, 1.25))
