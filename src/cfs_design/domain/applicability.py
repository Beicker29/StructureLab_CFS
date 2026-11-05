"""AISI S100-24 B4.1 and Table B4.1-1 (pp. 25-26): limits of applicability of DSM and EWM.

D12: the rows are applied per demand (an element enters a row only in the state that row names);
the interaction check (Chapter H) uses the union of the rows of the demands involved. Outside the
limits the check is OUT_OF_METHOD_SCOPE with a reference to B4.2, which is not automated.
Rows always met by the current scope (DC-9: C and Z with a simple lip): edge stiffener type
(simple lip, both methods) and number of intermediate stiffeners (nf = nfe = nw = 0).
EWM limits (b/t with Is vs Ia, Appendix 1.3) arrive with milestone M7.
"""
from ..errors import OutOfMethodScopeError, RuleNotImplementedError

# (variable, DSM limit, Table B4.1-1 row); variables are keys of section.elements, or Fy
DSM_LIMITS = {
    "w_t": (500.0, "stiffened element in compression"),
    "b_t": (160.0, "edge-stiffened element in compression"),
    "d_t": (60.0, "unstiffened element in compression"),
    "h_t": (300.0, "stiffened element in bending (web)"),
    "R_t": (20.0, "inside bend radius"),
    "do_bo": (0.7, "simple edge stiffener length/width ratio"),
    "Fy": (655.0, "nominal yield stress (MPa); see A3"),
}

# rows by demand (D12); flexure, shear and web crippling rows are added with their milestones
ROWS_BY_DEMAND = {
    "compression": ("w_t", "b_t", "d_t", "R_t", "do_bo", "Fy"),
}


def rows_for(demands: set[str]) -> tuple[str, ...]:
    """Union of the rows of the demands (D12); a demand without rows yet is not implemented."""
    rows: list[str] = []
    for demand in sorted(demands):
        if demand not in ROWS_BY_DEMAND:
            raise RuleNotImplementedError(f"Table B4.1-1 rows for {demand} are not defined yet", details={"demand": demand})
        rows += [r for r in ROWS_BY_DEMAND[demand] if r not in rows]
    return tuple(rows)


def check_dsm(demands: set[str], elements: dict[str, float], fy: float) -> dict[str, float]:
    """Raise OutOfMethodScopeError listing every violated row; return the evaluated values otherwise."""
    values = {row: (fy if row == "Fy" else elements[row]) for row in rows_for(demands)}
    violations = [{"variable": row, "value": value, "limit": DSM_LIMITS[row][0], "row": DSM_LIMITS[row][1]}
                  for row, value in values.items() if value > DSM_LIMITS[row][0]]
    if violations:
        raise OutOfMethodScopeError("member outside Table B4.1-1 for the Direct Strength Method; B4.2 is not automated",
                                    details={"violations": violations, "reference": "B4.2", "decision": "D12"})
    return values
