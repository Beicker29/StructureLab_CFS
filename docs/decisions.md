# Decisiones de proyecto

Decisiones que AISI S100-24 no resuelve por sí sola y que fijan el diseño del repositorio.
Estado: **Confirmada** (el usuario la aprobó) o **Propuesta** (recomendación vigente hasta que
el usuario la confirme o cambie). Las decisiones de cada capítulo van en `docs/chapter-<x>.md`.

| Id | Pregunta | Decisión | Estado |
| --- | --- | --- | --- |
| DC-0 | Nombre del repositorio y del paquete | Repositorio `StructureLab_CFS` (distribución `structurelab-cfs`), paquete `cfs_design` | Confirmada (2026-11-03) |
| DC-1 | Métodos de resistencia | Se implementan los dos: DSM y EWM. En el JSON, `method`: `DSM` (por defecto) o `EWM` calculan solo ese método; `both` calcula los dos y reporta el resultado de cada uno (una comprobación por método y demanda). El `status` y el `ratio` agregados salen del método más desfavorable: `INCOMPLETE` si alguno lo es, `FAIL` si alguno falla, `ratio` máximo | Confirmada (2026-11-03) |
| DC-2 | Origen de las cargas críticas elásticas | Apéndice 2.3 analítico en el núcleo; franjas finitas (pyCUFSM) como extra opcional `[fsm]`. Con FSM, longitudes de semionda dadas por el usuario o mínimos de la curva de firma; sin mínimo claro → `INCOMPLETE` | Propuesta |
| DC-3 | Dimensiones de entrada | Exteriores (como catálogos comerciales y el Manual AISI); la línea media se deriva y se reporta | Propuesta |
| DC-4 | Esquinas | Redondeadas en las propiedades; el oráculo verifica también esquinas rectas como control | Propuesta |
| DC-5 | Miembros fuera de la Tabla B4.1-1 | `INCOMPLETE` con la variable y el límite violados; B4.2 fuera de alcance | Propuesta |
| DC-6 | Aumento por trabajo en frío (A3.3.2) | Desactivado; opción explícita en un hito posterior | Propuesta |
| DC-7 | Catálogo de perfiles | Excel versionado solo con dimensiones; primero los perfiles de los ejemplos del Manual, luego el catálogo comercial colombiano | Propuesta |
| DC-8 | Origen de Fu | S100-24 (Tabla A3.1.1-1) da Fy pero no Fu. Fu se transcribe de cada norma ASTM con su referencia; mientras falte, `Materiales.xlsx` lo deja vacío y lo que requiera Fu queda `INCOMPLETE` | Propuesta |
