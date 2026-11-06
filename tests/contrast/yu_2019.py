"""External contrast: worked examples of Yu, LaBoube & Chen, Cold-Formed Steel Design, 5th ed. (Wiley, 2019).

The book follows AISI S100-16 and the 2017 AISI Design Manual, not S100-24. It is not an oracle:
this script imports cfs_design, computes the repo values and writes docs/validation-yu-2019.md
next to the book values (transcribed with their page) for the user to adjudicate each difference.

Rules (user, 2026-11-06):
- When the formulation differs (S100-16 vs S100-24, linear vs D1 section method, E/G constants), a
  difference is attributed in the first place to that formulation difference.
- An example that uses CUFSM (finite strip) for any of its values is not used for comparison: the
  repo has no numerical buckling analysis until M8. It is only listed with the reason.

Run: python tests/contrast/yu_2019.py   (tests/test_design_examples.py checks the file is current)
"""
import math
import sys
from pathlib import Path
from typing import Any

from cfs_design.codes.aisi_s100_24 import appendix_2 as a2
from cfs_design.execution import execute_payload

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "validation-yu-2019.md"
IN, KIP, KSI = 25.4, 4448.2216152605, 6.894757293168
IN2, IN3, IN4 = IN**2, IN**3, IN**4
KIP_IN = KIP * IN                                     # N·mm per kip-in
MATERIAL = "ASTM A653 SS Grade 50 Class 1"           # Fy does not enter the contrasted magnitudes

SAME = "igual"
F_EDITION = "distinta: S100-16 vs S100-24"
F_METHOD = "distinta: método lineal (libro) vs D1 (repo)"
F_CONST = "igual salvo E, G (29 500 / 11 300 ksi vs 203 000 / 78 000 MPa)"

Row = tuple[str, float, float, str, str]      # magnitude, book, repo, unit, formulation

# examples that use CUFSM somewhere: not used for comparison (rule of 2026-11-06)
EXCLUDED = (
    ("Ejemplo 3.9, pp. 113-114", "9CS2.5×059: Pcrd y Mcrd por CUFSM (además de las tablas del Manual)"),
    ("Ejemplo 3.10, pp. 114-115", "C/U con labios 8 × 8 × 1,34: Mcrℓ, Mcrd, eje neutro e inercia por CUFSM"),
    ("Ejemplo 4.12, pp. 160-162", "Vigueta 800S200-97: Mcrℓ y Mcrd por CUFSM"),
    ("Ejemplo 5.3, pp. 245-247", "Canal sin labio 8 × 3 × 0,135: Pcrℓ por CUFSM (además, forma fuera de DC-9)"),
)


def _member(H: float, B: float, D: float, t: float, R: float, **extra: Any) -> dict[str, Any]:
    payload = {"section": {"shape": "C_LIPPED", "H": H * IN, "B": B * IN, "D": D * IN, "t": t * IN, "R": R * IN},
               "material": MATERIAL, "cases": [{"name": "contrast", "Pu": 1.0}], **extra}
    return execute_payload(payload)


def _flange(result: dict[str, Any]) -> a2.FlangeProperties:
    el, t = result["section"]["elements"], result["section"]["dimensions"]["t"]
    return a2.flange_properties_c(el["b_mid"], el["d_mid"], t)


def _flange_rows(f: a2.FlangeProperties, book: dict[str, float]) -> list[Row]:
    units = {"Af": ("in²", IN2), "Jf": ("in⁴", IN4), "Ixf": ("in⁴", IN4), "Iyf": ("in⁴", IN4), "Ixyf": ("in⁴", IN4),
             "xof": ("in", IN), "xhf": ("in", IN), "yof": ("in", IN)}
    return [(f"{k} (Tabla 2.3.3-1)", v, getattr(f, k) / units[k][1], units[k][0], SAME) for k, v in book.items()]


def example_3_8() -> tuple[str, str, list[Row]]:
    """C 10 x 3.5 x 0.72 x 0.075 in; R = 3/32 in from w = 3.50 - 2(R + t) = 3.1624 (Ex. 4.5, p. 138)."""
    r = _member(10.0, 3.5, 0.72, 0.075, 0.09375, flexure={"Cb": 1.0})
    f, t, ho = _flange(r), 0.075 * IN, 10.0 * IN
    d = r["buckling"]["flexure_x"]["distortional"]
    ld = d["Ld_mm"]
    rows = _flange_rows(f, {"Af": 0.308, "Ixf": 0.00708, "Iyf": 0.376, "Ixyf": 0.0249, "xof": 1.428, "yof": -0.0567,
                            "xhf": -1.997, "Jf": 0.000578})
    rows += [
        ("Lcrd flexión x (Ec. 2.3.3.2-4)", 27.07, d["Lcrd_mm"] / IN, "in", F_CONST),
        ("k̄φfe (Ec. 2.3.3.1-3)", 0.429, a2.k_phi_fe(f, ld) / KIP, "kip", F_CONST),
        ("k̄φwe (Ec. 2.3.3.2-5)", 0.391, a2.k_phi_we_flexure_perpendicular(t, ho, ld) / KIP, "kip", F_EDITION),
        ("k̃φfg (Ec. 2.3.3.2-6)", 0.0220, a2.k_phi_fg_flexure(f, ld) / IN2, "in²", F_EDITION),
        ("k̃φwg (Ec. 2.3.3.2-7)", 0.00286, a2.k_phi_wg_flexure_perpendicular(t, ho, ld, 2.0) / IN2, "in²", F_EDITION),
        ("Fcrd flexión x", 32.98, d["stress_MPa"] / KSI, "ksi", F_EDITION),
        ("Sf = Sx", 4.11, r["section"]["properties"]["Sx"] / IN3, "in³", F_METHOD),
        ("Mcrd flexión x", 135.55, d["value"] * 1e6 / KIP_IN, "kip·in", F_EDITION),
    ]
    return ("Ejemplo 3.8, pp. 111-113", "C 10 × 3,5 × 0,72 × 0,075 in, R = 0,09375 in (de w = 3,1624 in, Ej. 4.5). "
            "Distorsional en flexión alrededor de x por las ecuaciones de S100-16 (Ecs. 3.106-3.116 del libro). "
            "La parte A del ejemplo (método simplificado del Commentary) no se contrasta: el repo no lo implementa.", rows)


EXAMPLES = (example_3_8,)


def _attribution(book: float, repo: float, formulation: str) -> tuple[str, str]:
    diff = (repo / book - 1) * 100 if book else math.nan
    text = f"{diff:+.1f} %"
    if abs(diff) <= 0.5:
        return text, "coincide (redondeo o constantes)"
    if not formulation.startswith("igual"):
        return text, "formulación distinta (primera instancia)"
    if formulation.startswith("igual salvo"):
        return text, "sin explicar por E, G; revisar"
    return text, "sin explicar; revisar"


def _fmt(v: float) -> str:
    return f"{v:.4g}" if abs(v) < 1e4 else f"{v:.0f}"


def existing_verdicts() -> dict[tuple[str, str], str]:
    """(example title, magnitude) -> the user's verdict already written in the report."""
    if not OUTPUT.exists():
        return {}
    verdicts, title = {}, ""
    for line in OUTPUT.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
        cells = line.split("|")
        if len(cells) == 10 and cells[1].strip() not in {"Magnitud", "---"} and cells[8].strip():
            verdicts[(title, cells[1].strip())] = cells[8].strip()
    return verdicts


def render(verdicts: dict[tuple[str, str], str] | None = None) -> str:
    verdicts = verdicts or {}
    lines = [
        "# Validación con ejemplos de Yu, LaBoube y Chen (2019)",
        "",
        "Contraste externo de los resultados del repositorio con los ejemplos resueltos de *Cold-Formed Steel Design*,",
        "5.ª ed. (Wiley, 2019), que está en `references/`. **El libro sigue AISI S100-16 y el Manual AISI 2017, no",
        "S100-24**, y no es un oráculo. Este archivo lo genera `tests/contrast/yu_2019.py`; no se edita a mano, salvo la",
        "columna *Dictamen*, que se copia al regenerar.",
        "",
        "**Reglas (usuario, 2026-11-06).**",
        "",
        "- Si la formulación difiere, la diferencia se atribuye en primera instancia a esa diferencia de formulación. El",
        "  usuario dirime cada caso en la columna *Dictamen*.",
        "- Un ejemplo que use CUFSM (franjas finitas) en cualquiera de sus valores no se usa para comparar: el repo no",
        "  tiene análisis numérico hasta M8 (DC-2). Se lista abajo con el motivo, sin valores.",
        "",
        "| Formulación | Significado |",
        "| --- | --- |",
        f"| {SAME} | Misma ecuación en S100-16 y S100-24 y mismo modelo |",
        f"| {F_CONST} | Misma ecuación; el libro usa E = 29 500 ksi (203 395 MPa) y G = 11 300 ksi (77 911 MPa) |",
        f"| {F_EDITION} | La ecuación cambió de 2016 a 2024 |",
        f"| {F_METHOD} | Propiedades de sección: línea media con arcos (libro) frente a esquinas exactas (D1) |",
        "",
        "Atribución preliminar: *coincide* si |dif| ≤ 0,5 %; *formulación distinta* si la formulación difiere; *sin",
        "explicar; revisar* si la formulación es igual y la diferencia supera 0,5 %. Valores en las unidades del libro.",
    ]
    counts: dict[str, int] = {}
    for build in EXAMPLES:
        title, description, rows = build()
        lines += ["", f"## {title}", "", description, "",
                  "| Magnitud | Libro | Repo | Unidad | Dif. | Formulación | Atribución preliminar | Dictamen |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for name, book, repo, unit, formulation in rows:
            diff, attribution = _attribution(book, repo, formulation)
            counts[attribution] = counts.get(attribution, 0) + 1
            verdict = verdicts.get((title, name), "")
            lines.append(f"| {name} | {_fmt(book)} | {_fmt(repo)} | {unit} | {diff} | {formulation} | {attribution} | {verdict} |")
    lines += ["", "## Ejemplos excluidos (usan CUFSM)", "", "| Ejemplo | Motivo |", "| --- | --- |"]
    lines += [f"| {title} | {reason} |" for title, reason in EXCLUDED]
    lines += ["", "## Resumen", "", "| Atribución preliminar | Filas |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(existing_verdicts()), encoding="utf-8")
    sys.stdout.write(f"written {OUTPUT}\n")
