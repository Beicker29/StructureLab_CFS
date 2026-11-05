# Capítulo E: miembros en compresión (M3)

Compresión de miembros C y Z con labio por el Método de Resistencia Directa (DSM), AISI S100-24.

| Qué | Dónde |
| --- | --- |
| Fórmulas | `codes/aisi_s100_24/compression.py` |
| Comprobación | `domain/compression.py` |
| Límites de la Tabla B4.1-1 | `domain/applicability.py` |
| Obligaciones de E1 | `domain/coverage.py` |
| Validación A3.1.1 del material | `materials.py` |

**Estado:** implementado (2026-11-03).
**Pendiente:** oráculo E y ejemplos DSM del Manual, en espera (DC-10).
**EWM (E3.1):** llega con M7. Mientras tanto, con `method: EWM` o `both` la comprobación EWM queda `INCOMPLETE`.

## Base normativa (transcrita de las imágenes de las páginas)

| Disposición | Ecuaciones | Página |
| --- | --- | --- |
| E1 | φcPn es el menor de E2, E3 y E4 cuando aplican | 43 |
| E2 | Pne = Ag·Fn (E2-1); Fn = 0,658^(λc²)·Fy si λc ≤ 1,5 (E2-2), o (0,877/λc²)·Fy si λc > 1,5 (E2-3); λc = √(Fy/Fcre) (E2-4); φc = 0,85 | 43 |
| E3.2 | Pnℓ = 1,2·Pne·(1 + 0,10λℓ²)/(1 + 0,55λℓ²) ≤ Pne, para λℓ ≤ 5 (E3.2-1); λℓ = √(Pne/Pcrℓ) (E3.2-2); φc = 0,85 | 44, 45 |
| E4 | Pnd = 1,2·Py·(1 + 0,05λd²)/(1 + 0,67λd²) ≤ Py, para λd ≤ 5 (E4-1); λd = √(Py/Pcrd) (E4-2); Py = Ag·Fy (E4-3); φc = 0,85. Aplica a C y Z con alas de borde rigidizado | 46 |
| B4.1, Tabla B4.1-1, columna DSM | w/t ≤ 500, b/t ≤ 160, d/t ≤ 60, h/t ≤ 300, R/t ≤ 20, do/bo ≤ 0,7, Fy ≤ 655 MPa (nota f: ver A3) | 25, 26 |
| A3.1.1 | Uso sin restricción si Fu/Fy ≥ 1,08 y elongación ≥ 10 % en 50 mm o ≥ 7 % en 200 mm | 14, 15 |

**Diferencia con ediciones anteriores:** las Ecs. E3.2-1 y E4-1 de 2024 no tienen la forma de esas ediciones. Lo verifica la prueba `test_pnl_e3_2_and_pnd_e4_use_the_2024_coefficients`.

**No aplican:**
- E2.1 (sección cajón) y E3.3 (tubos).
- Las variantes con agujeros (E3.2-3, E3.2-4, E4-4).
- La flexión adicional de los ángulos (H1.2).

## Decisiones (aprobadas por el usuario el 2026-11-05)

| Id | Decisión |
| --- | --- |
| D12 | **Filas de la Tabla B4.1-1 por solicitación.** En compresión se aplican w/t, b/t, d/t, R/t, do/bo y Fy. h/t ≤ 300 ("element in bending") entra con la flexión. La interacción (capítulo H) usa la unión de las filas de las solicitaciones que intervienen. Si se excede un límite, el estado es `OUT_OF_METHOD_SCOPE` con referencia a B4.2, que no se automatiza. El tipo de rigidizador (labio simple) y n_f = n_fe = n_w = 0 se cumplen siempre en el alcance de DC-9 |
| D13 | **λℓ > 5 o λd > 5 da `OUT_OF_METHOD_SCOPE`**, sin extrapolar. El "rational approach" del Commentary no se usa. E3.1 (EWM) queda registrada como alternativa futura para el pandeo local |
| D14 | **Lm faltante: Lm = Lcrd y kφ = 0**, con el supuesto reportado en `Lm_source`. Es el caso conservador, porque supone que no hay restricción discreta más corta que la semionda crítica. Vale para el distorsional en compresión y en flexión, porque es la misma función de `buckling/`. `INCOMPLETE` solo si no se identifica el modo distorsional. Si falta una obligación de E1, la capacidad es nula |
| D15 | **Material.** Cada acero se valida contra A3.1.1: el grado está en la Tabla A3.1.1-1 (prueba `test_catalog_matches_table_a3_1_1`), Fu/Fy ≥ 1,08 y elongación mínima. Fu, la elongación y su fuente son datos obligatorios de `Materiales.xlsx`. S100-24 no los tabula: se transcriben de cada norma ASTM. Sin ellos, todo diseño queda `INCOMPLETE`. Un acero que no cumple pertenece a A3.1.2 o A3.1.3, cuyas restricciones no se automatizan, y queda `INCOMPLETE` |
| D16 | **v1 sin incremento por conformado en frío** (A3.3.2). Confirma DC-6 |

**Estados** (D14; precedencia que extiende DC-1):

| Estado | Significado |
| --- | --- |
| `PASS` / `FAIL` | Hay capacidad y razón |
| `INCOMPLETE` | Falta un dato o una regla implementada |
| `OUT_OF_METHOD_SCOPE` | El miembro está fuera del alcance del método |
| `NOT_APPLICABLE` | El estado límite no aplica |

- **Precedencia en el caso y el miembro:** INCOMPLETE > OUT_OF_METHOD_SCOPE > FAIL > PASS. NOT_APPLICABLE no cuenta salvo que todas las comprobaciones lo sean.
- **Capacidad:** solo se reporta con PASS o FAIL.

## Comprobación

1. **Método.** Con un método distinto de DSM, la comprobación queda `INCOMPLETE` (M7).
2. **Tabla B4.1-1.** Las filas de compresión (D12); si alguna se excede, `OUT_OF_METHOD_SCOPE`.
3. **E2, E3.2 y E4,** con Fcre, Pcrℓ y Pcrd del bloque `buckling` (M2).
   - Si a una obligación le falta un insumo, se informan los demás valores y la comprobación queda `INCOMPLETE` sin capacidad.
   - Si λ > 5, `OUT_OF_METHOD_SCOPE`.
4. **Resultado.** φcPn con Pn = min(Pne, Pnℓ, Pnd); razón = Pu/φcPn; `PASS` si la razón es ≤ 1.

## Verificación (sin oráculo)

| Prueba | Qué comprueba |
| --- | --- |
| Fn de E2 a mano | E2-2 y E2-3; continuidad en λc = 1,5 (≤ 10⁻³) |
| Pnℓ y Pnd a mano | Coeficientes de 2024; tope Pne y Py |
| Capacidad | 0,85·min(Pne, Pnℓ, Pnd), modo que gobierna y razón |
| Bloqueos | Tabla B4.1-1 (w/t, d/t, do/bo); λℓ > 5; Lz faltante; EWM; material sin validar |
| A3.1.1 | Límites de Fu/Fy y de elongación en 50 y 200 mm |

Las pruebas del motor usan un doble de prueba del material: Fu = 1,3·Fy y elongación 20 % en 50 mm, valores inventados y marcados así. El catálogo real todavía no tiene Fu ni elongación.

## Pendiente

- **Fu, elongación y su fuente** en `Materiales.xlsx`, transcritos de las normas ASTM A653, A1003 y A1011. Hasta entonces ningún diseño real da capacidad.
- Oráculo E y ejemplos DSM del Manual (DC-10).
- EWM, E3.1 con el Apéndice 1 (M7).
