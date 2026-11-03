# Hoja de ruta

Un hito por sesión de Claude Code. Un hito cierra solo con su oráculo en verde, el contraste
externo documentado y su `docs/chapter-<x>.md` actualizado. Unidades: mm, MPa, kN; solo LRFD.

| Hito | Entrega | Criterio de cierre | Estado |
| --- | --- | --- | --- |
| M0 Esqueleto | Reglas, `.claude/`, pyproject, CI, modelos de entrada y salida, errores, catálogo de aceros, motor y CLI que devuelven `INCOMPLETE` | CI verde en Windows y Ubuntu | Cerrado (2026-11-03): CI verde en windows-2022 y ubuntu-24.04, run 41641602831 |
| M1 Secciones | `sections/`: lector de `Sections.xlsx` (C y Z con labio, `t_design_mm`) con validación de esquema; motor geométrico (línea media, esquinas redondeadas): A, I, Ixy, S, r, J, Cw, xo, j, ejes principales de la Z, Sy en ambas fibras, Zx, Zy, anchos planos y relaciones de B4.1-1; origen `catalog`/`geometry` en el resultado | Oráculo de secciones; motor geométrico contra las propiedades del Excel ±0,5 % | Implementado (2026-11-03); coherencia con el Excel verificada. Oráculo y contraste con el Manual **en espera hasta nuevo aviso del usuario** ([chapter-sections](chapter-sections.md)) |
| M2 Pandeo analítico | `codes/aisi_s100_24/appendix_2.py` y `buckling/analytical.py`: Fcre, Mcre, Fcrl, Fcrd, Mcrd; propiedades del ala con labio para el distorsional (Apéndice 2.3.3). Vcr pasa a M5 (D9) | Oráculo del Apéndice 2; Pcrd frente a CUFSM documentado | Implementado (2026-11-03). Oráculo y CUFSM en espera hasta nuevo aviso ([chapter-appendix-2](chapter-appendix-2.md)) |
| M3 Compresión DSM | E2, E2.1, E3.2, E4 y `domain/applicability.py` (Tabla B4.1-1). Al inicio: `method: both` da una comprobación por método (DC-1) | Oráculo E; ejemplos DSM del Manual | Siguiente |
| M4 Flexión DSM | F2.2, F3.2, F4 y reserva inelástica | Oráculo F; ejemplos DSM del Manual | |
| M5 Tracción, cortante y web crippling | D2, D3, G2, G2.3 y Vcr del Apéndice 2.3.4 (desde M2, D9), G3, G5, G6 (tablas de G5 versionadas) | Oráculos D y G | |
| M6 Interacción y memoria | H1, H2, H3; memoria en texto y PDF | Oráculo H; ejemplos con varias combinaciones | |
| M7 EWM | Apéndice 1 (1.1 a 1.4), E3.1, F3.1, F2.1.1, F3.1.1; `method: EWM` y `both` | Oráculo del Apéndice 1; contraste DSM frente a EWM documentado | |
| M8 FSM y torsión | `buckling/fsm.py` (extra `[fsm]`), G8 y H4 por bimomento | Paridad con CUFSM; oráculo G8/H4 | |

**Oráculos en espera (decisión del usuario, 2026-11-03):** hasta nuevo aviso, los hitos se
implementan sin oráculo independiente; el oráculo y el contraste con el Manual AISI se harán
cuando el usuario suba el documento. Mientras tanto ningún hito se marca como cerrado, solo
como implementado.

Después de M8: ensambles del capítulo I (I1.1, I1.2) y conexiones del capítulo J, cada uno con
su documento de alcance antes de escribir código.
