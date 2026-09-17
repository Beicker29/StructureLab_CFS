"""Deterministic M3 centerline-to-FSM mesh translation."""

from math import ceil

from cfs_design.core.exceptions import ValidationError
from cfs_design.mechanics.sections import (
    AdvancedSectionProperties,
    CenterlineSection,
)

from ..models import FSMMesh, FSMNode, FSMStrip


def build_fsm_mesh(
    centerline: CenterlineSection,
    advanced: AdvancedSectionProperties,
    *,
    target_strip_width_mm: float,
) -> FSMMesh:
    """Subdivide every authoritative M3 primitive without changing its contour.

    M3B sectorial coordinates are linear on each straight thin-wall segment,
    so the warping value at an inserted FSM node is obtained by interpolation
    between the corresponding authoritative M3B contour nodes.
    """

    if not isinstance(centerline, CenterlineSection):
        raise ValidationError("centerline must be CenterlineSection")
    if not isinstance(advanced, AdvancedSectionProperties):
        raise ValidationError("advanced must be AdvancedSectionProperties")
    if centerline.section_id is None:
        raise ValidationError("FSM meshing requires an identified section")
    if advanced.section_id != centerline.section_id:
        raise ValidationError("advanced section_id must match centerline")
    if advanced.geometry_id != centerline.geometry_id:
        raise ValidationError("advanced geometry_id must match centerline")
    if target_strip_width_mm <= 0.0:
        raise ValidationError("target_strip_width_mm must be greater than zero")
    sectorial_nodes = advanced.sectorial.nodes
    if len(sectorial_nodes) != len(centerline.primitives) + 1:
        raise ValidationError(
            "M3B contour nodes must correspond to M3 primitive endpoints"
        )

    nodes: list[FSMNode] = []
    strips: list[FSMStrip] = []
    maximum_width = 0.0
    for primitive_index, primitive in enumerate(centerline.primitives):
        subdivisions = max(1, ceil(primitive.length_mm / target_strip_width_mm))
        actual_width = primitive.length_mm / subdivisions
        maximum_width = max(maximum_width, actual_width)
        start_warping = sectorial_nodes[primitive_index].omega_normalized_mm2
        end_warping = sectorial_nodes[primitive_index + 1].omega_normalized_mm2
        for step in range(subdivisions + 1):
            if primitive_index > 0 and step == 0:
                continue
            fraction = step / subdivisions
            node_index = len(nodes)
            nodes.append(
                FSMNode(
                    index=node_index,
                    x_mm=primitive.start.x_mm
                    + fraction * (primitive.end.x_mm - primitive.start.x_mm),
                    y_mm=primitive.start.y_mm
                    + fraction * (primitive.end.y_mm - primitive.start.y_mm),
                    warping_mm2=start_warping
                    + fraction * (end_warping - start_warping),
                )
            )
            if node_index:
                strips.append(
                    FSMStrip(
                        index=len(strips),
                        start_node=node_index - 1,
                        end_node=node_index,
                        thickness_mm=centerline.thickness_mm,
                    )
                )

    return FSMMesh(
        section_id=centerline.section_id,
        geometry_id=centerline.geometry_id,
        nodes=tuple(nodes),
        strips=tuple(strips),
        target_strip_width_mm=float(target_strip_width_mm),
        maximum_actual_strip_width_mm=maximum_width,
    )


__all__ = ["build_fsm_mesh"]
