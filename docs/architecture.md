# Arquitectura

Las capas repiten las de StructureLab_HFS y añaden dos propias del acero formado en frío:
`sections/` lee las propiedades brutas del catálogo `data/Sections.xlsx` y calcula desde la
geometría las que faltan, o todas si la sección no está en el catálogo (DC-7), y `buckling/` produce
las cargas críticas elásticas (global, local, distorsional) que DSM y EWM consumen.

Marcado: **[M0]** existe hoy; el resto entra en el hito indicado.

```text
src/cfs_design/
├── models.py              [M0] entrada (CfsCase, MemberInput) y resultado (DesignResult)
├── errors.py              [M0] errores estructurados
├── materials.py           [M0] catálogo data/Materiales.xlsx (Fy, Fu, grupo de alargamiento)
├── engine.py              [M0] una comprobación por demanda → PASS / FAIL / INCOMPLETE
├── execution.py           [M0] ejecución en memoria de un miembro (CLI y web)
├── run.py                 [M0] CLI: JSON a stdout; archivos solo con --output
├── data/                  [M0] Materiales.xlsx; Sections.xlsx (dimensiones y propiedades, C y Z)
├── sections/              [M1] resolve_section (catálogo o geometría), catalog, geometry,
│                               thin_walled, elements
├── codes/aisi_s100_24/    fórmulas puras con id de ecuación y φ
│   ├── appendix_1.py      [M2] coeficientes k de placa (1.1, 1.1.2, 1.2.1, 1.2.2)
│   ├── appendix_2.py      [M2] Pcre/Mcre, Fcr local, Tabla 2.3.3-1, distorsional (Vcr en M5)
│   ├── compression.py     [M3] E2, E2.1, E3.2, E4  ·  [M7] E3.1
│   ├── flexure.py         [M4] F2, F3.2, F4  ·  [M7] F2.1.1, F3.1, F3.1.1
│   ├── tension.py         [M5] D2, D3
│   ├── shear.py           [M5] G2, G3
│   ├── web_crippling.py   [M5] G5, G6 y coeficientes de la Tabla G5
│   ├── interaction.py     [M6] H1, H2, H3  ·  [M8] H4
│   ├── appendix_1.py      [M7] anchos efectivos 1.1 a 1.4
│   └── torsion.py         [M8] G8.1, G8.2
├── buckling/              [M2] member_buckling, analytical.py  ·  [M8] fsm.py (extra [fsm])
├── domain/                selección por capítulo, applicability (B4.1-1), coverage, validation
└── reporting/             [M6] document, text, pdf, glossary (nunca recalcula)
```

## Flujo

1. `engine.run_member(member)` valida la entrada y resuelve el material del catálogo.
2. [M1] `sections/` toma del catálogo las propiedades brutas y `t_design_mm`, o las calcula
   desde la geometría si la sección no está en el catálogo, y calcula anchos planos, ejes
   principales, Sy en ambas fibras y Zx, Zy. Reporta el origen (`catalog` o `geometry`).
3. [M3] `domain/applicability.py` comprueba la Tabla B4.1-1 para el método pedido; fuera de
   límites → `INCOMPLETE` con la variable y el límite.
4. [M2] `buckling/` obtiene Pcre/Mcre, Pcrl/Mcrl y Pcrd/Mcrd.
5. `domain/<capítulo>.py` convierte cada carga crítica en resistencia nominal con
   `codes/aisi_s100_24/`, conserva todos los modos y aplica φ al menor.
6. `domain/coverage.py` enumera desde el texto normativo los estados límite obligatorios; si
   falta alguno, el estado es `INCOMPLETE`; si no, `PASS` o `FAIL` según demanda / capacidad.

Hoy (M2) la sección se resuelve y las cargas críticas elásticas se reportan en `buckling`,
pero ningún capítulo de resistencia existe: cada demanda produce un check
`INCOMPLETE` con código `RULE_NOT_IMPLEMENTED` y el capítulo que la cubrirá. Si la sección queda
bloqueada (sin `t_design_mm` o con una forma fuera de DC-9), todas las comprobaciones quedan
`INCOMPLETE` con ese motivo.

## Responsabilidades (una fuente de verdad por concepto)

| Concepto | Propietario |
| --- | --- |
| Ecuaciones y φ de cada capítulo | `codes/aisi_s100_24/<capítulo>.py` |
| Propiedades de pared delgada | `sections/thin_walled.py` (geometría en `sections/geometry.py`) |
| Catálogo de perfiles | `sections/catalog.py` + `data/Sections.xlsx` |
| Anchos planos y relaciones de B4.1-1 | `sections/elements.py` |
| Cargas críticas elásticas | `buckling/` (fórmulas en `codes/aisi_s100_24/appendix_2.py`) |
| Si DSM o EWM aplican al miembro | `domain/applicability.py` |
| Estados límite obligatorios | `domain/coverage.py` |
| Fy, Fu y grupo de alargamiento | `materials.py` + `data/Materiales.xlsx` |
| Qué capítulo cubre cada demanda | `engine.py` (`DEMAND_CHAPTERS`) |
| PASS / FAIL / INCOMPLETE | `engine.py` |
| Presentación | `reporting/` |

Ninguna interfaz (CLI, futura web) calcula capacidades: todas llaman a `engine`.

## Cómo añadir o modificar una disposición

1. Leer la sección en el PDF de S100-24; anotar edición, ecuación, página, condiciones y
   unidades. Distinguir Specification, User Note y Commentary.
2. Escribir los casos en el oráculo independiente (`tests/oracles/<capítulo>.py`), en otra
   sesión o con el subagente `revisor-normativo`.
3. Añadir la fórmula como función pura en `codes/aisi_s100_24/<capítulo>.py`, devolviendo el
   identificador de ecuación. Una función por formulación.
4. Seleccionarla en `domain/<capítulo>.py` (forma, método, datos requeridos). Si faltan datos
   o una decisión, bloquear con error estructurado.
5. Si cambia qué es obligatorio, actualizar `domain/coverage.py` desde el texto normativo, no
   desde la selección.
6. Regenerar `tests/fixtures/<capítulo>/reference.json`, correr la verificación completa y
   actualizar `docs/chapter-<x>.md`.
