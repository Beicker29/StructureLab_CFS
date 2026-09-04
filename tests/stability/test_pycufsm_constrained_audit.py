"""Executable audit gates for rejected pyCUFSM 0.2.0 constrained cFSM paths."""

from dataclasses import replace

import pytest
from pycufsm import helpers, strip_new
from pycufsm.solve import cfsm

from cfs_design.domain import SectionFamily
from cfs_design.mechanics.sections import build_centerline_section
from cfs_design.stability import build_fsm_mesh
from cfs_design.stability.pycufsm_adapter._solver import _section_properties
from tests.design.ewm.conftest import make_design_input


def test_public_orth2_path_remains_software_blocked_without_a_patch() -> None:
    design_input = make_design_input(
        family=SectionFamily.C_LIPPED,
        web_mm=120.0,
        flange_1_mm=80.0,
        flange_2_mm=80.0,
        lip_1_mm=15.0,
        lip_2_mm=15.0,
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
    section = design_input.resolved_member.section
    centerline = build_centerline_section(
        section.geometry, section_id=section.catalog_section.section_id
    )
    mesh = build_fsm_mesh(
        centerline,
        design_input.section_mechanics.advanced,
        target_strip_width_mm=20.0,
    )
    properties = {"steel": {"E": 210000.0, "nu": 0.3}}
    nodes = [[node.x_mm, node.y_mm, 1.0] for node in mesh.nodes]
    elements = [{"nodes": "all", "t": 1.0, "mat": "steel"}]
    old = helpers.inputs_new_to_old(
        props=properties,
        nodes=nodes,
        elements=elements,
        lengths=(100.0,),
    )
    base = cfsm.base_properties(nodes=old[1], elements=old[2])
    distortional_count = int(base[6])
    local_count = int(base[7])

    with pytest.raises(TypeError, match="expected numpy.ndarray, got list"):
        strip_new(
            props=properties,
            nodes=nodes,
            elements=elements,
            sect_props=_section_properties(design_input.section_mechanics),
            lengths=(100.0,),
            analysis_config={"B_C": "S-S", "n_eigs": 1},
            cfsm_config={
                "glob_modes": [0] * 4,
                "dist_modes": [0] * distortional_count,
                "local_modes": [1] * local_count,
                "other_modes": [0] * (2 * (len(nodes) - 1)),
                "null_space": "ST",
                "normalization": "vector",
                "coupled": False,
                "orthogonality": "modal_axial",
            },
        )
