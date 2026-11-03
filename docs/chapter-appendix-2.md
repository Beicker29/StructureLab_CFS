# Apéndice 2: pandeo elástico analítico (M2)

Cargas críticas elásticas de miembros C y Z con labio por AISI S100-24, Apéndice 2.3.

| Qué | Dónde |
| --- | --- |
| Fórmulas | `codes/aisi_s100_24/appendix_2.py`; coeficientes k en `appendix_1.py` |
| Selección según forma y eje | `buckling/analytical.py` |
| Salida | Bloque `buckling` del resultado, a nivel de miembro |

**Estado:** implementado (2026-11-03).
**Pendiente:** oráculo independiente y contraste de Pcrd con CUFSM, en espera hasta nuevo aviso (DC-10).
**Uso de estos valores:** ningún capítulo de resistencia los consume todavía; entran en M3 (compresión) y M4 (flexión).

## Base normativa

Las ecuaciones de 2.3.3 y las del Apéndice 1 salían ilegibles como texto, así que se transcribieron sobre imágenes de las páginas del PDF.

| Disposición | Ecuaciones | Página |
| --- | --- | --- |
| Constantes | E = 203 000 MPa, G = 78 000 MPa (2.3.1); μ = 0,30 (Symbols) | 2-3; xxxii |
| 2.1 Conversión | Pcr = Ag·Fcr (2.1-1); Mcr = Sfc·Fcr (2.1-2) | 2-1 |
| 2.3.1 Global | Pex, Pey, Pt, β (2.3.1-1 a -4) | 2-3 |
| 2.3.1.1 Compresión | Fcre (2.3.1.1-1); flexión (2.3.1.1.1-1); flexotorsión de la C (2.3.1.1.2-1); torsión de la Z (2.3.1.1.3) | 2-5, 2-6 |
| 2.3.1.2 Flexión | Fcre = Mcre/Sfc (2.3.1.2-1); C sobre x (2.3.1.2.1-1); C sobre y (2.3.1.2.2-1, con Cs·\|j\|); Z sobre x (2.3.1.2.3-1) | 2-7, 2-8 |
| 2.3.2 Local | Fcr de placa (2.3.2.1-2 / 2.3.2.2-2); Pcr (2.3.2.1-1); Mcr (2.3.2.2-1) | 2-10, 2-11 |
| Apéndice 1 | k = 4 (1.1); 0,43 (1.2.1); Ecs. 1.1.2-2 y 1.1.2-8; Ecs. 1.2.2-2 y 1.2.2-3 | 1-1, 1-4, 1-9, 1-10 |
| Tabla 2.3.3-1 | Columnas C y Z como funciones separadas | 2-12 |
| 2.3.3.1 Distorsional, compresión | 2.3.3.1-1 a -7 | 2-13, 2-14 |
| 2.3.3.2 Distorsional, flexión | Caso (a), eje ⟂ alma: 2.3.3.2-1 a -7. Caso (b), eje ∥ alma con alma en tracción: 2.3.3.2-8 a -11 | 2-14 a 2-16 |

**Ecuaciones parecidas que no se fusionan:**
- **k̃φfg:** la de compresión (2.3.3.1-5) tiene un término (x_of − x_hf)²(I_xyf/I_yf)² que la de flexión (2.3.3.2-6) no tiene.
- **k̄φwe:** la de compresión (2.3.3.1-4) no depende de L_d y la de flexión (2.3.3.2-5) sí.

## Decisiones (aprobadas por el usuario el 2026-11-03)

| Id | Decisión |
| --- | --- |
| D5 | Propiedades del ala. Tabla 2.3.3-1 con dimensiones de línea media (b_mid, d_mid, h_mid de `section.elements`, la línea media con esquinas agudas) y sin radio de esquinas; columnas C y Z como funciones separadas. ho = H (alma de fuera a fuera) |
| D6 | Coeficientes k del pandeo local. Ala k = 4; labio 0,43 o Ec. 1.2.2-2/-3 según el gradiente; alma 4 o Ec. 1.1.2-2. **Condición del usuario:** k = 4 en el ala supone que el labio la sostiene como un apoyo simple. Si el labio no alcanza para eso, la falla es distorsional y se calcula aparte (2.3.3); el pandeo local no la cubre |
| D7 | k̄φ = 0 y β = 1,0 si no se dan (2.3.3.1, 2.3.3.2 y Ec. 2.3.3.2-3 los permiten como valores conservadores), y se reportan siempre en el resultado. Cb y Lm son obligatorios (AGENTS.md). `Lm` va en `buckling` porque lo usa también el distorsional en compresión. Con k̄φ > 0 y sin Lm, Lm = Lcrd (definición de Lm en 2.3.3) |
| D8 | Quedan `INCOMPLETE`: la Z alrededor de y (global, local y distorsional) y el distorsional de la C alrededor de y con el alma comprimida. El distorsional de la Z alrededor de x sí se calcula (ver la verificación abajo) |
| D9 | Vcr pasa a M5, junto con G2.3 y la Ec. 2.3.4-2 |
| D10 | Z en compresión: 2.3.1.1.3, mínimo entre Pt y el pandeo por flexión sobre x e y, más el pandeo sobre el eje principal menor (I2) con max(KxLx, KyLy), según 2.3.1.1.1 |
| D11 | Mcrl. Cada placa con su k según el gradiente de esfuerzos de la sección bruta, evaluado sobre la línea media en los extremos de cada tramo plano. Su Fcr en el punto más comprimido se extrapola linealmente a la fibra extrema comprimida (User Note de 2.3.2.2) y gobierna el menor. Un ala con una parte en tracción se trata con la Ec. 1.1.2-2. Un labio con tracción queda `INCOMPLETE` |

### Verificación pedida en D8: la columna Z de la Tabla 2.3.3-1 con labios a 45° y 60°

- **Specification:** la sección 2.3.3 y la Tabla 2.3.3-1 (pp. 2-11 a 2-16) no limitan el ángulo θ. La columna Z es general en θ.
- **Commentary:** el límite 45° ≤ θ ≤ 90° (pp. 2-43, 2-44) es solo del "Simplified Method", que no se usa.
- **Apéndice 1.3:** el límite 140° ≥ θ ≥ 40° es de EWM.
- **Convención de la tabla:** labio hacia afuera y θ medido desde el plano del ala, la misma geometría de M1. Desarrollar x_hf con esa convención da la fórmula de la tabla, y con θ = 90° la columna Z reproduce la columna C (prueba `test_z_column_of_table_2_3_3_1_at_90_degrees_equals_c_column`).

## Salida

```text
buckling.compression                 global (Pcre, modo), local (Pcrl, elemento que gobierna), distortional (Pcrd, Lcrd, Ld)
buckling.flexure_x                   global (Mcre), local (Mcrl), distortional (Mcrd, ξweb, β)
buckling.flexure_y_tips_compression  solo la C: labios comprimidos (Cs = −1; distorsional caso b)
buckling.flexure_y_web_compression   solo la C: alma comprimida (Cs = +1; distorsional INCOMPLETE)
```

- **Unidades:** fuerzas en kN, momentos en kN·m, esfuerzos en MPa y longitudes en mm.
- **Supuestos:** el resultado trae `k_phi` y `beta_distortional` con su origen.
- **Valores bloqueados:** si a un valor le falta un dato o está fuera del alcance, trae `error` en lugar de `value`; los demás valores se calculan igual.

## Verificación (sin oráculo)

| Prueba | Qué comprueba |
| --- | --- |
| Tabla 2.3.3-1: Z con θ = 90° contra C | Coherencia de la transcripción (≤ 10⁻¹²) |
| Tabla 2.3.3-1, columna C | A_f, J_f, x_of, x_hf, y_of calculados a mano |
| 2.3.3.1-5 contra 2.3.3.2-6 | La diferencia es exactamente el término extra |
| Lcrd (2.3.3.1-7) | Fcrd(Lcrd) ≤ Fcrd(0,8·Lcrd) y Fcrd(1,25·Lcrd) |
| Pcre | Modo mínimo; Pey cerrado con Ly largo; Pft ≤ Pex en la C; eje principal menor en la Z |
| Local | k = 4 / 4 / 0,43 en compresión; k = 24 en el alma con flexión pura (ψ = 1) |
| Bloqueos | Lm, Cb o Lz faltantes bloquean solo su valor; D8; `fsm` remite a M8 |

**Ejemplo C** (203,2 × 63,5 × 15,9 × 1,519, R = 3,2, Lm = 1000):

| Valor | Resultado |
| --- | --- |
| Fcrd en compresión | 127 MPa (Lcrd = 604 mm) |
| Fcrd en flexión x | 283 MPa (Lcrd = 546 mm) |
| Fcrl en compresión | 45 MPa (alma) |
| Fcrl en flexión x | 284 MPa (alma) |

Los órdenes de magnitud son razonables, pero falta compararlos con CUFSM y con el Manual.

## Pendiente

- Oráculo del Apéndice 2 y Pcrd/Mcrd frente a CUFSM (DC-10).
- Z alrededor de y (2.3.1.2.5 biaxial) y distorsional con el alma comprimida: requieren solución numérica (M8) o una decisión nueva.
- Labio con tracción en el pandeo local (Ecs. 1.2.2-4/-5 y el caso del borde apoyado comprimido).
