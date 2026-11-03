---
description: Corre la verificación completa como la CI
---
Ejecuta y reporta cada comando con su resultado real:

1. `python -m ruff check .`
2. `python -m mypy`
3. `python -m pytest -q`
4. Cada `tests/oracles/*.py` y luego `git diff --exit-code -- tests/fixtures`.

Si algo falla, explica la causa; no cambies valores de referencia para que pase.
