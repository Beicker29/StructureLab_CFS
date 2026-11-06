# Pruebas y validación

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy
python -m pytest -q
python -m build            # opcional: comprueba el empaquetado
```

La CI (`.github/workflows/ci.yml`) ejecuta lo mismo en Windows y Ubuntu con Python 3.12,
vuelve a correr los oráculos exigiendo que `tests/fixtures` no cambie, y ejecuta la wheel
instalada fuera del repositorio.

## Suite

| Archivo | Garantía |
| --- | --- |
| `tests/test_inputs.py` | Rechazo de entradas inválidas o incompletas |
| `tests/test_materials.py` | Catálogo de aceros contra la Tabla A3.1.1-1 de S100-24; condiciones de A3.1.1; Fu no se supone |
| `tests/test_engine.py` | Cada demanda va a su capítulo y método; precedencia de estados; material o sección bloqueados |
| `tests/test_design_examples.py` | El informe de contraste con Yu (2019) coincide con lo que calcula el código hoy |
| `tests/test_compression.py` | Capítulo E por DSM: ecuaciones a mano (forma 2024), capacidad φcPn, Tabla B4.1-1, λ > 5, `both` y bloqueos (con doble de prueba del material) |
| `tests/test_buckling.py` | Apéndice 2.3: identidades de la transcripción (Tabla 2.3.3-1 Z(90°) = C, ecuaciones no fusionadas), casos límite, selección del modo y bloqueos |
| `tests/test_sections.py` | Motor geométrico contra las 125 filas de `Sections.xlsx` (±0,5 %), control en forma cerrada (C de esquinas rectas), origen `catalog`/`geometry` y bloqueos |
| `tests/test_interfaces.py` | CLI sin escritura por defecto, `--output`, errores con código 2, ejemplos |

## Oráculo independiente

Desde M1, cada capítulo tiene `tests/oracles/<nombre>.py`, escrito directamente desde
S100-24, en Decimal, **sin importar `cfs_design`** y en una sesión distinta de la que escribe
la implementación. Las pruebas consumen el resultado congelado
`tests/fixtures/<nombre>/reference.json`. Para añadir un caso, editar el oráculo,
regenerarlo (`python tests/oracles/<nombre>.py`) y revisar el diff: un valor de referencia
solo cambia por una razón normativa documentada, nunca para que pase el software.

## Contraste externo

Ejemplos resueltos de Yu, LaBoube y Chen, *Cold-Formed Steel Design*, 5.ª ed. (2019; sigue S100-16):
`tests/contrast/yu_2019.py` calcula los valores del repo y genera
[docs/validation-yu-2019.md](docs/validation-yu-2019.md) junto a los del libro, con la formulación de cada
fila y una atribución preliminar. **El usuario dirime cada diferencia** en la columna *Dictamen*, que se
conserva al regenerar. Si la formulación difiere (S100-16 vs S100-24, método de propiedades, CUFSM), la
diferencia se atribuye en primera instancia a la formulación. Un ejemplo que use CUFSM en cualquiera de sus
valores no se usa para comparar (el repo no tiene análisis numérico hasta M8); solo se lista con el motivo.
`tests/test_design_examples.py` exige que el
informe esté al día con el código. Más adelante, el Manual AISI y CUFSM. Nada de esto reemplaza al oráculo.

```powershell
python tests/contrast/yu_2019.py   # regenera el informe tras un cambio de cálculo
```

## Reglas

- No declarar validación normativa a partir de pruebas que comparan el motor consigo mismo.
- Un dominio sin datos o sin decisión se bloquea (`INCOMPLETE`); nunca se supone un valor.
- Las salidas generadas (`results/`, temporales) no se versionan.
