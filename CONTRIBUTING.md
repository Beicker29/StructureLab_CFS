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
| `tests/test_materials.py` | Catálogo de aceros contra la Tabla A3.1.1-1 de S100-24; Fu no se supone |
| `tests/test_engine.py` | Cada demanda va a su capítulo; sin capítulos implementados todo es `INCOMPLETE` y nunca hay capacidad |
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

Ejemplos del AISI Cold-Formed Steel Design Manual (±1 %) y cargas críticas de CUFSM, en
`docs/design-examples.md` a partir de M1. Sirven para contrastar; no reemplazan al oráculo.

## Reglas

- No declarar validación normativa a partir de pruebas que comparan el motor consigo mismo.
- Un dominio sin datos o sin decisión se bloquea (`INCOMPLETE`); nunca se supone un valor.
- Las salidas generadas (`results/`, temporales) no se versionan.
