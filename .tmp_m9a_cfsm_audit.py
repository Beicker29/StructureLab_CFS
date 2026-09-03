from math import ceil, pi, radians, sqrt

import numpy as np
from pycufsm import strip_new
from pycufsm.solve import cfsm

from cfs_design.domain import (
    GeometryConvention,
    SectionFamily,
    SectionGeometry,
)
from cfs_design.mechanics.sections import (
    build_centerline_section,
    compute_advanced_properties,
    compute_gross_properties,
)


geometry = SectionGeometry(
    geometry_id="AUDIT_C_LIPPED",
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
section = build_centerline_section(geometry, section_id="AUDIT_C_LIPPED")
gross = compute_gross_properties(section)
advanced = compute_advanced_properties(section, gross)
area = gross.a_mm2
ro2 = gross.ix_mm4 / area + gross.iy_mm4 / area + advanced.x0_mm**2
pex = pi**2 * 203000.0 * gross.ix_mm4 / 2500.0**2
pey = pi**2 * 203000.0 * gross.iy_mm4 / 2500.0**2
pt = ((203000.0 / (2 * 1.3)) * gross.j_mm4 + pi**2 * 203000.0 * advanced.cw_mm6 / 2500.0**2) / ro2
beta = 1 - (advanced.x0_mm**2 / ro2)
pft = 2 * pex * pt / (pex + pt + sqrt((pex + pt)**2 - 4 * beta * pex * pt))
print("analytic global", pex / area, pey / area, pt / area, pft / area)

nodes_xy: list[list[float]] = []
for primitive_index, primitive in enumerate(section.primitives):
    subdivisions = max(1, ceil(primitive.length_mm / 10.0))
    for step in range(subdivisions + 1):
        if primitive_index and step == 0:
            continue
        fraction = step / subdivisions
        nodes_xy.append(
            [
                primitive.start.x_mm
                + fraction * (primitive.end.x_mm - primitive.start.x_mm),
                primitive.start.y_mm
                + fraction * (primitive.end.y_mm - primitive.start.y_mm),
            ]
        )
elements = [{"nodes": list(range(len(nodes_xy))), "t": 1.0, "mat": "S100"}]

nodes_old = np.array(
    [[i, x, y, 1, 1, 1, 1, 1.0] for i, (x, y) in enumerate(nodes_xy)],
    dtype=float,
)
elements_old = np.array(
    [[i, i, i + 1, 1.0, 0] for i in range(len(nodes_xy) - 1)],
    dtype=float,
)
base = cfsm.base_properties(nodes=nodes_old, elements=elements_old)
n_dist_modes = int(base[6])
n_local_modes = int(base[7])
n_global_modes = 4
n_other_modes = 2 * (len(nodes_xy) - 1)
print(
    "mode counts",
    n_global_modes,
    n_dist_modes,
    n_local_modes,
    n_other_modes,
)


def sect_props(*, cw_factor=1.0, j_factor=1.0, b1=0.0, b2=0.0, wn=None):
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
        "J": gross.j_mm4 * j_factor,
        "x0": gross.x_bar_mm + advanced.x0_mm,
        "y0": gross.y_bar_mm + advanced.y0_mm,
        "Cw": advanced.cw_mm6 * cw_factor,
        "B1": b1,
        "B2": b2,
        "wn": np.array([]) if wn is None else np.asarray(wn, dtype=float),
    }


def run(mode, props, reference_stress=1.0, global_mask=None, coupled=False):
    selections = {
        "local": (
            [0] * n_global_modes,
            [0] * n_dist_modes,
            [1] * n_local_modes,
            [0] * n_other_modes,
        ),
        "dist": (
            [0] * n_global_modes,
            [1] * n_dist_modes,
            [0] * n_local_modes,
            [0] * n_other_modes,
        ),
        "global": (
            [1] * n_global_modes,
            [0] * n_dist_modes,
            [0] * n_local_modes,
            [0] * n_other_modes,
        ),
    }
    glob, dist, local, other = selections[mode]
    if global_mask is not None:
        glob = global_mask
    config = {
        "glob_modes": glob,
        "dist_modes": dist,
        "local_modes": local,
        "other_modes": other,
        "null_space": "ST",
        "normalization": "none" if coupled else "vector",
        "coupled": coupled,
        "orthogonality": "natural",
    }
    nodes = [[x, y, reference_stress] for x, y in nodes_xy]
    signature, _, _, _, lengths = strip_new(
        props={"S100": {"E": 203000.0, "nu": 0.3}},
        nodes=nodes,
        elements=elements,
        sect_props=props,
        lengths=[10.0, 50.0, 100.0, 250.0, 1000.0, 2500.0, 5000.0, 10000.0],
        analysis_config={"B_C": "S-S", "n_eigs": 1},
        cfsm_config=config,
    )
    return np.asarray(lengths), np.asarray(signature) * reference_stress


baseline = sect_props()
signature, _, _, _, raw_lengths = strip_new(
    props={"S100": {"E": 203000.0, "nu": 0.3}},
    nodes=[[x, y, 1.0] for x, y in nodes_xy],
    elements=elements,
    sect_props=baseline,
    lengths=[250.0, 1000.0, 2500.0, 5000.0, 10000.0],
    analysis_config={"B_C": "S-S", "n_eigs": 1},
)
print("unconstrained", list(zip(np.asarray(raw_lengths).tolist(), np.asarray(signature).tolist())))
lengths, values = run("global", baseline, coupled=True)
print("global coupled", list(zip(lengths.tolist(), values.tolist())))
for mode in ("local", "dist", "global"):
    lengths, values = run(mode, baseline)
    print(mode, list(zip(lengths.tolist(), values.tolist())))

for global_index in range(4):
    mask = [0] * 4
    mask[global_index] = 1
    lengths, values = run("global", baseline, global_mask=mask)
    print("global component", global_index, list(zip(lengths.tolist(), values.tolist())))

for mode in ("local", "dist"):
    for name, props in (
        ("Cw0", sect_props(cw_factor=0.0)),
        ("Cw1", sect_props(cw_factor=1.0)),
        ("Cw10", sect_props(cw_factor=10.0)),
        ("J0", sect_props(j_factor=0.0)),
        ("J1", sect_props(j_factor=1.0)),
        ("J10", sect_props(j_factor=10.0)),
        ("Bzero", sect_props(b1=0.0, b2=0.0)),
        ("Blarge", sect_props(b1=1.0e9, b2=-1.0e9)),
        ("wnlarge", sect_props(wn=np.full(len(nodes_xy), 1.0e9))),
    ):
        _, values = run(mode, props)
        print("sensitivity", mode, name, values.tolist())

for reference_stress in (1.0, 10.0):
    for mode in ("local", "dist"):
        _, values = run(mode, baseline, reference_stress)
        print("reference", reference_stress, mode, values.tolist())
