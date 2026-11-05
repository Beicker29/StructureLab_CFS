"""Limit states the Specification makes mandatory for each demand, enumerated from the text, not from the selection.

PASS needs every listed obligation evaluated; otherwise the capacity is null (D14).
"""

OBLIGATIONS = {
    # E1 (p. 43): the smallest of E2 (yielding and global), E3 (local) and E4 (distortional), where applicable;
    # E4 applies to C and Z members with edge-stiffened flanges (p. 46), i.e. to the whole current scope (DC-9)
    "compression": ("E2", "E3", "E4"),
}


def missing_obligations(demand: str, evaluated: set[str]) -> list[str]:
    return [o for o in OBLIGATIONS[demand] if o not in evaluated]
