# Secciones (M1)

Propiedades de sección de miembros C y Z con labio (DC-9). Código en `src/cfs_design/sections/`.

**Estado:** implementado y verificado contra el catálogo y un control en forma cerrada.
**Pendiente:** el oráculo independiente y el contraste con el AISI Cold-Formed Steel Design
Manual, en espera hasta nuevo aviso del usuario (decisión del 2026-11-03).

## Base normativa (AISI S100-24)

| Disposición | Página | Uso |
| --- | --- | --- |
| B5 Member Properties | p. 28 | Propiedades por "conventional methods of structural design" sobre la sección completa. S100-24 no da fórmulas de A, I, J ni Cw: el método es la decisión D1 |
| A1.3 Thickness | p. 7 | t = espesor de acero base, sin recubrimiento (`t_design_mm`, DC-7) |
| A1.3 Flat Width | p. 5 | Ancho de un elemento sin las esquinas, medido en su plano |
| B4.1, Tabla B4.1-1 y notas a–f | pp. 25–26 | Definen w, b, bo, d, do, h y R. M1 calcula las relaciones; los límites se comprueban en M3 |
| Apéndice 2, Ec. 2.3.1-6 | p. 2-3 | j (propiedad de asimetría) |
| Apéndice 2, Ec. 2.3.1-7 | p. 2-4 | ro = √(rx² + ry² + xo² + yo²) |
| F2.1 (Sf, Sfc) | p. 49 | Por eso se reporta Sy en las dos fibras de la C |
| F2.2 (Zf) | p. 50 | Módulo plástico, para Mp = Zf·Fy |

## Decisiones (aprobadas por el usuario el 2026-11-03)

| Id | Decisión |
| --- | --- |
| D1 | Método de las propiedades brutas, el mismo del catálogo. A, centroide, Ix, Iy, Ixy, Zx y Zy sobre el sólido exacto (tramos rectos y esquinas como sectores de anillo de radios R y R + t). J = A·t²/3. Cw, xo y j con la coordenada sectorial de la línea media (pared delgada, esquinas como arcos de radio R + t/2), todo referido al centroide de la línea media; xo se reporta respecto al centroide del sólido. Con R = 0 la esquina es en inglete (cuadrado t × t a 90°) y la línea media tiene vértice agudo |
| D2 | Ejes. x perpendicular al alma (eje de simetría de la C), y a lo largo del alma, x positivo del alma hacia las puntas de las alas. En la C, xo < 0. En la Z, ala superior hacia +x, con Ixy > 0. θp es el ángulo antihorario desde +x al eje principal mayor |
| D3 | Ángulo de labio. `lip_angle` en grados: obligatorio en la Z; en la C es 90° por definición y otro valor se rechaza. Interpretación de D y B (ver abajo) |
| D4 | Coherencia del catálogo. Las 125 filas se comparan en pytest contra el motor geométrico (±0,5 %). Si una fila se sale, se corrige el Excel, no el código |

### Interpretación geométrica

Se determinó contra `Sections.xlsx`, porque no está definida en otro lado.

- **C_LIPPED.** Labios a 90° hacia el otro ala; D es la dimensión exterior vertical del labio; B va hasta la cara exterior del labio.
- **Z_LIPPED.** Labio inclinado **hacia afuera** (alejándose del alma), a `lip_angle` del plano del ala.
  - B se mide desde la cara exterior del alma hasta la esquina exterior aguda entre ala y labio.
  - D se mide a lo largo de la cara exterior del labio desde esa esquina.
  - **Por qué esta:** otras lecturas (labio hacia adentro, D sobre la línea media o proyectado, B hasta la punta) se apartan del Excel entre 0,5 y 47 %.
- **xcent.** En la C, distancia del centroide a la cara exterior del alma. En la Z, distancia a la fibra más alejada en x.
- **Sy.** En la C, Sy = Iy/(B − xcent), que es Sy_tip, y también se reporta Sy_web = Iy/xcent. En la Z, Sy = Iy/xcent.

## Origen de cada propiedad (DC-7)

| Propiedad | Perfil de catálogo | Sección por geometría |
| --- | --- | --- |
| A, xcent, xo, J, Cw, j_asym, Ix, Iy, Ixy, Sx, Sy, rx, ry, ro | Excel | Motor geométrico |
| Sy_web, Sy_tip (C); I1, I2, θp (Z) | Derivadas de Ix, Iy, Ixy y xcent del Excel | Derivadas de las calculadas |
| Zx, Zy, anchos planos y relaciones de B4.1-1 | Motor geométrico con `t_design_mm` | Motor geométrico |

La propiedad de asimetría j (Ec. 2.3.1-6) se reporta como `j_asym`, para que no choque con
`J` en lectores de JSON que no distinguen mayúsculas (p. ej. `ConvertFrom-Json` de PowerShell).
El resultado trae `section.source` = `catalog` o `geometry`. Un perfil de catálogo sin
`t_design_mm` o una forma fuera de DC-9 dejan el miembro `INCOMPLETE`. Un nombre que no está
en el catálogo es una entrada inválida y sale con código 2.

## Verificación

| Prueba | Resultado (2026-11-03) |
| --- | --- |
| Motor geométrico contra las 125 filas del Excel | Máxima diferencia relativa: j 9,0·10⁻⁴; Cw 2,1·10⁻⁵; las demás ≤ 6,8·10⁻⁶ (redondeo a 6 cifras del Excel) |
| C de esquinas rectas (100 × 50 × 15 × 2), a mano con rectángulos | A, Ix, J, Zx, Zy, h, b y d exactos (≤ 10⁻⁹) |

- **Las 125 filas no son una validación normativa.** El Excel se calculó con el mismo método D1; la comparación solo muestra que el catálogo y el motor son coherentes entre sí.
- **Hipótesis sobre la diferencia en j (0,09 %):** el Excel podría haber integrado x³ y x·y² de otra forma. Con integrales sobre el sólido exacto la diferencia baja a 3,5·10⁻⁴, pero se conservó D1.
- **Hipótesis sobre Cw:** la de 2·10⁻⁵ podría venir de una discretización de las esquinas en el Excel.
- **El catálogo manda:** para perfiles de catálogo el motor usa los valores del Excel, así que estas diferencias no afectan el diseño.

## Pendiente

- Oráculo independiente en `tests/oracles/sections.py`, en espera hasta nuevo aviso. La definición de `revisor-normativo` ya tiene Write, Edit y PowerShell.
- Contraste con el Manual AISI en `docs/design-examples.md`, cuando el usuario suba el documento.
- Hoja Notas del Excel: sigue citando la hoja `Acesco_publicado`, que no existe, y el "Pendiente de criterio" del espesor de los PAG. Es informativa y no afecta el cálculo.
