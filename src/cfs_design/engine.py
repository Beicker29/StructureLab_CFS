"""Member run: one check per demand (and interaction), then PASS / FAIL / INCOMPLETE.

The section is resolved first (sections/, milestone M1); if it is blocked (missing data or a
shape out of scope) every check is INCOMPLETE with that reason. No chapter is implemented yet:
every demand yields an INCOMPLETE check that names the AISI S100-24 chapter and the roadmap
milestone that will cover it. Never a capacity.
"""
from collections.abc import Callable
from typing import Any

from .buckling import member_buckling
from .errors import BLOCKING_ERRORS, CfsDesignError, RuleNotImplementedError
from .materials import Material, get_material
from .models import CaseDemand, CaseResult, Check, DesignResult, MemberInput, Status
from .sections import resolve_section

# check name -> (S100-24 chapter/sections, milestone)
DEMAND_CHAPTERS: dict[str, tuple[str, str]] = {
    "compression": ("E", "M3"),
    "tension": ("D", "M5"),
    "flexure_x": ("F", "M4"),
    "flexure_y": ("F", "M4"),
    "shear_x": ("G2", "M5"),
    "shear_y": ("G2", "M5"),
    "web_crippling": ("G5", "M5"),
    "torsion": ("G8", "M8"),
    "interaction": ("H", "M6"),
}

Calculator = Callable[[MemberInput, Material, CaseDemand, str], Check]


def demanded_checks(case: CaseDemand) -> list[tuple[str, float]]:
    """Checks the case requires, with their demand. Interaction when axial and flexure act together or flexure is biaxial."""
    checks: list[tuple[str, float]] = []
    if case.Pu > 0:
        checks.append(("compression", case.Pu))
    elif case.Pu < 0:
        checks.append(("tension", -case.Pu))
    for name, value in (("flexure_x", case.Mux), ("flexure_y", case.Muy), ("shear_x", case.Vux), ("shear_y", case.Vuy),
                        ("web_crippling", case.Pw), ("torsion", case.Bu)):
        if value != 0:
            checks.append((name, abs(value)))
    flexures = sum(1 for v in (case.Mux, case.Muy) if v != 0)
    if (case.Pu != 0 and flexures) or flexures == 2 or (flexures and (case.Vux or case.Vuy or case.Pw or case.Bu)):
        checks.append(("interaction", 0.0))
    return checks


def _not_implemented(member: MemberInput, material: Material, case: CaseDemand, check: str) -> Check:
    chapter, milestone = DEMAND_CHAPTERS[check]
    raise RuleNotImplementedError(f"AISI S100-24 chapter {chapter} is not implemented yet (milestone {milestone})",
                                  details={"chapter": chapter, "milestone": milestone})


CALCULATORS: dict[str, Calculator] = {name: _not_implemented for name in DEMAND_CHAPTERS}


def _run_check(member: MemberInput, material: Material, case: CaseDemand, check: str, demand: float,
               blocked: dict[str, Any] | None) -> Check:
    chapter = DEMAND_CHAPTERS[check][0]
    if blocked is not None:
        return Check(check=check, chapter=chapter, demand=demand, status=Status.INCOMPLETE, method=member.method,
                     errors=[blocked])
    try:
        return CALCULATORS[check](member, material, case, check)
    except BLOCKING_ERRORS as error:
        return Check(check=check, chapter=chapter, demand=demand, status=Status.INCOMPLETE, method=member.method,
                     errors=[error.to_dict()])


def _aggregate(statuses: list[Status]) -> Status:
    if Status.INCOMPLETE in statuses:
        return Status.INCOMPLETE
    return Status.FAIL if Status.FAIL in statuses else Status.PASS


def _max_ratio(ratios: list[float | None]) -> float | None:
    known = [r for r in ratios if r is not None]
    return max(known) if known else None


def run_member(member: MemberInput) -> DesignResult:
    """Evaluate every combination of one member. Raises CfsDesignError only for invalid input (unknown material or section)."""
    material = get_material(member.material)
    section: dict[str, Any] | None = None
    buckling: dict[str, Any] | None = None
    blocked: dict[str, Any] | None = None
    try:
        resolved = resolve_section(member.section)
        section = resolved.to_dict()
        buckling = member_buckling(member, resolved)
    except BLOCKING_ERRORS as error:
        blocked = error.to_dict()
    cases: list[CaseResult] = []
    for case in member.cases:
        checks = [_run_check(member, material, case, name, demand, blocked) for name, demand in demanded_checks(case)]
        cases.append(CaseResult(name=case.name, status=_aggregate([c.status for c in checks]),
                                ratio=_max_ratio([c.ratio for c in checks]), checks=checks))
    ratios = [(c.ratio, c.name) for c in cases if c.ratio is not None]
    governing = max(ratios)[1] if ratios else None
    return DesignResult(status=_aggregate([c.status for c in cases]), ratio=_max_ratio([c.ratio for c in cases]),
                        governing=governing, material=material.to_dict(), section=section, buckling=buckling, cases=cases,
                        errors=[blocked] if blocked else [])


__all__ = ["DEMAND_CHAPTERS", "CfsDesignError", "demanded_checks", "run_member"]
