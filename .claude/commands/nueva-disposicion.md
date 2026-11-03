---
description: Añade o modifica una disposición de S100-24 siguiendo los pasos de docs/architecture.md
argument-hint: <sección, p. ej. E4>
---
Disposición $ARGUMENTS de AISI S100-24. Sigue "Cómo añadir o modificar una disposición" de
docs/architecture.md, en orden:

1. Lee la sección en el PDF; anota edición, ecuación, página, condiciones y unidades.
2. Pide al subagente revisor-normativo los casos del oráculo independiente, sin mostrarle el código.
3. Fórmula pura en codes/aisi_s100_24/, devolviendo el id de ecuación.
4. Selección en domain/; datos o decisión faltante → error estructurado (INCOMPLETE).
5. Si cambia lo obligatorio, actualiza domain/coverage.py desde el texto normativo.
6. Regenera la referencia del oráculo, corre /verificar y actualiza docs/chapter-<x>.md.
