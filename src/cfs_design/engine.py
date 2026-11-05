"""Member run: one check per demand (and interaction) and per method, then the member status.

The section is resolved first (sections/, M1) and its elastic critical loads computed (buckling/,
M2); the material is validated against A3.1.1 (D15). A blocked section or material makes every
check INCOMPLETE with that reason. With `method: both` each demand gets a DSM and an EWM check
(DC-1). Implemented chapters: E by DSM (M3); the rest yield INCOMPLETE naming their milestone.

Status precedence (DC-1, extended in D14): INCOMPLETE > OUT_OF_METHOD_SCOPE > FAIL > PASS;
NOT_APPLICABLE does not count unless every check is NOT_APPLICABLE. A capacity is reported only
with PASS or FAIL.
"""
from collections.abc import Callable
from typing import Any

from .buckling import member_buckling
from .domain import DesignContext
from .domain.compression import compression_check
from .errors import BLOCKING_ERRORS, CfsDesignError, OutOfMethodScopeError, RuleNotImplementedError
from .materials import get_material, validate_a3_1_1
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

PRECEDENCE = (Status.INCOMPLETE, Status.OUT_OF_METHOD_SCOPE, Status.FAIL, Status.PASS)

Calculator = Callable[[DesignContext, float, str], Check]


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


def _not_implemented(check: str) -> Calculator:
    def calculator(ctx: DesignContext, demand: float, method: str) -> Check:
        chapter, milestone = DEMAND_CHAPTERS[check]
        raise RuleNotImplementedError(f"AISI S100-24 chapter {chapter} is not implemented yet (milestone {milestone})",
                                      details={"chapter": chapter, "milestone": milestone})
    return calculator


CALCULATORS: dict[str, Calculator] = {name: _not_implemented(name) for name in DEMAND_CHAPTERS}
CALCULATORS["compression"] = compression_check


def _run_check(ctx: DesignContext | None, check: str, demand: float, method: str, blocked: list[dict[str, Any]]) -> Check:
    chapter = DEMAND_CHAPTERS[check][0]
    if ctx is None:
        return Check(check=check, chapter=chapter, demand=demand, status=Status.INCOMPLETE, method=method, errors=blocked)
    try:
        return CALCULATORS[check](ctx, demand, method)
    except OutOfMethodScopeError as error:
        return Check(check=check, chapter=chapter, demand=demand, status=Status.OUT_OF_METHOD_SCOPE, method=method,
                     errors=[error.to_dict()])
    except BLOCKING_ERRORS as error:
        return Check(check=check, chapter=chapter, demand=demand, status=Status.INCOMPLETE, method=method,
                     errors=[error.to_dict()])


def _aggregate(statuses: list[Status]) -> Status:
    for status in PRECEDENCE:
        if status in statuses:
            return status
    return Status.NOT_APPLICABLE


def _max_ratio(ratios: list[float | None]) -> float | None:
    known = [r for r in ratios if r is not None]
    return max(known) if known else None


def run_member(member: MemberInput) -> DesignResult:
    """Evaluate every combination of one member. Raises CfsDesignError only for invalid input (unknown material or section)."""
    material = get_material(member.material)
    section: dict[str, Any] | None = None
    buckling: dict[str, Any] | None = None
    blocked: list[dict[str, Any]] = []
    ctx: DesignContext | None = None
    try:
        resolved = resolve_section(member.section)
        section = resolved.to_dict()
        buckling = member_buckling(member, resolved)
        try:
            validate_a3_1_1(material)
            ctx = DesignContext(member, material, resolved, buckling)
        except BLOCKING_ERRORS as error:
            blocked.append(error.to_dict())
    except BLOCKING_ERRORS as error:
        blocked.append(error.to_dict())
    methods = ("DSM", "EWM") if member.method == "both" else (member.method,)
    cases: list[CaseResult] = []
    for case in member.cases:
        checks = [_run_check(ctx, name, demand, method, blocked) for name, demand in demanded_checks(case) for method in methods]
        cases.append(CaseResult(name=case.name, status=_aggregate([c.status for c in checks]),
                                ratio=_max_ratio([c.ratio for c in checks]), checks=checks))
    ratios = [(c.ratio, c.name) for c in cases if c.ratio is not None]
    governing = max(ratios)[1] if ratios else None
    return DesignResult(status=_aggregate([c.status for c in cases]), ratio=_max_ratio([c.ratio for c in cases]),
                        governing=governing, material=material.to_dict(), section=section, buckling=buckling, cases=cases,
                        errors=blocked)


__all__ = ["DEMAND_CHAPTERS", "CfsDesignError", "demanded_checks", "run_member"]
