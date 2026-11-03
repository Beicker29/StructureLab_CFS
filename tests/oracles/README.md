# Oráculos independientes

Un archivo por capítulo (`chapter_e.py`, `appendix_2.py`, `sections.py`…), escrito desde
AISI S100-24 en Decimal (50 dígitos), con sus propias escalas de unidades y **sin importar
`cfs_design`**. Al ejecutarse regenera `tests/fixtures/<nombre>/reference.json`, que las
pruebas consumen congelado. La CI vuelve a correrlos y exige que las referencias no cambien.

El primero llega en M1 (`sections.py`). Los archivos que empiezan por `_` son utilidades
compartidas y la CI no los ejecuta.
