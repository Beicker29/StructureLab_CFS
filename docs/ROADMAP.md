# Hoja de ruta

Un hito por sesión de Claude Code. Un hito cierra solo con su oráculo en verde, el contraste
externo documentado y su `docs/chapter-<x>.md` actualizado. Unidades: mm, MPa, kN; solo LRFD.

| Hito | Entrega | Criterio de cierre | Estado |
| --- | --- | --- | --- |
| M0 Esqueleto | Reglas, `.claude/`, pyproject, CI, modelos de entrada y salida, errores, catálogo de aceros, motor y CLI que devuelven `INCOMPLETE` | CI verde en Windows y Ubuntu | Verificado en local; CI pendiente del primer push |
| M1 Secciones | `sections/`: C con labio, U, Z con labio; esquinas redondeadas; línea media; A, I, S, r, J, Cw, xo, j; anchos planos | Oráculo de secciones; ejemplos del Manual ±0,5 % | Siguiente |
| M2 Pandeo analítico | `codes/aisi_s100_24/appendix_2.py` y `buckling/analytical.py`: Fcre, Mcre, Fcrl, Fcrd, Mcrd, Vcr | Oráculo del Apéndice 2; Pcrd frente a CUFSM documentado | |
| M3 Compresión DSM | E2, E2.1, E3.2, E4 y `domain/applicability.py` (Tabla B4.1-1) | Oráculo E; ejemplos DSM del Manual | |
| M4 Flexión DSM | F2.2, F3.2, F4 y reserva inelástica | Oráculo F; ejemplos DSM del Manual | |
| M5 Tracción, cortante y web crippling | D2, D3, G2, G3, G5, G6 (tablas de G5 versionadas) | Oráculos D y G | |
| M6 Interacción y memoria | H1, H2, H3; memoria en texto y PDF | Oráculo H; ejemplos con varias combinaciones | |
| M7 EWM | Apéndice 1 (1.1 a 1.4), E3.1, F3.1, F2.1.1, F3.1.1; `method: EWM` y `both` | Oráculo del Apéndice 1; contraste DSM frente a EWM documentado | |
| M8 FSM y torsión | `buckling/fsm.py` (extra `[fsm]`), G8 y H4 por bimomento | Paridad con CUFSM; oráculo G8/H4 | |

Después de M8: ensambles del capítulo I (I1.1, I1.2) y conexiones del capítulo J, cada uno con
su documento de alcance antes de escribir código.
