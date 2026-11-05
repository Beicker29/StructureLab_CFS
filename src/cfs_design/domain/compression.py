"""Compression check, AISI S100-24 Chapter E (milestone M3): Direct Strength Method.

E1: φcPn is the smallest of E2, E3.2 and E4. Elastic critical loads come from buckling/ (M2).
EWM (E3.1) arrives with milestone M7. Decisions D12-D15 in docs/chapter-e.md.
"""
from typing import Any

from ..codes.aisi_s100_24 import compression as e
from ..errors import IncompleteDataError, OutOfMethodScopeError, RuleNotImplementedError
from ..models import Check, Status
from . import DesignContext, applicability, coverage

CHAPTER = "E"


def _critical(ctx: DesignContext, mode: str) -> dict[str, Any]:
    """Elastic critical load of a mode, or the blocking error that buckling/ recorded for it."""
    if "error" in ctx.buckling:
        raise IncompleteDataError("elastic buckling is not available", details={"buckling": ctx.buckling["error"]})
    item = ctx.buckling["compression"][mode]
    if "error" in item:
        raise IncompleteDataError(f"elastic {mode} buckling is not available", details={"buckling": item["error"]})
    return item


def compression_check(ctx: DesignContext, demand: float, method: str) -> Check:
    """Design check for the factored axial compression `demand` (kN)."""
    if method != "DSM":
        raise RuleNotImplementedError("compression by the Effective Width Method (E3.1) is not implemented yet (milestone M7)",
                                      details={"milestone": "M7", "method": method})
    elements = ctx.section.elements
    fy, ag = ctx.material.Fy, ctx.section.properties["A"]
    limits = applicability.check_dsm({"compression"}, elements, fy)
    result: dict[str, Any] = {"Fy_MPa": fy, "Ag_mm2": ag, "phi_c": e.PHI_C, "B4_1": limits}
    evaluated: set[str] = set()
    errors: list[dict[str, Any]] = []
    out_of_scope: list[str] = []

    def step(name: str, fn: Any) -> None:
        try:
            fn()
            evaluated.add(name)
        except (IncompleteDataError, RuleNotImplementedError) as error:
            errors.append(error.to_dict())
        except OutOfMethodScopeError as error:
            errors.append(error.to_dict())
            out_of_scope.append(name)

    def e2() -> None:
        g = _critical(ctx, "global")
        lam = e.lambda_c(fy, g["stress_MPa"])
        fn = e.fn_global(fy, lam)
        result["E2"] = {"Fcre_MPa": g["stress_MPa"], "mode": g["mode"], "lambda_c": lam, "Fn_MPa": fn,
                        "Pne_kN": e.pne(ag, fn) / 1e3, "equation": "Eqs. E2-1 to E2-4"}

    def e3() -> None:
        if "E2" not in result:
            raise IncompleteDataError("E3.2 needs Pne from E2", details={"missing": ["Pne"]})
        p_ne, p_crl = result["E2"]["Pne_kN"], _critical(ctx, "local")["value"]
        lam = e.lambda_local(p_ne, p_crl)
        result["E3"] = {"Pcrl_kN": p_crl, "lambda_l": lam, "equation": "Eqs. E3.2-1, E3.2-2"}
        if lam > e.LAMBDA_DSM_MAX:
            raise OutOfMethodScopeError("λℓ > 5: Eq. E3.2-1 does not apply (no extrapolation; D13)",
                                        details={"lambda_l": lam, "limit": e.LAMBDA_DSM_MAX, "alternative": "E3.1 (EWM, M7)"})
        result["E3"]["Pnl_kN"] = e.pnl_dsm(p_ne, lam)

    def e4() -> None:
        d = _critical(ctx, "distortional")
        p_y = e.py(ag, fy) / 1e3
        lam = e.lambda_distortional(p_y, d["value"])
        result["E4"] = {"Pcrd_kN": d["value"], "Py_kN": p_y, "lambda_d": lam, "Lm_mm": d["Lm_mm"],
                        "Lm_source": d["Lm_source"], "equation": "Eqs. E4-1 to E4-3"}
        if lam > e.LAMBDA_DSM_MAX:
            raise OutOfMethodScopeError("λd > 5: Eq. E4-1 does not apply (no extrapolation; D13)",
                                        details={"lambda_d": lam, "limit": e.LAMBDA_DSM_MAX})
        result["E4"]["Pnd_kN"] = e.pnd_dsm(p_y, lam)

    step("E2", e2)
    step("E3", e3)
    step("E4", e4)
    result["k_phi"] = ctx.buckling.get("k_phi")
    missing = coverage.missing_obligations("compression", evaluated)
    if missing:
        result["missing_obligations"] = missing
        # a missing datum dominates a method-scope limit (same precedence as engine._aggregate)
        status = Status.OUT_OF_METHOD_SCOPE if set(missing) <= set(out_of_scope) else Status.INCOMPLETE
        return Check(check="compression", chapter=CHAPTER, demand=demand, status=status, method=method,
                     result=result, errors=errors)
    nominal = {"E2": result["E2"]["Pne_kN"], "E3": result["E3"]["Pnl_kN"], "E4": result["E4"]["Pnd_kN"]}
    governing = min(nominal, key=lambda k: nominal[k])
    capacity = e.PHI_C * nominal[governing]
    ratio = demand / capacity
    result.update({"Pn_kN": nominal[governing], "governing": governing})
    return Check(check="compression", chapter=CHAPTER, demand=demand, status=Status.PASS if ratio <= 1 else Status.FAIL,
                 capacity=capacity, ratio=ratio, method=method, result=result)
