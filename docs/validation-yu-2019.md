# Validación con ejemplos de Yu, LaBoube y Chen (2019)

Contraste externo de los resultados del repositorio con los ejemplos resueltos de *Cold-Formed Steel Design*,
5.ª ed. (Wiley, 2019), que está en `references/`. **El libro sigue AISI S100-16 y el Manual AISI 2017, no
S100-24**, y no es un oráculo. Este archivo lo genera `tests/contrast/yu_2019.py`; no se edita a mano, salvo la
columna *Dictamen*, que se copia al regenerar.

**Reglas (usuario, 2026-11-06).**

- Si la formulación difiere, la diferencia se atribuye en primera instancia a esa diferencia de formulación. El
  usuario dirime cada caso en la columna *Dictamen*.
- Un ejemplo que use CUFSM (franjas finitas) en cualquiera de sus valores no se usa para comparar: el repo no
  tiene análisis numérico hasta M8 (DC-2). Se lista abajo con el motivo, sin valores.

| Formulación | Significado |
| --- | --- |
| igual | Misma ecuación en S100-16 y S100-24 y mismo modelo |
| igual salvo E, G (29 500 / 11 300 ksi vs 203 000 / 78 000 MPa) | Misma ecuación; el libro usa E = 29 500 ksi (203 395 MPa) y G = 11 300 ksi (77 911 MPa) |
| distinta: S100-16 vs S100-24 | La ecuación cambió de 2016 a 2024 |
| distinta: método lineal (libro) vs D1 (repo) | Propiedades de sección: línea media con arcos (libro) frente a esquinas exactas (D1) |

Atribución preliminar: *coincide* si |dif| ≤ 0,5 %; *formulación distinta* si la formulación difiere; *sin
explicar; revisar* si la formulación es igual y la diferencia supera 0,5 %. Valores en las unidades del libro.

## Ejemplo 3.8, pp. 111-113

C 10 × 3,5 × 0,72 × 0,075 in, R = 0,09375 in (de w = 3,1624 in, Ej. 4.5). Distorsional en flexión alrededor de x por las ecuaciones de S100-16 (Ecs. 3.106-3.116 del libro). La parte A del ejemplo (método simplificado del Commentary) no se contrasta: el repo no lo implementa.

| Magnitud | Libro | Repo | Unidad | Dif. | Formulación | Atribución preliminar | Dictamen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Af (Tabla 2.3.3-1) | 0.308 | 0.3081 | in² | +0.0 % | igual | coincide (redondeo o constantes) |  |
| Ixf (Tabla 2.3.3-1) | 0.00708 | 0.007078 | in⁴ | -0.0 % | igual | coincide (redondeo o constantes) |  |
| Iyf (Tabla 2.3.3-1) | 0.376 | 0.3763 | in⁴ | +0.1 % | igual | coincide (redondeo o constantes) |  |
| Ixyf (Tabla 2.3.3-1) | 0.0249 | 0.02494 | in⁴ | +0.2 % | igual | coincide (redondeo o constantes) |  |
| xof (Tabla 2.3.3-1) | 1.428 | 1.428 | in | -0.0 % | igual | coincide (redondeo o constantes) |  |
| yof (Tabla 2.3.3-1) | -0.0567 | -0.0567 | in | +0.0 % | igual | coincide (redondeo o constantes) |  |
| xhf (Tabla 2.3.3-1) | -1.997 | -1.997 | in | +0.0 % | igual | coincide (redondeo o constantes) |  |
| Jf (Tabla 2.3.3-1) | 0.000578 | 0.0005776 | in⁴ | -0.1 % | igual | coincide (redondeo o constantes) |  |
| Lcrd flexión x (Ec. 2.3.3.2-4) | 27.07 | 27.06 | in | -0.0 % | igual salvo E, G (29 500 / 11 300 ksi vs 203 000 / 78 000 MPa) | coincide (redondeo o constantes) |  |
| k̄φfe (Ec. 2.3.3.1-3) | 0.429 | 0.4285 | kip | -0.1 % | igual salvo E, G (29 500 / 11 300 ksi vs 203 000 / 78 000 MPa) | coincide (redondeo o constantes) |  |
| k̄φwe (Ec. 2.3.3.2-5) | 0.391 | 0.4034 | kip | +3.2 % | distinta: S100-16 vs S100-24 | formulación distinta (primera instancia) |  |
| k̃φfg (Ec. 2.3.3.2-6) | 0.022 | 0.02185 | in² | -0.7 % | distinta: S100-16 vs S100-24 | formulación distinta (primera instancia) |  |
| k̃φwg (Ec. 2.3.3.2-7) | 0.00286 | 0.002865 | in² | +0.2 % | distinta: S100-16 vs S100-24 | coincide (redondeo o constantes) |  |
| Fcrd flexión x | 32.98 | 33.66 | ksi | +2.1 % | distinta: S100-16 vs S100-24 | formulación distinta (primera instancia) |  |
| Sf = Sx | 4.11 | 4.107 | in³ | -0.1 % | distinta: método lineal (libro) vs D1 (repo) | coincide (redondeo o constantes) |  |
| Mcrd flexión x | 135.6 | 138.2 | kip·in | +2.0 % | distinta: S100-16 vs S100-24 | formulación distinta (primera instancia) |  |

## Ejemplos excluidos (usan CUFSM)

| Ejemplo | Motivo |
| --- | --- |
| Ejemplo 3.9, pp. 113-114 | 9CS2.5×059: Pcrd y Mcrd por CUFSM (además de las tablas del Manual) |
| Ejemplo 3.10, pp. 114-115 | C/U con labios 8 × 8 × 1,34: Mcrℓ, Mcrd, eje neutro e inercia por CUFSM |
| Ejemplo 4.12, pp. 160-162 | Vigueta 800S200-97: Mcrℓ y Mcrd por CUFSM |
| Ejemplo 5.3, pp. 245-247 | Canal sin labio 8 × 3 × 0,135: Pcrℓ por CUFSM (además, forma fuera de DC-9) |

## Resumen

| Atribución preliminar | Filas |
| --- | --- |
| coincide (redondeo o constantes) | 12 |
| formulación distinta (primera instancia) | 4 |
