# StructureLab_CFS

Motor de cálculo de la **resistencia de miembros de acero formado en frío** según AISI S100-24
(North American Specification for the Design of Cold-Formed Steel Structural Members, 2024),
solo LRFD, por los dos métodos de la norma: **Método de Resistencia Directa (DSM)** y **Método
del Ancho Efectivo (EWM)**. Las propiedades de sección de los perfiles C y Z se leen
del catálogo `data/Sections.xlsx` o, fuera de él, se calculan desde la geometría de pared
delgada; el resultado indica el origen. Las cargas críticas elásticas salen del Apéndice 2 (analítico) o, como extra
opcional, de franjas finitas.

> **Estado: hitos M1 (secciones) y M2 (pandeo elástico), pendientes de validación.** El motor
> valida la entrada, resuelve el material y la sección, calcula las cargas críticas elásticas y
> asigna cada demanda a su capítulo, pero ningún capítulo de resistencia está implementado: el resultado es siempre
> `INCOMPLETE` con el motivo y el hito que lo cubrirá. Ver la [hoja de ruta](docs/ROADMAP.md).

> No es una certificación AISI. `PASS` significará que se evaluaron todos los estados límite
> exigidos para cada demanda dentro del alcance declarado. El análisis de segundo orden
> (Capítulo C), las combinaciones de carga, las conexiones (J) y los ensambles (I) quedan fuera.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\Activate.ps1
```

## Uso

```powershell
python -m cfs_design.run examples/c_lipped.json                  # imprime JSON
python -m cfs_design.run examples/c_lipped.json --output r.json  # además lo guarda
```

Desde Python:

```python
from cfs_design.execution import execute_payload

result = execute_payload({
    "section": {"shape": "C_LIPPED", "H": 203.2, "B": 63.5, "D": 15.9, "t": 1.519, "R": 3.2},
    "material": "ASTM A653 SS Grade 50 Class 1",
    "lengths": {"Lx": 3000, "Ly": 1000, "Lz": 1000},
    "cases": [{"name": "1.2D + 1.6L", "Pu": 18.0, "Mux": 2.1}],
})
print(result["status"])  # INCOMPLETE en M0
```

### Entrada (unidades: mm, MPa, kN, kN·m)

Un archivo por miembro; los datos del miembro van arriba y sus combinaciones en `cases`.

| Campo | Descripción |
| --- | --- |
| `section` | `name` de `data/Sections.xlsx` (p. ej. `PHR Z203x67x19-2.0`) o `shape` con dimensiones exteriores `H`, `B`, `D`, espesor de diseño `t`, radio interior `R` y `lip_angle` (grados; obligatorio en la Z, 90 en la C). Por ahora solo se calculan `C_LIPPED` y `Z_LIPPED`; las demás formas (`C_UNLIPPED`, `HAT`, `ANGLE`, `ANGLE_LIPPED`, `SIGMA`) dan `INCOMPLETE` |
| `material` | Nombre de `src/cfs_design/data/Materiales.xlsx` (Fy de la Tabla A3.1.1-1); no se aceptan Fy ni Fu numéricos |
| `lengths` | `Lx`, `Ly`, `Lz`: longitudes no arriostradas (mm) |
| `factors` | `Kx`, `Ky`, `Kt` (1 por defecto) |
| `method` | `DSM` (por defecto) o `EWM` calculan solo ese método; `both` calcula y reporta los dos |
| `buckling` | `source`: `analytical` (por defecto) o `fsm` (M8); `Lm`: distancia entre restricciones discretas del pandeo distorsional (mm, obligatoria para el distorsional); `k_phi`: rigidez rotacional continua en la unión ala/alma (N·mm/mm/rad; si falta, 0 conservador según 2.3.3) |
| `flexure` | `Cb` (obligatorio para Mcre), `inelastic_reserve` |
| `web_crippling` | `N` (mm), `load_case` (`EOF`, `IOF`, `ETF`, `ITF`), `fastened` |
| `cases[]` | `name` y demandas: `Pu` (> 0 compresión, < 0 tracción), `Mux`, `Muy`, `Vux`, `Vuy`, `Pw`, `Bu` |

### Salida

`status` (`PASS`/`FAIL`/`INCOMPLETE`), `ratio`, `governing`, `material`, `section` (origen
`catalog` o `geometry`, dimensiones, propiedades y anchos planos con las relaciones de la
Tabla B4.1-1; ver [secciones](docs/chapter-sections.md)), `buckling` (Pcre, Pcrl, Pcrd y Mcre,
Mcrl, Mcrd por el Apéndice 2.3; ver [pandeo elástico](docs/chapter-appendix-2.md)) y `cases`, cada uno
con una comprobación por demanda (`compression`, `tension`, `flexure_x`, `flexure_y`,
`shear_x`, `shear_y`, `web_crippling`, `torsion`) más `interaction` cuando actúan juntas.
Cada comprobación trae `chapter`, `demand`, `capacity` (φRn), `ratio`, `method`, `result` y
`errors`. Un dominio no soportado o con datos faltantes devuelve `INCOMPLETE` con el motivo;
nunca una resistencia supuesta.

## Documentación

- [Reglas de trabajo](AGENTS.md) · [Notas para Claude Code](CLAUDE.md)
- [Arquitectura](docs/architecture.md)
- [Decisiones de proyecto](docs/decisions.md)
- [Hoja de ruta](docs/ROADMAP.md)
- [Pruebas y validación](CONTRIBUTING.md)
